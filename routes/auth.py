import os
import secrets
from datetime import datetime, timedelta

import resend
from flask import Blueprint, render_template, render_template_string, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from database import get_db
from utils.auth import login_user, logout_user, get_current_user

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_user():
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        pais = request.form.get('pais', 'AR')

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()

        if not user or not check_password_hash(user['password_hash'], password):
            flash('Email o contraseña incorrectos.', 'error')
            return render_template('login.html')

        if not user['active']:
            flash('Cuenta desactivada. Contactá al administrador.', 'error')
            return render_template('login.html')

        # Sesión única: al loguear acá se invalida cualquier otra sesión activa
        login_user(user['id'])
        session['pais'] = pais

        if user['is_admin']:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('dashboard.index'))

    return render_template('login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# ─── RECUPERAR CONTRASEÑA ─────────────────────────────────────────────────────

@bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        db = get_db()
        user = db.execute("SELECT id, nombre FROM users WHERE email=?", (email,)).fetchone()

        if user:
            token = secrets.token_urlsafe(32)
            expires = datetime.utcnow() + timedelta(hours=1)
            db.execute(
                "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?,?,?)",
                (user['id'], token, expires.strftime('%Y-%m-%d %H:%M:%S'))
            )
            db.commit()

            api_key = os.environ.get('RESEND_API_KEY')
            app_url = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
            reset_url = f"{app_url}/restablecer/{token}"
            nombre = user['nombre'] or email.split('@')[0]

            if api_key:
                try:
                    resend.api_key = api_key
                    resend.Emails.send({
                        "from": "PresupuestoPRO <onboarding@resend.dev>",
                        "to": [email],
                        "subject": "Restablecer contrasena - PresupuestoPRO",
                        "html": (
                            '<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#222">'
                            '<h2 style="color:#1a56db">Restablece tu contrasena</h2>'
                            f'<p>Hola <strong>{nombre}</strong>,</p>'
                            '<p>Recibimos una solicitud para restablecer tu contrasena. Hace click en el boton:</p>'
                            '<div style="text-align:center;margin:28px 0">'
                            f'<a href="{reset_url}" style="background:#1a56db;color:#fff;padding:13px 30px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px">Restablecer contrasena</a>'
                            '</div>'
                            '<p style="color:#888;font-size:.85rem">Este link es valido por <strong>1 hora</strong>.<br>Si no solicitaste esto, ignora este email.</p>'
                            '<hr style="border:none;border-top:1px solid #eee;margin:20px 0">'
                            '<p style="color:#aaa;font-size:.78rem">PresupuestoPRO - Argentina</p>'
                            '</div>'
                        ),
                    })
                except Exception:
                    pass

        db.close()
        flash('Si ese email está registrado, te mandamos un link para restablecer tu contraseña.', 'success')
        return redirect(url_for('auth.login'))

    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recuperar contraseña — PresupuestoPRO</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
  body { background:#0d1e3c; min-height:100vh; display:flex; align-items:center; }
  .card { max-width:400px; width:100%; margin:auto; }
  .brand { color:#eab308; font-size:1.6rem; font-weight:700; }
</style>
</head><body><div class="container">
  <div class="text-center mb-4">
    <div class="brand"><i class="bi bi-calculator-fill"></i> PresupuestoPRO</div>
  </div>
  <div class="card shadow-lg mx-auto">
    <div class="card-body p-4">
      <h5 class="mb-1">Recuperar contraseña</h5>
      <p class="text-muted small mb-4">Te mandamos un link por email para que puedas crear una nueva.</p>
      {% with msgs = get_flashed_messages(with_categories=True) %}
        {% for cat, msg in msgs %}
          <div class="alert alert-{{ 'danger' if cat == 'error' else 'success' }}">{{ msg }}</div>
        {% endfor %}
      {% endwith %}
      <form method="POST">
        <div class="mb-3">
          <label class="form-label">Email de tu cuenta</label>
          <input type="email" name="email" class="form-control" required autofocus>
        </div>
        <div class="d-grid mt-3">
          <button type="submit" class="btn btn-warning fw-bold">Enviar link</button>
        </div>
      </form>
      <div class="text-center mt-3">
        <a href="{{ url_for('auth.login') }}" class="text-secondary small">← Volver al login</a>
      </div>
    </div>
  </div>
</div></body></html>
""")


@bp.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer(token):
    db = get_db()
    row = db.execute(
        "SELECT prt.id, prt.user_id, prt.expires_at, prt.used, u.email "
        "FROM password_reset_tokens prt "
        "JOIN users u ON u.id = prt.user_id "
        "WHERE prt.token=?", (token,)
    ).fetchone()

    error = None
    if not row:
        error = 'Link inválido.'
    elif row['used']:
        error = 'Este link ya fue usado. Solicitá uno nuevo.'
    elif datetime.utcnow() > datetime.strptime(row['expires_at'], '%Y-%m-%d %H:%M:%S'):
        error = 'El link expiró (válido 1 hora). Solicitá uno nuevo.'

    if error:
        db.close()
        flash(error, 'error')
        return redirect(url_for('auth.recuperar'))

    if request.method == 'POST':
        pw1 = request.form.get('password', '')
        pw2 = request.form.get('password2', '')
        if len(pw1) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
        elif pw1 != pw2:
            flash('Las contraseñas no coinciden.', 'error')
        else:
            db.execute("UPDATE users SET password_hash=? WHERE id=?",
                       (generate_password_hash(pw1), row['user_id']))
            db.execute("UPDATE password_reset_tokens SET used=1 WHERE id=?", (row['id'],))
            db.commit()
            db.close()
            flash('Contraseña actualizada. Ya podés ingresar.', 'success')
            return redirect(url_for('auth.login'))

    user_email = row['email'] if row else ''
    db.close()
    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nueva contraseña — PresupuestoPRO</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
  body { background:#0d1e3c; min-height:100vh; display:flex; align-items:center; }
  .card { max-width:400px; width:100%; margin:auto; }
  .brand { color:#eab308; font-size:1.6rem; font-weight:700; }
</style>
</head><body><div class="container">
  <div class="text-center mb-4">
    <div class="brand"><i class="bi bi-calculator-fill"></i> PresupuestoPRO</div>
  </div>
  <div class="card shadow-lg mx-auto">
    <div class="card-body p-4">
      <h5 class="mb-1">Nueva contraseña</h5>
      <p class="text-muted small mb-4">Para la cuenta <strong>{{ email }}</strong></p>
      {% with msgs = get_flashed_messages(with_categories=True) %}
        {% for cat, msg in msgs %}
          <div class="alert alert-{{ 'danger' if cat == 'error' else 'success' }}">{{ msg }}</div>
        {% endfor %}
      {% endwith %}
      <form method="POST">
        <div class="mb-3">
          <label class="form-label">Nueva contraseña</label>
          <input type="password" name="password" class="form-control" required minlength="6" autofocus>
        </div>
        <div class="mb-3">
          <label class="form-label">Repetir contraseña</label>
          <input type="password" name="password2" class="form-control" required minlength="6">
        </div>
        <div class="d-grid mt-3">
          <button type="submit" class="btn btn-warning fw-bold">Guardar nueva contraseña</button>
        </div>
      </form>
    </div>
  </div>
</div></body></html>
""", email=user_email)
