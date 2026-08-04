"""
Tracking de mails (entregado / abierto / rebotado / etc.) — pedido de Daniel
04/08/2026 (cont. 20): quiere ver desde la propia App si los mails
automáticos (bienvenida, recordatorio de inactividad, seguimiento manual de
Admin > Seguimiento) llegan y se abren, sin depender de entrar al dashboard
de Resend, y poder exportarlo en el Excel de Usuarios.

Cómo funciona (2 mitades):
  1. Cada vez que se manda un mail desde la app, se guarda un evento propio
     'sent' con el `id` que devuelve `resend.Emails.send()` — ver
     registrar_envio(), llamado desde routes/landing.py,
     utils/recordatorios.py y routes/admin.py::seguimiento_email.
  2. Resend manda webhooks reales (delivered/opened/clicked/bounced/etc.) a
     POST /webhooks/resend (routes/webhooks_resend.py) — cada uno se guarda
     tal cual con registrar_evento(). No se pisa nada, queda 1 fila por
     evento (historial completo); estado_email() lee el ÚLTIMO evento por
     dirección de mail para mostrar/exportar un solo estado resumen.

Los webhooks de Resend viajan sin autenticación propia -- se firman con el
esquema de Svix (headers svix-id/svix-timestamp/svix-signature). Acá se
verifica esa firma a mano (HMAC-SHA256), sin agregar la librería `svix` como
dependencia nueva, siguiendo el esquema documentado por Resend/Svix. Si no
hay RESEND_WEBHOOK_SECRET configurado, se acepta igual pero sin verificar
(mismo criterio pragmático que ya usa el resto del proyecto con secretos
opcionales, ej. WhatsApp) -- ver verificar_firma().
"""
import base64
import hashlib
import hmac
import os

from database import get_db

# SQL reutilizado tal cual en routes/admin.py (usuarios() y
# _usuarios_para_exportar()) para traer el ÚLTIMO evento de cada usuario
# directo en la misma query (evita N+1 conexiones a DB por usuario en listas
# largas -- mismo criterio ya documentado en admin.py::_usuarios_seguimiento
# para no abrir una conexión por fila). Se toma el evento más RECIENTE (no
# el "mejor histórico"): si se manda un mail nuevo, el estado vuelve a
# 'sent' hasta que llegue el próximo webhook -- es justamente lo que
# interesa mostrar ("¿el ÚLTIMO mail que le mandamos llegó/se abrió?"), no
# mezclarlo con la apertura de un mail viejo de hace semanas.
#
# ORDER BY created_at DESC, id DESC (no solo created_at): SQLite guarda
# CURRENT_TIMESTAMP con resolución de 1 segundo -- si 2+ eventos del mismo
# mail llegan en el mismo segundo (nada raro: 'delivered' y 'opened' pueden
# llegar casi juntos), quedan empatados y el orden por fecha sola no es
# confiable. `id` es autoincrement, así que desempata siempre por el orden
# real de inserción (confirmado con un test que manda 2 eventos en el mismo
# segundo -- sin el `id DESC` el más nuevo NO siempre ganaba).
SQL_MAIL_ESTADO = (
    "(SELECT evento FROM email_eventos e WHERE e.email=LOWER(u.email) "
    "ORDER BY e.created_at DESC, e.id DESC LIMIT 1)"
)
SQL_MAIL_ESTADO_FECHA = (
    "(SELECT created_at FROM email_eventos e WHERE e.email=LOWER(u.email) "
    "ORDER BY e.created_at DESC, e.id DESC LIMIT 1)"
)

ETIQUETAS_EVENTO = {
    'sent':             'Enviado',
    'delivered':        'Entregado',
    'opened':           'Abierto',
    'clicked':          'Abierto (con click)',
    'delivery_delayed': 'Demorado',
    'bounced':          'Rebotado',
    'complained':       'Marcado como spam',
    'failed':           'Falló el envío',
}


def registrar_envio(resend_id, email, tipo):
    """Se llama justo después de un `resend.Emails.send()` exitoso. `tipo`
    identifica de qué mail se trata (ej. 'bienvenida', 'recordatorio_inactividad',
    'seguimiento_A') -- no afecta el estado que se muestra (eso sale del
    evento más reciente sea cual sea el tipo), es solo para poder revisar el
    historial completo más adelante si hace falta. Nunca lanza excepción
    hacia afuera -- un problema acá no tiene que tumbar el envío del mail."""
    if not resend_id or not email:
        return
    try:
        db = get_db()
        db.execute(
            "INSERT INTO email_eventos (resend_id, email, tipo, evento) VALUES (?,?,?,?)",
            (resend_id, email.strip().lower(), tipo, 'sent')
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"[email_tracking] Error registrando envío a {email}: {e}")


def registrar_evento(resend_id, email, evento, tipo=''):
    """Guarda un evento real de Resend (delivered/opened/clicked/bounced/...).
    Se llama desde el webhook. `email` puede venir vacío si el payload no lo
    trae -- en ese caso no se guarda nada (no serviría para nada sin saber
    de quién es)."""
    if not email or not evento:
        return
    try:
        db = get_db()
        db.execute(
            "INSERT INTO email_eventos (resend_id, email, tipo, evento) VALUES (?,?,?,?)",
            (resend_id or '', email.strip().lower(), tipo, evento)
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"[email_tracking] Error registrando evento '{evento}' de {email}: {e}")


def estado_email(email):
    """Devuelve {'evento': ..., 'etiqueta': ..., 'fecha': ...} con el ÚLTIMO
    evento registrado para ese email, o None si nunca se le mandó ni se
    registró nada. Uso puntual (1 sola dirección) -- para listas de muchos
    usuarios a la vez usar SQL_MAIL_ESTADO/SQL_MAIL_ESTADO_FECHA directo en
    la query, no esta función en un loop (evita N+1 conexiones a DB)."""
    if not email:
        return None
    db = get_db()
    fila = db.execute(
        "SELECT evento, created_at FROM email_eventos WHERE email=? ORDER BY created_at DESC, id DESC LIMIT 1",
        (email.strip().lower(),)
    ).fetchone()
    db.close()
    if not fila:
        return None
    return {
        'evento': fila['evento'],
        'etiqueta': ETIQUETAS_EVENTO.get(fila['evento'], fila['evento']),
        'fecha': (fila['created_at'] or '')[:10],
    }


def verificar_firma(payload_bytes, svix_id, svix_timestamp, svix_signature, secret):
    """Verifica la firma Svix de un webhook de Resend a mano (HMAC-SHA256),
    sin depender del paquete `svix`. Esquema documentado por Resend/Svix:
      contenido_firmado = f"{svix_id}.{svix_timestamp}.{payload}"
      secreto_real       = base64decode(secret sin el prefijo "whsec_")
      firma_esperada     = base64encode(HMAC_SHA256(secreto_real, contenido_firmado))
    El header svix-signature puede traer varias firmas separadas por
    espacio (formato "v1,<base64>"), por rotación de secreto -- alcanza con
    que matchee UNA. Devuelve True/False; nunca lanza excepción (payloads
    con headers faltantes/formato raro se tratan como no verificados)."""
    if not (svix_id and svix_timestamp and svix_signature and secret):
        return False
    try:
        secreto_real = base64.b64decode(secret.split('_', 1)[1] if secret.startswith('whsec_') else secret)
        contenido = f"{svix_id}.{svix_timestamp}.{payload_bytes.decode('utf-8')}".encode('utf-8')
        firma_calculada = base64.b64encode(
            hmac.new(secreto_real, contenido, hashlib.sha256).digest()
        ).decode('utf-8')
        for parte in svix_signature.split(' '):
            valor = parte.split(',', 1)[1] if ',' in parte else parte
            if hmac.compare_digest(valor, firma_calculada):
                return True
        return False
    except Exception as e:
        print(f"[email_tracking] Error verificando firma de webhook: {e}")
        return False
