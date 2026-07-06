import os
import resend
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from utils.auth import login_required
from database import get_db

bp = Blueprint('sugerencias', __name__)


@bp.route('/sugerencias', methods=['GET', 'POST'])
@login_required
def index():
    db = get_db()

    if request.method == 'POST':
        mensaje = (request.form.get('mensaje') or '').strip()
        if mensaje:
            db.execute(
                "INSERT INTO sugerencias (user_id, mensaje) VALUES (?, ?)",
                (g.user['id'], mensaje)
            )
            db.commit()
            _enviar_notificacion(g.user, mensaje)
            flash('¡Gracias! Tu sugerencia fue enviada.', 'success')
        db.close()
        return redirect(url_for('sugerencias.index'))

    mias = db.execute(
        "SELECT * FROM sugerencias WHERE user_id=? ORDER BY created_at DESC",
        (g.user['id'],)
    ).fetchall()
    db.close()
    return render_template('sugerencias.html', mias=mias, user=g.user)


def _enviar_notificacion(user, mensaje):
    """Email al admin cada vez que un usuario carga una sugerencia nueva
    (05/07/2026, mismo patrón que routes/landing.py::contacto())."""
    api_key = os.environ.get('RESEND_API_KEY')
    admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')
    if not api_key:
        print(f"[sugerencias] Sin RESEND_API_KEY — sugerencia de {user['email']}: {mensaje}")
        return
    try:
        resend.api_key = api_key
        resend.Emails.send({
            "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
            "to": [admin_email],
            "subject": f"💡 Nueva sugerencia de {user['nombre'] or user['email']}",
            "text": (
                f"Nueva sugerencia en PresupuestoPRO\n\n"
                f"Usuario:  {user['nombre'] or '(sin nombre)'}\n"
                f"Email:    {user['email']}\n\n"
                f"Sugerencia:\n{mensaje}\n\n"
                f"Ver todas las sugerencias:\n"
                f"https://web-production-0c9c1.up.railway.app/admin/sugerencias"
            ),
        })
    except Exception as e:
        print(f"[sugerencias] Error enviando email: {e}")
