import os
from flask import Blueprint, render_template, g, jsonify, redirect, url_for
from utils.auth import get_current_user, login_required
from utils.trial import get_trial_status
from database import get_db

bp = Blueprint('dashboard', __name__)


@bp.route('/tour/completar', methods=['POST'])
@login_required
def tour_completar():
    """Marca el tour interactivo de onboarding (spotlight, static/js/tour.js)
    como terminado — se llama tanto al completar el último paso (Guardar
    presupuesto, paso 8) como al saltearlo en cualquier momento (cerrar el
    popover con la X). En ambos casos no debe volver a mostrarse. Pedido de
    Daniel 02/08/2026, contexto: 45 de 140 usuarios vencieron la prueba sin
    convertir nunca."""
    db = get_db()
    db.execute("UPDATE users SET tour_completado=1 WHERE id=?", (g.user['id'],))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@bp.route('/instalar-app/visto', methods=['POST'])
@login_required
def instalar_visto():
    """Marca que ya se le ofreció (una vez) el prompt automático de
    "Instalar app" a este usuario -- pedido de Daniel 04/08/2026 (cont. 20).
    Se llama apenas se INTENTA mostrarlo (ver templates/base.html), no
    importa si terminó instalando o cancelando -- es un solo empujón, no
    insiste. Mismo patrón que tour_completar() de acá arriba."""
    db = get_db()
    db.execute("UPDATE users SET instalar_prompt_visto=1 WHERE id=?", (g.user['id'],))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@bp.route('/')
def index():
    user = get_current_user()
    if not user:
        return render_template('landing.html')
    g.user = user
    db = get_db()
    borradores = db.execute(
        "SELECT * FROM presupuestos WHERE user_id=? AND status='borrador' ORDER BY updated_at DESC",
        (g.user['id'],)
    ).fetchall()
    presupuestos = db.execute(
        "SELECT * FROM presupuestos WHERE user_id=? AND status='completo' ORDER BY created_at DESC LIMIT 20",
        (g.user['id'],)
    ).fetchall()

    # Prueba gratis (06/07/2026): estado para el banner persistente + cartel
    # de bienvenida una sola vez (primer login después de registrarse).
    trial = get_trial_status(g.user)
    mostrar_bienvenida_trial = False
    if trial['es_trial'] and not g.user['trial_visto']:
        mostrar_bienvenida_trial = True
        db.execute("UPDATE users SET trial_visto=1 WHERE id=?", (g.user['id'],))
        db.commit()

    db.close()
    return render_template('dashboard.html',
                           presupuestos=presupuestos,
                           borradores=borradores,
                           user=g.user,
                           trial=trial,
                           mostrar_bienvenida_trial=mostrar_bienvenida_trial)


@bp.route('/prueba-terminada')
@login_required
def trial_vencido():
    trial = get_trial_status(g.user)
    if not trial['vencido']:
        return redirect(url_for('dashboard.index'))
    return render_template('trial_vencido.html', user=g.user, trial=trial)


# Eliminado 06/08/2026, pedido de Daniel: la ruta POST /inscripcion (+
# _enviar_notificacion) alimentaba el modal viejo de "Inscripción" de la
# landing -- ese modal ya se había sacado de templates/landing.html el
# 08/07/2026 (todos los botones "Probá gratis" apuntan directo a /registro
# desde entonces, ver comentario ahí). Sin ningún <form>/fetch en ningún
# template apuntando acá, esta ruta llevaba casi un mes recibiendo cero
# requests reales -- confirmado con un grep de todo el proyecto antes de
# borrar (no queda ninguna referencia activa a "/inscripcion" ni a
# "modalInscripcion"). La tabla `leads` y la pantalla admin.leads (ya sin
# link en el menú, ver bloque anterior) se dejan intactas -- ahí quedan los
# 7 registros viejos de cuando el modal SÍ estaba activo, por si hace falta
# consultarlos.
