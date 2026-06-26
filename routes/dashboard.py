import os
import resend
from flask import Blueprint, render_template, g, request, jsonify
from utils.auth import get_current_user
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
    db.close()
    return render_template('dashboard.html',
                           presupuestos=presupuestos,
                           borradores=borradores,
                           user=g.user)


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
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [admin_email],
            "subject": f"Nuevo inscripto: {nombre} {apellido} — PresupuestoPRO",
            "text": cuerpo,
        })
    except Exception as e:
        print(f"[inscripcion] Error enviando email: {e}")
