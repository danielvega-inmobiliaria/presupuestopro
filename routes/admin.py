import json
import os
import urllib.request
from datetime import date, timedelta
from flask import Blueprint, render_template, render_template_string, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash
from utils.auth import admin_required
from utils.calculations import PAISES
from utils.normalizacion import PROVINCIAS_AR
from database import get_db, recalcular_precio_mo_ars

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@admin_required
def dashboard():
    db = get_db()
    stats = {
        'total_users':   db.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=0").fetchone()['c'],
        'activos':       db.execute("SELECT COUNT(*) as c FROM users WHERE active=1 AND is_admin=0").fetchone()['c'],
        'vencidos':      db.execute("SELECT COUNT(*) as c FROM users WHERE subscription_expires < date('now') AND is_admin=0").fetchone()['c'],
        'presupuestos':  db.execute("SELECT COUNT(*) as c FROM presupuestos").fetchone()['c'],
        'mensajes_nuevos': db.execute("SELECT COUNT(*) as c FROM contactos WHERE leido=0").fetchone()['c'],
        'sugerencias_nuevas': db.execute("SELECT COUNT(*) as c FROM sugerencias WHERE leido=0").fetchone()['c'],
        # Fix 08/07/2026: badge de inscriptos nuevos — el botón "Inscriptos"
        # ya existía en el dashboard pero sin ningún contador, así que un
        # inscripto nuevo (ej. Ricardo Jordan) pasaba desapercibido salvo que
        # Daniel entrara a revisar la lista sin motivo aparente.
        'leads_nuevos': db.execute("SELECT COUNT(*) as c FROM leads WHERE estado='nuevo'").fetchone()['c'],
    }
    proximos = db.execute(
        "SELECT * FROM users WHERE subscription_expires >= date('now') AND is_admin=0 ORDER BY subscription_expires LIMIT 5"
    ).fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats, proximos=proximos, user=g.user)

# USUARIOS
@bp.route('/usuarios')
@admin_required
def usuarios():
    """Fix 05/07/2026: agregado conteo de presupuestos completos/borradores y
    consultas de Costo/m2 por usuario, + filtros por localidad/provincia/pais
    (pedido de Daniel para tener a mano el uso real de cada usuario)."""
    f_ciudad    = (request.args.get('f_ciudad') or '').strip()
    f_provincia = (request.args.get('f_provincia') or '').strip()
    f_pais      = (request.args.get('f_pais') or '').strip()

    where = ["is_admin=0"]
    params = []
    if f_ciudad:
        where.append("ciudad LIKE ?")
        params.append(f"%{f_ciudad}%")
    if f_provincia:
        # Fix 10/07/2026: provincia ya es lista cerrada (select) — match exacto,
        # no LIKE. Con LIKE, "Buenos Aires" también traía a los de "Ciudad
        # Autónoma de Buenos Aires" por ser substring.
        where.append("provincia = ?")
        params.append(f_provincia)
    if f_pais:
        where.append("pais = ?")
        params.append(f_pais)

    db = get_db()
    users = db.execute(
        f"""SELECT u.*,
                   (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='completo') AS n_presupuestos,
                   (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='borrador')  AS n_borradores,
                   (SELECT COUNT(*) FROM costo_m2_consultas c WHERE c.user_id=u.id)                    AS n_costo_m2
            FROM users u
            WHERE {' AND '.join(where)}
            ORDER BY u.created_at DESC""",
        params
    ).fetchall()

    # Fix 10/07/2026 (pedido de Daniel): al filtrar por localidad, mostrar
    # automáticamente también el total de esa provincia y ese país (niveles
    # más amplios), sin que haga falta ir tocando los otros filtros a mano.
    # Si filtra por provincia, muestra el total del país. Si filtra por país,
    # no hace falta nada más — ese total ya es el badge "Usuarios N" de arriba.
    # Cada nivel se cuenta de forma independiente (no combinado con los demás
    # filtros activos), porque la idea es "cuánta gente hay en esa provincia
    # en total", no "cuánta gente de esa provincia además cumple los otros
    # filtros puestos".
    breakdown = []
    if f_ciudad:
        provincias_de_ciudad = db.execute(
            "SELECT DISTINCT provincia FROM users WHERE is_admin=0 AND ciudad LIKE ? AND provincia != ''",
            (f"%{f_ciudad}%",)
        ).fetchall()
        for row in provincias_de_ciudad:
            prov = row['provincia']
            c = db.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=0 AND provincia=?", (prov,)).fetchone()['c']
            breakdown.append({'nivel': 'Provincia', 'nombre': prov, 'cantidad': c})
        paises_de_ciudad = db.execute(
            "SELECT DISTINCT pais FROM users WHERE is_admin=0 AND ciudad LIKE ? AND pais != ''",
            (f"%{f_ciudad}%",)
        ).fetchall()
        for row in paises_de_ciudad:
            p = row['pais']
            c = db.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=0 AND pais=?", (p,)).fetchone()['c']
            breakdown.append({'nivel': 'País', 'nombre': PAISES.get(p, {}).get('nombre', p), 'cantidad': c})
    elif f_provincia:
        paises_de_provincia = db.execute(
            "SELECT DISTINCT pais FROM users WHERE is_admin=0 AND provincia=? AND pais != ''",
            (f_provincia,)
        ).fetchall()
        for row in paises_de_provincia:
            p = row['pais']
            c = db.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=0 AND pais=?", (p,)).fetchone()['c']
            breakdown.append({'nivel': 'País', 'nombre': PAISES.get(p, {}).get('nombre', p), 'cantidad': c})

    # Fix 10/07/2026: antes esto era un DISTINCT de lo cargado en users.provincia
    # (texto libre, con duplicados). Provincia ahora es lista cerrada — se
    # usa PROVINCIAS_AR para que el filtro sea un <select> real, igual que País.
    # Localidad sigue siendo abierta, pero ahora hay tabla `localidades`
    # autoalimentada (fix de hoy) para ofrecer autocompletado real, no el
    # autocompletado del navegador que Daniel vio antes.
    localidades_lista = [r['nombre_display'] for r in db.execute(
        "SELECT nombre_display FROM localidades WHERE merged_en='' ORDER BY veces_usada DESC"
    ).fetchall()]
    db.close()

    return render_template('admin/usuarios.html', users=users, user=g.user,
                            provincias=PROVINCIAS_AR, localidades_lista=localidades_lista, paises=PAISES,
                            f_ciudad=f_ciudad, f_provincia=f_provincia, f_pais=f_pais,
                            breakdown=breakdown)


@bp.route('/localidades')
@admin_required
def localidades():
    db = get_db()
    filas = db.execute("SELECT * FROM localidades ORDER BY merged_en != '', veces_usada DESC").fetchall()
    # Para poder mostrar "fusionada en: <nombre>" en vez de solo la clave.
    por_clave = {f['clave_normalizada']: f for f in filas}
    db.close()
    return render_template('admin/localidades.html', filas=filas, por_clave=por_clave, user=g.user)


@bp.route('/localidades/<int:lid>/renombrar', methods=['POST'])
@admin_required
def localidad_renombrar(lid):
    nuevo_nombre = (request.form.get('nombre_display') or '').strip()
    if not nuevo_nombre:
        flash('El nombre no puede quedar vacío.', 'error')
        return redirect(url_for('admin.localidades'))
    db = get_db()
    fila = db.execute("SELECT * FROM localidades WHERE id=?", (lid,)).fetchone()
    if not fila:
        db.close()
        flash('No se encontró esa localidad.', 'error')
        return redirect(url_for('admin.localidades'))
    # Los usuarios que ya tenían la grafía vieja se actualizan también, para
    # que no quede desincronizado lo que ve Daniel acá vs. lo que dice cada
    # usuario en Admin > Usuarios.
    db.execute("UPDATE users SET ciudad=? WHERE ciudad=?", (nuevo_nombre, fila['nombre_display']))
    db.execute("UPDATE localidades SET nombre_display=? WHERE id=?", (nuevo_nombre, lid))
    db.commit()
    db.close()
    flash(f'Renombrada a "{nuevo_nombre}".', 'success')
    return redirect(url_for('admin.localidades'))


@bp.route('/localidades/fusionar', methods=['POST'])
@admin_required
def localidad_fusionar():
    """Fusiona `origen_id` hacia `destino_id`: todos los usuarios que tenían
    la grafía de origen pasan a la de destino, y de acá en más cualquiera que
    se registre escribiendo la clave de origen también cae en destino (ver
    routes/landing.py::_guardar_localidad, sigue la cadena `merged_en`)."""
    try:
        origen_id = int(request.form.get('origen_id'))
        destino_id = int(request.form.get('destino_id'))
    except (TypeError, ValueError):
        flash('Elegí las dos localidades a fusionar.', 'error')
        return redirect(url_for('admin.localidades'))
    if origen_id == destino_id:
        flash('Elegí dos localidades distintas.', 'error')
        return redirect(url_for('admin.localidades'))

    db = get_db()
    origen = db.execute("SELECT * FROM localidades WHERE id=?", (origen_id,)).fetchone()
    destino = db.execute("SELECT * FROM localidades WHERE id=?", (destino_id,)).fetchone()
    if not origen or not destino:
        db.close()
        flash('No se encontró alguna de las dos localidades.', 'error')
        return redirect(url_for('admin.localidades'))

    db.execute("UPDATE users SET ciudad=? WHERE ciudad=?", (destino['nombre_display'], origen['nombre_display']))
    db.execute(
        "UPDATE localidades SET merged_en=?, veces_usada=0 WHERE id=?",
        (destino['clave_normalizada'], origen_id)
    )
    db.execute(
        "UPDATE localidades SET veces_usada = veces_usada + ? WHERE id=?",
        (origen['veces_usada'], destino_id)
    )
    db.commit()
    db.close()
    flash(f'"{origen["nombre_display"]}" fusionada en "{destino["nombre_display"]}".', 'success')
    return redirect(url_for('admin.localidades'))

@bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@admin_required
def usuario_nuevo():
    if request.method == 'POST':
        email     = request.form.get('email', '').strip().lower()
        nombre    = request.form.get('nombre', '')
        telefono  = request.form.get('telefono', '').strip()
        ciudad    = request.form.get('ciudad', '').strip()
        provincia = request.form.get('provincia', '').strip()
        password  = request.form.get('password', '')
        pais      = request.form.get('pais', 'AR')
        vence     = request.form.get('subscription_expires', '')
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (email, password_hash, nombre, telefono, ciudad, provincia, pais, active, subscription_expires) VALUES (?,?,?,?,?,?,?,1,?)",
                (email, generate_password_hash(password), nombre, telefono, ciudad, provincia, pais, vence or None)
            )
            db.commit()
            flash(f'Usuario {email} creado.', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        finally:
            db.close()
        return redirect(url_for('admin.usuarios'))
    return render_template('admin/usuario_form.html', u=None, user=g.user,
                           now_date=date.today(), timedelta=timedelta)

@bp.route('/usuarios/<int:uid>/editar', methods=['GET', 'POST'])
@admin_required
def usuario_editar(uid):
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close(); return redirect(url_for('admin.usuarios'))

    if request.method == 'POST':
        nombre    = request.form.get('nombre', '')
        telefono  = request.form.get('telefono', '').strip()
        ciudad    = request.form.get('ciudad', '').strip()
        provincia = request.form.get('provincia', '').strip()
        pais      = request.form.get('pais', 'AR')
        active    = 1 if request.form.get('active') else 0
        vence     = request.form.get('subscription_expires', '')
        new_pw    = request.form.get('password', '').strip()
        if new_pw:
            db.execute(
                "UPDATE users SET nombre=?, telefono=?, ciudad=?, provincia=?, pais=?, active=?, subscription_expires=?, password_hash=? WHERE id=?",
                (nombre, telefono, ciudad, provincia, pais, active, vence or None, generate_password_hash(new_pw), uid)
            )
        else:
            db.execute(
                "UPDATE users SET nombre=?, telefono=?, ciudad=?, provincia=?, pais=?, active=?, subscription_expires=? WHERE id=?",
                (nombre, telefono, ciudad, provincia, pais, active, vence or None, uid)
            )
        if not active:
            db.execute("UPDATE users SET session_token=NULL WHERE id=?", (uid,))
        db.commit()
        flash('Usuario actualizado.', 'success')
        db.close()
        return redirect(url_for('admin.usuarios'))

    db.close()
    return render_template('admin/usuario_form.html', u=u, user=g.user)

@bp.route('/usuarios/<int:uid>/eliminar', methods=['POST'])
@admin_required
def usuario_eliminar(uid):
    """Borra un usuario y todo lo asociado. Agregado 10/07/2026 — pedido de
    Daniel para poder limpiar las cuentas ficticias/de prueba que va cargando
    mientras testea el flujo de validación de cuenta, sin tener que pedirle
    a un dev que lo haga a mano en la base. Irreversible: borra en cascada
    presupuestos, suscripciones, consultas de costo/m2, sugerencias, perfil
    de empresa, tokens de reset de password y códigos de verificación del
    usuario, antes de borrar la fila de users."""
    db = get_db()
    u = db.execute("SELECT email, nombre, is_admin FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('admin.usuarios'))
    if u['is_admin']:
        db.close()
        flash('No se puede eliminar una cuenta de administrador desde acá.', 'error')
        return redirect(url_for('admin.usuarios'))

    for tabla in ('presupuestos', 'suscripciones', 'costo_m2_consultas', 'sugerencias',
                  'empresa_perfil', 'password_reset_tokens', 'verificacion_codigos'):
        db.execute(f"DELETE FROM {tabla} WHERE user_id=?", (uid,))
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    db.close()
    flash(f"Usuario {u['email']} eliminado.", 'success')
    return redirect(url_for('admin.usuarios'))


@bp.route('/usuarios/<int:uid>/enviar-activacion', methods=['POST'])
@admin_required
def usuario_enviar_activacion(uid):
    db = get_db()
    u = db.execute("SELECT email, nombre, subscription_expires FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('admin.usuarios'))

    # Si no tiene fecha de vencimiento, asignar hoy + 30 días y activar
    exp_str = u['subscription_expires']
    if not exp_str:
        exp_str = (date.today() + timedelta(days=30)).isoformat()
        db.execute(
            "UPDATE users SET active=1, subscription_expires=? WHERE id=?",
            (exp_str, uid)
        )
        db.commit()

    db.close()

    from routes.pagos import _enviar_email_activacion
    from datetime import datetime
    exp_display = exp_str
    try:
        exp_display = datetime.strptime(exp_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except Exception:
        pass

    ok = _enviar_email_activacion(
        user_email=u['email'],
        user_nombre=u['nombre'],
        fecha_vencimiento=exp_display,
    )
    if ok:
        flash(f'Email de activacion enviado a {u["email"]}.', 'success')
    else:
        flash('No se pudo enviar el email (revisar RESEND_API_KEY).', 'error')
    return redirect(url_for('admin.usuarios'))


# CONTACTOS
@bp.route('/contactos')
@admin_required
def contactos():
    db = get_db()
    msgs = db.execute("SELECT * FROM contactos ORDER BY created_at DESC").fetchall()
    db.execute("UPDATE contactos SET leido=1 WHERE leido=0")
    db.commit()
    db.close()
    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mensajes - Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  .card-nuevo  { border-left: 4px solid #0d6efd; }
  .card-leido  { border-left: 4px solid #dee2e6; }
  .card-contest{ border-left: 4px solid #198754; }
</style>
</head><body class="bg-light">
<div class="container py-4" style="max-width:760px">
  <a href="/admin/" class="btn btn-outline-secondary btn-sm mb-3">Volver</a>
  <h4 class="fw-bold mb-1">Mensajes de contacto</h4>
  <p class="text-muted small mb-3">
    <span class="badge bg-primary">{{ msgs|length }} total</span>
    <span class="badge bg-success ms-1">{{ msgs|selectattr('contestado','equalto',1)|list|length }} contestados</span>
    <span class="badge bg-warning text-dark ms-1">{{ msgs|selectattr('leido','equalto',0)|list|length }} nuevos</span>
  </p>
  {% if not msgs %}<p class="text-muted">No hay mensajes aun.</p>{% endif %}
  {% for m in msgs %}
  {% set card_class = 'card-contest' if m.contestado else ('card-nuevo' if not m.leido else 'card-leido') %}
  <div class="card mb-3 shadow-sm {{ card_class }}">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-1">
        <div>
          <strong>{{ m.nombre }} {{ m.apellido or '' }}</strong>
          {% if not m.leido %}<span class="badge bg-primary ms-2">NUEVO</span>{% endif %}
          {% if m.contestado %}<span class="badge bg-success ms-2">Contestado</span>{% endif %}
        </div>
        <small class="text-muted text-nowrap ms-2">{{ m.created_at[:16] }}</small>
      </div>
      <div class="text-muted small mb-2">
        {% if m.email %}<a href="mailto:{{ m.email }}">{{ m.email }}</a>&nbsp;{% endif %}
        {% if m.telefono %}{{ m.telefono }}&nbsp;{% endif %}
        {% if m.ciudad or m.provincia %}{{ m.ciudad or '' }}{% if m.ciudad and m.provincia %}, {% endif %}{{ m.provincia or '' }}{% endif %}
      </div>
      <p class="mb-3 border rounded p-2 bg-white">{{ m.mensaje }}</p>
      <div class="d-flex gap-2 flex-wrap">
        {% if m.email %}
        <a href="mailto:{{ m.email }}" class="btn btn-sm btn-outline-primary">Responder</a>
        {% endif %}
        <form method="POST" action="/admin/contactos/{{ m.id }}/contestado" style="display:inline">
          <button type="submit" class="btn btn-sm {{ 'btn-success' if m.contestado else 'btn-outline-success' }}">
            {% if m.contestado %}Contestado{% else %}Marcar contestado{% endif %}
          </button>
        </form>
      </div>
    </div>
  </div>
  {% endfor %}
</div></body></html>
""", msgs=msgs, user=g.user)

@bp.route('/contactos/<int:mid>/contestado', methods=['POST'])
@admin_required
def contacto_contestado(mid):
    db = get_db()
    row = db.execute("SELECT contestado FROM contactos WHERE id=?", (mid,)).fetchone()
    if row:
        nuevo = 0 if row['contestado'] else 1
        db.execute("UPDATE contactos SET contestado=? WHERE id=?", (nuevo, mid))
        db.commit()
    db.close()
    return redirect(url_for('admin.contactos'))

# SUGERENCIAS (05/07/2026)
@bp.route('/sugerencias')
@admin_required
def sugerencias():
    db = get_db()
    msgs = db.execute("""
        SELECT s.*, u.nombre as user_nombre, u.email as user_email
        FROM sugerencias s LEFT JOIN users u ON u.id = s.user_id
        ORDER BY s.created_at DESC
    """).fetchall()
    db.execute("UPDATE sugerencias SET leido=1 WHERE leido=0")
    db.commit()
    db.close()
    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sugerencias - Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  .card-nuevo  { border-left: 4px solid #0d6efd; }
  .card-leido  { border-left: 4px solid #dee2e6; }
  .card-resp   { border-left: 4px solid #198754; }
</style>
</head><body class="bg-light">
<div class="container py-4" style="max-width:760px">
  <a href="/admin/" class="btn btn-outline-secondary btn-sm mb-3">Volver</a>
  <h4 class="fw-bold mb-1">Sugerencias de usuarios</h4>
  <p class="text-muted small mb-3">
    <span class="badge bg-primary">{{ msgs|length }} total</span>
    <span class="badge bg-success ms-1">{{ msgs|selectattr('respondida','equalto',1)|list|length }} respondidas</span>
    <span class="badge bg-warning text-dark ms-1">{{ msgs|selectattr('leido','equalto',0)|list|length }} nuevas</span>
  </p>
  {% if not msgs %}<p class="text-muted">No hay sugerencias aun.</p>{% endif %}
  {% for m in msgs %}
  {% set card_class = 'card-resp' if m.respondida else ('card-nuevo' if not m.leido else 'card-leido') %}
  <div class="card mb-3 shadow-sm {{ card_class }}">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-1">
        <div>
          <strong>{{ m.user_nombre or m.user_email or 'Usuario #' ~ m.user_id }}</strong>
          {% if not m.leido %}<span class="badge bg-primary ms-2">NUEVA</span>{% endif %}
          {% if m.respondida %}<span class="badge bg-success ms-2">Respondida</span>{% endif %}
        </div>
        <small class="text-muted text-nowrap ms-2">{{ m.created_at[:16] }}</small>
      </div>
      <div class="text-muted small mb-2">
        {% if m.user_email %}<a href="mailto:{{ m.user_email }}">{{ m.user_email }}</a>{% endif %}
      </div>
      <p class="mb-3 border rounded p-2 bg-white">{{ m.mensaje }}</p>
      <div class="d-flex gap-2 flex-wrap">
        {% if m.user_email %}
        <a href="mailto:{{ m.user_email }}" class="btn btn-sm btn-outline-primary">Responder</a>
        {% endif %}
        <form method="POST" action="/admin/sugerencias/{{ m.id }}/respondida" style="display:inline">
          <button type="submit" class="btn btn-sm {{ 'btn-success' if m.respondida else 'btn-outline-success' }}">
            {% if m.respondida %}Respondida{% else %}Marcar respondida{% endif %}
          </button>
        </form>
      </div>
    </div>
  </div>
  {% endfor %}
</div></body></html>
""", msgs=msgs, user=g.user)

@bp.route('/sugerencias/<int:mid>/respondida', methods=['POST'])
@admin_required
def sugerencia_respondida(mid):
    db = get_db()
    row = db.execute("SELECT respondida FROM sugerencias WHERE id=?", (mid,)).fetchone()
    if row:
        nuevo = 0 if row['respondida'] else 1
        db.execute("UPDATE sugerencias SET respondida=? WHERE id=?", (nuevo, mid))
        db.commit()
    db.close()
    return redirect(url_for('admin.sugerencias'))

# PRECIOS MATERIALES
_LISTA_PRECIOS = [
    ('CORRALÓN - Áridos y Cemento', [
        'Cemento portland bolsas', 'Cemento Albañilería', 'Cal hidráulica hidratada',
        'Cal aérea Milagro', 'Hidrófugo', 'Arena común', 'Tierra Colorada',
        'Piedra Partida (Calc. ó Granít.)', 'Granza (mediana)', 'Hormigon elaborado colado',
        'Perlitas Telgopor (75 Lts)',
    ]),
    ('CORRALÓN - Ladrillos y Mampostería', [
        'Ladrillos comunes', 'Ladrillos vista',
        'Ladrillo hueco 8x18x33cm', 'Ladrillo hueco 12X18X33cm',
        'Ladrillo hueco 18X18X33cm', 'Ladrillo hueco Portante 12x18x33cm',
        'Ladrillo hueco Portante 18x18x33cm',
    ]),
    ('CORRALÓN - Hierros y Ferretería', [
        'Hierro redondo d=10mm', 'Alambre negro',
        'Clavos 2"', 'Clavos 2" 1/2', 'Clavos 3"', 'Clavos 4"',
    ]),
    ('CORRALÓN - Viguetas', [
        'Viga Vipret 4m.', 'Ladrillo Telgopor 12*38*1m',
    ]),
    ('Maderera', [
        'Palito 1"x1"', 'Metal desplegado', 'Saligna   1"x2"', 'Saligna 1"x4"',
        'Saligna 3"x3"', 'Pino encofrado 1"', 'Tirantes 2x6', 'Pino tabla machimbre',
        'Escurridores 1/2 x 2', 'Issolant', 'Clavadores 2 x 2', 'Chapas Techo',
        'Tornillo c/arand goma', 'Chapas Cerco', 'Zocalo de madera', 'Tarugo 6',
        'Tornillo',
    ]),
    ('Instalaciones - Electricas', [
        'Cano Corrugado 1"', 'Cano Corrugado 3/4"', 'Cajas Metalicas',
        'Cable 2,5 mm', 'Cable 1,5 mm',
    ]),
    ('Instalaciones - Sanitarias', [
        'Cano Awaduct 110', 'Cano Awaduct 63', 'Cano Awaduct 50',
        'Cano Awaduct 40', 'Accesorios Desagues',
    ]),
    ('Instalaciones - Agua F/C', [
        'Cano TF 25', 'Cano TF 20', 'Accesorios TF', 'Llaves de Paso Agua',
    ]),
    ('Instalaciones - Gas', [
        'Cano Epoxi 3/4', 'Cano epoxi 1/2', 'Accesorios Gas', 'Llaves de Paso Gas',
    ]),
    ('Revestimientos y Pisos', [
        'Klaukol', 'Pastina',
        'Rvto.ceramico 1', 'Rvto.ceramico 2', 'Rvto.ceramico 3 (porcellanato)',
        'Piso ceramico 1', 'Piso ceramico 2', 'Piso ceramico 3 (porcellanato)',
        'Mosaico calcareo', 'Loseta cemento 60x40cm', 'Baldosa ceramica azotea',
        'Zocalo ceramico 1', 'Zocalo ceramico 2', 'Zocalo ceramico 3 (Porcellanato)',
    ]),
    ('Pinturas y Terminaciones', [
        'Pintura latex exterior', 'Pintura latex interior', 'Pintura latex cielos',
        'Esmalte albalux', 'Pintura especial 1', 'Pintura especial 2',
        'Pintura satinol', 'Color pintura cal', 'Enduido sintetico',
    ]),
    ('Materiales Especiales', [
        'Super Iggam', 'Salpicrete', 'Rev Text.', 'Fondo Base',
    ]),
    ('Servicios y Varios', [
        'Transporte material suelto', 'Martillo neumatico',
    ]),
]

@bp.route('/precios')
@admin_required
def precios():
    db = get_db()
    rows = db.execute(
        "SELECT sub_nombre, MAX(precio_ars) as precio_ars "
        "FROM analisis_sub WHERE es_material=1 GROUP BY sub_nombre"
    ).fetchall()
    cfg_jo = db.execute("SELECT valor FROM config WHERE clave='jornal_oficial_dia'").fetchone()
    cfg_ja = db.execute("SELECT valor FROM config WHERE clave='jornal_ayudante_dia'").fetchone()
    db.close()
    precios_dict = {r['sub_nombre']: r['precio_ars'] for r in rows}

    jornal_oficial_dia  = int(float(cfg_jo['valor'])) if cfg_jo else 80000
    jornal_ayudante_dia = int(float(cfg_ja['valor'])) if cfg_ja else 40000

    # ⚠️ Cemento portland, Cemento Albañilería, Cal aérea, Klaukol, Salpicrete y
    # Super Iggam YA están en analisis_sub como precio por bolsa (migraciones 2j/2k/2l
    # en database.py). No van en este diccionario: si se los vuelve a multiplicar acá
    # por el factor de bolsa queda una DOBLE CONVERSIÓN y el precio comercial sale
    # 25-30 veces más caro de lo real (mismo bug que había en paso6_materiales).
    COMERCIAL = {
        'cal hidr':     (25,   'bolsa 25kg'),   # sin migrar — sigue en $/kg
        'cal viv':      (25,   'bolsa 25kg'),   # sin migrar — sigue en $/kg
        'perlitas':     (75,   'bolsa 75Lt'),   # sin migrar — sigue en $/lt
        'revear':       (30,   'balde 30kg'),   # sin migrar — sigue en $/kg
        'hierro':       (7.44, 'barra 12m'),    # sin migrar — sigue en $/kg
        'pastina':      (5,    'bolsa 5kg'),    # sin migrar — sigue en $/kg
    }

    def _info_comercial(nombre):
        n = nombre.lower()
        for kw, (factor, unidad) in COMERCIAL.items():
            if kw in n:
                return factor, unidad
        return 1, ''

    sectores = []
    for sector, nombres in _LISTA_PRECIOS:
        items = []
        for n in nombres:
            precio_calc = precios_dict.get(n, 0)
            factor, unidad_com = _info_comercial(n)
            precio_com = round(precio_calc * factor) if factor != 1 else precio_calc
            items.append({
                'nombre':      n,
                'precio':      precio_calc,
                'precio_com':  precio_com,
                'factor':      factor,
                'unidad_com':  unidad_com,
            })
        sectores.append({'sector': sector, 'items': items})

    return render_template('admin/precios.html', sectores=sectores, user=g.user,
                           jornal_oficial_dia=jornal_oficial_dia,
                           jornal_ayudante_dia=jornal_ayudante_dia)

@bp.route('/precios/actualizar', methods=['POST'])
@admin_required
def precios_actualizar():
    db = get_db()
    actualizados = 0
    jornal_cambio = False
    for key, val in request.form.items():
        if key.startswith('calc_'):
            sub_nombre = key[5:]
            try:
                precio_ars = float(val)
                if precio_ars >= 0:
                    db.execute(
                        "UPDATE analisis_sub SET precio_ars=? WHERE sub_nombre=?",
                        (precio_ars, sub_nombre)
                    )
                    actualizados += 1
            except:
                pass
        elif key in ('jornal_oficial_dia', 'jornal_ayudante_dia'):
            try:
                valor = float(val)
                if valor > 0:
                    db.execute(
                        "INSERT OR REPLACE INTO config (clave, valor) VALUES (?, ?)",
                        (key, str(int(valor)))
                    )
                    actualizados += 1
                    jornal_cambio = True
            except:
                pass
    # Fix 07/07/2026: si se tocó el jornal, recalcular precio_mo_ars de TODOS
    # los ítems con los jornales nuevos — antes esta pantalla guardaba el
    # jornal en `config` pero nada volvía a leerlo, así que ningún ítem
    # cambiaba de costo de MO. Ver database.py::recalcular_precio_mo_ars.
    if jornal_cambio:
        n_mo = recalcular_precio_mo_ars(db)
        actualizados += n_mo
    db.commit()
    db.close()
    flash(f'Precios actualizados ({actualizados} ítems).', 'success')
    return redirect(url_for('admin.precios'))

# TIPOS DE CAMBIO
@bp.route('/tipos-cambio', methods=['GET', 'POST'])
@admin_required
def tipos_cambio():
    db = get_db()
    if request.method == 'POST':
        for key, val in request.form.items():
            if key.startswith('tasa_'):
                pais = key.replace('tasa_', '')
                try:
                    db.execute(
                        "UPDATE tipos_cambio SET tasa=?, updated_at=datetime('now', 'localtime') WHERE pais=?",
                        (float(val), pais)
                    )
                except:
                    pass
        db.commit()
        flash('Tipos de cambio actualizados.', 'success')
        db.close()
        return redirect(url_for('admin.tipos_cambio'))
    tcs = db.execute("SELECT * FROM tipos_cambio ORDER BY pais").fetchall()
    db.close()
    return render_template('admin/tipos_cambio.html', tcs=tcs, user=g.user)


@bp.route('/tipos-cambio/fetch-web')
@admin_required
def tipos_cambio_fetch():
    db = get_db()
    errores = []
    actualizados = []

    try:
        req = urllib.request.Request(
            'https://dolarapi.com/v1/dolares/oficial',
            headers={'User-Agent': 'PresupuestoPRO/1.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        tasa_ar = round(float(data.get('venta', 0)), 2)
        if tasa_ar > 0:
            db.execute("UPDATE tipos_cambio SET tasa=?, updated_at=datetime('now', 'localtime') WHERE pais='AR'",
                       (tasa_ar,))
            actualizados.append(f"ARS: {tasa_ar:.2f}")
    except Exception as e:
        errores.append(f"ARS: {e}")

    try:
        req2 = urllib.request.Request(
            'https://open.er-api.com/v6/latest/USD',
            headers={'User-Agent': 'PresupuestoPRO/1.0'}
        )
        with urllib.request.urlopen(req2, timeout=5) as r:
            rates = json.loads(r.read()).get('rates', {})
        mapa = {'CL': 'CLP', 'UY': 'UYU', 'BR': 'BRL', 'PY': 'PYG'}
        for pais, moneda in mapa.items():
            tasa = rates.get(moneda)
            if tasa:
                tasa_r = round(float(tasa), 2)
                db.execute(
                    "UPDATE tipos_cambio SET tasa=?, updated_at=datetime('now', 'localtime') WHERE pais=?",
                    (tasa_r, pais)
                )
                actualizados.append(f"{pais}: {tasa_r}")
    except Exception as e:
        errores.append(f"LATAM: {e}")

    db.commit()
    db.close()

    if actualizados:
        flash(f"Cotizaciones actualizadas: {', '.join(actualizados)}", 'success')
    if errores:
        flash(f"Errores: {'; '.join(errores)}", 'error')

    return redirect(url_for('admin.tipos_cambio'))


# RENDIMIENTOS
@bp.route('/rendimientos')
@admin_required
def rendimientos():
    db = get_db()
    items = db.execute("SELECT * FROM items_obra ORDER BY rubro_num, id").fetchall()
    db.close()
    from utils.calculations import RUBROS_DEFAULT
    return render_template('admin/rendimientos.html', items=items,
                           rubros=RUBROS_DEFAULT, user=g.user)

@bp.route('/rendimientos/actualizar', methods=['POST'])
@admin_required
def rendimientos_actualizar():
    db = get_db()
    for key, val in request.form.items():
        if key.startswith('hof_') or key.startswith('hay_'):
            tipo, iid = key.split('_', 1)
            try:
                if tipo == 'hof':
                    db.execute("UPDATE items_obra SET hof=? WHERE id=?", (float(val), int(iid)))
                else:
                    db.execute("UPDATE items_obra SET hay=? WHERE id=?", (float(val), int(iid)))
            except Exception:
                pass
    # Fix 07/07/2026: al cambiar HOF/HAY hay que recalcular precio_mo_ars con
    # esos valores nuevos (usando el jornal vigente en `config`) — antes
    # quedaba desactualizado hasta la próxima migración manual (ver bug
    # documentado en PROYECTO.md, sesión 04/07, y database.py::recalcular_precio_mo_ars).
    recalcular_precio_mo_ars(db)
    db.commit()
    db.close()
    flash('Rendimientos actualizados correctamente.', 'success')
    return redirect(url_for('admin.rendimientos'))


# FIX DB
@bp.route('/fix-db')
def fix_db():
    db = get_db()
    log = []
    items_borrar = [
        'Ayuda gremios y varios',
        'Rvto. marmol',
        'Ho.Ado. tanque (90-13)',
        'H.Elab. tanque (90-13)',
        'Cemento: revoque tanque',
    ]
    for nombre in items_borrar:
        r = db.execute("DELETE FROM items_obra WHERE nombre=?", (nombre,))
        if r.rowcount:
            log.append(f"DEL items_obra: {nombre}")

    r = db.execute("UPDATE items_obra SET precio_mo_ars=5000 WHERE id IN (97,98,99,100,101)")
    log.append(f"UPD pintura MO x{r.rowcount}")

    ceramicos = {82:11550, 83:11550, 84:21800, 87:4050, 88:4050, 92:14650, 93:14650}
    for iid, mo in ceramicos.items():
        db.execute("UPDATE items_obra SET precio_mo_ars=? WHERE id=?", (mo, iid))
    log.append(f"UPD ceramicos MO x{len(ceramicos)}")

    db.commit()
    cnt = db.execute("SELECT COUNT(*) FROM items_obra").fetchone()[0]
    db.close()
    log.append(f"VERIFY items_obra:{cnt}")
    from flask import jsonify
    return jsonify({'ok': True, 'cambios': log})


# CONFIGURACION
@bp.route('/configuracion', methods=['GET', 'POST'])
@admin_required
def configuracion():
    db = get_db()
    if request.method == 'POST':
        for clave in ('pct_gg', 'pct_impuestos'):
            val = request.form.get(clave)
            if val:
                db.execute(
                    "INSERT OR REPLACE INTO config (clave, valor) VALUES (?,?)",
                    (clave, val)
                )
        # Fix 10/07/2026: validación de cuenta (email/WhatsApp) — checkbox no
        # tildado no manda el campo en el form, por eso se chequea presencia
        # en vez de leer el valor.
        verificacion_val = '1' if request.form.get('verificacion_activa') == 'on' else '0'
        verificacion_previa = db.execute(
            "SELECT valor FROM config WHERE clave='verificacion_activa'"
        ).fetchone()
        se_esta_prendiendo = verificacion_val == '1' and (not verificacion_previa or verificacion_previa['valor'] != '1')
        db.execute(
            "INSERT OR REPLACE INTO config (clave, valor) VALUES ('verificacion_activa', ?)",
            (verificacion_val,)
        )
        # Fix 10/07/2026: al PRENDER el switch (no antes), se marca como
        # validado a cualquiera que ya tuviera cuenta y todavía no hubiera
        # validado — el bloqueo arranca a regir recién de acá para adelante,
        # nunca retroactivo a alguien que se registró antes de que el switch
        # estuviera prendido (Daniel lo pidió explícitamente 10/07/2026).
        if se_esta_prendiendo:
            n_grandfather = db.execute(
                "UPDATE users SET email_verificado=1, phone_verificado=1 "
                "WHERE metodo_verificacion != '' AND (email_verificado=0 OR phone_verificado=0)"
            ).rowcount
            if n_grandfather:
                print(f"[admin.configuracion] verificacion_activa prendida: "
                      f"{n_grandfather} cuenta(s) existente(s) marcadas como ya validadas (no retroactivo)")
        db.commit()
        db.close()
        if se_esta_prendiendo and n_grandfather:
            flash(f'Configuracion guardada. Validación activada — {n_grandfather} cuenta(s) que ya '
                  f'existían quedaron marcadas como validadas (no se les exige validar retroactivamente).',
                  'success')
        else:
            flash('Configuracion guardada.', 'success')
        return redirect(url_for('admin.dashboard'))
    cfg = {r['clave']: r['valor'] for r in db.execute("SELECT * FROM config").fetchall()}
    pendientes_validar = db.execute(
        "SELECT COUNT(*) c FROM users WHERE metodo_verificacion != '' "
        "AND ((metodo_verificacion='email' AND email_verificado=0) "
        "OR (metodo_verificacion='whatsapp' AND phone_verificado=0))"
    ).fetchone()['c']
    db.close()
    return render_template('admin/configuracion.html', cfg=cfg, user=g.user,
                           pendientes_validar=pendientes_validar)


# LEADS
@bp.route('/leads')
@admin_required
def leads():
    db = get_db()
    todos = db.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template('admin/leads.html', leads=todos, user=g.user)

@bp.route('/leads/<int:lid>/estado', methods=['POST'])
@admin_required
def lead_estado(lid):
    estado = request.form.get('estado', 'nuevo')
    notas  = request.form.get('notas', '')
    db = get_db()
    db.execute("UPDATE leads SET estado=?, notas=? WHERE id=?", (estado, notas, lid))
    db.commit()
    db.close()
    flash('Lead actualizado.', 'success')
    return redirect(url_for('admin.leads'))
