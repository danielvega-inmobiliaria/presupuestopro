"""
Blueprint: costo_m2
Calculadora de Costo por M2/M3 — seleccionás un ítem y obtenés el costo por
unidad con desglose de materiales y mano de obra.

Fix 05/07/2026: antes esta calculadora tenía su PROPIA lógica de cálculo,
independiente de la del presupuesto real — daba números distintos para ítems
compuestos (Hormigón/Armadura/Encofrado) y usaba % de GG/Impuestos fijos en
el código (10%/5% sobre MO solamente) en vez de los configurables de Admin
(sobre MO+Materiales). Ahora reutiliza EXACTAMENTE las mismas funciones que
routes/presupuesto.py usa para el presupuesto real:
  - _calcular_materiales_desde_rubros(): misma expansión recursiva de ítems
    compuestos, mismos sinónimos, misma conversión a bolsas de compra.
  - items_obra.precio_mo_ars: mismo costo de MO de referencia ya congelado
    que se usa en el presupuesto (dejó de recalcularse con un jornal editable
    en pantalla, para que el número sea siempre el mismo que se termina
    cobrando en un presupuesto real).
  - get_config_pct(): mismos % de Gastos generales/Beneficio e Impuestos y
    seguros configurados en Admin.

Fix 07/07/2026 (cont. 2): Beneficio/Seguros en ESTA calculadora se aplican
SOLO sobre la MO (no sobre MO+Materiales) — a diferencia del presupuesto real,
que sigue aplicándolos sobre MO+Materiales (Costo Directo) sin cambios. Costo/m2
es una referencia de cuánto sale la mano de obra por unidad, con los materiales
mostrados aparte a modo informativo (cuánto material hace falta y qué sale).

Rutas:
  GET  /costo-m2              → lista de ítems con checkbox
  GET  /costo-m2/resultado    → ventana de resultado (item_id en query)
"""

from flask import Blueprint, render_template, request, session, redirect, url_for
from database import get_db
from routes.presupuesto import _calcular_materiales_desde_rubros, get_config_pct
from utils.auth import login_required
from utils.trial import trial_required

# 05/07/2026: se registra cada consulta a esta calculadora en costo_m2_consultas,
# para que el panel admin de usuarios pueda mostrar cuántas veces consultó cada uno.

bp = Blueprint('costo_m2', __name__, url_prefix='/costo-m2')

# Defaults de jornal (solo para mostrar de referencia — ya no recalculan la MO)
JORNAL_DIA_OF_DEF = 80000
JORNAL_DIA_AY_DEF = 40000


@bp.route('/')
@login_required
@trial_required
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
@login_required
@trial_required
def resultado():
    item_id = request.args.get('item_id', type=int)
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

    # Registrar la consulta (para el contador del panel admin)
    try:
        db.execute("INSERT INTO costo_m2_consultas (user_id, item_id) VALUES (?, ?)",
                   (session.get('user_id'), item_id))
        db.commit()
    except Exception as e:
        print(f"[costo_m2] error registrando consulta: {e}")

    # Jornales de referencia — solo informativos (misma fuente que paso 5 del
    # presupuesto), ya no se usan para recalcular la MO.
    cfg_jo = db.execute("SELECT valor FROM config WHERE clave='jornal_oficial_dia'").fetchone()
    cfg_ja = db.execute("SELECT valor FROM config WHERE clave='jornal_ayudante_dia'").fetchone()
    jornal_of_dia = float(cfg_jo['valor']) if cfg_jo else JORNAL_DIA_OF_DEF
    jornal_ay_dia = float(cfg_ja['valor']) if cfg_ja else JORNAL_DIA_AY_DEF
    db.close()

    # ── Factor de conversión m3 → m2 (igual que antes) ─────────────────────
    factor = item['m2_factor']
    unidad_orig = item['unidad']
    if factor and unidad_orig == 'm3':
        display_unit = 'm2'
        factor_conv = factor
    else:
        display_unit = unidad_orig
        factor_conv = 1.0

    # ── MO: mismo costo de referencia congelado que usa el presupuesto real ──
    mo_por_unit_display = round((item['precio_mo_ars'] or 0) * factor_conv, 2)

    # ── Materiales: MISMA función recursiva que el presupuesto (fix 05/07/2026).
    # Se arma un "presupuesto sintético" de 1 solo ítem con cantidad=factor_conv,
    # así la expansión de compuestos, sinónimos y conversión a bolsas es idéntica
    # a la que ve el usuario en el paso 6 (Materiales) de un presupuesto real.
    p_sintetico = {'rubros': [{'items': [{'nombre': item['nombre'], 'cantidad': factor_conv}]}]}
    # Fix 10/07/2026: redondear=False → NO redondear cada material a unidad de
    # compra entera (bolsa/u). En un presupuesto real ese redondeo hacia arriba
    # es correcto (no se compra 0.8 bolsas), pero acá estamos mostrando el
    # consumo real de referencia por 1 m2/m3, y redondear cada material a la
    # bolsa/unidad entera más cercana infla el costo (ej. Cemento Albañilería
    # aparecía como 1 bolsa completa consumida por m2 cuando en realidad son
    # ~0.8 bolsas). Ver docstring de _calcular_materiales_desde_rubros.
    mat_items_raw = _calcular_materiales_desde_rubros(p_sintetico, redondear=False)
    mat_items = [{
        'nombre':          m['nombre'],
        'cantidad':        m['cantidad'],
        'costo_comercial': m['precio_local'],
        'costo_necesario': m['subtotal'],
    } for m in mat_items_raw]
    total_mat_display = sum(m['subtotal'] for m in mat_items_raw)

    hs_oficial  = round(item['hof'] * factor_conv, 2)
    hs_ayudante = round(item['hay'] * factor_conv, 2)

    # ── GG/Impuestos: mismos % configurables del presupuesto (Admin > Precios).
    # Fix 07/07/2026 (cont. 2): Daniel aclaró que ACÁ (Costo/m2 solamente,
    # NO en el presupuesto real) Beneficio y Seguros se aplican SOLO sobre la
    # MO, no sobre MO+Materiales. Costo/m2 es una referencia de "cuánto sale
    # la mano de obra por unidad", con los materiales mostrados aparte como
    # dato informativo — no es el Costo Directo del presupuesto. El
    # presupuesto real (routes/presupuesto.py::get_config_pct + funciones de
    # totales) NO se toca, sigue aplicando los % sobre MO+Materiales como
    # siempre. Ejemplo verificado con Daniel (Mamp. ladrillo comun 30cm,
    # jornales 80.000/40.000, Beneficio 10%, Seguros 7%): MO pura $35.250 ×
    # 1.17 = $41.243.
    pct_gg, pct_imp = get_config_pct()
    gg_monto  = round(mo_por_unit_display * pct_gg / 100, 2)
    imp_monto = round(mo_por_unit_display * pct_imp / 100, 2)
    # MO neta = MO pura + Beneficio + Seguros (todo calculado sobre la MO).
    mo_neto = round(mo_por_unit_display + gg_monto + imp_monto, 2)
    # TOTAL final de referencia = MO neta + Materiales (puros, sin adicionales).
    total_final = round(mo_neto + total_mat_display, 2)

    return render_template('costo_m2/resultado.html',
        item=item,
        display_unit=display_unit,
        mat_items=mat_items,
        tiene_materiales=total_mat_display > 0,
        tiene_desglose=len(mat_items) > 0,
        total_mat=total_mat_display,
        mo_por_unit=mo_por_unit_display,
        mo_neto=mo_neto,
        hs_oficial=hs_oficial,
        hs_ayudante=hs_ayudante,
        jornal_of_dia=jornal_of_dia,
        jornal_ay_dia=jornal_ay_dia,
        pct_gg=pct_gg,
        pct_imp=pct_imp,
        gg_monto=gg_monto,
        imp_monto=imp_monto,
        total_final=total_final,
        factor_conv=factor_conv,
        hof_orig=item['hof'],
        hay_orig=item['hay'],
    )
