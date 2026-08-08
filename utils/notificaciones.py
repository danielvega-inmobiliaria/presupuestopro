"""
Notificaciones a Daniel (admin) por mail vía Resend.

Extraído 08/08/2026 de routes/pagos.py para reusar el mismo patrón de envío
en el aviso "llamar en caliente" (ver RETENCION_USUARIOS/PROYECTO.md,
sección del 08/08/2026) en vez de duplicar lógica.

Bug arreglado de paso (encontrado 06/08/2026, documentado en
APP_PRESUPUESTOPRO/PROYECTO.md, nunca corregido hasta ahora): la función
original en pagos.py llamaba `user_full.get('apellido')` y
`user_full.get('telefono')` sobre un `sqlite3.Row`, que NO tiene `.get()`
(solo soporta indexado tipo `row['col']`) -- rompía con AttributeError en
CADA pago aprobado, silenciado por un `except Exception` que solo logueaba
un warning. Resultado: el mail de "pago aprobado" a Daniel nunca se mandó
desde que existe el código. Acá se usa `_row_get()`, que sí funciona con
sqlite3.Row.
"""
import logging
import os

logger = logging.getLogger(__name__)


def _row_get(row, campo, default=''):
    """Reemplazo de `.get()` para sqlite3.Row (no lo tiene)."""
    try:
        valor = row[campo]
    except (IndexError, KeyError):
        return default
    return valor if valor is not None else default


def notificar_admin(asunto, texto):
    """Manda un mail a ADMIN_EMAIL (default danve61@gmail.com) vía Resend.
    Devuelve (ok, detalle) -- nunca lanza, para no romper el flujo que
    dispara la notificación (pago, respuesta de retención, etc.)."""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        detalle = "Falta RESEND_API_KEY en las variables de entorno de Railway."
        logger.warning(f"[Notificaciones] {detalle}")
        return False, detalle
    admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')
    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
            "to": [admin_email],
            "subject": asunto,
            "text": texto,
        })
        return True, None
    except Exception as e:
        logger.warning(f"[Notificaciones] No se pudo notificar al admin: {e}")
        return False, str(e)


def notificar_admin_pago(user_full, nueva_exp, payment_id):
    """Aviso de pago aprobado -- misma lógica que tenía routes/pagos.py,
    ahora con el bug de `.get()` sobre sqlite3.Row arreglado. `user_full`
    es la Row con columnas email/nombre/apellido/telefono."""
    nombre = _row_get(user_full, 'nombre')
    apellido = _row_get(user_full, 'apellido')
    nombre_display = f"{nombre} {apellido}".strip() or user_full['email']
    tel = _row_get(user_full, 'telefono', 'sin teléfono') or 'sin teléfono'
    app_url = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
    tel_wa = tel.replace(' ', '').replace('-', '').replace('+', '') if tel != 'sin teléfono' else ''
    texto = (
        f"Se activó una suscripción nueva.\n\n"
        f"Usuario:   {nombre_display}\n"
        f"Email:     {user_full['email']}\n"
        f"Teléfono:  {tel}\n"
        f"Vence:     {nueva_exp.isoformat()}\n"
        f"Payment:   {payment_id}\n\n"
        + (f"WhatsApp: https://wa.me/549{tel_wa}\n" if tel_wa else "")
        + f"Link login: {app_url}/login"
    )
    return notificar_admin(f"[PresupuestoPRO] Pago aprobado — {nombre_display}", texto)


def notificar_admin_respuesta_retencion(uid, nombre, contacto, canal, segmento, texto_respuesta):
    """Aviso "llamar en caliente" (08/08/2026, PRIORIDAD 1) -- pedido de
    Daniel: cuando alguien con un contacto de retención reciente (últimos
    30 días) responde por WhatsApp o mail, avisarle YA en vez de que
    dependa de que él revise las bandejas por su cuenta.

    Contexto que motivó esto: con el export del 06/08 se confirmó que de
    180 registrados solo hay 2 abonados reales, y los dos convirtieron por
    llamada telefónica de Daniel -- ninguno por mensaje automático. El
    contacto humano en caliente es la única palanca de conversión
    comprobada hoy.

    `uid` es el id en `users`, `contacto` es el teléfono o email según
    `canal`. Devuelve (ok, detalle)."""
    app_url = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
    link_perfil = f"{app_url}/admin/seguimiento/{uid}"
    nombre_display = nombre or contacto
    asunto = f"🔥 Respondió {nombre_display} ({canal}) — llamalo ahora"
    texto = (
        f"{nombre or '(sin nombre)'} respondió a un mensaje de retención.\n\n"
        f"Canal:     {canal}\n"
        f"Contacto:  {contacto}\n"
        f"Segmento:  {segmento or '(sin segmento)'}\n\n"
        f"Respondió:\n\"{texto_respuesta}\"\n\n"
        f"Perfil completo: {link_perfil}\n\n"
        f"Llamalo ahora, con esto en la mano -- es la única palanca de "
        f"conversión que viene funcionando de verdad."
    )
    return notificar_admin(asunto, texto)
