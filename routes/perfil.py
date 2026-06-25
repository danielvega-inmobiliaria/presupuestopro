import base64
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
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
    return render_template('perfil/perfil.html', perfil=perfil)


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
