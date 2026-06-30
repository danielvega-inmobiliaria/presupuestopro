"""
Blueprint: costo_m2
Calculadora de Costo por M2 — seleccionás un ítem, ingresás jornales,
obtenés el costo/m2 con desglose de materiales y mano de obra.

Rutas:
  GET  /costo-m2              → lista de ítems con checkbox
  GET  /costo-m2/resultado    → ventana de resultado (item_id + jornales en query)
"""

from flask import Blueprint, render_template, request, session, redirect, url_for
from functools import wraps
from database import get_db

bp = Blueprint('costo_m2', __name__, url_prefix='/costo-m2')


def _login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@bp.route('/')
@_login_required
def index():
    db = get_db()
    items = db.execute(
        "SELECT id, rubro_num, rubro_nombre, nombre, unidad, precio_ars, precio_mo_ars, hof, hay "
        "FROM items_obra ORDER BY rubro_num, orden, id"
    ).fetchall()
    db.close()

    # Agrupar por rubro
    rubros = {}
    for it in items:
        key = (it['rubro_num'], it['rubro_nombre'])
        rubros.setdefault(key, []).append(it)

    return render_template('costo_m2/index.html', rubros=rubros)


@bp.route('/resultado')
@_login_required
def resultado():
    item_id = request.args.get('item_id', type=int)
    jornal_of_dia = request.args.get('jornal_of', type=float, default=0)
    jornal_ay_dia = request.args.get('jornal_ay', type=float, default=0)

    if not item_id:
        return redirect(url_for('costo_m2.index'))

    db = get_db()

    item = db.execute(
        "SELECT id, rubro_nombre, nombre, unidad, precio_ars, precio_mo_ars, hof, hay "
        "FROM items_obra WHERE id=?", (item_id,)
    ).fetchone()

    if not item:
        db.close()
        return redirect(url_for('costo_m2.index'))

    # Materiales desde analisis_sub para este ítem
    materiales = db.execute(
        "SELECT sub_nombre, cant_por_unit, precio_ars "
        "FROM analisis_sub WHERE item_nombre=? AND es_material=1 ORDER BY rowid",
        (item['nombre'],)
    ).fetchall()

    # Jornales default de config si no se pasaron
    if jornal_of_dia == 0 and jornal_ay_dia == 0:
        cfg_jo = db.execute("SELECT valor FROM config WHERE clave='jornal_oficial_dia'").fetchone()
        cfg_ja = db.execute("SELECT valor FROM config WHERE clave='jornal_ayudante_dia'").fetchone()
        jornal_of_dia = float(cfg_jo['valor']) if cfg_jo else 80000
        jornal_ay_dia = float(cfg_ja['valor']) if cfg_ja else 50000

    db.close()

    UNIDADES = 100  # base de cálculo

    # ── Cálculo por unidad ──────────────────────────────────────────────────
    # Materiales: cant_por_unit × precio_ars × UNIDADES
    mat_items = []
    total_mat = 0.0
    for m in materiales:
        cant_total = round(m['cant_por_unit'] * UNIDADES, 3)
        subtotal = round(m['cant_por_unit'] * m['precio_ars'] * UNIDADES, 2)
        total_mat += subtotal
        mat_items.append({
            'nombre':     m['sub_nombre'],
            'cant_unit':  m['cant_por_unit'],
            'cant_total': cant_total,
            'precio':     m['precio_ars'],
            'subtotal':   subtotal,
        })

    # MO: 1 oficial + 1 ayudante
    # hof/hay = horas por unidad
    # jornal_horario = jornal_dia / 8
    jornal_hora_of = jornal_of_dia / 8
    jornal_hora_ay = jornal_ay_dia / 8

    mo_por_unidad = item['hof'] * jornal_hora_of + item['hay'] * jornal_hora_ay
    total_mo = round(mo_por_unidad * UNIDADES, 2)

    # Horas totales para 100 unidades
    hs_oficial  = round(item['hof'] * UNIDADES, 1)
    hs_ayudante = round(item['hay'] * UNIDADES, 1)

    # Subtotal costo directo
    costo_directo = total_mat + total_mo

    # Gastos/Beneficio 10% + Impuestos/Seguros 5%
    PCT_GG  = 0.10
    PCT_IMP = 0.05

    gg_monto  = round(costo_directo * PCT_GG, 2)
    imp_monto = round(costo_directo * PCT_IMP, 2)

    total_100 = costo_directo + gg_monto + imp_monto
    costo_m2  = round(total_100 / UNIDADES, 2)

    return render_template('costo_m2/resultado.html',
        item=item,
        mat_items=mat_items,
        total_mat=total_mat,
        total_mo=total_mo,
        hs_oficial=hs_oficial,
        hs_ayudante=hs_ayudante,
        jornal_of_dia=jornal_of_dia,
        jornal_ay_dia=jornal_ay_dia,
        costo_directo=costo_directo,
        pct_gg=int(PCT_GG * 100),
        pct_imp=int(PCT_IMP * 100),
        gg_monto=gg_monto,
        imp_monto=imp_monto,
        total_100=total_100,
        costo_m2=costo_m2,
        UNIDADES=UNIDADES,
    )
