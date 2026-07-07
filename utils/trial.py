"""
Lógica de la prueba gratis (campaña de lanzamiento, 06/07/2026).

Regla: 3 presupuestos completos guardados O 14 días desde la creación de la
cuenta, lo que se cumpla primero. Solo aplica a usuarios con `es_trial=1`
(altas nuevas desde /registro). Cuentas creadas por admin sin marcar la
casilla de prueba, y cualquier cuenta con es_trial=0, no tienen límite acá
(siguen rigiéndose solo por `subscription_expires`, como siempre).
"""
from datetime import datetime
from functools import wraps
from flask import g, redirect, url_for, flash
from database import get_db

TRIAL_MAX_PRESUPUESTOS = 3
TRIAL_MAX_DIAS = 14


def get_trial_status(user):
    """Devuelve un dict con el estado de la prueba gratis de `user`.
    Si no es cuenta de prueba, siempre 'vencido': False (sin límite)."""
    if not user or not user['es_trial']:
        return {'es_trial': False, 'vencido': False}

    db = get_db()
    n_presupuestos = db.execute(
        "SELECT COUNT(*) c FROM presupuestos WHERE user_id=? AND status='completo'",
        (user['id'],)
    ).fetchone()['c']
    db.close()

    try:
        creado = datetime.fromisoformat((user['created_at'] or '').replace(' ', 'T'))
        dias_pasados = (datetime.utcnow() - creado).days
    except (ValueError, TypeError):
        dias_pasados = 0

    vencido_por_presupuestos = n_presupuestos >= TRIAL_MAX_PRESUPUESTOS
    vencido_por_dias = dias_pasados >= TRIAL_MAX_DIAS

    return {
        'es_trial':               True,
        'vencido':                vencido_por_presupuestos or vencido_por_dias,
        'motivo':                 'presupuestos' if vencido_por_presupuestos else ('dias' if vencido_por_dias else None),
        'n_presupuestos':         n_presupuestos,
        'max_presupuestos':       TRIAL_MAX_PRESUPUESTOS,
        'presupuestos_restantes': max(0, TRIAL_MAX_PRESUPUESTOS - n_presupuestos),
        'dias_pasados':           dias_pasados,
        'max_dias':               TRIAL_MAX_DIAS,
        'dias_restantes':         max(0, TRIAL_MAX_DIAS - dias_pasados),
    }


def trial_required(f):
    """Decorator para rutas que la prueba gratis vencida debe bloquear
    (crear/editar presupuesto, Costo/m2, ver/descargar PDF). Va DESPUÉS de
    @login_required (necesita g.user ya cargado)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        ts = get_trial_status(g.user)
        if ts['vencido']:
            flash('Tu prueba gratis terminó. Suscribite para seguir usando esta función.', 'error')
            return redirect(url_for('dashboard.trial_vencido'))
        return f(*args, **kwargs)
    return decorated
