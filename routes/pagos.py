"""
Blueprint: pagos
Integración Mercado Pago — Suscripciones (Preapproval)

Rutas:
  GET  /pagos/planes              → página de planes/precios
  POST /pagos/crear-suscripcion   → crea preapproval en MP y redirige al usuario
  GET  /pagos/retorno             → landing tras pago (success / pending / failure)
  POST /pagos/webhook             → notificaciones de MP (sin autenticación requerida)
  GET  /pagos/estado              → estado de suscripción del usuario actual
"""

import json
import logging
from datetime import datetime, date, timedelta
from functools import wraps

import mercadopago
from flask import (Blueprint, current_app, g, jsonify, redirect,
                   render_template_string, request, session, url_for)

from database import get_db

bp = Blueprint('pagos', __name__, url_prefix='/pagos')
logger = logging.getLogger(__name__)

# ─── helpers ──────────────────────────────────────────────────────────────────

def _get_sdk():
    return mercadopago.SDK(current_app.config['MP_ACCESS_TOKEN'])


def _login_required(f):
    """Decorador mínimo: redirige a /login si no hay sesión."""
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


def _activar_suscripcion(db, user_id, preapproval_id, meses=1):
    """Activa o renueva la suscripción del usuario."""
    hoy = date.today()
    # Si ya tiene vigencia futura, sumamos desde ahí
    user = db.execute("SELECT subscription_expires FROM users WHERE id=?", (user_id,)).fetchone()
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
        (nueva_exp.isoformat(), preapproval_id, user_id)
    )
    db.execute("""
        INSERT INTO suscripciones (user_id, mp_preapproval_id, plan_nombre, monto_ars, estado, fecha_inicio, fecha_fin)
        VALUES (?, ?, 'mensual', ?, 'authorized', ?, ?)
        ON CONFLICT(mp_preapproval_id) DO UPDATE SET
            estado='authorized',
            fecha_fin=excluded.fecha_fin,
            updated_at=CURRENT_TIMESTAMP
    """, (user_id, preapproval_id,
          current_app.config.get('MP_PRECIO_ARS', 15000),
          hoy.isoformat(), nueva_exp.isoformat()))
    db.commit()
    logger.info(f"[MP] Usuario {user_id} activado hasta {nueva_exp}")


def _cancelar_suscripcion(db, preapproval_id):
    """Marca la suscripción como cancelada (sin desactivar inmediatamente)."""
    db.execute("""
        UPDATE suscripciones SET estado='cancelled', updated_at=CURRENT_TIMESTAMP
        WHERE mp_preapproval_id=?
    """, (preapproval_id,))
    db.commit()
    logger.info(f"[MP] Suscripción {preapproval_id} cancelada")


# ─── rutas ────────────────────────────────────────────────────────────────────

@bp.route('/planes')
@_login_required
def planes():
    """Página de planes — muestra precio y botón de suscripción."""
    user = _get_user(session['user_id'])
    precio_ars = current_app.config.get('MP_PRECIO_ARS', 15000)
    public_key = current_app.config.get('MP_PUBLIC_KEY', '')

    # Estado de suscripción actual
    sub_activa = False
    sub_expires = None
    if user and user['subscription_expires']:
        try:
            sub_expires = datetime.strptime(user['subscription_expires'], '%Y-%m-%d').date()
            sub_activa = sub_expires >= date.today() and bool(user['active'])
        except Exception:
            pass

    # HTML inline (sin template file para no requerir archivos extra ahora)
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
  <h2 class="text-center mb-2">Elegí tu plan</h2>
  <p class="text-center text-muted mb-5">Acceso completo a PresupuestoPRO</p>

  {% if sub_activa %}
  <div class="alert alert-success text-center">
    ✅ Tu suscripción está activa hasta el <strong>{{ sub_expires }}</strong>
  </div>
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
            <li>🔄 Renovación automática mensual</li>
          </ul>
          {% if not sub_activa %}
          <form method="POST" action="/pagos/crear-suscripcion">
            <button type="submit" class="btn btn-primary btn-lg w-100">
              Suscribirme con Mercado Pago
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
    Podés cancelar en cualquier momento desde tu cuenta de MP.
  </p>
</div>
</body>
</html>
"""
    from flask import render_template_string
    return render_template_string(html,
        precio_ars=precio_ars,
        public_key=public_key,
        sub_activa=sub_activa,
        sub_expires=sub_expires)


@bp.route('/crear-suscripcion', methods=['POST'])
@_login_required
def crear_suscripcion():
    """Crea un preapproval en MP y redirige al init_point."""
    user = _get_user(session['user_id'])
    sdk = _get_sdk()
    base_url = current_app.config['APP_BASE_URL']

    preapproval_data = {
        "reason": current_app.config['MP_PLAN_NOMBRE'],
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": current_app.config['MP_PRECIO_ARS'],
            "currency_id": "ARS",
        },
        "payer_email": user['email'],
        "back_url": f"{base_url}/pagos/retorno",
    }

    result = sdk.preapproval().create(preapproval_data)
    response = result.get("response", {})

    if result.get("status") not in (200, 201) or "init_point" not in response:
        logger.error(f"[MP] Error creando preapproval: {result}")
        return redirect(url_for('pagos.planes') + '?error=mp_error')

    init_point = response["init_point"]
    # Guardamos el preapproval_id en la sesión para verificar al retorno
    session['mp_preapproval_id'] = response.get("id")
    return redirect(init_point)


@bp.route('/retorno')
@_login_required
def retorno():
    """Landing tras el flujo de MP. MP envía: preapproval_id, status."""
    status = request.args.get('status', '')
    preapproval_id = request.args.get('preapproval_id') or session.pop('mp_preapproval_id', None)

    if status == 'authorized' and preapproval_id:
        db = get_db()
        _activar_suscripcion(db, session['user_id'], preapproval_id)
        db.close()
        mensaje = "✅ ¡Suscripción activada! Ya podés usar PresupuestoPRO."
        tipo = "success"
    elif status == 'pending':
        mensaje = "⏳ Tu pago está pendiente. Te avisaremos cuando se acredite."
        tipo = "warning"
    else:
        mensaje = "❌ El pago no se completó. Podés intentarlo de nuevo."
        tipo = "danger"

    html = """
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>PresupuestoPRO — Estado de pago</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body><div class="container py-5 text-center">
<div class="alert alert-{{ tipo }} fs-5">{{ mensaje }}</div>
<a href="/dashboard" class="btn btn-primary mt-3">Ir al Dashboard</a>
<a href="/pagos/planes" class="btn btn-outline-secondary mt-3 ms-2">Ver planes</a>
</div></body></html>
"""
    return render_template_string(html, mensaje=mensaje, tipo=tipo)


@bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint público para notificaciones IPN / Webhooks de Mercado Pago.
    MP envía POST con JSON: { "type": "subscription_preapproval", "data": {"id": "..."} }
    También puede enviar query params: ?topic=preapproval&id=...
    """
    # MP puede mandar el id por body JSON o por query param
    data = request.get_json(silent=True) or {}
    topic = data.get("type") or request.args.get("topic", "")
    resource_id = (data.get("data", {}).get("id")
                   or request.args.get("id")
                   or request.args.get("preapproval_id"))

    logger.info(f"[MP Webhook] topic={topic} id={resource_id}")

    if not resource_id:
        return jsonify({"ok": True}), 200  # ignorar pings sin id

    # Solo procesamos eventos de suscripciones
    if topic not in ("subscription_preapproval", "preapproval"):
        return jsonify({"ok": True}), 200

    try:
        sdk = _get_sdk()
        result = sdk.preapproval().get(resource_id)
        preapproval = result.get("response", {})
        estado_mp = preapproval.get("status", "")
        payer_email = preapproval.get("payer_email", "")

        logger.info(f"[MP Webhook] preapproval {resource_id} estado={estado_mp} email={payer_email}")

        db = get_db()
        # Buscar usuario por email o por preapproval_id ya guardado
        user = (
            db.execute("SELECT id FROM users WHERE mp_preapproval_id=?", (resource_id,)).fetchone()
            or db.execute("SELECT id FROM users WHERE email=?", (payer_email,)).fetchone()
        )

        if user:
            user_id = user['id']
            if estado_mp == "authorized":
                _activar_suscripcion(db, user_id, resource_id)
            elif estado_mp in ("cancelled", "paused"):
                _cancelar_suscripcion(db, resource_id)
        else:
            logger.warning(f"[MP Webhook] Usuario no encontrado: email={payer_email} id={resource_id}")

        db.close()
    except Exception as e:
        logger.error(f"[MP Webhook] Error procesando {resource_id}: {e}")
        # Siempre devolver 200 a MP para que no reintente indefinidamente
        return jsonify({"ok": True, "error": str(e)}), 200

    return jsonify({"ok": True}), 200


@bp.route('/estado')
@_login_required
def estado():
    """API JSON con el estado de suscripción del usuario actual."""
    user = _get_user(session['user_id'])
    sub_activa = False
    dias_restantes = 0
    expires = None

    if user and user['subscription_expires']:
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
