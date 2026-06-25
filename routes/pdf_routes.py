import json
from flask import Blueprint, send_file, g, redirect, url_for, flash
from utils.auth import login_required
from utils.pdf_generator import generar_pdf_propietario, generar_pdf_constructor
from utils.calculations import calcular_cuotas, calcular_cuadro_pago
from database import get_db

bp = Blueprint('pdf', __name__, url_prefix='/pdf')

def cargar_presupuesto(pid, user_id):
    db = get_db()
    pres = db.execute(
        "SELECT * FROM presupuestos WHERE id=? AND user_id=?", (pid, user_id)
    ).fetchone()
    empresa_row = db.execute(
        "SELECT * FROM empresa_perfil WHERE user_id=?", (user_id,)
    ).fetchone()
    db.close()
    if not pres:
        return None, None
    p = dict(pres)
    for campo in ('rubros_json','subcontratos_json','indirectos_json','materiales_json'):
        p[campo.replace('_json','')] = json.loads(p[campo] or '[]')
    n_cuotas = calcular_cuotas(p['dias_obra'], p['frecuencia_pago'])
    p['cuadro_pago'] = calcular_cuadro_pago(
        p['total_presupuesto'], p['pct_anticipo'], p['pct_final'], n_cuotas
    )
    empresa = dict(empresa_row) if empresa_row else {}
    return p, empresa

@bp.route('/<int:pid>/propietario')
@login_required
def propietario(pid):
    p, empresa = cargar_presupuesto(pid, g.user['id'])
    if not p:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(url_for('dashboard.index'))
    buf = generar_pdf_propietario(p, empresa)
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f"Presupuesto_{p['nro']}_Propietario.pdf")

@bp.route('/<int:pid>/constructor')
@login_required
def constructor(pid):
    p, empresa = cargar_presupuesto(pid, g.user['id'])
    if not p:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(url_for('dashboard.index'))
    buf = generar_pdf_constructor(p, empresa)
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f"Presupuesto_{p['nro']}_Constructor.pdf")
