"""
Blueprint: landing
Rutas: POST /contacto (formulario de contacto de la landing real, templates/landing.html)

Fix 06/07/2026: se eliminó la landing vieja (GET/POST /landing, variable
LANDING_HTML con el formulario de pago directo por Mercado Pago) — era código
muerto, no la enlazaba nada del sitio actual (el modelo pasó a ser lanzamiento
gratis). La landing real y en uso hoy es templates/landing.html, servida desde
dashboard.index(). Se conserva solo contacto(), que sigue viva.
"""

import logging
import os
import resend
from flask import Blueprint, redirect, request

from database import get_db

bp = Blueprint('landing', __name__)
logger = logging.getLogger(__name__)


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
