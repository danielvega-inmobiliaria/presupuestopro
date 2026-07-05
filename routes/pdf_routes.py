import json
import re
from urllib.parse import quote
from flask import Blueprint, send_file, g, redirect, url_for, flash, render_template
from utils.auth import login_required
from utils.pdf_generator import generar_pdf_propietario, generar_pdf_constructor
from utils.calculations import calcular_cuotas, calcular_cuadro_pago
from routes.presupuesto import _calcular_materiales_desde_rubros
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
    # Fix 05/07/2026: en modo "Solo mano de obra" el wizard salta paso 6
    # (materiales) — p['materiales'] queda vacío. Para el PDF propietario,
    # el dueño necesita igual la lista de qué comprar, así que se calcula acá
    # en vivo desde los rubros (misma fuente que usa el paso 6 normalmente).
    if p.get('modo') == 'solo_mo' and not p.get('materiales'):
        try:
            p['materiales'] = _calcular_materiales_desde_rubros(p)
        except Exception:
            p['materiales'] = []
    empresa = dict(empresa_row) if empresa_row else {}
    return p, empresa

@bp.route('/<int:pid>/propietario-preview')
@login_required
def propietario_preview(pid):
    p, empresa = cargar_presupuesto(pid, g.user['id'])
    if not p:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(url_for('dashboard.index'))
    # Limpiar teléfono para wa.me (solo dígitos; si empieza con 0 → reemplazar por 54)
    tel_raw = (p.get('cliente_tel') or '').strip()
    tel_digits = re.sub(r'\D', '', tel_raw)
    if tel_digits.startswith('0'):
        tel_digits = '54' + tel_digits[1:]
    elif tel_digits and not tel_digits.startswith('54'):
        tel_digits = '54' + tel_digits
    msg = f"Hola {p.get('cliente_nombre', '')}! Te envío el presupuesto N° {p['nro']} de {empresa.get('nombre', 'PresupuestoPRO')}."
    wa_url = f"https://wa.me/{tel_digits}?text={quote(msg)}" if tel_digits else None
    return render_template('presupuesto/pdf_preview.html',
                           p=p, empresa=empresa,
                           wa_url=wa_url,
                           tiene_tel=bool(tel_digits))


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
