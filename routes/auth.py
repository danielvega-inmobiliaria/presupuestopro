from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
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
