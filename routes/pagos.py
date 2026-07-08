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


def _activar_suscripcion(db, user_id, payment_id, meses=1):
    """Activa o renueva la suscripcion del usuario por N meses."""
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
    db.execute("""
        INSERT INTO suscripciones (user_id, mp_preapproval_id, plan_nombre, monto_ars, estado, fecha_inicio, fecha_fin)
        VALUES (?, ?, 'mensual', ?, 'authorized', ?, ?)
        ON CONFLICT(mp_preapproval_id) DO UPDATE SET
            estado='authorized',
            fecha_fin=excluded.fecha_fin,
            updated_at=CURRENT_TIMESTAMP
    """, (user_id, payment_id,
          current_app.config.get('MP_PRECIO_ARS', 15000),
          hoy.isoformat(), nueva_exp.isoformat()))
    db.commit()
    logger.info(f"[MP] Usuario {user_id} activado hasta {nueva_exp}")

    # Notificar al usuario y al admin
    user_full = db.execute("SELECT email, nombre, apellido, telefono FROM users WHERE id=?", (user_id,)).fetchone()
    if user_full:
        _enviar_email_activacion(user_full['email'], user_full['nombre'], nueva_exp.isoformat())
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


# ─── rutas ────────────────────────────────────────────────────────────────────

@bp.route('/planes')
@_login_required
def planes():
    user = _get_user(session['user_id'])
    precio_ars = current_app.config.get('MP_PRECIO_ARS', 15000)
    public_key = current_app.config.get('MP_PUBLIC_KEY', '')

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
            sub_activa = sub_expires >= date.today() and bool(user['active'])
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
  .plan-card { border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,.08); }
  .price { font-size: 2.5rem; font-weight: 700; color: #0d6efd; }
</style>
</head>
<body>
<div class="container py-5">
  <h2 class="text-center mb-2">Activa tu suscripcion</h2>
  <p class="text-center text-muted mb-5">Crea presupuestos profesionales y descargalos en PDF</p>

  {% if sub_activa %}
  <div class="alert alert-success text-center">
    Tu suscripcion esta activa hasta el <strong>{{ sub_expires }}</strong>
  </div>
  {% endif %}

  {% if error %}
  <div class="alert alert-danger text-center">{{ error }}</div>
  {% endif %}

  <div class="row justify-content-center">
    <div class="col-md-5">
      <div class="card plan-card p-4">
        <div class="card-body text-center">
          <h4 class="mb-1">Plan Mensual</h4>
          <div class="price my-3">$ {{ '{:,.0f}'.format(precio_ars) }} <small class="fs-6 text-muted">ARS/mes</small></div>
          <ul class="list-unstyled text-start mb-4">
            <li>Presupuestos ilimitados</li>
            <li>PDF profesional</li>
            <li>Analisis de costos</li>
            <li>Multi-moneda</li>
            <li>Paga con cualquier billetera o tarjeta</li>
          </ul>
          {% if not sub_activa %}
          <form method="POST" action="/pagos/crear-suscripcion">
            <button type="submit" class="btn btn-primary btn-lg w-100">
              Pagar con Mercado Pago
            </button>
          </form>
          {% else %}
          <a href="/dashboard" class="btn btn-success btn-lg w-100">Ir al Dashboard</a>
          {% endif %}
        </div>
      </div>
    </div>
  </div>

  <p class="text-center mt-4 text-muted small">
    Pagos seguros procesados por Mercado Pago.<br>
    Podes pagar con cualquier tarjeta, billetera digital o efectivo.
  </p>
</div>
</body>
</html>
"""
    return render_template_string(html,
        precio_ars=precio_ars,
        public_key=public_key,
        sub_activa=sub_activa,
        sub_expires=sub_expires,
        error=request.args.get('error'))


@bp.route('/crear-suscripcion', methods=['POST'])
@_login_required
def crear_suscripcion():
    """Crea una preference de pago unico en MP y redirige al checkout."""
    user = _get_user(session['user_id'])
    sdk = _get_sdk()
    base_url = current_app.config['APP_BASE_URL']
    precio = current_app.config['MP_PRECIO_ARS']
    user_id = session['user_id']

    preference_data = {
        "items": [
            {
                "title": current_app.config['MP_PLAN_NOMBRE'],
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
      Aceptamos tarjetas, saldo Mercado Pago, transferencia bancaria y efectivo (Rapipago / Pagofacil)
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
        db = get_db()
        _activar_suscripcion(db, session['user_id'], payment_id)
        db.close()
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

    try:
        sdk = _get_sdk()
        result = sdk.payment().get(resource_id)
        payment = result.get("response", {})

        estado   = payment.get("status", "")
        metadata = payment.get("metadata", {})
        payer    = payment.get("payer", {})
        payer_email = payer.get("email", "")
        user_id_meta = metadata.get("user_id")

        logger.info(f"[MP Webhook] payment {resource_id} estado={estado} email={payer_email} user_id_meta={user_id_meta}")

        if estado != "approved":
            return jsonify({"ok": True}), 200

        db = get_db()
        user = None
        if user_id_meta:
            user = db.execute("SELECT id FROM users WHERE id=?", (user_id_meta,)).fetchone()
        if not user and payer_email:
            user = db.execute("SELECT id FROM users WHERE email=?", (payer_email,)).fetchone()

        if user:
            _activar_suscripcion(db, user['id'], str(resource_id))
            logger.info(f"[MP Webhook] Usuario {user['id']} activado por payment {resource_id}")
        else:
            logger.warning(f"[MP Webhook] Usuario no encontrado: email={payer_email} meta_id={user_id_meta}")

        db.close()

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
