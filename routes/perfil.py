import base64
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from werkzeug.security import check_password_hash, generate_password_hash
from utils.auth import login_required
from database import get_db

bp = Blueprint('perfil', __name__, url_prefix='/perfil')

ALLOWED_EXTS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB


def _get_perfil(user_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM empresa_perfil WHERE user_id=?", (user_id,)
    ).fetchone()
    db.close()
    return dict(row) if row else {}


@bp.route('/', methods=['GET'])
@login_required
def ver():
    perfil = _get_perfil(g.user['id'])
    # Fix 11/07/2026: faltaba pasar `user` al template — sin esto, el navbar
    # ({% if user %} en base.html) no se mostraba en esta página.
    return render_template('perfil/perfil.html', perfil=perfil, user=g.user)


@bp.route('/guardar', methods=['POST'])
@login_required
def guardar():
    nombre   = request.form.get('nombre', '').strip()
    contacto = request.form.get('contacto', '').strip()
    telefono = request.form.get('telefono', '').strip()
    email    = request.form.get('email', '').strip()
    slogan   = request.form.get('slogan', '').strip()

    logo_data     = None
    logo_filename = None

    archivo = request.files.get('logo')
    if archivo and archivo.filename:
        ext = archivo.filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXTS:
            flash('Formato de logo no permitido (PNG, JPG, GIF, WEBP, SVG).', 'error')
            return redirect(url_for('perfil.ver'))
        raw = archivo.read()
        if len(raw) > MAX_LOGO_BYTES:
            flash('El logo no puede superar 2 MB.', 'error')
            return redirect(url_for('perfil.ver'))
        logo_data     = base64.b64encode(raw).decode('utf-8')
        logo_filename = archivo.filename

    db = get_db()
    existe = db.execute(
        "SELECT id FROM empresa_perfil WHERE user_id=?", (g.user['id'],)
    ).fetchone()

    if existe:
        if logo_data is not None:
            db.execute("""
                UPDATE empresa_perfil
                SET nombre=?, contacto=?, telefono=?, email=?, slogan=?,
                    logo_data=?, logo_filename=?, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=?
            """, (nombre, contacto, telefono, email, slogan,
                  logo_data, logo_filename, g.user['id']))
        else:
            db.execute("""
                UPDATE empresa_perfil
                SET nombre=?, contacto=?, telefono=?, email=?, slogan=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=?
            """, (nombre, contacto, telefono, email, slogan, g.user['id']))
    else:
        db.execute("""
            INSERT INTO empresa_perfil
                (user_id, nombre, contacto, telefono, email, slogan, logo_data, logo_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (g.user['id'], nombre, contacto, telefono, email, slogan,
              logo_data or '', logo_filename or ''))

    db.commit()
    db.close()
    flash('Perfil de empresa guardado correctamente.', 'success')
    return redirect(url_for('perfil.ver'))


@bp.route('/cambiar-password', methods=['GET', 'POST'])
@login_required
def cambiar_password():
    """Agregado 11/07/2026: no existía ninguna forma de cambiar la propia
    contraseña estando logueado (solo el flujo de "olvidé mi contraseña" por
    email, que requiere que el email de la cuenta reciba correo — no
    garantizado para admin@presupuestopro.com). Sirve para cualquier usuario
    logueado, incluido el admin."""
    if request.method == 'POST':
        actual = request.form.get('actual', '')
        pw1 = request.form.get('password', '')
        pw2 = request.form.get('password2', '')

        db = get_db()
        row = db.execute("SELECT password_hash FROM users WHERE id=?", (g.user['id'],)).fetchone()

        if not row or not check_password_hash(row['password_hash'], actual):
            db.close()
            flash('La contraseña actual no es correcta.', 'error')
            return redirect(url_for('perfil.cambiar_password'))
        if len(pw1) < 6:
            db.close()
            flash('La contraseña nueva debe tener al menos 6 caracteres.', 'error')
            return redirect(url_for('perfil.cambiar_password'))
        if pw1 != pw2:
            db.close()
            flash('Las contraseñas nuevas no coinciden.', 'error')
            return redirect(url_for('perfil.cambiar_password'))

        db.execute("UPDATE users SET password_hash=? WHERE id=?",
                   (generate_password_hash(pw1), g.user['id']))
        db.commit()
        db.close()
        flash('Contraseña actualizada correctamente.', 'success')
        return redirect(url_for('perfil.ver'))

    return render_template('perfil/cambiar_password.html', user=g.user)


@bp.route('/borrar-logo', methods=['POST'])
@login_required
def borrar_logo():
    db = get_db()
    db.execute(
        "UPDATE empresa_perfil SET logo_data='', logo_filename='' WHERE user_id=?",
        (g.user['id'],)
    )
    db.commit()
    db.close()
    flash('Logo eliminado.', 'success')
    return redirect(url_for('perfil.ver'))
