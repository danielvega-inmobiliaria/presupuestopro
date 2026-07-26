"""
Blueprint: email_bot
Agregado 25/07/2026, paso 1 del CRM unificado pedido por Daniel (WhatsApp +
Email + Facebook Messenger + Instagram en un solo lugar). Este archivo cubre
el mail entrante a contacto@presupuestopro.com.ar.

Contexto: Cloudflare Email Routing ya reenvía ese casillero a
presupuestopro.app@gmail.com (confirmado por Daniel 24/07/2026), pero eso
significa que si un usuario responde el mail de retención, esa respuesta
queda solo en Gmail -- no aparece en la app, a diferencia de WhatsApp. Para
que también quede acá, se agrega un Cloudflare Worker
(cloudflare_email_worker/, ver ese folder) que:
  1. Sigue reenviando el mail a Gmail tal cual (no se pierde nada de lo que
     ya funciona).
  2. Además parsea el mail (remitente, asunto, texto) y hace un POST acá
     con el resultado.

A diferencia de Messenger/Instagram (routes/social_bot.py), acá SÍ hay un
dato para cruzar contra `users` -- el email -- así que esta bandeja sigue
el mismo patrón que whatsapp_inbox (routes/admin.py) en vez del de social_inbox.

Requiere 1 variable de entorno en Railway (no cargada todavía, 25/07/2026 --
falta que Daniel deploye el Worker y la cargue en los dos lados):
  EMAIL_WEBHOOK_SECRET → string arbitrario elegido por Daniel, tiene que ser
                          EXACTAMENTE el mismo valor que el secreto
                          `EMAIL_WEBHOOK_SECRET` cargado en el Worker de
                          Cloudflare (`wrangler secret put`), para que este
                          endpoint no acepte POSTs de cualquiera que
                          adivine la URL.

Rutas:
  POST /webhook/email → recibe el mail ya parseado por el Worker
"""
import logging
import os

from flask import Blueprint, jsonify, request

from database import get_db

bp = Blueprint('email_bot', __name__, url_prefix='/webhook/email')
logger = logging.getLogger(__name__)


@bp.route('', methods=['POST'])
def recibir_email():
    """El Worker de Cloudflare manda acá un JSON {from, subject, text} por
    cada mail que le llega a contacto@presupuestopro.com.ar. Devuelve 200
    rápido -- no hay reintentos automáticos de Cloudflare como con Meta,
    pero igual conviene no bloquear."""
    secreto_esperado = os.environ.get('EMAIL_WEBHOOK_SECRET', '')
    secreto_recibido = request.headers.get('X-Webhook-Secret', '')
    if not secreto_esperado or secreto_recibido != secreto_esperado:
        logger.warning("[email_bot] Webhook rechazado: secreto inválido o EMAIL_WEBHOOK_SECRET sin cargar.")
        return jsonify({"error": "unauthorized"}), 403

    payload = request.get_json(silent=True) or {}
    remitente = (payload.get('from') or '').strip().lower()
    asunto = (payload.get('subject') or '').strip()
    texto = (payload.get('text') or '').strip()

    if not remitente or not texto:
        # Mail sin remitente o sin texto (ej. solo adjuntos) -- no hay nada
        # útil que guardar todavía.
        return jsonify({"ok": True, "guardado": False}), 200

    db = get_db()
    usuario = db.execute(
        "SELECT id, nombre FROM users WHERE lower(email)=?", (remitente,)
    ).fetchone()
    nombre_remitente = usuario['nombre'] if usuario else ''
    db.execute(
        """INSERT INTO email_consultas_entrantes
           (email_remitente, nombre_remitente, asunto, mensaje)
           VALUES (?,?,?,?)""",
        (remitente, nombre_remitente, asunto, texto),
    )
    db.commit()
    db.close()
    return jsonify({"ok": True, "guardado": True}), 200


def enviar_respuesta_email(destinatario, texto, asunto="Re: PresupuestoPRO"):
    """Contesta un mail entrante usando Resend, mismo remitente/reply_to que
    ya usa admin.seguimiento_email -- así, si el usuario responde de nuevo,
    la respuesta sigue llegando a contacto@ (Cloudflare) y de ahí acá.
    Devuelve (ok, detalle)."""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        return False, "Falta RESEND_API_KEY en las variables de entorno de Railway."
    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
            "to": [destinatario],
            "subject": asunto,
            "text": texto,
            "reply_to": ["contacto@presupuestopro.com.ar"],
        })
        return True, None
    except Exception as e:
        logger.error("[email_bot] Error enviando respuesta a %s: %s", destinatario, e)
        return False, str(e)
