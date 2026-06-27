"""
Blueprint: landing
Página pública de presentación y registro rápido.
Rutas: GET/POST /landing  |  POST /contacto
"""

import logging
from werkzeug.security import generate_password_hash
from flask import Blueprint, current_app, redirect, render_template_string, request, session, url_for

from database import get_db
from utils.auth import login_user

bp = Blueprint('landing', __name__)
logger = logging.getLogger(__name__)

PROVINCIAS_AR = [
    "Buenos Aires", "CABA", "Catamarca", "Chaco", "Chubut", "Córdoba",
    "Corrientes", "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja",
    "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta", "San Juan",
    "San Luis", "Santa Cruz", "Santa Fe", "Santiago del Estero",
    "Tierra del Fuego", "Tucumán",
]

LANDING_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PresupuestoPRO — Presupuestos profesionales en minutos</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  :root { --azul: #1a56db; --azul-dark: #1342a8; --gris: #f3f4f6; }
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', sans-serif; background: #fff; }

  .hero {
    background: linear-gradient(135deg, #1a56db 0%, #0e42a8 100%);
    color: #fff; padding: 56px 20px 48px; text-align: center;
  }
  .hero .badge-pill {
    background: rgba(255,255,255,.18); color: #fff; border-radius: 50px;
    padding: 4px 14px; font-size: .78rem; letter-spacing: .05em;
    display: inline-block; margin-bottom: 16px;
  }
  .hero h1 { font-size: 2rem; font-weight: 800; margin-bottom: 12px; line-height: 1.2; }
  .hero p  { font-size: 1.05rem; opacity: .88; max-width: 520px; margin: 0 auto 28px; }
  .btn-cta {
    background: #fff; color: var(--azul); font-weight: 700; font-size: 1.05rem;
    border-radius: 50px; padding: 14px 36px; border: none;
    box-shadow: 0 4px 20px rgba(0,0,0,.18); text-decoration: none;
    display: inline-block; transition: transform .15s;
  }
  .btn-cta:hover { transform: translateY(-2px); color: var(--azul-dark); }

  .features { padding: 48px 20px; background: var(--gris); }
  .feature-icon {
    width: 52px; height: 52px; background: var(--azul); border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; margin: 0 auto 14px;
  }
  .feature-card {
    text-align: center; background: #fff; border-radius: 16px;
    padding: 28px 18px; height: 100%; box-shadow: 0 2px 12px rgba(0,0,0,.06);
  }
  .feature-card h5 { font-weight: 700; font-size: .95rem; margin-bottom: 6px; }
  .feature-card p  { font-size: .85rem; color: #6b7280; margin: 0; }

  .precio-section { padding: 48px 20px; text-align: center; }
  .precio-card {
    background: #fff; border: 2px solid var(--azul); border-radius: 20px;
    padding: 36px 28px; max-width: 380px; margin: 0 auto;
    box-shadow: 0 8px 32px rgba(26,86,219,.12);
  }
  .precio-card .monto { font-size: 2.6rem; font-weight: 800; color: var(--azul); line-height: 1; }
  .precio-card .monto small { font-size: 1rem; color: #6b7280; font-weight: 400; }
  .check-list { list-style: none; padding: 0; text-align: left; margin: 20px 0; }
  .check-list li { padding: 5px 0; font-size: .92rem; }
  .check-list li::before { content: "✅ "; }

  .form-section { background: linear-gradient(135deg, #f0f5ff 0%, #e8f0fe 100%); padding: 48px 20px 60px; }
  .form-card {
    background: #fff; border-radius: 20px; padding: 36px 28px;
    max-width: 460px; margin: 0 auto; box-shadow: 0 8px 40px rgba(26,86,219,.1);
  }
  .form-card h3 { font-weight: 800; color: #111; margin-bottom: 6px; }
  .form-card .sub { color: #6b7280; font-size: .9rem; margin-bottom: 24px; }
  .form-control, .form-select {
    border-radius: 10px !important; padding: 11px 14px !important;
    border: 1.5px solid #d1d5db !important; font-size: .92rem !important; margin-bottom: 12px;
  }
  .form-control:focus, .form-select:focus {
    border-color: var(--azul) !important; box-shadow: 0 0 0 3px rgba(26,86,219,.12) !important;
  }
  .form-label { font-weight: 600; font-size: .82rem; color: #374151; margin-bottom: 3px; }
  .fila { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .btn-pagar {
    background: var(--azul); color: #fff; font-weight: 700; font-size: 1.05rem;
    border-radius: 50px; padding: 14px; border: none; width: 100%; margin-top: 8px;
    transition: background .15s;
  }
  .btn-pagar:hover { background: var(--azul-dark); }
  .btn-pagar:disabled { opacity: .65; }
  .error-msg { background: #fee2e2; color: #b91c1c; border-radius: 10px; padding: 10px 14px; font-size: .88rem; margin-bottom: 14px; }
  .ok-msg { background: #d1fae5; color: #065f46; border-radius: 10px; padding: 12px 16px; text-align: center; margin-bottom: 16px; font-weight: 600; }
  .seguro { font-size: .78rem; color: #9ca3af; text-align: center; margin-top: 14px; }

  .contacto-section { background: #fff; padding: 48px 20px 60px; }

  footer { text-align: center; padding: 24px 20px; color: #9ca3af; font-size: .8rem; }
</style>
</head>
<body>

<!-- HERO -->
<section class="hero">
  <div class="badge-pill">⚡ Para Albañiles Profesionales</div>
  <h1>Presupuestos profesionales<br>para albañiles<br>en minutos</h1>
  <p>Calculá costos, generá PDFs listos para el cliente y controlá tu negocio desde cualquier lugar.</p>
  <a href="#registro" class="btn-cta">Quiero probarlo →</a>
</section>

<!-- FEATURES -->
<section class="features">
  <div class="container">
    <h2 class="text-center mb-4" style="font-weight:800;font-size:1.3rem">¿Qué incluye?</h2>
    <div class="row g-3">
      <div class="col-6"><div class="feature-card">
        <div class="feature-icon">📋</div>
        <h5>Presupuestos ilimitados</h5><p>Creá todos los que necesites sin límite</p>
      </div></div>
      <div class="col-6"><div class="feature-card">
        <div class="feature-icon">📄</div>
        <h5>PDF profesional</h5><p>Listo para enviar al cliente al instante</p>
      </div></div>
      <div class="col-6"><div class="feature-card">
        <div class="feature-icon">📊</div>
        <h5>Análisis de costos</h5><p>Desglose por categorías en tiempo real</p>
      </div></div>
      <div class="col-6"><div class="feature-card">
        <div class="feature-icon">💱</div>
        <h5>Multi-moneda</h5><p>Trabajá en ARS y USD simultáneamente</p>
      </div></div>
    </div>
  </div>
</section>

<!-- PRECIO -->
<section class="precio-section">
  <h2 class="mb-4" style="font-weight:800;font-size:1.3rem">Simple y accesible</h2>
  <div class="precio-card">
    <div class="monto">$ {{ '{:,.0f}'.format(precio_ars) }} <small>ARS/mes</small></div>
    <p class="text-muted mt-1 mb-0" style="font-size:.85rem">Renovación mensual · Cancelá cuando quieras</p>
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

<!-- FORMULARIO REGISTRO -->
<section class="form-section" id="registro">
  <div class="form-card">
    <h3>Creá tu cuenta</h3>
    <p class="sub">Completá tus datos y pagá con Mercado Pago</p>

    {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}

    <form method="POST" action="/landing" id="formRegistro">
      <div class="fila">
        <div>
          <label class="form-label">Nombre</label>
          <input type="text" name="nombre" class="form-control" placeholder="Nombre" required value="{{ prev.nombre or '' }}">
        </div>
        <div>
          <label class="form-label">Apellido</label>
          <input type="text" name="apellido" class="form-control" placeholder="Apellido" required value="{{ prev.apellido or '' }}">
        </div>
      </div>

      <div class="fila">
        <div>
          <label class="form-label">Teléfono</label>
          <input type="tel" name="telefono" class="form-control" placeholder="11 1234-5678" value="{{ prev.telefono or '' }}">
        </div>
        <div>
          <label class="form-label">Email</label>
          <input type="email" name="email" class="form-control" placeholder="tu@email.com" required value="{{ prev.email or '' }}">
        </div>
      </div>

      <div class="fila">
        <div>
          <label class="form-label">Ciudad</label>
          <input type="text" name="ciudad" class="form-control" placeholder="Tu ciudad" value="{{ prev.ciudad or '' }}">
        </div>
        <div>
          <label class="form-label">Provincia</label>
          <select name="provincia" class="form-select">
            <option value="">Seleccioná</option>
            {% for p in provincias %}
            <option value="{{ p }}" {{ 'selected' if prev.provincia == p else '' }}>{{ p }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <label class="form-label">Contraseña</label>
      <input type="password" name="password" class="form-control" placeholder="Mínimo 6 caracteres" required minlength="6">

      <button type="submit" class="btn-pagar" id="btnPagar">
        🔒 Ir a pagar con Mercado Pago
      </button>
    </form>
    <p class="seguro">🔐 Pagos seguros procesados por Mercado Pago.<br>Tu información está protegida.</p>
  </div>
</section>

<!-- COMPARATIVA -->
<section style="background:#f3f4f6;padding:40px 20px;text-align:center">
  <h2 style="font-weight:800;font-size:1.2rem;margin-bottom:6px">¿Caro? Mirá esto 👇</h2>
  <p style="color:#6b7280;font-size:.9rem;margin-bottom:28px">
    Por menos de lo que gastás en una semana, tenés una herramienta profesional todo el mes
  </p>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;max-width:420px;margin:0 auto">
    <div style="background:#fff;border-radius:16px;padding:20px 10px;box-shadow:0 2px 12px rgba(0,0,0,.06)">
      <div style="font-size:2rem">🍺</div>
      <div style="font-size:1.5rem;font-weight:800;color:#1a56db;margin:6px 0">{{ cervezas }}</div>
      <div style="font-size:.75rem;color:#6b7280;line-height:1.3">cervezas<br>artesanales</div>
    </div>
    <div style="background:#fff;border-radius:16px;padding:20px 10px;box-shadow:0 2px 12px rgba(0,0,0,.06)">
      <div style="font-size:2rem">🚬</div>
      <div style="font-size:1.5rem;font-weight:800;color:#1a56db;margin:6px 0">{{ atados }}</div>
      <div style="font-size:.75rem;color:#6b7280;line-height:1.3">atados de<br>cigarrillos</div>
    </div>
    <div style="background:#fff;border-radius:16px;padding:20px 10px;box-shadow:0 2px 12px rgba(0,0,0,.06)">
      <div style="font-size:2rem">🥤</div>
      <div style="font-size:1.5rem;font-weight:800;color:#1a56db;margin:6px 0">{{ cocas }}</div>
      <div style="font-size:.75rem;color:#6b7280;line-height:1.3">Coca-Colas<br>2.25 litros</div>
    </div>
  </div>
  <p style="margin-top:20px;font-size:.85rem;color:#374151;font-weight:600">
    Eso cuesta PresupuestoPRO por mes. Y te genera presupuestos que valen miles.
  </p>
  <a href="#registro" style="display:inline-block;margin-top:10px;background:#1a56db;color:#fff;font-weight:700;border-radius:50px;padding:12px 32px;text-decoration:none;font-size:.95rem">
    Empezar ahora →
  </a>
</section>

<!-- FORMULARIO CONTACTO -->
<section class="contacto-section" id="contacto">
  <div class="form-card">
    <h3>¿Tenés dudas?</h3>
    <p class="sub">Si tenés problemas para pagar o querés más info, dejanos un mensaje y te contactamos.</p>

    {% if contacto_ok %}<div class="ok-msg">✅ ¡Mensaje enviado! Te contactamos pronto.</div>{% endif %}

    <form method="POST" action="/contacto">
      <div class="fila">
        <div>
          <label class="form-label">Nombre</label>
          <input type="text" name="nombre" class="form-control" placeholder="Nombre" required>
        </div>
        <div>
          <label class="form-label">Apellido</label>
          <input type="text" name="apellido" class="form-control" placeholder="Apellido" required>
        </div>
      </div>

      <div class="fila">
        <div>
          <label class="form-label">Teléfono</label>
          <input type="tel" name="telefono" class="form-control" placeholder="11 1234-5678">
        </div>
        <div>
          <label class="form-label">Email</label>
          <input type="email" name="email" class="form-control" placeholder="tu@email.com">
        </div>
      </div>

      <div class="fila">
        <div>
          <label class="form-label">Ciudad</label>
          <input type="text" name="ciudad" class="form-control" placeholder="Tu ciudad">
        </div>
        <div>
          <label class="form-label">Provincia</label>
          <select name="provincia" class="form-select">
            <option value="">Seleccioná</option>
            {% for p in provincias %}
            <option value="{{ p }}">{{ p }}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <label class="form-label">Mensaje</label>
      <textarea name="mensaje" class="form-control" rows="3"
        placeholder="¿En qué te podemos ayudar?" required
        style="border-radius:10px;padding:12px 14px;border:1.5px solid #d1d5db;font-size:.92rem;width:100%;margin-bottom:12px"></textarea>

      <button type="submit" class="btn-pagar">Enviar mensaje</button>
    </form>
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


def _render(precio_ars, error=None, prev=None, contacto_ok=False):
    # Precios de referencia en ARS (actualizar según inflación)
    P_CERVEZA  = 3500   # cerveza artesanal / chopera
    P_ATADO    = 4500   # atado de cigarrillos
    P_COCA     = 3000   # Coca-Cola 2.25L
    return render_template_string(
        LANDING_HTML,
        precio_ars=precio_ars,
        error=error,
        prev=prev or {},
        contacto_ok=contacto_ok,
        provincias=PROVINCIAS_AR,
        cervezas=int(precio_ars // P_CERVEZA),
        atados=int(precio_ars // P_ATADO),
        cocas=int(precio_ars // P_COCA),
    )


@bp.route('/landing', methods=['GET', 'POST'])
def landing():
    precio_ars = current_app.config.get('MP_PRECIO_ARS', 15000)

    if request.method == 'GET':
        return _render(precio_ars, contacto_ok=bool(request.args.get('contacto_ok')))

    # POST — registro
    f = request.form
    nombre   = f.get('nombre', '').strip()
    apellido = f.get('apellido', '').strip()
    telefono = f.get('telefono', '').strip()
    email    = f.get('email', '').strip().lower()
    ciudad   = f.get('ciudad', '').strip()
    provincia= f.get('provincia', '').strip()
    password = f.get('password', '')

    prev = dict(nombre=nombre, apellido=apellido, telefono=telefono,
                email=email, ciudad=ciudad, provincia=provincia)

    if not nombre or not apellido or not email or not password:
        return _render(precio_ars, error="Completá los campos obligatorios.", prev=prev)
    if len(password) < 6:
        return _render(precio_ars, error="La contraseña debe tener al menos 6 caracteres.", prev=prev)

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        # Ya existe → actualizar datos y redirigir a pago
        db.execute(
            "UPDATE users SET nombre=?, apellido=?, telefono=?, ciudad=?, provincia=? WHERE id=?",
            (nombre, apellido, telefono, ciudad, provincia, existing['id'])
        )
        db.commit()
        db.close()
        login_user(existing['id'])
        logger.info(f"[Landing] Usuario existente {email} → pago")
        return redirect(url_for('pagos.crear_suscripcion'), code=307)

    try:
        password_hash = generate_password_hash(password)
        cursor = db.execute(
            """INSERT INTO users (email, password_hash, nombre, apellido, telefono, ciudad, provincia, pais, active)
               VALUES (?,?,?,?,?,?,?,?,1)""",
            (email, password_hash, nombre, apellido, telefono, ciudad, provincia, 'AR')
        )
        user_id = cursor.lastrowid
        db.commit()
        db.close()
        logger.info(f"[Landing] Nuevo usuario {email} id={user_id}")
    except Exception as e:
        db.close()
        logger.error(f"[Landing] Error creando usuario {email}: {e}")
        return _render(precio_ars, error="Error al crear la cuenta. Intentá de nuevo.", prev=prev)

    login_user(user_id)
    return redirect(url_for('pagos.crear_suscripcion'), code=307)


@bp.route('/contacto', methods=['POST'])
def contacto():
    f = request.form
    nombre   = f.get('nombre', '').strip()
    apellido = f.get('apellido', '').strip()
    telefono = f.get('telefono', '').strip()
    email    = f.get('email', '').strip()
    ciudad   = f.get('ciudad', '').strip()
    provincia= f.get('provincia', '').strip()
    mensaje  = f.get('mensaje', '').strip()

    if nombre and mensaje:
        try:
            db = get_db()
            db.execute(
                """INSERT INTO contactos (nombre, apellido, telefono, email, ciudad, provincia, mensaje)
                   VALUES (?,?,?,?,?,?,?)""",
                (nombre, apellido, telefono, email, ciudad, provincia, mensaje)
            )
            db.commit()
            db.close()
            logger.info(f"[Contacto] Mensaje de {nombre} {apellido} / {email}")
        except Exception as e:
            logger.error(f"[Contacto] Error: {e}")

    return redirect('/landing?contacto_ok=1#contacto')
