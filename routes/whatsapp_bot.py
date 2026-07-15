"""
Blueprint: whatsapp_bot
Bot de FAQ para WhatsApp Business Platform (Meta Cloud API) — responde
preguntas frecuentes sobre uso y ubicación de funciones de PresupuestoPRO.
No deriva a un humano: si no encuentra una respuesta, guarda la consulta en
`whatsapp_consultas_sin_responder` para revisión manual desde Admin.

Contenido de las preguntas/respuestas: ver CHATBOT_WHATSAPP_BUSINESS/FAQ_BOT.md
(fuente editable en texto plano) — las FAQ_DATA de acá abajo son la versión
"compilada" para el matching. Si se edita el contenido, actualizar los dos
lugares.

Requiere 3 variables de entorno en Railway (ninguna cargada todavía,
14/07/2026 — el número sigue sin dar de alta en Meta):
  WHATSAPP_TOKEN         → access token de la app de Meta
  WHATSAPP_PHONE_ID      → ID del número de WhatsApp Business
  WHATSAPP_VERIFY_TOKEN  → string arbitrario elegido por Daniel, se lo repite
                            a Meta al configurar el webhook (Meta lo manda de
                            vuelta en el GET de verificación para confirmar
                            que el dueño del endpoint es quien dice ser)

Rutas:
  GET  /webhook/whatsapp   → verificación del webhook ante Meta
  POST /webhook/whatsapp   → recibe mensajes entrantes y responde
"""
import json
import logging
import os
import re
import unicodedata
import urllib.error
import urllib.request

from flask import Blueprint, request

from database import get_db

bp = Blueprint('whatsapp_bot', __name__, url_prefix='/webhook/whatsapp')
logger = logging.getLogger(__name__)


# ─── contenido del FAQ (mantener sincronizado con FAQ_BOT.md) ─────────────────
# Cada entrada: keywords (si aparece cualquiera en el mensaje normalizado, hay
# match) y la respuesta tal cual se manda por WhatsApp.
FAQ_DATA = [
    {
        "keywords": ["registrar", "registro", "como empiezo", "como uso la app", "crear cuenta"],
        "respuesta": "Entrá a presupuestopro.com.ar/registro, completá tus datos y elegí una contraseña. Quedás adentro al instante, sin pagar nada.",
    },
    {
        "keywords": ["prueba gratis", "limite", "cuantos presupuestos", "dias gratis", "cuanto dura la prueba"],
        "respuesta": "La prueba gratis dura hasta 3 presupuestos completos o 14 días, lo que se cumpla primero. En el panel principal siempre ves cuánto te queda.",
    },
    {
        "keywords": ["codigo de verificacion", "codigo de 6 digitos", "donde cargo el codigo"],
        "respuesta": "Te llega por email un código de 6 dígitos. Se carga en la pantalla que aparece después del registro. Podés entrar al dashboard mientras tanto, pero no crear presupuestos hasta validar la cuenta.",
    },
    {
        "keywords": ["cuanto cuesta", "precio", "suscribo", "suscribir", "mercado pago", "pago mensual"],
        "respuesta": "Cuando se cumple el límite de la prueba gratis, la app te invita a suscribirte. Desde ese aviso o desde \"Suscribirme\" se abre Mercado Pago para el pago recurrente mensual.",
    },
    {
        "keywords": ["pague y no", "no se activo", "problema con el pago", "no se acredito"],
        "respuesta": "Escribinos desde \"Sugerencias\" dentro de la app y lo revisamos.",
    },
    {
        "keywords": ["olvide mi contraseña", "olvide la contraseña", "recuperar contraseña"],
        "respuesta": "En la pantalla de inicio de sesión, tocá \"Olvidé mi contraseña\", escribí tu email y te llega un link para crear una nueva.",
    },
    {
        "keywords": ["cambiar mi contraseña", "cambiar contraseña", "cambiar clave"],
        "respuesta": "Menú de usuario (arriba a la derecha) → \"Cambiar contraseña\".",
    },
    {
        "keywords": ["dos dispositivos", "celular y la compu", "sesion abierta en dos"],
        "respuesta": "No por ahora — por seguridad, iniciar sesión en un dispositivo nuevo cierra la sesión en el otro.",
    },
    {
        "keywords": ["donde veo mis presupuestos", "donde estan mis presupuestos"],
        "respuesta": "En el Dashboard (pantalla principal al iniciar sesión): ahí están tus borradores en progreso y tus presupuestos completos.",
    },
    {
        "keywords": ["que es un borrador"],
        "respuesta": "Un presupuesto que empezaste pero no terminaste. El Dashboard te muestra en qué paso quedaste — tocá \"Retomar\" para seguir, o el tacho para eliminarlo.",
    },
    {
        "keywords": ["nuevo presupuesto", "arrancar un presupuesto", "como hago un presupuesto", "crear un presupuesto"],
        "respuesta": "Con el asistente de 8 pasos (Dashboard → \"Nuevo presupuesto\"): datos del cliente/obra, cómputo, subcontratos, costos indirectos, modo de cotización, materiales, forma de pago y resumen final. Se va guardando solo a medida que avanzás.",
    },
    {
        "keywords": ["se corto la conexion", "perdi lo que cargue", "se me corto internet"],
        "respuesta": "No se pierde nada importante. Cada paso se guarda al tocar \"Siguiente\" o al saltar de paso. Solo se pierde lo que escribiste en la pantalla actual si todavía no la guardaste.",
    },
    {
        "keywords": ["volver a un paso anterior", "saltar de paso", "cambiar de paso"],
        "respuesta": "Sí, con los íconos de la barra superior del asistente (INICIO, CÓMPUTO, SUBCONT, INDIR, MODO, MATER, F PAGO, RESUMEN). Los pasos ya visitados quedan en verde y podés saltar a cualquiera.",
    },
    {
        "keywords": ["retomar un borrador", "seguir un borrador", "continuar presupuesto"],
        "respuesta": "Dashboard → \"Retomar\" en \"Borradores en progreso\".",
    },
    {
        "keywords": ["editar un presupuesto", "modificar un presupuesto"],
        "respuesta": "Sí, con el botón \"Editar\" desde el Dashboard — vuelve a abrir el asistente con los datos ya cargados.",
    },
    {
        "keywords": ["descargar el pdf", "descargo el pdf", "bajar el pdf"],
        "respuesta": "Desde el Dashboard, en cada presupuesto completo tenés el botón \"PDF\" (versión para el cliente) o \"Constr.\" (versión con detalle de costos internos).",
    },
    {
        "keywords": ["diferencia entre el pdf", "pdf propietario", "pdf constructor"],
        "respuesta": "El Propietario es para el cliente, sin costos internos. El Constructor incluye mano de obra, materiales y márgenes.",
    },
    {
        "keywords": ["costo por m2", "costo m2", "calculadora de costo"],
        "respuesta": "Dashboard → \"Costo/m²\", elegís un ítem de la lista y te muestra mano de obra, materiales y total. Los jornales y precios son editables ahí mismo para simular variaciones.",
    },
    {
        "keywords": ["cargar el logo", "logo de mi empresa", "mi empresa"],
        "respuesta": "Menú de usuario → \"Mi empresa\". Ahí subís logo, nombre, eslogan y datos de contacto — aparecen en los PDFs que le mandás a tus clientes.",
    },
    {
        "keywords": ["pedir una mejora", "avisar un error", "sugerencia", "reportar un problema"],
        "respuesta": "Menú principal → \"Sugerencias\". Queda registrada y cuando se responde o implementa se marca \"Respondida\" en tu lista.",
    },
    {
        "keywords": ["precios de materiales", "precio de los materiales", "materiales actualizados"],
        "respuesta": "Sí, los actualiza el equipo de PresupuestoPRO tomando como referencia listas de corralones de primera línea. Si notás alguno desactualizado, avisanos desde \"Sugerencias\".",
    },
    {
        "keywords": ["instalar la app", "instalar en el celular", "agregar a pantalla de inicio"],
        "respuesta": "Menú de usuario → \"Instalar app\". En Android/Chrome abre el instalador directo; en iPhone te explica el paso a paso de Safari (compartir → \"Agregar a pantalla de inicio\").",
    },
]

FALLBACK_RESPUESTA = (
    "No tengo la respuesta a mano para eso. Dejé tu consulta anotada, "
    "te contestamos apenas la vea el equipo."
)


def _normalizar(texto):
    """minúsculas, sin tildes, espacios simples — para matching tolerante."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def buscar_respuesta(mensaje):
    """Devuelve la respuesta de la primera FAQ cuyo keyword aparezca en el
    mensaje (substring simple), o None si ninguna matchea."""
    normalizado = _normalizar(mensaje)
    for entrada in FAQ_DATA:
        for kw in entrada["keywords"]:
            if _normalizar(kw) in normalizado:
                return entrada["respuesta"]
    return None


def _guardar_consulta_sin_responder(telefono, mensaje):
    db = get_db()
    db.execute(
        "INSERT INTO whatsapp_consultas_sin_responder (telefono, mensaje) VALUES (?,?)",
        (telefono, mensaje),
    )
    db.commit()
    db.close()


def enviar_mensaje_whatsapp(telefono, texto):
    """Manda un mensaje de texto libre (dentro de la ventana de 24hs de la
    conversación iniciada por el usuario — no requiere template aprobado,
    a diferencia de enviar_codigo_whatsapp en utils/verificacion.py)."""
    token = os.environ.get('WHATSAPP_TOKEN')
    phone_id = os.environ.get('WHATSAPP_PHONE_ID')
    if not token or not phone_id:
        logger.warning("[whatsapp_bot] Sin WHATSAPP_TOKEN/WHATSAPP_PHONE_ID — no se puede responder a %s", telefono)
        return False
    body = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto},
    }
    req = urllib.request.Request(
        f"https://graph.facebook.com/v20.0/{phone_id}/messages",
        data=json.dumps(body).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        logger.error("[whatsapp_bot] Error WhatsApp API (%s): %s", e.code, e.read())
        return False
    except Exception as e:
        logger.error("[whatsapp_bot] Error enviando mensaje a %s: %s", telefono, e)
        return False


@bp.route('', methods=['GET'])
def verificar_webhook():
    """Meta llama a esto una sola vez al configurar el webhook, para
    confirmar que el dueño del endpoint es quien dice ser."""
    verify_token = os.environ.get('WHATSAPP_VERIFY_TOKEN', '')
    modo = request.args.get('hub.mode')
    token_recibido = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge', '')
    if modo == 'subscribe' and verify_token and token_recibido == verify_token:
        return challenge, 200
    return 'Forbidden', 403


@bp.route('', methods=['POST'])
def recibir_mensaje():
    """Procesa mensajes entrantes. Devuelve 200 siempre y rápido — Meta
    reintenta si no responde a tiempo, y no queremos duplicados."""
    payload = request.get_json(silent=True) or {}
    try:
        entry = payload.get('entry', [])[0]
        cambio = entry.get('changes', [])[0]
        valor = cambio.get('value', {})
        mensajes = valor.get('messages', [])
        if not mensajes:
            # Notificación de estado (entregado/leído), no un mensaje nuevo — ignorar.
            return '', 200
        msg = mensajes[0]
        telefono = msg.get('from', '')
        texto = (msg.get('text') or {}).get('body', '')
        if not telefono or not texto:
            return '', 200

        respuesta = buscar_respuesta(texto)
        if respuesta:
            enviar_mensaje_whatsapp(telefono, respuesta)
        else:
            _guardar_consulta_sin_responder(telefono, texto)
            enviar_mensaje_whatsapp(telefono, FALLBACK_RESPUESTA)
    except Exception as e:
        logger.error("[whatsapp_bot] Error procesando webhook: %s", e)
    return '', 200
