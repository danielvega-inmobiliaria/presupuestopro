"""
Blueprint: costo_m2
Calculadora de Costo por M2/M3 — seleccionás un ítem, ingresás jornales,
obtenés el costo por unidad con desglose de materiales y mano de obra.

Rutas:
  GET  /costo-m2              → lista de ítems con checkbox
  GET  /costo-m2/resultado    → ventana de resultado (item_id + jornales en query)
"""

from flask import Blueprint, render_template, request, session, redirect, url_for
from functools import wraps
from database import get_db

bp = Blueprint('costo_m2', __name__, url_prefix='/costo-m2')

# Jornal horario usado en la app para calcular precio_mo_ars (fallback)
JORNAL_HORA_OF_APP = 10000   # $10.000/hr oficial
JORNAL_HORA_AY_APP = 5000    # $5.000/hr ayudante = $40.000/día
JORNAL_DIA_OF_DEF  = 80000   # default display
JORNAL_DIA_AY_DEF  = 40000   # default display


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
        "SELECT id, rubro_num, rubro_nombre, nombre, unidad, precio_ars, "
        "precio_mo_ars, hof, hay, m2_factor "
        "FROM items_obra ORDER BY rubro_num, orden, id"
    ).fetchall()
    db.close()

    rubros = {}
    for it in items:
        key = (it['rubro_num'], it['rubro_nombre'])
        rubros.setdefault(key, []).append(it)

    return render_template('costo_m2/index.html', rubros=rubros)


@bp.route('/resultado')
@_login_required
def resultado():
    item_id      = request.args.get('item_id', type=int)
    jornal_of_dia = request.args.get('jornal_of', type=float, default=0)
    jornal_ay_dia = request.args.get('jornal_ay', type=float, default=0)

    if not item_id:
        return redirect(url_for('costo_m2.index'))

    db = get_db()

    item = db.execute(
        "SELECT id, rubro_nombre, nombre, unidad, precio_ars, precio_mo_ars, "
        "hof, hay, m2_factor "
        "FROM items_obra WHERE id=?", (item_id,)
    ).fetchone()

    if not item:
        db.close()
        return redirect(url_for('costo_m2.index'))

    # Materiales para 1 unidad desde analisis_sub
    materiales = db.execute(
        "SELECT sub_nombre, cant_por_unit, precio_ars "
        "FROM analisis_sub WHERE item_nombre=? AND es_material=1 ORDER BY rowid",
        (item['nombre'],)
    ).fetchall()

    if jornal_of_dia == 0 and jornal_ay_dia == 0:
        cfg_jo = db.execute("SELECT valor FROM config WHERE clave='jornal_oficial_dia'").fetchone()
        cfg_ja = db.execute("SELECT valor FROM config WHERE clave='jornal_ayudante_dia'").fetchone()
        jornal_of_dia = float(cfg_jo['valor']) if cfg_jo else JORNAL_DIA_OF_DEF
        jornal_ay_dia = float(cfg_ja['valor']) if cfg_ja else JORNAL_DIA_AY_DEF

    db.close()

    # ── Factor de conversión m3 → m2 ───────────────────────────────────────
    factor = item['m2_factor']  # None = sin conversión, float = espesor en m
    unidad_orig = item['unidad']
    if factor and unidad_orig == 'm3':
        display_unit = 'm2'
        # Ajustar cant/precio de materiales: por cada m3 × factor = cantidad por m2
        # Los precios de materiales ya vienen por unidad de material, no cambian
        factor_conv = factor
    else:
        display_unit = unidad_orig
        factor_conv = 1.0  # sin conversión

    # ── Cálculo para 1 unidad display (m2 o la unidad original) ────────────
    jornal_hora_of = jornal_of_dia / 8
    jornal_hora_ay = jornal_ay_dia / 8

    # MO por unidad original (m3 o lo que sea)
    mo_por_unit_orig = item['hof'] * jornal_hora_of + item['hay'] * jornal_hora_ay
    # MO por unidad display (si convierte m3→m2: multiplica por factor = m3/m2)
    mo_por_unit_display = mo_por_unit_orig * factor_conv

    # Materiales: cant y costo por unidad display
    mat_items = []
    total_mat_display = 0.0
    for m in materiales:
        cant_display   = round(m['cant_por_unit'] * factor_conv, 4)
        costo_com      = m['precio_ars']          # precio comercial por unidad de material
        costo_necesario = round(cant_display * costo_com, 2)
        total_mat_display += costo_necesario
        mat_items.append({
            'nombre':          m['sub_nombre'],
            'cantidad':        cant_display,
            'costo_comercial': costo_com,
            'costo_necesario': costo_necesario,
        })

    # Si no hay analisis_sub, usar precio_ars - precio_mo_ars como referencia
    if not mat_items and item['precio_ars']:
        precio_mo_ref = item['precio_mo_ars'] or 0
        total_mat_display = (item['precio_ars'] - precio_mo_ref) * factor_conv

    # Horas para 1 unidad display
    hs_oficial   = round(item['hof'] * factor_conv, 2)
    hs_ayudante  = round(item['hay'] * factor_conv, 2)

    # Costos por unidad display
    costo_directo = total_mat_display + mo_por_unit_display

    PCT_GG  = 0.10
    PCT_IMP = 0.05

    gg_monto  = round(costo_directo * PCT_GG,  2)
    imp_monto = round(costo_directo * PCT_IMP, 2)
    total_display = round(costo_directo + gg_monto + imp_monto, 2)

    return render_template('costo_m2/resultado.html',
        item=item,
        display_unit=display_unit,
        mat_items=mat_items,
        tiene_materiales=len(mat_items) > 0,
        total_mat=total_mat_display,
        mo_por_unit=mo_por_unit_display,
        hs_oficial=hs_oficial,
        hs_ayudante=hs_ayudante,
        jornal_of_dia=jornal_of_dia,
        jornal_ay_dia=jornal_ay_dia,
        costo_directo=costo_directo,
        pct_gg=int(PCT_GG * 100),
        pct_imp=int(PCT_IMP * 100),
        gg_monto=gg_monto,
        imp_monto=imp_monto,
        total_display=total_display,
        factor_conv=factor_conv,
        hof_orig=item['hof'],
        hay_orig=item['hay'],
    )
