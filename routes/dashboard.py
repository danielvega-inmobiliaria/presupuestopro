import os
import resend
from flask import Blueprint, render_template, g, request, jsonify, redirect, url_for
from utils.auth import get_current_user, login_required
from utils.trial import get_trial_status
from database import get_db

bp = Blueprint('dashboard', __name__)


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


@bp.route('/inscripcion', methods=['POST'])
def inscripcion():
    data = request.get_json(silent=True) or {}
    nombre   = (data.get('nombre') or '').strip()
    apellido = (data.get('apellido') or '').strip()
    telefono = (data.get('telefono') or '').strip()
    email    = (data.get('email') or '').strip()
    ciudad   = (data.get('ciudad') or '').strip()
    provincia= (data.get('provincia') or '').strip()

    if not nombre or not apellido or not telefono:
        return jsonify({'ok': False, 'error': 'Datos incompletos'}), 400

    # Guardar en DB
    db = get_db()
    db.execute(
        "INSERT INTO leads (nombre, apellido, telefono, email, ciudad, provincia) VALUES (?,?,?,?,?,?)",
        (nombre, apellido, telefono, email, ciudad, provincia)
    )
    db.commit()
    db.close()

    # Notificar por email
    _enviar_notificacion(nombre, apellido, telefono, email, ciudad, provincia)

    return jsonify({'ok': True})


def _enviar_notificacion(nombre, apellido, telefono, email, ciudad, provincia):
    """Envía email de notificación al administrador cuando hay un nuevo inscripto."""
    api_key    = os.environ.get('RESEND_API_KEY')
    admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')

    if not api_key:
        print(f"[inscripcion] Sin RESEND_API_KEY — lead: {nombre} {apellido} | {telefono} | {email}")
        return

    cuerpo = f"""Nuevo inscripto en PresupuestoPRO 🎉

Nombre:    {nombre} {apellido}
Teléfono:  {telefono}
Email:     {email or '(no indicó)'}
Ciudad:    {ciudad}, {provincia}

Entrá al panel admin para ver todos los leads:
https://web-production-0c9c1.up.railway.app/admin/leads
"""
    try:
        resend.api_key = api_key
        payload = {
            "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
            "to": [admin_email],
            "subject": f"Nuevo inscripto: {nombre} {apellido} — PresupuestoPRO",
            "text": cuerpo,
        }
        # Fix 05/07/2026: Reply-To al email del inscripto, para responder
        # directo con un Reply en vez de a noreply@.
        if email:
            payload["reply_to"] = [email]
        resend.Emails.send(payload)
    except Exception as e:
        print(f"[inscripcion] Error enviando email: {e}")
