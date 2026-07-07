import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, g
from database import get_db

def login_user(user_id):
    """Genera un nuevo token de sesión e invalida cualquier sesión anterior."""
    token = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(days=30)
    db = get_db()
    db.execute(
        "UPDATE users SET session_token=?, session_expires=? WHERE id=?",
        (token, expires.isoformat(), user_id)
    )
    db.commit()
    db.close()
    session['user_id'] = user_id
    session['session_token'] = token
    session.permanent = True

def logout_user():
    uid = session.get('user_id')
    if uid:
        db = get_db()
        db.execute("UPDATE users SET session_token=NULL, session_expires=NULL WHERE id=?", (uid,))
        db.commit()
        db.close()
    session.clear()

def get_current_user():
    uid = session.get('user_id')
    token = session.get('session_token')
    if not uid or not token:
        return None
    db = get_db()
    # Fix 06/07/2026: las cuentas de prueba gratis (es_trial=1) pueden entrar
    # aunque su subscription_expires ya haya pasado — la prueba vencida se
    # maneja con un bloqueo suave (ver utils/trial.py::trial_required), no con
    # un corte total en el login como las suscripciones pagas vencidas.
    user = db.execute(
        """SELECT * FROM users WHERE id=? AND session_token=?
           AND active=1 AND (subscription_expires IS NULL OR subscription_expires >= date('now') OR es_trial=1)""",
        (uid, token)
    ).fetchone()
    db.close()
    return user

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            session.clear()
            return redirect(url_for('auth.login'))
        g.user = user
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or not user['is_admin']:
            return redirect(url_for('auth.login'))
        g.user = user
        return f(*args, **kwargs)
    return decorated
