"""
Blueprint: landing
Rutas: POST /contacto (formulario de contacto de la landing real, templates/landing.html)
       GET/POST /registro (alta gratis — campaña de lanzamiento, 06/07/2026)

Fix 06/07/2026: se eliminó la landing vieja (GET/POST /landing, variable
LANDING_HTML con el formulario de pago directo por Mercado Pago) — era código
muerto, no la enlazaba nada del sitio actual (el modelo pasó a ser lanzamiento
gratis). La landing real y en uso hoy es templates/landing.html, servida desde
dashboard.index(). Se conserva solo contacto(), que sigue viva.

Agregado 06/07/2026: /registro — alta pública de autoservicio para la campaña
de lanzamiento con prueba gratis (3 presupuestos o 14 días, ver utils/trial.py).
No pide pago; crea la cuenta con es_trial=1 y loguea directo. Daniel: para usar
esto en la campaña, apuntá el botón/link de "Probála gratis" de tu landing o
publicidad a esta URL (/registro).
"""

import logging
import os
from datetime import date, timedelta
import resend
from werkzeug.security import generate_password_hash
from flask import Blueprint, flash, redirect, render_template, request, url_for

from database import get_db
from utils.auth import login_user
from utils.trial import TRIAL_MAX_DIAS, TRIAL_MAX_PRESUPUESTOS

bp = Blueprint('landing', __name__)
logger = logging.getLogger(__name__)


@bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('registro.html',
                                max_presupuestos=TRIAL_MAX_PRESUPUESTOS,
                                max_dias=TRIAL_MAX_DIAS)

    f = request.form
    nombre    = f.get('nombre', '').strip()
    apellido  = f.get('apellido', '').strip()
    telefono  = f.get('telefono', '').strip()
    email     = f.get('email', '').strip().lower()
    ciudad    = f.get('ciudad', '').strip()
    provincia = f.get('provincia', '').strip()
    password  = f.get('password', '')

    prev = dict(nombre=nombre, apellido=apellido, telefono=telefono,
                email=email, ciudad=ciudad, provincia=provincia)

    def _error(msg):
        return render_template('registro.html', error=msg, prev=prev,
                                max_presupuestos=TRIAL_MAX_PRESUPUESTOS,
                                max_dias=TRIAL_MAX_DIAS)

    if not nombre or not apellido or not email or not password:
        return _error("Completá los campos obligatorios.")
    if len(password) < 6:
        return _error("La contraseña debe tener al menos 6 caracteres.")

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        db.close()
        return _error("Ya existe una cuenta con ese email. Iniciá sesión en vez de registrarte de nuevo.")

    try:
        password_hash = generate_password_hash(password)
        vence = (date.today() + timedelta(days=TRIAL_MAX_DIAS)).isoformat()
        cursor = db.execute(
            """INSERT INTO users
               (email, password_hash, nombre, apellido, telefono, ciudad, provincia,
                pais, active, es_trial, trial_visto, subscription_expires)
               VALUES (?,?,?,?,?,?,?,?,1,1,0,?)""",
            (email, password_hash, nombre, apellido, telefono, ciudad, provincia, 'AR', vence)
        )
        user_id = cursor.lastrowid
        db.commit()
        logger.info(f"[Registro] Nueva cuenta de prueba {email} id={user_id}")
    except Exception as e:
        db.close()
        logger.error(f"[Registro] Error creando cuenta {email}: {e}")
        return _error("Error al crear la cuenta. Intentá de nuevo.")
    db.close()

    _notificar_registro(nombre, apellido, telefono, email, ciudad, provincia)

    login_user(user_id)
    flash(f'¡Bienvenido, {nombre}! Tenés {TRIAL_MAX_PRESUPUESTOS} presupuestos gratis o {TRIAL_MAX_DIAS} días para probar la app, lo que se cumpla primero.', 'success')
    return redirect(url_for('dashboard.index'))


def _notificar_registro(nombre, apellido, telefono, email, ciudad, provincia):
    """Aviso al admin de cada alta nueva de prueba gratis (mismo patrón que
    routes/dashboard.py::_enviar_notificacion para leads)."""
    api_key = os.environ.get('RESEND_API_KEY')
    admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')
    if not api_key:
        print(f"[registro] Sin RESEND_API_KEY — nueva cuenta trial: {nombre} {apellido} | {email}")
        return
    try:
        resend.api_key = api_key
        payload = {
            "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
            "to": [admin_email],
            "subject": f"🎉 Nueva cuenta de prueba gratis: {nombre} {apellido}",
            "text": (
                f"Nueva cuenta de prueba gratis en PresupuestoPRO\n\n"
                f"Nombre:    {nombre} {apellido}\n"
                f"Teléfono:  {telefono or '(no indicó)'}\n"
                f"Email:     {email}\n"
                f"Ciudad:    {ciudad or '-'}, {provincia or '-'}\n\n"
                f"Ver todos los usuarios:\n"
                f"https://web-production-0c9c1.up.railway.app/admin/usuarios"
            ),
        }
        if email:
            payload["reply_to"] = [email]
        resend.Emails.send(payload)
    except Exception as e:
        print(f"[registro] Error enviando email: {e}")


@bp.route('/contacto', methods=['POST'])
def contacto():
    f = request.form
    nombre   = f.get('nombre', '').strip()
    apellido = f.get('apellido', '').strip()
    telefono = f.get('telefono', '').strip()
    email    = f.get('email', '').strip()
    ciudad   = f.get('ciudad', '').strip()
    provincia= f.get('provincia', '').strip()
    mensaje  = f.get('mensaje', '').strip()

    if nombre and mensaje:
        try:
            db = get_db()
            db.execute(
                """INSERT INTO contactos (nombre, apellido, telefono, email, ciudad, provincia, mensaje)
                   VALUES (?,?,?,?,?,?,?)""",
                (nombre, apellido, telefono, email, ciudad, provincia, mensaje)
            )
            db.commit()
            db.close()
            logger.info(f"[Contacto] Mensaje de {nombre} {apellido} / {email}")
        except Exception as e:
            logger.error(f"[Contacto] Error: {e}")

        # Notificación email al admin
        try:
            api_key = os.environ.get('RESEND_API_KEY')
            admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')
            if api_key:
                resend.api_key = api_key
                payload = {
                    "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
                    "to": [admin_email],
                    "subject": f"💬 Nuevo mensaje de contacto: {nombre} {apellido}",
                    "text": (
                        f"Nuevo mensaje de contacto en PresupuestoPRO\n\n"
                        f"Nombre:    {nombre} {apellido}\n"
                        f"Teléfono:  {telefono or '(no indicó)'}\n"
                        f"Email:     {email or '(no indicó)'}\n"
                        f"Ciudad:    {ciudad or '-'}, {provincia or '-'}\n\n"
                        f"Mensaje:\n{mensaje}\n\n"
                        f"Ver todos los mensajes:\n"
                        f"https://web-production-0c9c1.up.railway.app/admin/contactos"
                    ),
                }
                # Fix 05/07/2026: Reply-To al email de contacto, para responder
                # directo con un Reply en vez de a noreply@.
                if email:
                    payload["reply_to"] = [email]
                resend.Emails.send(payload)
        except Exception as e:
            logger.error(f"[Contacto] Error enviando email: {e}")

    # ⚠️ Fix 06/07/2026 pendiente de confirmar con Daniel: este redirect apunta
    # a '/landing', ruta que se ELIMINÓ en este mismo fix (era la landing vieja
    # muerta). Se dejó sin tocar a pedido explícito ("sin tocar la función
    # contacto()"), pero si este formulario vuelve a usarse (ej. en la landing
    # real, templates/landing.html) este redirect va a dar 404. Cambiar a
    # '/?contacto_ok=1#contacto' (la home real) en cuanto se confirme.
    return redirect('/landing?contacto_ok=1#contacto')
