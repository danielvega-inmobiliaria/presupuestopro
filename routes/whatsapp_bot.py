"""
Blueprint: whatsapp_bot
Bot de FAQ para WhatsApp Business Platform (Meta Cloud API) — responde
preguntas frecuentes sobre uso y ubicación de funciones de PresupuestoPRO.
Si no encuentra una respuesta, guarda la consulta en
`whatsapp_consultas_sin_responder` para revisión manual desde Admin.
Excepción agregada 21/07/2026: a quien responde un mensaje de la campaña
de retención (`_contacto_retencion_reciente`) NO se le manda el menú de
FAQ ni se intenta matching — se deriva directo a revisión humana, para
tener una conversación real en vez de que el bot lo maree.

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
from datetime import datetime, timedelta

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

FALLBACK_RESPUESTA = "¡Hola! Para arrancar, escribí: menú"

# ─── menú de bienvenida (mensaje interactivo tipo lista) ──────────────────────
# Se manda cuando arranca una conversación nueva (o pasaron más de 24hs desde
# el último mensaje) para guiar al usuario a una respuesta más precisa en vez
# de depender solo del matching por palabras clave. WhatsApp permite hasta 10
# filas en total por lista — exactamente las 10 categorías del FAQ.
SALUDO_MENU = (
    "¡Hola! 👋 Soy el asistente de *PresupuestoPRO*. Elegí un tema de la "
    "lista para ayudarte más rápido, o escribime tu consulta directamente.\n\n"
    "¿No encontrás lo que buscás o querés dejarnos un comentario? "
    "Contanos desde la app: Menú → Sugerencias."
)

CATEGORIAS = [
    {
        "id": "cat_registro",
        "title": "Registro y prueba",
        "description": "Cómo empezar a usar la app gratis",
        "respuesta": (
            "*Registro y prueba gratis*\n\n"
            "▸ *¿Cómo me registro?*\nEntrá a presupuestopro.com.ar/registro, "
            "completá tus datos y elegí una contraseña. Quedás adentro al "
            "instante, sin pagar nada.\n\n"
            "▸ *¿La prueba gratis tiene límite?*\nSí: hasta 3 presupuestos "
            "completos o 14 días, lo que se cumpla primero. En el panel "
            "principal siempre ves cuánto te queda.\n\n"
            "▸ *¿Dónde cargo el código de verificación?*\nTe llega por email "
            "un código de 6 dígitos, se carga en la pantalla que aparece "
            "después del registro."
        ),
    },
    {
        "id": "cat_pago",
        "title": "Suscripción y pago",
        "description": "Precio, cómo suscribirte y problemas de pago",
        "respuesta": (
            "*Suscripción y pago*\n\n"
            "▸ *¿Cuánto cuesta / cómo me suscribo?*\nCuando se cumple el "
            "límite de la prueba gratis, la app te invita a suscribirte. "
            "Desde \"Suscribirme\" se abre Mercado Pago para el pago "
            "recurrente mensual.\n\n"
            "▸ *Pagué y no se activó / tengo un problema con el pago*\n"
            "Escribinos desde \"Sugerencias\" dentro de la app y lo revisamos."
        ),
    },
    {
        "id": "cat_login",
        "title": "Login y contraseña",
        "description": "Recuperar o cambiar tu contraseña",
        "respuesta": (
            "*Login y contraseña*\n\n"
            "▸ *Olvidé mi contraseña*\nEn la pantalla de inicio de sesión, "
            "tocá \"Olvidé mi contraseña\", escribí tu email y te llega un "
            "link para crear una nueva.\n\n"
            "▸ *¿Cómo la cambio estando logueado?*\nMenú de usuario (arriba "
            "a la derecha) → \"Cambiar contraseña\".\n\n"
            "▸ *¿Puedo estar logueado en el celu y la compu a la vez?*\n"
            "No — por seguridad, iniciar sesión en un dispositivo nuevo "
            "cierra la sesión en el otro."
        ),
    },
    {
        "id": "cat_dashboard",
        "title": "Panel principal",
        "description": "Dashboard, borradores y presupuestos",
        "respuesta": (
            "*Panel principal (Dashboard)*\n\n"
            "▸ *¿Dónde veo mis presupuestos?*\nEn el Dashboard, pantalla "
            "principal al iniciar sesión: ahí están tus borradores en "
            "progreso y tus presupuestos completos.\n\n"
            "▸ *¿Qué es un borrador?*\nUn presupuesto que empezaste pero no "
            "terminaste. Tocá \"Retomar\" para seguir, o el tacho para "
            "eliminarlo.\n\n"
            "▸ *¿Dónde arranco un presupuesto nuevo?*\nBotón \"Nuevo "
            "presupuesto\" en el Dashboard.\n\n"
            "▸ *¿Dónde está la calculadora de Costo/m²?*\nBotón \"Costo/m²\" "
            "en el Dashboard, junto a \"Nuevo presupuesto\"."
        ),
    },
    {
        "id": "cat_presupuesto",
        "title": "Crear un presupuesto",
        "description": "El asistente de 8 pasos, paso a paso",
        "respuesta": (
            "*Crear un presupuesto (asistente de 8 pasos)*\n\n"
            "▸ *¿Cómo hago un presupuesto?*\nDashboard → \"Nuevo "
            "presupuesto\": datos del cliente/obra, cómputo, subcontratos, "
            "costos indirectos, modo de cotización, materiales, forma de "
            "pago y resumen final. Se guarda solo a medida que avanzás.\n\n"
            "▸ *Se me cortó la conexión, ¿perdí lo que cargué?*\nNo. Cada "
            "paso se guarda al tocar \"Siguiente\". Solo se pierde lo que "
            "escribiste en la pantalla actual si todavía no la guardaste.\n\n"
            "▸ *¿Puedo volver a un paso anterior sin perder lo cargado?*\n"
            "Sí, con los íconos de la barra superior del asistente. Los "
            "pasos visitados quedan en verde.\n\n"
            "▸ *¿Cómo retomo un borrador después?*\nDashboard → \"Retomar\" "
            "en \"Borradores en progreso\"."
        ),
    },
    {
        "id": "cat_ver_editar",
        "title": "Ver, editar y PDF",
        "description": "Editar presupuestos y descargar el PDF",
        "respuesta": (
            "*Ver, editar y descargar presupuestos*\n\n"
            "▸ *¿Puedo editar un presupuesto después de guardarlo?*\nSí, "
            "con el botón \"Editar\" desde el Dashboard.\n\n"
            "▸ *¿Cómo descargo el PDF?*\nDesde el Dashboard, en cada "
            "presupuesto completo tenés el botón \"PDF\" (para el cliente) "
            "o \"Constr.\" (con detalle de costos internos).\n\n"
            "▸ *¿Cuál es la diferencia entre los dos PDF?*\nEl Propietario "
            "es para el cliente, sin costos internos. El Constructor "
            "incluye mano de obra, materiales y márgenes."
        ),
    },
    {
        "id": "cat_costo_m2",
        "title": "Costo por m²",
        "description": "Cómo usar la calculadora de Costo/m²",
        "respuesta": (
            "*Costo por m²*\n\n"
            "Dashboard → \"Costo/m²\", elegís un ítem de la lista y te "
            "muestra mano de obra, materiales y total. Los jornales y "
            "precios son editables ahí mismo para simular variaciones."
        ),
    },
    {
        "id": "cat_mi_empresa",
        "title": "Mi empresa",
        "description": "Logo, nombre y datos para tus PDFs",
        "respuesta": (
            "*Mi Empresa*\n\n"
            "Menú de usuario → \"Mi empresa\". Ahí subís logo, nombre, "
            "eslogan y datos de contacto — aparecen en los PDFs que le "
            "mandás a tus clientes."
        ),
    },
    {
        "id": "cat_sugerencias",
        "title": "Sugerencias y soporte",
        "description": "Pedir mejoras, avisar errores o precios",
        "respuesta": (
            "*Sugerencias / soporte*\n\n"
            "▸ *Quiero pedir una mejora o avisar de un error*\nMenú "
            "principal → \"Sugerencias\". Cuando se responde o implementa "
            "se marca \"Respondida\" en tu lista.\n\n"
            "▸ *¿Los precios de materiales se actualizan solos?*\nSí, los "
            "actualiza el equipo tomando como referencia listas de "
            "corralones de primera línea. Si notás alguno desactualizado, "
            "avisanos desde \"Sugerencias\"."
        ),
    },
    {
        "id": "cat_instalar",
        "title": "Instalar en el celular",
        "description": "Instalar la app como acceso directo",
        "respuesta": (
            "*Instalar la app en el celular*\n\n"
            "Menú de usuario → \"Instalar app\". En Android/Chrome abre el "
            "instalador directo; en iPhone te explica el paso a paso de "
            "Safari (compartir → \"Agregar a pantalla de inicio\")."
        ),
    },
]

_KEYWORDS_MENU = {"menu", "menú", "opciones", "ayuda", "inicio", "hola", "buenas"}


def buscar_categoria(categoria_id):
    """Devuelve la categoría del menú por id, o None si no existe."""
    for cat in CATEGORIAS:
        if cat["id"] == categoria_id:
            return cat
    return None


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


_DIAS_VENTANA_RETENCION = 30


def _contacto_retencion_reciente(telefono, dias=_DIAS_VENTANA_RETENCION):
    """Agregado 21/07/2026, pedido de Daniel: cuando alguien de la campaña de
    retención responde al template que le mandamos, NO lo queremos mandar al
    menú de 10 categorías del bot de FAQ — Daniel quiere una conversación
    real para escuchar la experiencia del usuario, y el menú automático
    puede marearlo y hacer que abandone el chat sin decir lo que quería
    decir. Esta función devuelve el nombre del usuario si `telefono`
    pertenece a alguien que recibió un mensaje de retención (WhatsApp o
    email, da igual el canal) en los últimos `dias` días, o None si no.

    Comparación tolerante a formato: usa telefono_normalizado (mismo criterio
    que ya usa admin.whatsapp_inbox para cruzar teléfono ↔ usuario), así no
    importa si el teléfono entrante trae +54, el 9 extra, espacios, etc."""
    from utils.normalizacion import telefono_normalizado
    tel_norm = telefono_normalizado(telefono)
    if not tel_norm:
        return None
    db = get_db()
    filas = db.execute(
        """SELECT u.nombre, u.telefono, rc.created_at
           FROM retencion_contactos rc
           JOIN users u ON u.id = rc.user_id
           WHERE u.telefono IS NOT NULL AND u.telefono != ''
           ORDER BY rc.created_at DESC"""
    ).fetchall()
    db.close()
    limite = datetime.utcnow() - timedelta(days=dias)
    for f in filas:
        if telefono_normalizado(f['telefono']) != tel_norm:
            continue
        try:
            creado = datetime.fromisoformat(str(f['created_at']))
        except (ValueError, TypeError):
            continue
        if creado >= limite:
            return f['nombre'] or ''
    return None


def _sesion_vencida(telefono):
    """True si es la primera vez que este teléfono escribe, o si pasaron más
    de 24hs desde su última interacción (mismo criterio que la "ventana de
    servicio al cliente" de WhatsApp) — en ese caso conviene mandar el
    saludo + menú en vez de ir directo al matching."""
    db = get_db()
    fila = db.execute(
        "SELECT ultima_interaccion FROM whatsapp_conversaciones WHERE telefono=?",
        (telefono,),
    ).fetchone()
    db.close()
    if not fila or not fila[0]:
        return True
    try:
        ultima = datetime.fromisoformat(str(fila[0]))
    except ValueError:
        return True
    return (datetime.utcnow() - ultima) > timedelta(hours=24)


def _actualizar_sesion(telefono):
    db = get_db()
    db.execute(
        "INSERT INTO whatsapp_conversaciones (telefono, ultima_interaccion) "
        "VALUES (?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(telefono) DO UPDATE SET ultima_interaccion=CURRENT_TIMESTAMP",
        (telefono,),
    )
    db.commit()
    db.close()


def _enviar_payload(telefono, body):
    """POST genérico a la Cloud API de mensajes — usado tanto para texto
    libre como para el mensaje interactivo del menú."""
    token = os.environ.get('WHATSAPP_TOKEN')
    phone_id = os.environ.get('WHATSAPP_PHONE_ID')
    if not token or not phone_id:
        logger.warning("[whatsapp_bot] Sin WHATSAPP_TOKEN/WHATSAPP_PHONE_ID — no se puede responder a %s", telefono)
        return False
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


def enviar_mensaje_whatsapp(telefono, texto):
    """Manda un mensaje de texto libre (dentro de la ventana de 24hs de la
    conversación iniciada por el usuario — no requiere template aprobado,
    a diferencia de enviar_codigo_whatsapp en utils/verificacion.py)."""
    body = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto},
    }
    return _enviar_payload(telefono, body)


def enviar_plantilla_whatsapp(telefono, nombre_plantilla, parametros=None, idioma='es_AR'):
    """Agregado 20/07/2026, pedido de Daniel — manda un template PRE-APROBADO
    por Meta (mensaje que arranca la empresa, fuera de la ventana de 24hs,
    a diferencia de enviar_mensaje_whatsapp que solo sirve dentro de esa
    ventana). Se usa desde admin.seguimiento_whatsapp para la campaña de
    retención. `nombre_plantilla` tiene que coincidir EXACTO con el nombre
    aprobado en Meta Business Manager, si no la Cloud API devuelve error y
    esto vuelve False.

    `parametros`: dict {nombre_variable: valor} — ACTUALIZADO 21/07/2026:
    Meta dejó de aceptar variables posicionales ({{1}}, {{2}}) en plantillas
    nuevas, ahora exige variables con nombre ({{nombre}}, {{fecha}}, etc.),
    minúsculas y guion bajo. Cada key de `parametros` tiene que coincidir
    EXACTO con el nombre de la variable tal como quedó en el body aprobado
    en Meta (ej. si el body dice "Hola {{nombre}}!", pasar
    parametros={'nombre': 'Alejandro'})."""
    body = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": nombre_plantilla,
            "language": {"code": idioma},
        },
    }
    if parametros:
        body["template"]["components"] = [{
            "type": "body",
            "parameters": [
                {"type": "text", "parameter_name": nombre_var, "text": valor}
                for nombre_var, valor in parametros.items()
            ],
        }]
    return _enviar_payload(telefono, body)


def enviar_menu_whatsapp(telefono):
    """Manda el saludo + lista interactiva con las 10 categorías del FAQ."""
    body = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "PresupuestoPRO"},
            "body": {"text": SALUDO_MENU},
            "footer": {"text": "Escribí \"menú\" para volver a ver esta lista."},
            "action": {
                "button": "Ver temas",
                "sections": [
                    {
                        "title": "Temas",
                        "rows": [
                            {
                                "id": cat["id"],
                                "title": cat["title"],
                                "description": cat["description"],
                            }
                            for cat in CATEGORIAS
                        ],
                    }
                ],
            },
        },
    }
    return _enviar_payload(telefono, body)


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
        tipo = msg.get('type', 'text')
        if not telefono:
            return '', 200

        # Selección de una opción del menú interactivo → responde directo con
        # el contenido compilado de esa categoría, sin pasar por el matching.
        if tipo == 'interactive':
            list_reply = (msg.get('interactive') or {}).get('list_reply') or {}
            categoria = buscar_categoria(list_reply.get('id', ''))
            if categoria:
                enviar_mensaje_whatsapp(telefono, categoria["respuesta"])
            _actualizar_sesion(telefono)
            return '', 200

        texto = (msg.get('text') or {}).get('body', '')
        if not texto:
            return '', 200

        normalizado = _normalizar(texto)
        nueva_conversacion = _sesion_vencida(telefono)

        # Prioridad 21/07/2026: si este teléfono respondió a un mensaje de la
        # campaña de retención hace poco, no lo mandamos al bot de FAQ (menú
        # de 10 categorías) — Daniel quiere una conversación humana real acá,
        # no que se muestre el menú y la persona se maree y abandone antes
        # de contar su experiencia. Se guarda para Admin > WhatsApp y se
        # avisa que un humano va a responder, nada de matching automático.
        nombre_retencion = _contacto_retencion_reciente(telefono)
        if nombre_retencion is not None:
            _guardar_consulta_sin_responder(telefono, texto)
            saludo = f", {nombre_retencion.split()[0]}" if nombre_retencion else ""
            enviar_mensaje_whatsapp(
                telefono,
                f"¡Gracias por contarnos{saludo}! Te responde en breve alguien "
                "del equipo de PresupuestoPRO (no un bot) 🙂",
            )
            _actualizar_sesion(telefono)
            return '', 200

        # Saludo/pedido explícito de menú, o conversación nueva/inactiva
        # hace más de 24hs → mandar bienvenida + lista de temas primero.
        if normalizado in _KEYWORDS_MENU or nueva_conversacion:
            enviar_menu_whatsapp(telefono)
            # Si además el mensaje ya trae una pregunta puntual con match,
            # respondemos también — no hace falta que el usuario repita.
            if normalizado not in _KEYWORDS_MENU:
                respuesta = buscar_respuesta(texto)
                if respuesta:
                    enviar_mensaje_whatsapp(telefono, respuesta)
                else:
                    # Antes se perdía: si el primer mensaje de una conversación
                    # nueva no matcheaba ninguna FAQ, se mandaba el menú pero
                    # la pregunta en sí no quedaba guardada para revisión.
                    _guardar_consulta_sin_responder(telefono, texto)
        else:
            respuesta = buscar_respuesta(texto)
            if respuesta:
                enviar_mensaje_whatsapp(telefono, respuesta)
            else:
                _guardar_consulta_sin_responder(telefono, texto)
                enviar_mensaje_whatsapp(telefono, FALLBACK_RESPUESTA)

        _actualizar_sesion(telefono)
    except Exception as e:
        logger.error("[whatsapp_bot] Error procesando webhook: %s", e)
    return '', 200
