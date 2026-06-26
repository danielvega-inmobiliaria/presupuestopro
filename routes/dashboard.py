from flask import Blueprint, render_template, g
from utils.auth import login_required, get_current_user
from database import get_db

bp = Blueprint('dashboard', __name__)

@bp.route('/')
def index():
    user = get_current_user()
    if not user:
        return render_template('landing.html')
    g.user = user
    db = get_db()
    borradores = db.execute(
        "SELECT * FROM presupuestos WHERE user_id=? AND status='borrador' ORDER BY updated_at DESC",
        (g.user['id'],)
    ).fetchall()
    presupuestos = db.execute(
        "SELECT * FROM presupuestos WHERE user_id=? AND status='completo' ORDER BY created_at DESC LIMIT 20",
        (g.user['id'],)
    ).fetchall()
    db.close()
    return render_template('dashboard.html',
                           presupuestos=presupuestos,
                           borradores=borradores,
                           user=g.user)
