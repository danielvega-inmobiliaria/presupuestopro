"""
Blueprint: pagos
Integración Mercado Pago — Pago único (Preference)

Rutas:
  GET  /pagos/planes              → página de planes/precios
  POST /pagos/crear-suscripcion   → crea preference en MP y redirige al usuario
  GET  /pagos/retorno             → landing tras pago (success / pending / failure)
  POST /pagos/webhook             → notificaciones de MP
  GET  /pagos/estado              → estado de suscripción del usuario actual
"""

import json
import logging
import os
from datetime import datetime, date, timedelta
from functools import wraps

import mercadopago
import resend
from flask import (Blueprint, current_app, g, jsonify, redirect,
                   render_template_string, request, session, url_for)

from database import get_db

bp = Blueprint('pagos', __name__, url_prefix='/pagos')
logger = logging.getLogger(__name__)

# ─── helpers ──────────────────────────────────────────────────────────────────

def _get_sdk():
    return mercadopago.SDK(current_app.config['MP_ACCESS_TOKEN'])


def _login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def _get_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    db.close()
    return user


def _enviar_email_activacion(user_email, user_nombre, fecha_vencimiento):
    """Envia email de bienvenida/activacion al usuario."""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        logger.warning("[Email] RESEND_API_KEY no configurada, no se envio email de activacion")
        return False
    try:
        resend.api_key = api_key
        nombre_display = user_nombre or user_email.split('@')[0]
        app_url = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
        admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')

        html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;color:#222">
  <h2 style="color:#1a56db;margin-bottom:4px">Tu cuenta esta activa!</h2>
  <p style="color:#555;margin-top:4px">Hola <strong>{nombre_display}</strong>,</p>
  <p>Tu suscripcion a <strong>PresupuestoPRO</strong> fue activada correctamente.</p>
  <div style="background:#f0f5ff;border-radius:10px;padding:16px;margin:20px 0">
    <p style="margin:0 0 8px 0">Email: <strong>{user_email}</strong></p>
    <p style="margin:0 0 8px 0">Activa hasta: <strong>{fecha_vencimiento}</strong></p>
  </div>
  <p>Usa el email y la contrasena que elegiste al registrarte para ingresar:</p>
  <div style="text-align:center;margin:24px 0">
    <a href="{app_url}/login"
       style="background:#1a56db;color:#fff;padding:12px 28px;border-radius:8px;
              text-decoration:none;font-weight:bold;font-size:16px">
      Ingresar a la app
    </a>
  </div>
  <p style="color:#888;font-size:.85rem">
    Si olvidaste tu contrasena, podes restablecerla desde la pantalla de login.
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
  <p style="color:#aaa;font-size:.78rem;text-align:center">PresupuestoPRO - Argentina</p>
</div>"""

        # Intentar enviar al usuario; si falla (ej: restricción dominio Resend),
        # enviar al admin como notificación para que avise manualmente.
        try:
            resend.Emails.send({
                "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
                "to": [user_email],
                "subject": "Tu cuenta de PresupuestoPRO esta activa",
                "html": html_body,
            })
            logger.info(f"[Email] Activacion enviada a usuario: {user_email}")
            return True
        except Exception as e_user:
            logger.warning(f"[Email] No se pudo enviar al usuario {user_email}: {type(e_user).__name__}: {e_user}")
            # Fallback: notificar al admin con los datos para que avise por WA
            try:
                resend.Emails.send({
                    "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
                    "to": [admin_email],
                    "subject": f"[PresupuestoPRO] Activar manualmente a {user_email}",
                    "text": f"No se pudo enviar email al usuario.\n\nDatos para notificar por WhatsApp:\n\nUsuario: {nombre_display}\nEmail: {user_email}\nVence: {fecha_vencimiento}\nLink: {app_url}/login\n\nError original: {e_user}",
                })
                logger.info(f"[Email] Notificacion de activacion enviada al admin para {user_email}")
                return False  # retorna False para que el flash muestre aviso
            except Exception as e_admin:
                logger.error(f"[Email] Fallo total: usuario={e_user} admin={e_admin}")
                return False
    except Exception as e:
        logger.error(f"[Email] Error general: {type(e).__name__}: {e}")
        return False


def _activar_suscripcion(db, user_id, payment_id, meses=1, plan_nombre='mensual', monto_ars=None):
    """Activa o renueva la suscripcion del usuario por N meses.

    Fix 05/08/2026 (bug reportado por Daniel: pagó 1 mes y le quedó vencimiento
    a 2 meses). Causa: un mismo pago aprobado dispara ESTA función 2 veces —
    una vez desde /retorno (cuando MP redirige al navegador del usuario con
    status=approved) y otra vez desde /webhook (notificación server-to-server
    de MP), sin ninguna verificación de que ya se había procesado. Cada
    llamada suma 30*meses días sobre el vencimiento actual (`base = max(...)`
    ya toma el valor recién actualizado por la primera llamada), así que 1
    pago aprobado terminaba sumando 60 días en vez de 30. Fix: si ya existe
    una fila en `suscripciones` con este mismo `payment_id`, no se vuelve a
    sumar (idempotente por pago) — solo una renovación real (pago nuevo, con
    payment_id distinto el mes que viene) vuelve a extender la fecha."""
    ya_procesado = db.execute(
        "SELECT 1 FROM suscripciones WHERE mp_preapproval_id=?", (str(payment_id),)
    ).fetchone()
    if ya_procesado:
        logger.info(f"[MP] payment_id {payment_id} ya procesado antes, no se vuelve a sumar vencimiento (usuario {user_id}).")
        return
    hoy = date.today()
    user = db.execute("SELECT email, nombre, subscription_expires FROM users WHERE id=?", (user_id,)).fetchone()
    if user and user['subscription_expires']:
        try:
            base = datetime.strptime(user['subscription_expires'], '%Y-%m-%d').date()
            base = max(base, hoy)
        except Exception:
            base = hoy
    else:
        base = hoy
    nueva_exp = base + timedelta(days=30 * meses)

    # Fix 07/07/2026: se agrega es_trial=0 — un pago real convierte la cuenta
    # de prueba en cuenta paga de forma definitiva. Antes quedaba es_trial=1
    # para siempre, así que get_trial_status()/trial_required() lo seguían
    # bloqueando (por los 3 presupuestos o los 14 días) aunque ya hubiera
    # pagado, y /pagos/planes seguía sin reconocer la suscripción como activa.
    db.execute(
        "UPDATE users SET active=1, subscription_expires=?, mp_preapproval_id=?, es_trial=0 WHERE id=?",
        (nueva_exp.isoformat(), payment_id, user_id)
    )
    # Fix 06/08/2026: antes `plan_nombre` quedaba hardcodeado 'mensual' y
    # `monto_ars` salía siempre de MP_PRECIO_ARS (el precio único viejo) --
    # ahora que hay 4 planes por duración (MP_PLANES), cada uno guarda su
    # propio nombre/monto real. Si no se pasa nada (compatibilidad con algún
    # llamado viejo), cae al comportamiento anterior.
    if monto_ars is None:
        monto_ars = current_app.config.get('MP_PRECIO_ARS', 15000)
    db.execute("""
        INSERT INTO suscripciones (user_id, mp_preapproval_id, plan_nombre, monto_ars, estado, fecha_inicio, fecha_fin)
        VALUES (?, ?, ?, ?, 'authorized', ?, ?)
        ON CONFLICT(mp_preapproval_id) DO UPDATE SET
            estado='authorized',
            fecha_fin=excluded.fecha_fin,
            updated_at=CURRENT_TIMESTAMP
    """, (user_id, payment_id, plan_nombre, monto_ars,
          hoy.isoformat(), nueva_exp.isoformat()))
    db.commit()
    logger.info(f"[MP] Usuario {user_id} activado hasta {nueva_exp}")

    # Notificar al usuario y al admin
    # Fix 06/08/2026 (bug encontrado de paso, reportado y confirmado con
    # Daniel): acá había una llamada a _enviar_email_activacion() ADEMÁS de
    # la de más abajo ("Enviar notificacion al usuario") -- el mail de
    # "tu cuenta está activa" se mandaba 2 VECES por cada pago, y encima con
    # fechas en formato distinto (acá salía ISO "2026-08-06", abajo
    # "06/08/2026"). Se saca esta llamada duplicada y se deja una sola, la
    # de abajo (que ya tenía el formato de fecha correcto para mostrar).
    user_full = db.execute("SELECT email, nombre, apellido, telefono FROM users WHERE id=?", (user_id,)).fetchone()
    if user_full:
        # Siempre notificar al admin también
        try:
            api_key = os.environ.get('RESEND_API_KEY')
            admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')
            app_url = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
            if api_key:
                resend.api_key = api_key
                nombre_display = f"{user_full['nombre'] or ''} {user_full.get('apellido') or ''}".strip() or user_full['email']
                tel = user_full.get('telefono') or 'sin teléfono'
                resend.Emails.send({
                    "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
                    "to": [admin_email],
                    "subject": f"[PresupuestoPRO] Pago aprobado — {nombre_display}",
                    "text": (
                        f"Se activó una suscripción nueva.\n\n"
                        f"Usuario:   {nombre_display}\n"
                        f"Email:     {user_full['email']}\n"
                        f"Teléfono:  {tel}\n"
                        f"Vence:     {nueva_exp.isoformat()}\n"
                        f"Payment:   {payment_id}\n\n"
                        f"WhatsApp: https://wa.me/549{tel.replace(' ','').replace('-','').replace('+','')}\n"
                        f"Link login: {app_url}/login"
                    ),
                })
                logger.info(f"[Email] Admin notificado por activacion de {user_full['email']}")
        except Exception as e_admin:
            logger.warning(f"[Email] No se pudo notificar al admin: {e_admin}")

    # Enviar notificacion al usuario
    if user:
        _enviar_email_activacion(
            user_email=user['email'],
            user_nombre=user['nombre'],
            fecha_vencimiento=nueva_exp.strftime('%d/%m/%Y'),
        )

    # NUEVO 06/08/2026, pedido de Daniel: agradecimiento automático por
    # WhatsApp al confirmarse CUALQUIER pago (alta nueva o renovación) --
    # plantilla `retencion_agradecimiento_suscripcion` (Meta), ver
    # RETENCION_USUARIOS/PROYECTO.md. No bloquea el flujo de pago si falla
    # (ej. plantilla todavía no aprobada en Meta) -- solo queda el error
    # registrado en retencion_contactos para revisar en Admin > Seguimiento.
    if user_full and user_full['telefono']:
        try:
            from routes.whatsapp_bot import enviar_plantilla_whatsapp
            ok_wa, detalle_wa = enviar_plantilla_whatsapp(
                user_full['telefono'], 'retencion_agradecimiento_suscripcion',
                parametros={'nombre': user_full['nombre'] or ''}
            )
            db.execute(
                "INSERT INTO retencion_contactos (user_id, canal, segmento, mensaje, resultado) "
                "VALUES (?,?,?,?,?)",
                (user_id, 'whatsapp', 'abonado_gracias',
                 'retencion_agradecimiento_suscripcion' if ok_wa
                 else f'retencion_agradecimiento_suscripcion — ERROR: {detalle_wa}',
                 'ok' if ok_wa else 'error')
            )
            db.commit()
            if not ok_wa:
                logger.warning(f"[WA] agradecimiento no enviado a user {user_id}: {detalle_wa}")
        except Exception as e:
            logger.warning(f"[WA] Error mandando agradecimiento a user {user_id}: {e}")


def _procesar_pago_por_id(payment_id):
    """Consulta el pago directamente en MP por su ID y, si está aprobado,
    activa la suscripción con los datos que MP tiene guardados (metadata:
    user_id, plan, meses) — fuente única de verdad tanto para /retorno como
    para /webhook.

    Agregado 06/08/2026 al sumar los 4 planes por duración: antes /retorno
    llamaba a _activar_suscripcion() con meses=1 SIEMPRE (hardcodeado, sin
    leer qué plan se pagó en realidad), confiando en la sesión del navegador.
    Eso es fragil para 2 casos reales que ya soporta la pantalla de pago:
    (a) alguien paga desde el link compartido en otro dispositivo/sesión, sin
    el `session` del usuario que lo generó, y (b) si /retorno llegara a
    procesar el pago ANTES que /webhook con un meses incorrecto, la
    deduplicación por payment_id (fix 05/08) haría que /webhook, con el dato
    correcto, ya no pueda corregirlo. Consultar el pago por API en los 2
    lugares evita ambos problemas: los meses/plan siempre salen del lado
    servidor↔MP, nunca de un query param o de la sesión."""
    sdk = _get_sdk()
    result = sdk.payment().get(payment_id)
    payment = result.get("response", {})

    estado = payment.get("status", "")
    if estado != "approved":
        logger.info(f"[MP] payment {payment_id} estado={estado!r}, no se activa nada.")
        return False

    metadata    = payment.get("metadata", {}) or {}
    payer       = payment.get("payer", {}) or {}
    payer_email = payer.get("email", "")
    user_id_meta = metadata.get("user_id")
    plan_key    = metadata.get("plan") or 'mensual'
    try:
        meses = int(metadata.get("meses") or 1)
    except (TypeError, ValueError):
        meses = 1

    planes_cfg = current_app.config.get('MP_PLANES', {})
    plan_info  = planes_cfg.get(plan_key, {})
    plan_nombre = plan_info.get('nombre', plan_key)
    monto_ars   = plan_info.get('precio_total')

    db = get_db()
    user = None
    if user_id_meta:
        user = db.execute("SELECT id FROM users WHERE id=?", (user_id_meta,)).fetchone()
    if not user and payer_email:
        user = db.execute("SELECT id FROM users WHERE email=?", (payer_email,)).fetchone()

    if user:
        _activar_suscripcion(db, user['id'], str(payment_id), meses=meses,
                              plan_nombre=plan_nombre, monto_ars=monto_ars)
        logger.info(f"[MP] Usuario {user['id']} activado por payment {payment_id} (plan={plan_key}, meses={meses})")
    else:
        logger.warning(f"[MP] Usuario no encontrado para payment {payment_id}: email={payer_email} meta_id={user_id_meta}")
    db.close()
    return bool(user)


# ─── rutas ────────────────────────────────────────────────────────────────────

@bp.route('/planes')
@_login_required
def planes():
    """Fix 06/08/2026: antes había 1 solo plan mensual (botón único). Ahora
    muestra los 4 planes de MP_PLANES (config.py) — pago único por duración,
    sin renovación automática, mismo esquema que el competidor Sismat (ver
    UNIFICACION_PRESUPUESTOPRO/PROYECTO.md, Ideas Futuras 05-06/08). Se le
    calcula acá el % de ahorro de cada plan contra pagar mes a mes al precio
    del plan mensual, para mostrar el badge "Ahorrás X%"."""
    user = _get_user(session['user_id'])
    public_key = current_app.config.get('MP_PUBLIC_KEY', '')
    planes_cfg = current_app.config.get('MP_PLANES', {})
    precio_mensual_base = planes_cfg.get('mensual', {}).get('precio_mes', 0)

    planes_lista = []
    for clave, p in planes_cfg.items():
        costo_mes_a_mes = precio_mensual_base * p['meses']
        ahorro_pct = 0
        if costo_mes_a_mes > 0:
            ahorro_pct = round((costo_mes_a_mes - p['precio_total']) / costo_mes_a_mes * 100)
        planes_lista.append({
            'clave': clave,
            'nombre': p['nombre'],
            'meses': p['meses'],
            'precio_mes': p['precio_mes'],
            'precio_total': p['precio_total'],
            'destacado': p.get('destacado', False),
            'ahorro_pct': ahorro_pct,
        })
    # Orden fijo por duración (el dict de Python ya respeta orden de
    # inserción, pero se ordena explícito por las dudas).
    orden = {'mensual': 0, 'trimestral': 1, 'semestral': 2, 'anual': 3}
    planes_lista.sort(key=lambda p: orden.get(p['clave'], 99))

    sub_activa = False
    sub_expires = None
    # Fix 07/07/2026: en cuentas de prueba (es_trial=1), `subscription_expires`
    # guarda la FECHA LÍMITE DE LA PRUEBA (hoy+14 días al registrarse), no una
    # suscripción paga — antes esta pantalla comparaba esa fecha contra hoy y
    # mostraba "Tu suscripción está activa hasta..." aunque el usuario nunca
    # pagó nada (y aunque ya se le haya vencido la prueba por los 3
    # presupuestos, antes de llegar al día 14). Mientras es_trial=1, nunca se
    # considera "activa" acá — siempre se muestra el botón para pagar. Una vez
    # que paga de verdad, _activar_suscripcion() pone es_trial=0 y a partir de
    # ahí sí vale la fecha de subscription_expires.
    if user and not user['es_trial'] and user['subscription_expires']:
        try:
            sub_expires = datetime.strptime(user['subscription_expires'], '%Y-%m-%d').date()
            # Fix 07/08/2026 (cont. 24): date.today() usa la hora del servidor
            # (Railway = UTC), no ART -- en la franja 21:00-23:59 ART del día
            # exacto de vencimiento, mostraba "hay que pagar" hasta 3hs antes
            # de tiempo. Mismo ajuste -3hs que ya se aplicó en utils/auth.py
            # y routes/admin.py para el mismo problema.
            hoy_ar = (datetime.utcnow() - timedelta(hours=3)).date()
            sub_activa = sub_expires >= hoy_ar and bool(user['active'])
        except Exception:
            pass

    html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>PresupuestoPRO - Planes</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { background: #f8f9fa; }
  .plan-card { border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,.08); border: 2px solid transparent; height: 100%; }
  .plan-card.destacado { border-color: #0d6efd; box-shadow: 0 8px 32px rgba(13,110,253,.18); transform: scale(1.03); }
  .badge-destacado { position: absolute; top: -14px; left: 50%; transform: translateX(-50%);
                      background: #0d6efd; color: #fff; padding: 4px 16px; border-radius: 20px;
                      font-size: .78rem; font-weight: 700; white-space: nowrap; }
  .badge-ahorro { background: #d1f5e0; color: #0a7a3d; font-size: .74rem; font-weight: 700;
                   padding: 3px 10px; border-radius: 20px; display: inline-block; }
  .price { font-size: 2.1rem; font-weight: 700; color: #0d1e3c; }
  .price-total { font-size: .82rem; color: #888; }
  .plan-card .card-body { position: relative; }
</style>
</head>
<body>
<div class="container py-5">
  <h2 class="text-center mb-2">Elegí tu plan</h2>
  <p class="text-center text-muted mb-5">Pago único, sin renovación automática — vos decidís cuándo volver a pagar</p>

  {% if sub_activa %}
  <div class="alert alert-success text-center">
    Tu suscripcion esta activa hasta el <strong>{{ sub_expires }}</strong>
  </div>
  {% endif %}

  {% if error %}
  <div class="alert alert-danger text-center">{{ error }}</div>
  {% endif %}

  <div class="row justify-content-center g-4">
    {% for p in planes %}
    <div class="col-6 col-md-3">
      <div class="card plan-card p-3 {{ 'destacado' if p.destacado else '' }}">
        {% if p.destacado %}<span class="badge-destacado">Más elegido</span>{% endif %}
        <div class="card-body text-center px-1">
          <h5 class="mb-1">{{ p.nombre }}</h5>
          <div class="price my-2">$ {{ '{:,.0f}'.format(p.precio_mes) }}<small class="fs-6 text-muted">/mes</small></div>
          <div class="price-total mb-2">
            Total $ {{ '{:,.0f}'.format(p.precio_total) }} ({{ p.meses }} {{ 'mes' if p.meses == 1 else 'meses' }})
          </div>
          {% if p.ahorro_pct > 0 %}
          <div class="mb-3"><span class="badge-ahorro">Ahorrás {{ p.ahorro_pct }}%</span></div>
          {% else %}
          <div class="mb-3">&nbsp;</div>
          {% endif %}
          {% if not sub_activa %}
          <form method="POST" action="/pagos/crear-suscripcion">
            <input type="hidden" name="plan" value="{{ p.clave }}">
            <button type="submit" class="btn {{ 'btn-primary' if p.destacado else 'btn-outline-primary' }} w-100">
              Elegir
            </button>
          </form>
          {% else %}
          <a href="/dashboard" class="btn btn-success w-100">Ir al Dashboard</a>
          {% endif %}
        </div>
      </div>
    </div>
    {% endfor %}
  </div>

  <ul class="list-unstyled text-center text-muted mt-5 mb-3 small">
    <li>Presupuestos ilimitados · PDF profesional · Análisis de costos · Multi-moneda</li>
  </ul>
  <p class="text-center text-muted small">
    Pagos seguros procesados por Mercado Pago.<br>
    Podes pagar con dinero en cuenta, tarjeta de debito/credito (en cuotas) o efectivo en Rapipago/Pago Facil.
  </p>
</div>
</body>
</html>
"""
    return render_template_string(html,
        planes=planes_lista,
        public_key=public_key,
        sub_activa=sub_activa,
        sub_expires=sub_expires,
        error=request.args.get('error'))


@bp.route('/crear-suscripcion', methods=['POST'])
@_login_required
def crear_suscripcion():
    """Crea una preference de pago unico en MP y redirige al checkout.

    Fix 06/08/2026: antes el precio/nombre salían fijos de MP_PRECIO_ARS/
    MP_PLAN_NOMBRE (1 solo plan). Ahora lee qué plan eligió el usuario en
    /pagos/planes (campo `plan` del form) contra MP_PLANES — si viene vacío o
    inválido, cae a 'mensual' por las dudas (nunca deja pasar un plan que no
    exista en la config). `meses` y `plan` quedan en el metadata del pago
    para que /retorno y /webhook (vía _procesar_pago_por_id) sepan cuánto
    tiempo sumar sin tener que confiar en la sesión del navegador."""
    user = _get_user(session['user_id'])
    sdk = _get_sdk()
    base_url = current_app.config['APP_BASE_URL']
    user_id = session['user_id']

    planes_cfg = current_app.config.get('MP_PLANES', {})
    plan_key = request.form.get('plan', 'mensual')
    if plan_key not in planes_cfg:
        plan_key = 'mensual'
    plan_info = planes_cfg.get(plan_key, {'nombre': current_app.config['MP_PLAN_NOMBRE'],
                                           'precio_total': current_app.config['MP_PRECIO_ARS'],
                                           'meses': 1})
    precio = plan_info['precio_total']

    preference_data = {
        "items": [
            {
                "title": f"PresupuestoPRO — {plan_info['nombre']}",
                "quantity": 1,
                "unit_price": float(precio),
                "currency_id": "ARS",
            }
        ],
        "payer": {
            "email": user['email'],
        },
        "back_urls": {
            "success": f"{base_url}/pagos/retorno?status=approved",
            "pending": f"{base_url}/pagos/retorno?status=pending",
            "failure": f"{base_url}/pagos/retorno?status=failure",
        },
        "auto_return": "approved",
        "metadata": {
            "user_id": user_id,
            "app": "presupuestopro",
            "plan": plan_key,
            "meses": plan_info['meses'],
        },
        "statement_descriptor": "PRESUPUESTOPRO",
        "expires": False,
        "notification_url": f"{base_url}/pagos/webhook",
    }

    result = sdk.preference().create(preference_data)
    response = result.get("response", {})

    if result.get("status") not in (200, 201) or "init_point" not in response:
        logger.error(f"[MP] Error creando preference: {result}")
        return redirect(url_for('pagos.planes') + '?error=Error+al+generar+el+link+de+pago')

    preference_id = response.get("id")
    session['mp_preference_id'] = preference_id
    logger.info(f"[MP] Preference {preference_id} creada para user {user_id}")

    init_point = response.get("init_point")

    html_link = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>PresupuestoPRO - Tu link de pago</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { background: #f0f5ff; }
  .card { border-radius: 20px; box-shadow: 0 8px 32px rgba(26,86,219,.1); }
  .link-box { background: #f8f9fa; border: 1.5px solid #d1d5db; border-radius: 10px;
              padding: 12px 14px; font-size: .85rem; word-break: break-all;
              color: #374151; font-family: monospace; }
</style>
</head>
<body>
<div class="container py-5">
  <div class="card p-4 mx-auto" style="max-width:480px">
    <h4 class="fw-bold mb-1 text-center">Tu link de pago</h4>
    <p class="text-muted text-center mb-4" style="font-size:.9rem">
      Podes pagar vos directamente o enviar este link a otra persona para que pague por vos.
      Una vez abonado, tu cuenta queda activa automaticamente.
    </p>

    <div class="link-box mb-3" id="linkPago">{{ init_point }}</div>

    <button class="btn btn-outline-secondary w-100 mb-3" onclick="copiarLink()">
      Copiar link para compartir
    </button>

    <a href="{{ init_point }}" class="btn btn-primary btn-lg w-100">
      Pagar ahora
    </a>

    <p class="text-center text-muted mt-3" style="font-size:.78rem">
      Aceptamos tarjetas de debito/credito, dinero en cuenta de Mercado Pago y efectivo (Rapipago / Pago Facil)
    </p>
  </div>
</div>
<script>
function copiarLink() {
  const txt = document.getElementById('linkPago').innerText;
  navigator.clipboard.writeText(txt).then(() => {
    const btn = event.target;
    btn.textContent = 'Link copiado!';
    setTimeout(() => { btn.textContent = 'Copiar link para compartir'; }, 2500);
  });
}
</script>
</body></html>
"""
    from flask import render_template_string as rts
    return rts(html_link, init_point=init_point)


@bp.route('/retorno')
@_login_required
def retorno():
    """Landing post-pago."""
    status          = request.args.get('status') or request.args.get('collection_status', '')
    payment_id      = request.args.get('payment_id') or request.args.get('collection_id', '')
    preference_id   = request.args.get('preference_id') or session.pop('mp_preference_id', None)

    if status == 'approved' and payment_id:
        # Fix 06/08/2026: antes llamaba a _activar_suscripcion() con meses=1
        # fijo, sin importar qué plan se pagó -- ver docstring completo en
        # _procesar_pago_por_id() más arriba.
        try:
            _procesar_pago_por_id(payment_id)
        except Exception as e:
            logger.error(f"[MP retorno] Error procesando {payment_id}: {e}")
        mensaje = "Pago aprobado! Ya podes usar PresupuestoPRO."
        tipo = "success"
    elif status == 'pending':
        mensaje = "Tu pago esta pendiente de acreditacion. Te avisaremos cuando se confirme."
        tipo = "warning"
    else:
        mensaje = "El pago no se completo. Podes intentarlo de nuevo."
        tipo = "danger"

    html = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>PresupuestoPRO - Estado de pago</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="manifest" href="/static/manifest.json">
</head><body><div class="container py-5 text-center">
<div class="alert alert-{{ tipo }} fs-5">{{ mensaje }}</div>
{% if tipo == 'success' %}
<p class="text-muted">Guarda la app en tu celular para acceder siempre rapido.</p>
<button id="btnInstalar" class="btn btn-outline-primary mb-3" style="display:none">
  Agregar al inicio del celular
</button>
{% endif %}
<a href="/dashboard" class="btn btn-primary mt-2">Ir al Dashboard</a>
<a href="/pagos/planes" class="btn btn-outline-secondary mt-2 ms-2">Ver planes</a>
</div>
<script>
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const btn = document.getElementById('btnInstalar');
  if (btn) btn.style.display = 'inline-block';
});
document.getElementById('btnInstalar')?.addEventListener('click', async () => {
  if (deferredPrompt) {
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
  }
});
</script>
</body></html>
"""
    return render_template_string(html, mensaje=mensaje, tipo=tipo)


@bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Webhook de MP. Para pagos unicos (preference) llega:
      { "type": "payment", "data": { "id": "PAYMENT_ID" } }
    """
    data      = request.get_json(silent=True) or {}
    topic     = data.get("type") or request.args.get("topic", "")
    resource_id = (data.get("data", {}).get("id")
                   or request.args.get("id")
                   or request.args.get("payment_id"))

    logger.info(f"[MP Webhook] topic={topic} id={resource_id}")

    if not resource_id:
        return jsonify({"ok": True}), 200

    if topic not in ("payment", "merchant_order"):
        return jsonify({"ok": True}), 200

    # Fix 06/08/2026: antes esta ruta consultaba el pago por API acá mismo y
    # duplicaba (con otro código) exactamente lo que hace /retorno -- ahora
    # las 2 comparten _procesar_pago_por_id(), que ya lee meses/plan del
    # metadata en vez de asumir 1 mes siempre.
    try:
        _procesar_pago_por_id(resource_id)
    except Exception as e:
        logger.error(f"[MP Webhook] Error procesando {resource_id}: {e}")

    return jsonify({"ok": True}), 200


@bp.route('/estado')
@_login_required
def estado():
    user = _get_user(session['user_id'])
    sub_activa = False
    dias_restantes = 0
    expires = None

    # Fix 07/07/2026: mismo criterio que planes() — mientras es_trial=1,
    # subscription_expires es la fecha límite de la prueba, no una suscripción
    # paga (este endpoint no está en uso desde ningún template hoy, se corrige
    # igual por las dudas de que se conecte a futuro).
    if user and not user['es_trial'] and user['subscription_expires']:
        try:
            exp = datetime.strptime(user['subscription_expires'], '%Y-%m-%d').date()
            expires = exp.isoformat()
            dias_restantes = (exp - date.today()).days
            sub_activa = dias_restantes >= 0 and bool(user['active'])
        except Exception:
            pass

    return jsonify({
        "activa": sub_activa,
        "expires": expires,
        "dias_restantes": dias_restantes,
        "email": user['email'] if user else None,
    })
