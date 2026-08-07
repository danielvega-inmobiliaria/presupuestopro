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
    # Fix 06/08/2026 (cont. 23): date('now') es UTC -- comparado contra un
    # subscription_expires pensado en día calendario ART, cortaba el acceso
    # hasta 3hs antes de tiempo (21:00 a 23:59 ART, cuando en UTC ya es el
    # día siguiente). Mismo ajuste que en actividad_diaria: -3hs fijas.
    user = db.execute(
        """SELECT * FROM users WHERE id=? AND session_token=?
           AND active=1 AND (subscription_expires IS NULL OR subscription_expires >= date('now', '-3 hours') OR es_trial=1)""",
        (uid, token)
    ).fetchone()
    if user:
        # Fix 06/08/2026, pedido de Daniel: registrar actividad para el cuadro
        # de "Actividad de usuarios" del dashboard de Admin. ultima_actividad
        # se pisa en cada request autenticado y alimenta el contador en vivo
        # (ventana de 5 min, ver routes/admin.py::dashboard). actividad_diaria
        # es 1 fila por usuario y día (INSERT OR IGNORE -- no cuenta doble
        # aunque el usuario haga muchos requests el mismo día) y alimenta el
        # gráfico de conexiones por día. No se cuentan los admins en ninguno
        # de los dos (el cuadro mide uso real de clientes, no las propias
        # sesiones de Daniel navegando el panel).
        db.execute("UPDATE users SET ultima_actividad=datetime('now') WHERE id=?", (uid,))
        if not user['is_admin']:
            # Fix 06/08/2026 (cont. 23): date('now') de SQLite es UTC, no hora
            # Argentina (UTC-3) -- entre las 21:00 y las 23:59 ART el día ya
            # cambiaba en UTC, así que conexiones de esa franja se contaban en
            # el gráfico de "mañana" en vez de "hoy". Se resta 3hs a mano
            # (Argentina no tiene horario de verano, -3 es fijo todo el año)
            # para que el balde de "fecha" respete el día calendario ART.
            db.execute(
                "INSERT OR IGNORE INTO actividad_diaria (user_id, fecha) VALUES (?, date('now', '-3 hours'))",
                (uid,)
            )
        db.commit()
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
