"""
Blueprint: social_bot
Agregado 25/07/2026, fase 1 del CRM unificado pedido por Daniel (WhatsApp +
Email + Facebook Messenger + Instagram DM en un solo lugar). Este archivo
cubre Messenger e Instagram -- comparten el mismo formato de webhook y la
misma Send API de Meta (solo cambia el campo "object": "page" para Messenger,
"instagram" para Instagram), así que un solo endpoint alcanza para los dos,
igual que hacen Meta y la mayoría de las integraciones reales.

Diferencia importante con WhatsApp (routes/whatsapp_bot.py): ahí el teléfono
permite cruzar cada mensaje contra `users` para saber quién escribe. Acá NO
hay ningún dato así -- Messenger e Instagram solo mandan un ID de plataforma
(PSID / IGSID) que no identifica a la persona salvo que ella misma escriba su
nombre/mail/teléfono en el chat. Por eso, a diferencia de whatsapp_inbox, esta
bandeja NO intenta cruzar contra `users` todavía -- queda para una fase 2 si
Daniel confirma que quiere pedirle el dato al usuario y vincularlo a mano.

Requiere 2 variables de entorno en Railway (ninguna cargada todavía,
25/07/2026 -- falta que Daniel complete el alta de Messenger/Instagram en
Meta, ver PROYECTO.md):
  MESSENGER_TOKEN         -> Page Access Token (sirve para Messenger e
                              Instagram una vez que la cuenta de Instagram
                              está vinculada a la misma Facebook Page)
  MESSENGER_VERIFY_TOKEN  -> string arbitrario elegido por Daniel, mismo
                              patrón que WHATSAPP_VERIFY_TOKEN

Rutas:
  GET  /webhook/social   -> verificación del webhook ante Meta
  POST /webhook/social   -> recibe mensajes entrantes (Messenger o Instagram)
"""
import json
import logging
import os
import urllib.error
import urllib.request

from flask import Blueprint, request

from database import get_db

bp = Blueprint('social_bot', __name__, url_prefix='/webhook/social')
logger = logging.getLogger(__name__)


def _enviar_payload(destinatario_id, body):
    """POST genérico a la Send API de Meta -- misma API para Messenger e
    Instagram una vez que el Page Access Token tiene los permisos de los
    dos productos. Devuelve (ok, detalle), mismo patrón que
    whatsapp_bot.py::_enviar_payload."""
    token = os.environ.get('MESSENGER_TOKEN')
    if not token:
        logger.warning("[social_bot] Sin MESSENGER_TOKEN -- no se puede responder a %s", destinatario_id)
        return False, "Falta MESSENGER_TOKEN en las variables de entorno de Railway."
    req = urllib.request.Request(
        f"https://graph.facebook.com/v20.0/me/messages?access_token={token}",
        data=json.dumps(body).encode('utf-8'),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True, None
    except urllib.error.HTTPError as e:
        cuerpo = e.read()
        try:
            data = json.loads(cuerpo)
            err = data.get('error', {})
            detalle = f"{err.get('code', e.code)}: {err.get('message', '')}"
        except (json.JSONDecodeError, AttributeError):
            detalle = f"{e.code}: {cuerpo[:300]}"
        logger.error("[social_bot] Error Graph API (%s): %s", e.code, cuerpo)
        return False, detalle
    except Exception as e:
        logger.error("[social_bot] Error enviando mensaje a %s: %s", destinatario_id, e)
        return False, str(e)


def enviar_mensaje_social(destinatario_id, texto):
    """Manda un mensaje de texto libre por Messenger o Instagram (dentro de
    la ventana de 24hs de la conversación iniciada por el usuario -- misma
    regla que WhatsApp). Devuelve (ok, detalle)."""
    body = {
        "recipient": {"id": destinatario_id},
        "message": {"text": texto},
    }
    return _enviar_payload(destinatario_id, body)


def _guardar_consulta(canal, remitente_id, mensaje):
    db = get_db()
    db.execute(
        "INSERT INTO redes_consultas_sin_responder (canal, remitente_id, mensaje) VALUES (?,?,?)",
        (canal, remitente_id, mensaje),
    )
    db.commit()
    db.close()


@bp.route('', methods=['GET'])
def verificar_webhook():
    """Meta llama a esto una sola vez por cada suscripción (Messenger e
    Instagram por separado, aunque apunten al mismo callback URL) para
    confirmar que el dueño del endpoint es quien dice ser."""
    verify_token = os.environ.get('MESSENGER_VERIFY_TOKEN', '')
    modo = request.args.get('hub.mode')
    token_recibido = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge', '')
    if modo == 'subscribe' and verify_token and token_recibido == verify_token:
        return challenge, 200
    return 'Forbidden', 403


@bp.route('', methods=['POST'])
def recibir_mensaje():
    """Procesa mensajes entrantes de Messenger e Instagram. Devuelve 200
    siempre y rápido -- Meta reintenta si no responde a tiempo, y no
    queremos duplicados (mismo criterio que whatsapp_bot.py)."""
    payload = request.get_json(silent=True) or {}
    objeto = payload.get('object', '')
    canal = {'page': 'messenger', 'instagram': 'instagram'}.get(objeto)
    if not canal:
        # No es ni Messenger ni Instagram -- ignorar sin romper nada.
        return '', 200

    try:
        for entry in payload.get('entry', []):
            for evento in entry.get('messaging', []):
                remitente_id = (evento.get('sender') or {}).get('id', '')
                texto = (evento.get('message') or {}).get('text', '')
                if not remitente_id or not texto:
                    # Puede ser un evento de "delivered"/"read"/postback sin
                    # texto -- no hay nada que guardar todavía.
                    continue
                _guardar_consulta(canal, remitente_id, texto)
                enviar_mensaje_social(
                    remitente_id,
                    "¡Gracias por escribirnos! Te responde en breve alguien "
                    "del equipo de PresupuestoPRO (no un bot) 🙂",
                )
    except Exception as e:
        logger.error("[social_bot] Error procesando webhook (%s): %s", canal, e)

    return '', 200
