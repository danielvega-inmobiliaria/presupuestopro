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
    """Envía email de bienvenida/activación al usuario."""
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        logger.warning("[Email] RESEND_API_KEY no configurada, no se envió email de activación")
        return False
    try:
        resend.api_key = api_key
        nombre_display = user_nombre or user_email.split('@')[0]
        app_url = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
        resend.Emails.send({
            "from": "PresupuestoPRO <onboarding@resend.dev>",
            "to": [user_email],
            "subject": "✅ Tu cuenta de PresupuestoPRO está activa",
            "html": f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;color:#222">
  <h2 style="color:#1a56db;margin-bottom:4px">¡Tu cuenta está activa! 🎉</h2>
  <p style="color:#555;margin-top:4px">Hola <strong>{nombre_display}</strong>,</p>
  <p>Tu suscripción a <strong>PresupuestoPRO</strong> fue activada correctamente.</p>

  <div style="background:#f0f5ff;border-radius:10px;padding:16px;margin:20px 0">
    <p style="margin:0 0 8px 0">📧 <strong>Email:</strong> {user_email}</p>
    <p style="margin:0 0 8px 0">📅 <strong>Activa hasta:</strong> {fecha_vencimiento}</p>
  </div>

  <p>Usá el email y la contraseña que elegiste al registrarte para ingresar:</p>

  <div style="text-align:center;margin:24px 0">
    <a href="{app_url}/auth/login"
       style="background:#1a56db;color:#fff;padding:12px 28px;border-radius:8px;
              text-decoration:none;font-weight:bold;font-size:16px">
      Ingresar a la app →
    </a>
  </div>

  <p style="color:#888;font-size:.85rem">
    Si olvidaste tu contraseña, podés restablecerla desde la pantalla de login.<br>
    Ante cualquier consulta respondé este email o escribinos por WhatsApp.
  </p>
  <hr style="border:none;border-top:1px solid #eee;margin:20px 0">
  <p style="color:#aaa;font-size:.78rem;text-align:center">PresupuestoPRO · Argentina</p>
</div>
""",
        })
        logger.info(f"[Email] Email de activación enviado a {user_email}")
        return True
    except Exception as e:
        logger.error(f"[Email] Error enviando activación a {user_email}: {e}")
        return False


def _activar_suscripcion(db, user_id, payment_id, meses=1):
    """Activa o renueva la suscripción del usuario por N meses."""
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

    db.execute(
        "UPDATE users SET active=1, subscription_expires=?, mp_preapproval_id=? WHERE id=?",
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

    # Enviar notificación al usuario
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
    if user and user['subscription_expires']:
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
<title>PresupuestoPRO — Planes</title>
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
  <h2 class="text-center mb-2">Activá tu suscripción</h2>
  <p class="text-center text-muted mb-5">Creá presupuestos profesionales y descargalos en PDF</p>

  {% if sub_activa %}
  <div class="alert alert-success text-center">
    ✅ Tu suscripción está activa hasta el <strong>{{ sub_expires }}</strong>
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
            <li>✅ Presupuestos ilimitados</li>
            <li>✅ PDF profesional</li>
            <li>✅ Análisis de costos</li>
            <li>✅ Multi-moneda</li>
            <li>💳 Pagá con cualquier billetera o tarjeta</li>
          </ul>
          {% if not sub_activa %}
          <form method="POST" action="/pagos/crear-suscripcion">
            <button type="submit" class="btn btn-primary btn-lg w-100">
              Pagar con Mercado Pago
            </button>
          </form>
          {% else %}
          <a href="/dashboard" class="btn btn-success btn-lg w-100">Ir al Dashboard →</a>
          {% endif %}
        </div>
      </div>
    </div>
  </div>

  <p class="text-center mt-4 text-muted small">
    Pagos seguros procesados por Mercado Pago.<br>
    Podés pagar con cualquier tarjeta, billetera digital o efectivo.
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
    """Crea una preference de pago único en MP y redirige al checkout."""
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
        # Guardamos el user_id en metadata para recuperarlo en el webhook
        "metadata": {
            "user_id": user_id,
            "app": "presupuestopro",
        },
        "statement_descriptor": "PRESUPUESTOPRO",
        "expires": False,
    }

    result = sdk.preference().create(preference_data)
    response = result.get("response", {})

    if result.get("status") not in (200, 201) or "init_point" not in response:
        logger.error(f"[MP] Error creando preference: {result}")
        return redirect(url_for('pagos.planes') + '?error=Error+al+generar+el+link+de+pago')

    # Guardar preference_id en sesión para recuperar en retorno
    preference_id = response.get("id")
    session['mp_preference_id'] = preference_id
    logger.info(f"[MP] Preference {preference_id} creada para user {user_id}")

    init_point = response.get("init_point")

    # Página intermedia: mostrar link de pago compartible
    html_link = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>PresupuestoPRO — Tu link de pago</title>
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
    <h4 class="fw-bold mb-1 text-center">💳 Tu link de pago</h4>
    <p class="text-muted text-center mb-4" style="font-size:.9rem">
      Podés pagar vos directamente o enviar este link a otra persona para que pague por vos.
      Una vez abonado, tu cuenta queda activa automáticamente.
    </p>

    <div class="link-box mb-3" id="linkPago">{{ init_point }}</div>

    <button class="btn btn-outline-secondary w-100 mb-3" onclick="copiarLink()">
      📋 Copiar link para compartir
    </button>

    <a href="{{ init_point }}" class="btn btn-primary btn-lg w-100">
      Pagar ahora →
    </a>

    <p class="text-center text-muted mt-3" style="font-size:.78rem">
      Aceptamos tarjetas, saldo Mercado Pago, transferencia bancaria y efectivo (Rapipago / Pagofácil)
    </p>
  </div>
</div>
<script>
function copiarLink() {
  const txt = document.getElementById('linkPago').innerText;
  navigator.clipboard.writeText(txt).then(() => {
    const btn = event.target;
    btn.textContent = '✅ ¡Link copiado!';
    setTimeout(() => { btn.textContent = '📋 Copiar link para compartir'; }, 2500);
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
    """
    Landing post-pago. MP envía:
      ?collection_id=...&collection_status=approved&payment_id=...&status=approved&preference_id=...
    """
    status          = request.args.get('status') or request.args.get('collection_status', '')
    payment_id      = request.args.get('payment_id') or request.args.get('collection_id', '')
    preference_id   = request.args.get('preference_id') or session.pop('mp_preference_id', None)

    if status == 'approved' and payment_id:
        # Activación inmediata desde la URL de retorno
        db = get_db()
        _activar_suscripcion(db, session['user_id'], payment_id)
        db.close()
        mensaje = "✅ ¡Pago aprobado! Ya podés usar PresupuestoPRO."
        tipo = "success"
    elif status == 'pending':
        mensaje = "⏳ Tu pago está pendiente de acreditación. Te avisaremos cuando se confirme."
        tipo = "warning"
    else:
        mensaje = "❌ El pago no se completó. Podés intentarlo de nuevo."
        tipo = "danger"

    html = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>PresupuestoPRO — Estado de pago</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="manifest" href="/static/manifest.json">
</head><body><div class="container py-5 text-center">
<div class="alert alert-{{ tipo }} fs-5">{{ mensaje }}</div>
{% if tipo == 'success' %}
<p class="text-muted">Guardá la app en tu celular para acceder siempre rápido.</p>
<button id="btnInstalar" class="btn btn-outline-primary mb-3" style="display:none">
  📲 Agregar al inicio del celular
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
    Webhook de MP. Para pagos únicos (preference) llega:
      { "type": "payment", "data": { "id": "PAYMENT_ID" } }
   