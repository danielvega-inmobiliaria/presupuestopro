"""
Webhook de Resend — pedido de Daniel 04/08/2026 (cont. 20): recibe en tiempo
real los eventos de los mails que manda la app (entregado/abierto/rebotado/
etc.) para poder verlo desde Admin > Usuarios y exportarlo en el Excel, sin
depender de entrar al dashboard de Resend. Ver utils/email_tracking.py para
la lógica de guardado/verificación de firma.

Configuración pendiente en Resend (Daniel, esto NO se puede hacer desde acá):
  1. Entrar a resend.com/webhooks → "Add Webhook".
  2. Endpoint: https://<tu-dominio>/webhooks/resend
  3. Eventos a suscribir: email.sent, email.delivered, email.opened,
     email.clicked, email.bounced, email.complained, email.delivery_delayed.
  4. Copiar el "Signing secret" (empieza con whsec_) y cargarlo en Railway
     como variable de entorno RESEND_WEBHOOK_SECRET.
Sin ese paso, este endpoint existe pero nunca lo va a llamar nadie -- no
hace falta para que el resto de la app funcione, es autocontenido.
"""
import os

from flask import Blueprint, request, jsonify

from utils.email_tracking import registrar_evento, verificar_firma

bp = Blueprint('webhooks_resend', __name__, url_prefix='/webhooks')


@bp.route('/resend', methods=['POST'])
def resend_webhook():
    payload_bytes = request.get_data()  # raw body, NO request.json -- la firma se calcula sobre el texto tal cual

    secret = os.environ.get('RESEND_WEBHOOK_SECRET', '')
    if secret:
        ok = verificar_firma(
            payload_bytes,
            request.headers.get('svix-id', ''),
            request.headers.get('svix-timestamp', ''),
            request.headers.get('svix-signature', ''),
            secret,
        )
        if not ok:
            # 400, no 401/403: Resend reintenta con backoff ante cualquier
            # respuesta que no sea 200 -- un 400 por firma inválida no debe
            # reintentarse indefinidamente, pero tampoco hace falta un
            # código especial, esto no es autenticación de usuario.
            return jsonify({'ok': False, 'error': 'firma inválida'}), 400
    else:
        # Sin secreto configurado todavía (ver docstring de arriba) -- se
        # acepta igual sin verificar, mismo criterio pragmático que otros
        # webhooks opcionales del proyecto (ej. WhatsApp sin credenciales).
        print("[webhooks_resend] RESEND_WEBHOOK_SECRET no configurado -- aceptando sin verificar firma")

    data = request.get_json(silent=True) or {}
    tipo_evento = data.get('type', '')  # ej. "email.delivered"
    evento = tipo_evento.split('.', 1)[1] if '.' in tipo_evento else tipo_evento
    payload = data.get('data', {}) or {}
    resend_id = payload.get('email_id', '')
    destinatarios = payload.get('to') or []

    for email in destinatarios:
        registrar_evento(resend_id, email, evento)

    # Siempre 200 ante un webhook bien formado y procesado -- Resend
    # reintenta con backoff exponencial si no devolvemos 200 (ver docstring).
    return jsonify({'ok': True}), 200
