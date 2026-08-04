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
