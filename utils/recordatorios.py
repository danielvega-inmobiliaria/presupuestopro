"""
Recordatorio automático de inactividad durante la prueba gratis — pedido de
Daniel 04/08/2026 (cont. 20), 3ra pata del plan para atacar el uso casi nulo
de la prueba de 14 días (ver PROYECTO.md). Antes NINGÚN mensaje volvía a
buscar a un usuario que se registró y nunca volvió — las campañas de
Admin > Seguimiento (utils/exportar_contactos.py, routes/admin.py) son 100%
manuales, Daniel tiene que entrar y mandarlas a mano una por una.

Este módulo corre periódicamente (ver app.py::_iniciar_scheduler, cada 60
minutos) y manda UN mail automático a cada usuario de prueba que, entre las
48hs y las 96hs desde que se registró, todavía no hizo NADA (0 presupuestos,
0 borradores, 0 consultas de costo/m²) — el mismo criterio que el Segmento C
de utils/exportar_contactos.py, pero disparado solo por el paso del tiempo,
sin esperar a que Daniel lo mande a mano.

Nota sobre duplicados: con 2 workers de gunicorn (ver Procfile) este job
corre en cada proceso por separado — la protección contra mandar el mail 2
veces NO es el scheduler (ambos corren igual, no hay forma simple de
compartir un único scheduler entre procesos con gunicorn prefork), es el
UPDATE atómico con `WHERE recordatorio_inactividad_enviado=0` de acá abajo:
el worker que gana la carrera marca la fila (rowcount=1) y manda el mail; el
que pierde no matchea ninguna fila (rowcount=0) y no manda nada. Funciona
sin importar cuántos workers/procesos corran el job al mismo tiempo.
"""
import os
from datetime import date, timedelta

import resend

from database import get_db
from utils.email_tracking import registrar_envio

APP_URL = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
WA_LINK = 'https://wa.me/5493417542009'

# Ventana de disparo: entre 2 y 4 días desde el registro. No es exactamente
# "a las 48hs" porque el job corre cada 60 min, no en el instante justo --
# una ventana de 2 días de margen asegura que ningún candidato se escape
# entre corridas, sin mandar el mail antes de tiempo (recién a partir del
# día 2) ni tan tarde que ya se solape con "trial por vencer" (día 14).
DIAS_MIN = 2
DIAS_MAX = 4


def _mensaje(nombre):
    nombre = nombre or ''
    return (
        f"Hola {nombre}!\n\n"
        f"Vimos que te registraste en PresupuestoPRO hace un par de días pero "
        f"todavía no armaste tu primer presupuesto. Tu prueba gratis sigue activa "
        f"(3 presupuestos o 14 días, lo que se cumpla primero) — no la dejes pasar. "
        f"Probá la App, te resuelve un presupuesto en minutos.\n\n"
        f"Entrá acá cuando quieras: {APP_URL}/login\n\n"
        f"¿Te trabaste en algún paso o tenés alguna duda? Respondé este mail o "
        f"escribinos por WhatsApp, te ayudamos a armar el primero: {WA_LINK}"
    )


def _candidatos(db):
    hoy = date.today()
    desde = (hoy - timedelta(days=DIAS_MAX)).isoformat()
    hasta = (hoy - timedelta(days=DIAS_MIN)).isoformat()
    return db.execute(
        """SELECT u.id, u.nombre, u.email
           FROM users u
           WHERE u.is_admin=0 AND u.es_trial=1 AND u.recordatorio_inactividad_enviado=0
             AND date(u.created_at) BETWEEN ? AND ?
             AND (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='completo'
                    AND (p.es_demo IS NULL OR p.es_demo=0)) = 0
             AND (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='borrador') = 0
             AND (SELECT COUNT(*) FROM costo_m2_consultas c WHERE c.user_id=u.id) = 0
        """,
        (desde, hasta)
    ).fetchall()


def enviar_recordatorios_inactividad():
    """Corre la búsqueda + el envío. Devuelve la cantidad de mails mandados
    en ESTA corrida (0 si no hay RESEND_API_KEY o no hay candidatos). Segura
    de llamar desde varios workers/procesos al mismo tiempo -- ver docstring
    del módulo."""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        return 0

    db = get_db()
    candidatos = _candidatos(db)

    enviados = 0
    resend.api_key = api_key
    for u in candidatos:
        if not u['email']:
            continue
        cur = db.execute(
            "UPDATE users SET recordatorio_inactividad_enviado=1 "
            "WHERE id=? AND recordatorio_inactividad_enviado=0",
            (u['id'],)
        )
        db.commit()
        if cur.rowcount == 0:
            continue  # otro worker ya lo tomó en esta misma corrida
        try:
            resp = resend.Emails.send({
                "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
                "to": [u['email']],
                "reply_to": ["contacto@presupuestopro.com.ar"],
                "subject": "Tu prueba gratis de PresupuestoPRO sigue activa",
                "text": _mensaje(u['nombre']),
            })
            registrar_envio(resp.get('id', ''), u['email'], 'recordatorio_inactividad')
            enviados += 1
        except Exception as e:
            print(f"[recordatorios] Error mandando a {u['email']}: {e}")
    db.close()
    return enviados


# ─── check-in de abonados nuevos (06/08/2026, pedido de Daniel) ───────────────
# 2da automatización de este módulo: a los DIAS_CHECKIN_ABONADO días de la
# PRIMERA suscripción paga (no en renovaciones), preguntar por WhatsApp cómo
# le está yendo y si tiene dudas o sugerencias. Corre en el mismo job de
# app.py::_iniciar_scheduler (cada 60 min), mismo mecanismo de protección
# contra duplicados entre workers (UPDATE atómico con
# WHERE checkin_suscripcion_enviado=0).

DIAS_CHECKIN_ABONADO = 7


def _candidatos_checkin_abonado(db):
    objetivo = (date.today() - timedelta(days=DIAS_CHECKIN_ABONADO)).isoformat()
    return db.execute(
        """SELECT u.id, u.nombre, u.telefono
           FROM users u
           WHERE u.is_admin=0 AND u.es_trial=0 AND u.active=1
             AND u.checkin_suscripcion_enviado=0
             AND u.telefono IS NOT NULL AND u.telefono != ''
             AND (SELECT COUNT(*) FROM suscripciones s
                    WHERE s.user_id=u.id AND s.estado='authorized') = 1
             AND (SELECT MIN(fecha_inicio) FROM suscripciones s
                    WHERE s.user_id=u.id AND s.estado='authorized') = ?
        """,
        (objetivo,)
    ).fetchall()


def enviar_checkin_primera_suscripcion():
    """Corre la búsqueda + el envío del check-in de WhatsApp para quien se
    suscribió por primera vez hace exactamente DIAS_CHECKIN_ABONADO días.
    Se manda UNA sola vez -- si ya tiene más de 1 suscripción 'authorized'
    (renovó), deja de ser "primera vez" y no matchea el filtro COUNT=1,
    aunque el flag siga en 0. Requiere que la plantilla
    `retencion_checkin_primera_suscripcion` esté aprobada en Meta -- si
    falla, queda el error en retencion_contactos, no rompe nada."""
    from routes.whatsapp_bot import enviar_plantilla_whatsapp

    db = get_db()
    candidatos = _candidatos_checkin_abonado(db)

    enviados = 0
    for u in candidatos:
        cur = db.execute(
            "UPDATE users SET checkin_suscripcion_enviado=1 "
            "WHERE id=? AND checkin_suscripcion_enviado=0",
            (u['id'],)
        )
        db.commit()
        if cur.rowcount == 0:
            continue  # otro worker ya lo tomó en esta misma corrida
        try:
            ok, detalle = enviar_plantilla_whatsapp(
                u['telefono'], 'retencion_checkin_primera_suscripcion',
                parametros={'nombre': u['nombre'] or ''}
            )
            db.execute(
                "INSERT INTO retencion_contactos (user_id, canal, segmento, mensaje, resultado) "
                "VALUES (?,?,?,?,?)",
                (u['id'], 'whatsapp', 'abonado_checkin',
                 'retencion_checkin_primera_suscripcion' if ok
                 else f'retencion_checkin_primera_suscripcion — ERROR: {detalle}',
                 'ok' if ok else 'error')
            )
            db.commit()
            if ok:
                enviados += 1
        except Exception as e:
            print(f"[recordatorios] Error mandando check-in a user {u['id']}: {e}")
    db.close()
    return enviados


# ─── mails de retención automáticos por tandas horarias (07/08/2026) ─────────
# Pedido de Daniel: los 6 mensajes de segmento/trigger (A/B/C/D + prueba por
# vencer) que hoy se mandan a mano desde Admin > Seguimiento, mandarlos SOLOS
# por mail (sin riesgo tipo Meta, WhatsApp queda para otra etapa) en tandas
# horarias en vez de un solo batch diario -- así se puede comparar qué
# horario responde más. HOY (07/08) es una prueba con 4 cortes en la tarde;
# de acá en más, mientras no se cambie este diccionario, corre el esquema
# estable de 2 cortes (10 y 19hs) con más volumen a las 10 -- ajustar según
# lo que midamos hoy.
#
# "Vencidos" (suscripción/prueba vencida) queda AFUERA a propósito: depende
# de la oferta 50%/48hs todavía en construcción (ver routes/pagos.py cuando
# esté), no del mensaje de soporte viejo -- mandarle las 2 cosas por
# separado sería contactar dos veces con mensajes distintos en poco tiempo.
#
# "Abonados" (categoría nueva 07/08/2026, ver routes/admin.py::_categoria)
# TAMBIÉN queda afuera: ya tienen su propio automático dedicado
# (enviar_checkin_primera_suscripcion(), a los 7 días de la primera
# suscripción) -- sumarlos acá los duplicaría con un 2do check-in genérico.
# Esta categoría queda para contacto MANUAL desde Seguimiento, a criterio
# de Daniel.
HORARIOS_BACKLOG_EMAIL = {
    '2026-08-07': [(16, 5), (17, 5), (18, 5), (19, 5)],
}
HORARIOS_BACKLOG_EMAIL_DEFAULT = [(10, 12), (19, 8)]


def _tanda_de_hoy(hora_art, fecha_str):
    horarios = HORARIOS_BACKLOG_EMAIL.get(fecha_str, HORARIOS_BACKLOG_EMAIL_DEFAULT)
    for hora, cantidad in horarios:
        if hora == hora_art:
            return cantidad
    return 0


def _candidatos_backlog_email(db, limite):
    """Reusa la misma clasificación que ya usa Admin > Seguimiento
    (_usuarios_seguimiento/_categoria/_tipo_mensaje en routes/admin.py) para
    no duplicar la lógica de segmentos -- import perezoso para no generar un
    import circular (mismo criterio que ya usa este archivo con
    routes.whatsapp_bot más arriba). Excluye 'vencidos' (ver nota arriba) y
    a cualquiera que YA tenga un envío de email registrado para ESE tipo en
    retencion_contactos (evita repetir aunque haya recibido otro tipo de
    mail antes, ej. el de bienvenida). Ordena por más antiguo primero."""
    from routes.admin import _usuarios_seguimiento, _categoria, _tipo_mensaje

    candidatos = []
    for fila in _usuarios_seguimiento():
        if not fila.get('email'):
            continue
        categoria = _categoria(fila)
        if categoria in ('vencidos', 'abonados'):
            continue
        tipo = _tipo_mensaje(fila, categoria)
        ya = db.execute(
            "SELECT 1 FROM retencion_contactos WHERE user_id=? AND canal='email' AND segmento=? LIMIT 1",
            (fila['id'], tipo)
        ).fetchone()
        if ya:
            continue
        candidatos.append((fila, tipo))

    candidatos.sort(key=lambda ft: ft[0].get('created_at') or '')
    return candidatos[:limite]


def enviar_backlog_email_segmentos():
    """Corre la tanda horaria de mails de retención. Devuelve la cantidad
    mandada en ESTA corrida (0 si no hay RESEND_API_KEY, si esta hora no
    tiene tanda asignada, o si otro worker ya corrió esta misma tanda -- ver
    envios_batch_log / migración 3j en database.py)."""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        return 0

    from datetime import datetime as _dt
    ahora_art = _dt.utcnow() - timedelta(hours=3)
    hora_art = ahora_art.hour
    fecha_str = ahora_art.date().isoformat()

    db = get_db()

    limite = _tanda_de_hoy(hora_art, fecha_str)
    if limite <= 0:
        db.close()
        return 0

    cur = db.execute(
        "INSERT OR IGNORE INTO envios_batch_log (tipo, fecha, hora) VALUES ('backlog_email', ?, ?)",
        (fecha_str, hora_art)
    )
    db.commit()
    if cur.rowcount == 0:
        db.close()
        return 0  # otro worker ya corrió esta tanda

    from routes.admin import _enviar_email_seguimiento

    candidatos = _candidatos_backlog_email(db, limite)
    enviados = 0
    for fila, tipo in candidatos:
        try:
            ok, _cuerpo = _enviar_email_seguimiento(db, fila, tipo)
            db.commit()
            if ok:
                enviados += 1
        except Exception as e:
            print(f"[recordatorios] Error mandando backlog email a user {fila.get('id')}: {e}")
    db.close()
    return enviados


# ─── recordatorio de 24hs para el link de pago con descuento (07/08/2026) ────
# Campaña de conversión 50%/48hs (vencidos D/B, ver routes/admin.py y
# routes/pagos.py). A la mitad del plazo (24hs después de generado el link),
# si todavía no pagó, se le manda UN mail avisando que quedan 24hs antes de
# perder el descuento. Por EMAIL (no WhatsApp) a pedido de Daniel -- ya
# funciona hoy sin esperar otra aprobación de Meta.
VENTANA_RECORDATORIO_PROMO_MIN = 23  # horas
VENTANA_RECORDATORIO_PROMO_MAX = 25  # horas


def _candidatos_recordatorio_promo(db):
    from datetime import datetime as _dt
    ahora = _dt.utcnow()
    desde = (ahora - timedelta(hours=VENTANA_RECORDATORIO_PROMO_MAX)).isoformat(sep=' ')
    hasta = (ahora - timedelta(hours=VENTANA_RECORDATORIO_PROMO_MIN)).isoformat(sep=' ')
    return db.execute(
        """SELECT rp.id, rp.token, rp.vence_at, u.id AS user_id, u.nombre, u.email
           FROM retencion_promos rp JOIN users u ON u.id=rp.user_id
           WHERE rp.usado=0 AND rp.recordatorio_enviado=0
             AND rp.vence_at > ?
             AND rp.creado_at BETWEEN ? AND ?
        """,
        (ahora.isoformat(sep=' '), desde, hasta)
    ).fetchall()


def enviar_recordatorio_promo_24h():
    """Corre la búsqueda + el envío del recordatorio de 24hs. Devuelve la
    cantidad mandada en ESTA corrida. Mismo mecanismo de protección contra
    duplicados entre workers que el resto del archivo (UPDATE atómico con
    WHERE recordatorio_enviado=0)."""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        return 0

    import resend
    from routes.pagos import _art_str

    db = get_db()
    candidatos = _candidatos_recordatorio_promo(db)

    app_url = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
    enviados = 0
    resend.api_key = api_key
    for p in candidatos:
        if not p['email']:
            continue
        cur = db.execute(
            "UPDATE retencion_promos SET recordatorio_enviado=1 WHERE id=? AND recordatorio_enviado=0",
            (p['id'],)
        )
        db.commit()
        if cur.rowcount == 0:
            continue  # otro worker ya lo tomó en esta misma corrida
        link = f"{app_url}/pagos/promo/{p['token']}"
        vence_str = _art_str(p['vence_at'], '%d/%m a las %H:%M')
        nombre = p['nombre'] or ''
        texto = (
            f"Hola {nombre}! Te quedan menos de 24hs para aprovechar el 50% de descuento "
            f"en tu reactivación de PresupuestoPRO. Después del {vence_str} (hora Argentina) "
            f"vuelve al precio normal.\n\nPagá acá con el descuento ya aplicado: {link}\n\n"
            f"Cualquier duda, respondé este mail o escribinos por WhatsApp: {WA_LINK}"
        )
        try:
            resp = resend.Emails.send({
                "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
                "to": [p['email']],
                "reply_to": ["contacto@presupuestopro.com.ar"],
                "subject": "Te quedan 24hs de tu 50% de descuento en PresupuestoPRO",
                "text": texto,
            })
            registrar_envio(resp.get('id', ''), p['email'], 'recordatorio_promo_24h')
            db.execute(
                "INSERT INTO retencion_contactos (user_id, canal, segmento, mensaje, resultado) VALUES (?,?,?,?,?)",
                (p['user_id'], 'email', 'recordatorio_promo_24h', texto[:500], 'ok')
            )
            db.commit()
            enviados += 1
        except Exception as e:
            print(f"[recordatorios] Error mandando recordatorio de promo a {p['email']}: {e}")
    db.close()
    return enviados
