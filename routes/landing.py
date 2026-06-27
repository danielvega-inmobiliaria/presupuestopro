"""
Blueprint: landing
Página pública de presentación y registro rápido.
Ruta: GET/POST /landing
"""

import logging
from werkzeug.security import generate_password_hash
from flask import Blueprint, current_app, redirect, render_template_string, request, session, url_for

from database import get_db
from utils.auth import login_user

bp = Blueprint('landing', __name__)
logger = logging.getLogger(__name__)

LANDING_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PresupuestoPRO — Presupuestos profesionales en minutos</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  :root {
    --azul: #1a56db;
    --azul-dark: #1342a8;
    --verde: #0e9f6e;
    --gris: #f3f4f6;
  }
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', sans-serif; background: #fff; }

  /* HERO */
  .hero {
    background: linear-gradient(135deg, #1a56db 0%, #0e42a8 100%);
    color: #fff;
    padding: 56px 20px 48px;
    text-align: center;
  }
  .hero .badge-pill {
    background: rgba(255,255,255,.18);
    color: #fff;
    border-radius: 50px;
    padding: 4px 14px;
    font-size: .78rem;
    letter-spacing: .05em;
    display: inline-block;
    margin-bottom: 16px;
  }
  .hero h1 { font-size: 2rem; font-weight: 800; margin-bottom: 12px; line-height: 1.2; }
  .hero p  { font-size: 1.05rem; opacity: .88; max-width: 520px; margin: 0 auto 28px; }
  .btn-cta {
    background: #fff;
    color: var(--azul);
    font-weight: 700;
    font-size: 1.05rem;
    border-radius: 50px;
    padding: 14px 36px;
    border: none;
    box-shadow: 0 4px 20px rgba(0,0,0,.18);
    text-decoration: none;
    display: inline-block;
    transition: transform .15s;
  }
  .btn-cta:hover { transform: translateY(-2px); color: var(--azul-dark); }

  /* FEATURES */
  .features { padding: 48px 20px; background: var(--gris); }
  .feature-icon {
    width: 52px; height: 52px;
    background: var(--azul);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem;
    margin: 0 auto 14px;
  }
  .feature-card {
    text-align: center;
    background: #fff;
    border-radius: 16px;
    padding: 28px 18px;
    height: 100%;
    box-shadow: 0 2px 12px rgba(0,0,0,.06);
  }
  .feature-card h5 { font-weight: 700; font-size: .95rem; margin-bottom: 6px; }
  .feature-card p  { font-size: .85rem; color: #6b7280; margin: 0; }

  /* PRECIO */
  .precio-section { padding: 48px 20px; text-align: center; }
  .precio-card {
    background: #fff;
    border: 2px solid var(--azul);
    border-radius: 20px;
    padding: 36px 28px;
    max-width: 380px;
    margin: 0 auto;
    box-shadow: 0 8px 32px rgba(26,86,219,.12);
  }
  .precio-card .monto { font-size: 2.6rem; font-weight: 800; color: var(--azul); }
  .precio-card .monto small { font-size: 1rem; color: #6b7280; }
  .check-list { list-style: none; padding: 0; text-align: left; margin: 20px 0; }
  .check-list li { padding: 5px 0; font-size: .92rem; }
  .check-list li::before { content: "✅ "; }

  /* FORMULARIO */
  .form-section {
    background: linear-gradient(135deg, #f0f5ff 0%, #e8f0fe 100%);
    padding: 48px 20px 60px;
  }
  .form-card {
    background: #fff;
    border-radius: 20px;
    padding: 36px 28px;
    max-width: 420px;
    margin: 0 auto;
    box-shadow: 0 8px 40px rgba(26,86,219,.1);
  }
  .form-card h3 { font-weight: 800; color: #111; margin-bottom: 6px; }
  .form-card .sub { color: #6b7280; font-size: .9rem; margin-bottom: 24px; }
  .form-control {
    border-radius: 10px !important;
    padding: 12px 14px !important;
    border: 1.5px solid #d1d5db !important;
    font-size: .95rem !important;
    margin-bottom: 14px;
  }
  .form-control:focus { border-color: var(--azul) !important; box-shadow: 0 0 0 3px rgba(26,86,219,.12) !important; }
  .btn-pagar {
    background: var(--azul);
    color: #fff;
    font-weight: 700;
    font-size: 1.05rem;
    border-radius: 50px;
    padding: 14px;
    border: none;
    width: 100%;
    margin-top: 6px;
    transition: background .15s;
  }
  .btn-pagar:hover { background: var(--azul-dark); }
  .btn-pagar:disabled { opacity: .65; }
  .error-msg { background: #fee2e2; color: #b91c1c; border-radius: 10px; padding: 10px 14px; font-size: .88rem; margin-bottom: 14px; }
  .form-label { font-weight: 600; font-size: .85rem; color: #374151; margin-bottom: 4px; }
  .seguro { font-size: .78rem; color: #9ca3af; text-align: center; margin-top: 14px; }

  /* FOOTER */
  footer { text-align: center; padding: 24px 20px; color: #9ca3af; font-size: .8rem; }
</style>
</head>
<body>

<!-- HERO -->
<section class="hero">
  <div class="badge-pill">⚡ Para profesionales de la construcción</div>
  <h1>Presupuestos<br>profesionales<br>en minutos</h1>
  <p>Calculá costos, generá PDFs listos para el cliente y controlá tu negocio desde cualquier lugar.</p>
  <a href="#registro" class="btn-cta">Quiero probarlo →</a>
</section>

<!-- FEATURES -->
<section class="features">
  <div class="container">
    <h2 class="text-center fw-800 mb-4" style="font-weight:800;font-size:1.3rem">¿Qué incluye?</h2>
    <div class="row g-3">
      <div class="col-6">
        <div class="feature-card">
          <div class="feature-icon">📋</div>
          <h5>Presupuestos ilimitados</h5>
          <p>Creá todos los que necesites sin límite</p>
        </div>
      </div>
      <div class="col-6">
        <div class="feature-card">
          <div class="feature-icon">📄</div>
          <h5>PDF profesional</h5>
          <p>Listo para enviar al cliente al instante</p>
        </div>
      </div>
      <div class="col-6">
        <div class="feature-card">
          <div class="feature-icon">📊</div>
          <h5>Análisis de costos</h5>
          <p>Desglose por categorías en tiempo real</p>
        </div>
      </div>
      <div class="col-6">
        <div class="feature-card">
          <div class="feature-icon">💱</div>
          <h5>Multi-moneda</h5>
          <p>Trabajá en ARS y USD simultáneamente</p>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- PRECIO -->
<section class="precio-section">
  <h2 class="fw-800 mb-4" style="font-weight:800;font-size:1.3rem">Simple y accesible</h2>
  <div class="precio-card">
    <div class="monto">$ {{ '{:,.0f}'.format(precio_ars) }} <small>ARS/mes</small></div>
    <p class="text-muted mt-1 mb-0" style="font-size:.85rem">Renovación automática · Cancelá cuando quieras</p>
    <ul class="check-list mt-3">
      <li>Presupuestos ilimitados</li>
      <li>PDF con tu logo y datos</li>
      <li>Análisis de rentabilidad</li>
      <li>Multi-moneda ARS/USD</li>
      <li>Soporte incluido</li>
    </ul>
    <a href="#registro" class="btn-cta d-block text-center" style="border-radius:50px;padding:13px;">Empezar ahora</a>
  </div>
</section>

<!-- FORMULARIO -->
<section class="form-section" id="registro">
  <div class="form-card">
    <h3>Creá tu cuenta</h3>
    <p class="sub">Completá tus datos y pagá con Mercado Pago</p>

    {% if error %}
    <div class="error-msg">{{ error }}</div>
    {% endif %}

    <form method="POST" action="/landing" id="formRegistro">
      <label class="form-label">Nombre completo</label>
      <input type="text" name="nombre" class="form-control" placeholder="Tu nombre" required
             value="{{ nombre_prev or '' }}">

      <label class="form-label">Email</label>
      <input type="email" name="email" class="form-control" placeholder="tu@email.com" required
             value="{{ email_prev or '' }}">

      <label class="form-label">Contraseña</label>
      <input type="password" name="password" class="form-control" placeholder="Mínimo 6 caracteres" required minlength="6">

      <button type="submit" class="btn-pagar" id="btnPagar">
        🔒 Ir a pagar con Mercado Pago
      </button>
    </form>

    <p class="seguro">🔐 Pagos seguros procesados por Mercado Pago.<br>Tu información está protegida.</p>
  </div>
</section>

<footer>
  PresupuestoPRO · Herramienta para profesionales de la construcción
</footer>

<script>
document.getElementById('formRegistro').addEventListener('submit', function() {
  var btn = document.getElementById('btnPagar');
  btn.disabled = true;
  btn.textContent = 'Procesando...';
});
</script>
</body>
</html>
"""


@bp.route('/landing', methods=['GET', 'POST'])
def landing():
    precio_ars = current_app.config.get('MP_PRECIO_ARS', 15000)

    if request.method == 'GET':
        return render_template_string(LANDING_HTML, precio_ars=precio_ars,
                                      error=None, nombre_prev=None, email_prev=None)

    # POST — registrar usuario y redirigir a pago
    nombre   = request.form.get('nombre', '').strip()
    email    = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')

    # Validaciones básicas
    if not nombre or not email or not password:
        return render_template_string(LANDING_HTML, precio_ars=precio_ars,
                                      error="Completá todos los campos.",
                                      nombre_prev=nombre, email_prev=email)
    if len(password) < 6:
        return render_template_string(LANDING_HTML, precio_ars=precio_ars,
                                      error="La contraseña debe tener al menos 6 caracteres.",
                                      nombre_prev=nombre, email_prev=email)

    db = get_db()

    # ¿Ya existe el email?
    existing = db.execute("SELECT id, active FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        # Usuario existente: lo logueamos y lo mandamos a pagar
        db.close()
        login_user(existing['id'])
        logger.info(f"[Landing] Usuario existente {email} → redirigiendo a pago")
        return redirect(url_for('pagos.crear_suscripcion'), code=307)

    # Usuario nuevo: crear cuenta
    try:
        password_hash = generate_password_hash(password)
        cursor = db.execute(
            "INSERT INTO users (email, password_hash, nombre, pais, active) VALUES (?,?,?,?,1)",
            (email, password_hash, nombre, 'AR')
        )
        user_id = cursor.lastrowid
        db.commit()
        db.close()
        logger.info(f"[Landing] Nuevo usuario {email} (id={user_id}) creado desde landing")
    except Exception as e:
        db.close()
        logger.error(f"[Landing] Error creando usuario {email}: {e}")
        return render_template_string(LANDING_HTML, precio_ars=precio_ars,
                                      error="Error al crear la cuenta. Intentá de nuevo.",
                                      nombre_prev=nombre, email_prev=email)

    login_user(user_id)
    return redirect(url_for('pagos.crear_suscripcion'), code=307)
