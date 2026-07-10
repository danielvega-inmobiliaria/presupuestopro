import json
import math
import urllib.request
from urllib.parse import urlparse
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, g, flash
from utils.auth import login_required
from utils.trial import trial_required
from utils.calculations import (
    RUBROS_DEFAULT, SUBCONTRATOS_SUGERIDOS, PAISES,
    calcular_dias_obra, calcular_cuotas, calcular_cuadro_pago,
    normalize_nombre, ANALISIS_NAME_MAP, ITEMS_G_FACTOR
)
from database import get_db

bp = Blueprint('presupuesto', __name__, url_prefix='/presupuesto')


def _actualizar_tipos_cambio_silencioso():
    try:
        db = get_db()
        req = urllib.request.Request(
            'https://dolarapi.com/v1/dolares/oficial',
            headers={'User-Agent': 'PresupuestoPRO/1.0'}
        )
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read())
        tasa_ar = round(float(data.get('venta', 0)), 2)
        if tasa_ar > 0:
            db.execute(
                "UPDATE tipos_cambio SET tasa=?, updated_at=datetime('now', 'localtime') WHERE pais='AR'",
                (tasa_ar,)
            )
        req2 = urllib.request.Request(
            'https://open.er-api.com/v6/latest/USD',
            headers={'User-Agent': 'PresupuestoPRO/1.0'}
        )
        with urllib.request.urlopen(req2, timeout=4) as r:
            rates = json.loads(r.read()).get('rates', {})
        for pais, moneda in [('CL', 'CLP'), ('UY', 'UYU'), ('BR', 'BRL'), ('PY', 'PYG')]:
            tasa = rates.get(moneda)
            if tasa:
                db.execute(
                    "UPDATE tipos_cambio SET tasa=?, updated_at=datetime('now', 'localtime') WHERE pais=?",
                    (round(float(tasa), 2), pais)
                )
        db.commit()
        db.close()
    except Exception:
        pass


def get_tipo_cambio(pais):
    db = get_db()
    tc = db.execute("SELECT tasa, simbolo FROM tipos_cambio WHERE pais=?", (pais,)).fetchone()
    db.close()
    return (tc['tasa'], tc['simbolo']) if tc else (1, '$')


def get_config_pct():
    db = get_db()
    rows = db.execute(
        "SELECT clave, valor FROM config WHERE clave IN ('pct_gg','pct_impuestos')"
    ).fetchall()
    db.close()
    cfg = {r['clave']: float(r['valor']) for r in rows}
    return cfg.get('pct_gg', 20), cfg.get('pct_impuestos', 7)


def _redir_next(default_url):
    """Fix 05/07/2026: si el form enviado trae el campo oculto '_next' (lo pone
    el botón "Anterior" con su propio destino, o el JS wizardGoto() cuando se
    salta de paso clickeando un ícono verde en _wizard_steps.html), redirige
    ahí en vez de al siguiente paso por defecto. Así el paso actual SIEMPRE se
    guarda antes de navegar a cualquier otro lado (antes "Anterior" y los
    íconos eran <a href> planos que descartaban cambios sin guardar — ej. la
    frecuencia de pago elegida en paso 7 se perdía al volver de paso 5/6).
    Solo acepta rutas internas (empiezan con /presupuesto/) para evitar un
    open-redirect si alguien manipula el campo.

    Fix 05/07/2026 (cont. 5): el JS antes mandaba `this.href` (URL absoluta,
    con dominio) en vez de la ruta relativa que generaba url_for() — como esa
    URL absoluta nunca empezaba con '/presupuesto/', SIEMPRE caía al
    default_url (el paso siguiente por defecto), sin importar qué ícono se
    hubiera clickeado. Ahora se parsea con urlparse y se compara solo el
    path, así funciona tanto si `_next` viene relativo como absoluto."""
    destino = (request.form.get('_next') or '').strip()
    if destino:
        path = urlparse(destino).path
        if path.startswith('/presupuesto/'):
            return redirect(path)
    return redirect(default_url)


def get_config_jornales():
    """Jornales por defecto configurados en Admin > Precios (misma fuente que
    routes/admin.py y routes/costo_m2.py). Fix 04/07/2026: paso 5 mostraba
    0,0 en vez de estos valores porque nunca los consultaba."""
    db = get_db()
    rows = db.execute(
        "SELECT clave, valor FROM config WHERE clave IN ('jornal_oficial_dia','jornal_ayudante_dia')"
    ).fetchall()
    db.close()
    cfg = {r['clave']: float(r['valor']) for r in rows}
    return cfg.get('jornal_oficial_dia', 80000), cfg.get('jornal_ayudante_dia', 40000)


# =========================================================================
# HELPER: Materiales desde analisis_sub × cantidades actuales (TOT MAT)
# =========================================================================
def _categoria_material(nombre):
    """Devuelve (nro_categoria, nombre) para ordenar la lista de materiales por rubro."""
    n = nombre.lower()
    # 1 — Desagues
    if any(x in n for x in ['awaduct', 'desague']):
        return (1, nombre)
    # 2 — Electricidad
    if any(x in n for x in ['corrugado', 'cajas', 'cable']):
        return (2, nombre)
    # 3 — Agua F/C
    if any(x in n for x in ['caño tf', 'accesorios tf', 'llaves de paso agua']):
        return (3, nombre)
    # 4 — Gas
    if any(x in n for x in ['epoxi', 'accesorios gas', 'llaves de paso gas']):
        return (4, nombre)
    # 5 — Techos / madera estructural
    # 'chapas cerco' va a Corralón (0), no a Techos
    if any(x in n for x in ['chapa', 'issol', 'isol', 'tirante', 'clavador', 'escurrid',
                              'machimbre', 'tornillo c/arand', 'ladrillo telgopor', 'vipret']) \
            and 'cerco' not in n:
        return (5, nombre)
    # 6 — Cerámicos
    if any(x in n for x in ['klaukol', 'pastina', 'cerámico', 'ceramico', 'piso cer',
                              'piso cal', 'zócalo cer', 'zocalo cer', 'mármol', 'mosaico',
                              'loseta', 'baldosa', 'porcellanato']):
        return (6, nombre)
    # 7 — Pintura
    if any(x in n for x in ['pintura', 'látex', 'latex', 'esmalte', 'enduido',
                              'satinol', 'color para cal', 'fondo base', 'rev text',
                              'revear', 'salpicrete', 'iggam']):
        return (7, nombre)
    # 0 — Corralón general (cemento, arena, cal, ladrillos, hierro, etc.)
    return (0, nombre)

def _get_unidad_material(nombre):
    """Infiere unidad a partir del nombre del material."""
    n = nombre.lower()
    # Casos especiales primero (antes de los grupos generales)
    if 'perlitas' in n:
        return 'Bolsas 75 Lts.'
    if 'martillo neum' in n:
        return 'Hs.'
    if 'transporte material' in n:
        return 'M3'
    if 'rev text' in n:
        return 'Kg'
    # Bolsas — usar keywords específicos para evitar falsos matches (ej. 'loseta cemento')
    if any(x in n for x in ['cemento port', 'cemento alb', 'cal hidr', 'cal a', 'cal viv',
                              'deckar', 'revear', 'salpicrete', 'iggam', 'klaukol']):
        return 'Bolsas'
    if any(x in n for x in ['arena', 'piedra', 'tierra', 'granza', 'cascote', 'canto', 'partida',
                              'hormigon elaborado', 'hormigón elaborado', 'elab.colado']):
        return 'M3'
    if any(x in n for x in ['hierro', 'alambre', 'hidrófugo', 'hidrofugo', 'clavos', 'clav',
                              'pastina', 'enduido', 'color pintura']):
        return 'Kg'
    if any(x in n for x in ['ladrillo', 'lad.', 'tornillo', 'caja',
                              'transporte', 'máquina', 'maquina', 'martillo']):
        return 'U'
    if any(x in n for x in ['pintura', 'esmalte', 'látex', 'latex', 'satinol',
                              'fondo base']):
        return 'lt'
    if any(x in n for x in ['zócalo', 'zocalo',
                              'caño', 'cable', 'saligna', 'tirante', 'escurrid',
                              'clavador', 'vipret', 'palito']):
        return 'ml'
    if any(x in n for x in ['loseta', 'mosaico', 'baldosa', 'piso', 'rvto',
                              'chapa', 'isol', 'issol', 'machimbre', 'pino m', 'pino enc', 'cielorraso',
                              'metal despl', 'despleg']):
        return 'm2'
    return 'U'   # default: tratar como unidad entera (ceil)

def _redondear_cantidad(cantidad, unidad):
    """Redondeo según unidad: enteros para Kg/Bolsas/U, decimales para M3/m2/lt."""
    u = unidad.lower()
    if u in ('bolsas', 'kg', 'u', 'nº', 'n°'):
        return math.ceil(cantidad)          # siempre redondear arriba para compras
    elif u in ('ml', 'ml.'):
        return round(cantidad)              # ml siempre entero
    elif u in ('m3',):
        return round(cantidad, 2)           # M3: 2 decimales
    elif u in ('m2',):
        return math.ceil(cantidad)          # m2: redondear arriba (se compra por unidades/chapas/tablones)
    elif u in ('lt', 'litro', 'litros'):
        return round(cantidad, 1)
    else:
        # Sin unidad reconocida: siempre ceil (no se puede fraccionar un servicio)
        return math.ceil(cantidad)

def _resolver_material(nombre, cant, precio, analisis_mat, visitados=None):
    """Expande recursivamente sub-ítems compuestos (Hormigón colado, Armadura, Encofrado)
    a sus materiales hoja. Retorna lista de (nombre, cant, precio)."""
    if visitados is None:
        visitados = set()
    n_key = ANALISIS_NAME_MAP.get(normalize_nombre(nombre), normalize_nombre(nombre))
    if n_key in analisis_mat and n_key not in visitados:
        visitados = visitados | {n_key}
        hojas = []
        for child in analisis_mat[n_key]:
            hojas.extend(_resolver_material(
                child['nombre'], child['cant'] * cant, child['precio'],
                analisis_mat, visitados
            ))
        return hojas
    else:
        return [(nombre, cant, precio)]


def _materiales_por_unidad_items():
    """Costo de materiales por 1 UNIDAD de cada ítem de obra (fix 04/07/2026), para
    mostrar en paso 2 un precio unitario/subtotal en vivo consistente con
    analisis_sub (en vez de items_obra.precio_ars). Expande recursivamente
    sub-ítems compuestos (Hormigón colado, Armadura, Encofrado) igual que
    _calcular_materiales_desde_rubros, pero para 1 sola unidad de cada ítem.
    Devuelve {item_key_normalizado: costo_materiales_por_unidad}."""
    try:
        db = get_db()
        subs_rows = db.execute(
            "SELECT item_nombre, sub_nombre, cant_por_unit, precio_ars, es_material "
            "FROM analisis_sub WHERE es_material=1"
        ).fetchall()
        db.close()
    except Exception as e:
        print(f"[_materiales_por_unidad_items] error DB: {e}")
        return {}

    analisis_mat = {}
    for row in subs_rows:
        key = ANALISIS_NAME_MAP.get(normalize_nombre(row['item_nombre']),
                                    normalize_nombre(row['item_nombre']))
        analisis_mat.setdefault(key, []).append({
            'nombre': row['sub_nombre'],
            'cant':   row['cant_por_unit'],
            'precio': row['precio_ars'],
        })

    resultado = {}
    for item_key, subs in analisis_mat.items():
        total = 0.0
        for sub in subs:
            for _, hoja_c, hoja_p in _resolver_material(
                    sub['nombre'], sub['cant'], sub['precio'], analisis_mat,
                    visitados={item_key}):
                total += hoja_c * hoja_p
        resultado[item_key] = total
    return resultado


def _calcular_materiales_desde_rubros(p, redondear=True):
    """Recalcula la lista de materiales (formato TOT MAT) desde analisis_sub
    usando las cantidades actuales de los rubros en el presupuesto.

    redondear=True  (default, presupuesto real / PDF): cantidad de compra
        redondeada arriba a unidad comercial (bolsa/u entera) — correcto
        para lo que hay que comprar en el corralón.
    redondear=False (Costo/m2, ver routes/costo_m2.py): NO redondea a unidad
        de compra. Fix 10/07/2026 — Daniel detectó que en Costo/m2 el Cemento
        de Albañilería (y cualquier material 'Bolsas'/'U'/'Kg') se mostraba
        siempre como 1 bolsa entera consumida, aunque el consumo real por m2
        fuera una fracción chica (ej. Mamp. ladrillo comun 30cm: ~0.8 bolsas
        = ~20kg reales, no 1 bolsa completa). Pasaba porque esta función
        siempre hacía ceil() para redondear a unidad de compra (correcto en
        un presupuesto real de obra completa, donde no podés comprar 0.8
        bolsas), pero Costo/m2 calcula sobre una unidad sintética de 1 m2
        (o factor_conv chico), así que ese ceil() infla el costo de
        referencia. Con redondear=False se usa la cantidad real fraccionaria
        tanto para mostrar como para el subtotal."""
    try:
        db2 = get_db()
        subs_rows = db2.execute(
            "SELECT item_nombre, sub_nombre, cant_por_unit, precio_ars, es_material "
            "FROM analisis_sub WHERE es_material=1"
        ).fetchall()
        db2.close()

        analisis_mat = {}
        for row in subs_rows:
            key = ANALISIS_NAME_MAP.get(normalize_nombre(row['item_nombre']),
                                        normalize_nombre(row['item_nombre']))
            analisis_mat.setdefault(key, []).append({
                'nombre': row['sub_nombre'],
                'cant':   row['cant_por_unit'],
                'precio': row['precio_ars'],
            })

        mat_acum = {}
        for rubro in p.get('rubros', []):
            for it in rubro.get('items', []):
                qty = it.get('cantidad', 0)
                if qty <= 0:
                    continue
                key = ANALISIS_NAME_MAP.get(normalize_nombre(it['nombre']),
                                            normalize_nombre(it['nombre']))
                for sub in analisis_mat.get(key, []):
                    # Expande recursivamente ítems compuestos (Ho.Ado., H.Elab.).
                    # Se pasa {key} como visitados para evitar que un sub_nombre con el
                    # mismo nombre normalizado que el ítem padre (ej: 'Piso cerámico 1'
                    # dentro de 'Piso ceramico 1') se expanda recursivamente duplicando
                    # Klaukol, Pastina y otros materiales.
                    for hoja_n, hoja_c, hoja_p in _resolver_material(
                            sub['nombre'], sub['cant'] * qty, sub['precio'], analisis_mat,
                            visitados={key}):
                        # Canonicalizar nombre antes de acumular (unifica sinónimos)
                        hoja_key = normalize_nombre(hoja_n)
                        canonical = _NORMALIZE_MAT.get(hoja_key)
                        if canonical:
                            hoja_n = canonical
                            hoja_key = normalize_nombre(canonical)
                        if hoja_key not in mat_acum:
                            mat_acum[hoja_key] = {'cantidad': 0.0, 'precio': hoja_p,
                                                  'nombre_display': hoja_n}
                        mat_acum[hoja_key]['cantidad'] += hoja_c

        # Conversión kg/L acumulados → bolsas/unidades de compra.
        # Formato: keyword → (factor_base, etiqueta_unidad)
        #
        # ⚠️ IMPORTANTE: las migraciones 2j (database.py) y 2k/2l ya convirtieron
        # cant_por_unit / precio_ars en analisis_sub A UNIDAD COMERCIAL (bolsa) para:
        # Cemento portland bolsas, Cemento Albañilería, Cal aérea Milagro, Klaukol,
        # Salpicrete y Super Iggam. Esos valores en DB YA vienen en "bolsas" y "$/bolsa",
        # no en kg. Si acá se los vuelve a dividir/multiplicar por el factor de bolsa,
        # queda una DOBLE CONVERSIÓN: la cantidad mostrada sale ~25-30 veces más chica
        # y el precio unitario ~25-30 veces más caro (el subtotal además se distorsiona
        # extra por el redondeo hacia arriba aplicado sobre la cantidad ya dividida).
        # Por eso esos 6 materiales NO van en este diccionario: se usan tal cual vienen
        # de analisis_sub. Los que siguen abajo NO fueron tocados por 2j/2k/2l y
        # siguen almacenados en kg/L "crudos", así que sí necesitan esta conversión.
        BOLSAS_KG = {
            'cal hidr':     (25, 'Bolsas'),          # cal hidráulica: bolsa 25 kg (sin migrar)
            'cal viv':      (25, 'Bolsas'),          # cal viva: bolsa 25 kg (sin migrar)
            'perlitas':     (75, 'Bolsas 75 Lts.'), # perlitas telgopor: bolsa 75 lt (sin migrar)
            'revear':       (30, 'Bolsas'),          # Revear: balde 30 kg (sin migrar)
            'hierro':       (7.44, 'Barras'),        # Hierro 10mm: barra 12m = 7.44 kg (sin migrar)
        }

        result = []
        for _key, vals in sorted(mat_acum.items()):
            if vals['cantidad'] <= 0:
                continue
            # Usar nombre_display si existe (viene del acumulador normalizado)
            nombre = vals.get('nombre_display', _key)
            unidad = _get_unidad_material(nombre)
            raw_qty = vals['cantidad']
            precio_unit = vals['precio']
            # convertir kg → bolsas/unidades de compra para display
            n_lower = nombre.lower()
            for kw, (kg_por_unidad, etiqueta) in BOLSAS_KG.items():
                if kw in n_lower:
                    raw_qty = raw_qty / kg_por_unidad
                    precio_unit = vals['precio'] * kg_por_unidad
                    unidad = etiqueta
                    break
            if redondear:
                cant_final = _redondear_cantidad(raw_qty, unidad)
            else:
                # Costo/m2: cantidad real sin redondear a unidad de compra
                # (ver docstring de la función — fix 10/07/2026).
                cant_final = round(raw_qty, 3)
            cat_num, _ = _categoria_material(nombre)
            result.append({
                'nombre':       nombre,
                'cantidad':     cant_final,
                'unidad':       unidad,
                'precio_local': round(precio_unit),
                'subtotal':     round(cant_final * precio_unit),
                'categoria':    cat_num,
            })
        return sorted(result, key=lambda m: _categoria_material(m['nombre']))
    except Exception as e:
        print(f"[materiales] Error calculando materiales: {e}")
        return p.get('materiales', [])


def _mo_materiales_frescos(p):
    """Fuente única de verdad para MO y Materiales de un presupuesto (fix 04/07/2026).
    Recalcula EN VIVO desde items_obra.precio_mo_ars y analisis_sub usando las
    cantidades actuales de p['rubros'] — nunca desde items_obra.precio_ars (catálogo
    viejo que ninguna migración de precios actualiza) ni desde total_mo_analisis /
    total_materiales cacheados de un paso anterior del wizard (paso 2 usa una versión
    simplificada sin expandir Hormigón/Armadura/Encofrado; esta es siempre la versión
    completa, recursiva, la misma que ve el usuario en la pantalla de materiales).
    Devuelve (total_mo, total_materiales, materiales_list)."""
    total_mo = 0.0
    try:
        db = get_db()
        mo_por_nombre = {row['nombre']: (row['precio_mo_ars'] or 0)
                          for row in db.execute("SELECT nombre, precio_mo_ars FROM items_obra").fetchall()}
        db.close()
        for rubro in p.get('rubros', []):
            for it in rubro.get('items', []):
                qty = it.get('cantidad', 0)
                if qty > 0:
                    total_mo += mo_por_nombre.get(it['nombre'], 0) * qty
    except Exception as e:
        print(f"[_mo_materiales_frescos] error MO: {e}")
        total_mo = p.get('total_mo_analisis', 0) or p.get('total_mo', 0)

    materiales_list = _calcular_materiales_desde_rubros(p) if p.get('rubros') else None
    if materiales_list:
        total_materiales = sum(m['subtotal'] for m in materiales_list)
    else:
        materiales_list = p.get('materiales', [])
        total_materiales = p.get('total_materiales', 0)
    return round(total_mo), round(total_materiales), materiales_list


def _calcular_totales_finales(modo, total_mo, total_materiales, subc, ind,
                               pct_gg, pct_imp, operarios_reales):
    """Única fuente de verdad para Costo Directo / Base / GG / Impuestos / TOTAL
    (fix 04/07/2026). La usan paso 5 (modo_tiempo) y paso 8 (resumen, antes de
    guardar) para que el total NUNCA dependa de en qué paso del wizard se calculó
    por última vez — siempre se deriva de total_mo + total_materiales frescos."""
    total_subc = sum(s.get('mo_local', 0) + s.get('mat_local', 0) for s in subc)
    total_ind  = sum(v for v in ind.values() if isinstance(v, (int, float)))

    if modo == 'solo_mo':
        base = total_mo + total_subc + total_ind
        costo_directo = 0
    else:
        costo_directo = total_mo + total_materiales
        base = costo_directo + total_subc + total_ind

    monto_gg  = round(base * pct_gg / 100)
    monto_imp = round(base * pct_imp / 100)
    ganancia_real = total_mo + monto_gg - operarios_reales

    return {
        'costo_directo':    round(costo_directo) if modo != 'solo_mo' else 0,
        'total_mo':         total_mo,
        'total_subc':       round(total_subc),
        'total_ind':        round(total_ind),
        'base':             round(base),
        'monto_gg':         monto_gg,
        'monto_imp':        monto_imp,
        'total_final':      round(base + monto_gg + monto_imp),
        'operarios_reales': operarios_reales,
        'ganancia_real':    round(ganancia_real),
    }


def _generar_descripcion_trabajos(rubros, subcontratos=None):
    """Fix 05/07/2026: genera automáticamente la "Descripción de trabajos" en
    paso 8 a partir de los nombres de los ítems ya cargados (SIN cantidades —
    esas ya están en la tabla de ítems del PDF, esto es solo la redacción en
    prosa). Decisión de Daniel: sacar el campo de paso 1 (ahí todavía no
    existen los ítems) y autogenerar esto en paso 8, dejándolo editable por si
    el constructor quiere adornarlo — así no se le puede pasar de largo
    ningún ítem al redactar a mano.
    Fix 05/07/2026 (cont.): también suma los subcontratos cargados en paso 3,
    con prefijo "SC" (ej. "SC Electricidad"), antes del cierre "Limpieza de
    obra." — para que tampoco se le pase de largo ningún subcontrato."""
    nombres = []
    vistos = set()
    for rubro in rubros or []:
        for it in rubro.get('items', []):
            if it.get('cantidad', 0) > 0:
                nombre = (it.get('nombre') or '').strip()
                if nombre and nombre not in vistos:
                    vistos.add(nombre)
                    nombres.append(nombre)
    for sc in subcontratos or []:
        nombre_sc = (sc.get('nombre') or '').strip()
        if nombre_sc:
            etiqueta = f"SC {nombre_sc}"
            if etiqueta not in vistos:
                vistos.add(etiqueta)
                nombres.append(etiqueta)
    if not nombres:
        return ''
    return "Se realizarán los siguientes trabajos: {}, Limpieza de obra.".format(', '.join(nombres))


def _actualizar_descripcion_con_faltantes(desc_actual, rubros, subcontratos=None):
    """Fix 05/07/2026 (cont. 5): antes, _generar_descripcion_trabajos() solo
    se ejecutaba si la descripción estaba TOTALMENTE vacía — así que al
    editar un presupuesto ya guardado (con descripción ya escrita) y agregar
    un ítem o subcontrato nuevo, ese nombre nunca se sumaba al texto (Daniel
    reportó: "agregué un subcontrato y no me lo agregó a la descripción").
    Esta función revisa qué nombres (ítems + "SC {nombre}") todavía NO
    aparecen como texto en la descripción actual, y los inserta antes de
    "Limpieza de obra." (o al final si esa frase no está) — sin tocar el
    resto del texto ya escrito/editado a mano."""
    desc_actual = (desc_actual or '').strip()

    nombres = []
    vistos = set()
    for rubro in rubros or []:
        for it in rubro.get('items', []):
            if it.get('cantidad', 0) > 0:
                nombre = (it.get('nombre') or '').strip()
                if nombre and nombre not in vistos:
                    vistos.add(nombre)
                    nombres.append(nombre)
    for sc in subcontratos or []:
        nombre_sc = (sc.get('nombre') or '').strip()
        if nombre_sc:
            etiqueta = f"SC {nombre_sc}"
            if etiqueta not in vistos:
                vistos.add(etiqueta)
                nombres.append(etiqueta)

    if not nombres:
        return desc_actual

    if not desc_actual:
        return "Se realizarán los siguientes trabajos: {}, Limpieza de obra.".format(', '.join(nombres))

    desc_baja = desc_actual.lower()
    faltantes = [n for n in nombres if n.lower() not in desc_baja]
    if not faltantes:
        return desc_actual

    agregado = ', '.join(faltantes)
    idx = desc_baja.rfind('limpieza de obra')
    if idx != -1:
        antes = desc_actual[:idx].rstrip()
        despues = desc_actual[idx:]
        if antes and not antes.endswith(','):
            antes += ','
        return "{} {}, {}".format(antes, agregado, despues)
    else:
        sep = '' if desc_actual.endswith(('.', ',')) else ','
        return "{}{} {}.".format(desc_actual, sep, agregado)


# =========================================================================
# BORRADOR: guardar/actualizar en DB
# =========================================================================
# Claves pesadas que NO van al cookie de sesión (límite ~4KB).
# Solo se guardan en DB session_json.
_HEAVY_SESSION_KEYS = ('materiales', 'rubros')

# Canonicalización de nombres de materiales: normalize_nombre(variante) → nombre_display canónico.
# Unifica sinónimos antes de acumular, evitando líneas duplicadas en la lista.
_NORMALIZE_MAT = {
    'arena':                              'Arena común',
    'cascotes ladrillos':                 'Granza',
    'cem alban':                          'Cemento Albañilería',
    'cemento portland en bolsas':         'Cemento portland bolsas',
    'cemento':                            'Cemento portland bolsas',  # 'Cemento' exacto
    'clavos':                             'Clavos 2"',
    'junta (equivalente de encofrado)':   'Junta (Pavimento Hormigón)',
    'ladrillo telgopor':                  'Ladrillo Telgopor 12*38*1m',
    'ladrillo telgopor 12*38*1m':         'Ladrillo Telgopor 12*38*1m',
    'cal aerea':                          'Cal aérea Milagro',
    'deckar':                             'Rev Text.',
    'piedra partida':                     'Piedra Granítica',
}

def _session_compact(p):
    """Versión compacta de p para el cookie de sesión Flask.
    Guarda rubros como rubros_cant (id→qty) para restaurar cantidades al volver."""
    compact = {k: v for k, v in p.items() if k not in _HEAVY_SESSION_KEYS}
    if 'rubros' in p:
        compact['rubros_cant'] = {
            str(it['id']): it['cantidad']
            for r in p.get('rubros', [])
            for it in r.get('items', [])
            if it.get('cantidad', 0) > 0
        }
    return compact


def _guardar_borrador(p, step):
    """Crea o actualiza el borrador en DB. Devuelve p con _pid actualizado.
    Hace MERGE con session_json existente en DB para no perder datos de pasos anteriores
    (necesario porque el cookie de sesión no guarda claves pesadas como rubros/materiales)."""
    user_id = g.user['id']
    db = get_db()
    pid = p.get('_pid')

    # Fix 05/07/2026: _max_step guarda el paso MAS AVANZADO al que llegó este
    # borrador (a diferencia de la columna wizard_step, que se pisa con el paso
    # actual cada vez que se guarda y puede bajar si el usuario vuelve atrás).
    # _wizard_steps.html lo usa para habilitar el salto directo hacia adelante
    # (ej. estar en el paso 2 y poder ir al 6 si ya se llegó a cargar el 6 antes).
    p['_max_step'] = max(int(p.get('_max_step', 0) or 0), step)

    if pid:
        # Consultar status actual para no degradar 'completo' a 'borrador'
        row = db.execute("SELECT status, session_json FROM presupuestos WHERE id=? AND user_id=?", (pid, user_id)).fetchone()
        current_status = row['status'] if row else 'borrador'
        new_status = current_status if current_status == 'completo' else 'borrador'

        # MERGE: DB es la base, p gana en claves conflictivas.
        # Esto preserva rubros/materiales de pasos anteriores cuando el cookie los omite.
        if row and row['session_json']:
            try:
                p_db = json.loads(row['session_json'])
                p = {**p_db, **p}
            except Exception:
                pass

        p_sin_pid = {k: v for k, v in p.items() if k not in ('_pid', '_editando_nro')}
        session_json = json.dumps(p_sin_pid, ensure_ascii=False)

        # Construir UPDATE dinamico: solo sobreescribir nombre/descripcion si no estan vacios
        set_parts = [
            "session_json=?", "wizard_step=?", "status=?", "updated_at=datetime('now', 'localtime')"
        ]
        set_vals = [session_json, step, new_status]
        if p.get('cliente_nombre'):
            set_parts.append("cliente_nombre=?")
            set_vals.append(p['cliente_nombre'])
        if p.get('obra_descripcion'):
            set_parts.append("obra_descripcion=?")
            set_vals.append(p['obra_descripcion'])
        set_vals.extend([pid, user_id])
        db.execute(
            "UPDATE presupuestos SET {} WHERE id=? AND user_id=?".format(', '.join(set_parts)),
            set_vals
        )
    else:
        p_sin_pid = {k: v for k, v in p.items() if k not in ('_pid', '_editando_nro')}
        session_json = json.dumps(p_sin_pid, ensure_ascii=False)
        db.execute(
            """INSERT INTO presupuestos
                (user_id, status, wizard_step, session_json,
                 cliente_nombre, obra_descripcion, fecha_presup,
                 nro, total_presupuesto)
            VALUES (?, 'borrador', ?, ?, ?, ?, ?, '', 0)""",
            (user_id, step, session_json,
             p.get('cliente_nombre', ''),
             p.get('obra_descripcion', ''),
             p.get('fecha_presup', date.today().isoformat()))
        )
        pid = db.execute("SELECT last_insert_rowid() as id").fetchone()['id']
        p['_pid'] = pid

    db.commit()
    db.close()
    return p


# =========================================================================
# EDITAR: cargar presupuesto existente a sesion
# =========================================================================
@bp.route('/editar/<int:pid>')
@login_required
@trial_required
def editar(pid):
    db = get_db()
    pres = db.execute(
        "SELECT * FROM presupuestos WHERE id=? AND user_id=?", (pid, g.user['id'])
    ).fetchone()
    db.close()
    if not pres:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(url_for('dashboard.index'))

    p = dict(pres)

    # Para borradores: cargar session_json (progreso del wizard)
    # Para completos: siempre reconstruir desde columnas de DB (evita cargar sesiones viejas con datos vacios)
    datos = None
    if p.get('status') == 'borrador' and p.get('session_json') and p['session_json'] != '{}':
        try:
            datos = json.loads(p['session_json'])
        except Exception:
            datos = None

    if datos is None:
        # Reconstruir datos desde columnas de DB (presupuesto completo)
        pais = session.get('pais', 'AR')
        tasa, simbolo = get_tipo_cambio(pais)
        datos = {
            '_editando_nro':      p.get('nro', ''),
            'cliente_nombre':     p.get('cliente_nombre', ''),
            'cliente_tel':        p.get('cliente_tel', ''),
            'cliente_email':      p.get('cliente_email', ''),
            'obra_descripcion':   p.get('obra_descripcion', ''),
            'obra_direccion':     p.get('obra_direccion', ''),
            'obra_tipo':          p.get('obra_tipo', 'Vivienda nueva'),
            'fecha_presup':       p.get('fecha_presup', date.today().isoformat()),
            'validez':            p.get('validez', 15),
            'descripcion_trabajos': p.get('descripcion_trabajos', ''),
            'rubros':      json.loads(p.get('rubros_json') or '[]'),
            'subcontratos':json.loads(p.get('subcontratos_json') or '[]'),
            'indirectos':  json.loads(p.get('indirectos_json') or '{}'),
            'materiales':  json.loads(p.get('materiales_json') or '[]'),
            'hh_total':           p.get('hh_total', 0),
            'n_oficiales':        p.get('n_oficiales', 2),
            'n_ayudantes':        p.get('n_ayudantes', 1),
            'jornal_oficial':     p.get('jornal_oficial', 0),
            'jornal_ayudante':    p.get('jornal_ayudante', 0),
            'dias_obra':          p.get('dias_obra', 0),
            'modo':               p.get('modo', 'mo_mat'),
            'superficie':         p.get('superficie', 0),
            'tipo_cambio':        p.get('tipo_cambio', tasa),
            'simbolo':            p.get('simbolo') or simbolo,
            'pct_gg':             p.get('pct_gg', 20),
            'pct_imp':            p.get('pct_impuestos', 7),
            'pct_anticipo':       p.get('pct_anticipo', 30),
            'pct_final':          p.get('pct_final', 20),
            'frecuencia':         p.get('frecuencia_pago', 'mensual'),
            'total_materiales':   p.get('total_materiales', 0),
            'total_mo':           p.get('total_mo', 0),
            'total_subcontratos': p.get('total_subcontratos', 0),
            'total_indirectos':   p.get('total_indirectos', 0),
        }

    # Asegurar que _editando_nro refleje el nro de DB
    datos['_editando_nro'] = p.get('nro', '') or datos.get('_editando_nro', '')

    # Guardar datos completos en DB, sesion minima en cookie (evita limite ~4KB)
    datos_sin_pid = {k: v for k, v in datos.items() if k != '_pid'}
    db2 = get_db()
    db2.execute(
        "UPDATE presupuestos SET session_json=?, wizard_step=1 WHERE id=?",
        (json.dumps(datos_sin_pid, ensure_ascii=False), pid)
    )
    db2.commit()
    db2.close()

    session['presup'] = {'_pid': pid}
    flash('Editando presupuesto {}. Guarda al terminar.'.format(p.get('nro', '')), 'info')
    return redirect(url_for('presupuesto.nuevo'))


# =========================================================================
# PASO 1: Datos de obra
# =========================================================================
@bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@trial_required
def nuevo():
    if request.method == 'GET':
        if request.args.get('limpiar'):
            session.pop('presup', None)
        _actualizar_tipos_cambio_silencioso()

    # Si la sesion tiene solo _pid (viene de editar), cargar datos completos desde DB
    _p_check = session.get('presup', {})
    if _p_check.get('_pid') and len(_p_check) <= 2:
        db_load = get_db()
        row = db_load.execute(
            "SELECT session_json FROM presupuestos WHERE id=? AND user_id=?",
            (_p_check['_pid'], g.user['id'])
        ).fetchone()
        db_load.close()
        if row and row['session_json'] and row['session_json'] != '{}':
            try:
                loaded = json.loads(row['session_json'])
                loaded['_pid'] = _p_check['_pid']
                session['presup'] = _session_compact(loaded)
            except Exception:
                pass

    if request.method == 'POST':
        p = session.get('presup', {})
        p.update({
            'cliente_nombre':      request.form.get('cliente_nombre', ''),
            'cliente_tel':         request.form.get('cliente_tel', ''),
            'cliente_email':       request.form.get('cliente_email', ''),
            'obra_descripcion':    request.form.get('obra_descripcion', ''),
            'obra_direccion':      request.form.get('obra_direccion', ''),
            'obra_tipo':           request.form.get('obra_tipo', 'Vivienda nueva'),
            'fecha_presup':        request.form.get('fecha_presup', date.today().isoformat()),
            'validez':             int(request.form.get('validez', 15)),
            # Fix 05/07/2026: "descripcion_trabajos" ya no se pide en paso 1
            # (todavía no existen los ítems acá) — se autogenera en paso 8.
            # Importante: NO tocar esta clave acá, para no pisarla con '' al
            # reeditar un presupuesto que ya tenía descripción guardada.
        })
        p = _guardar_borrador(p, 1)
        session['presup'] = _session_compact(p)
        return _redir_next(url_for('presupuesto.rubros'))

    return render_template('presupuesto/paso1_obra.html',
                           hoy=date.today().isoformat(),
                           p=session.get('presup', {}),
                           user=g.user)


# =========================================================================
# PASO 2: Computo (Rubros con Items)
# =========================================================================
@bp.route('/rubros', methods=['GET', 'POST'])
@login_required
def rubros():
    pais = session.get('pais', 'AR')
    tasa, simbolo = get_tipo_cambio(pais)
    p = session.get('presup', {})

    db = get_db()
    items_rows = db.execute(
        "SELECT * FROM items_obra ORDER BY rubro_num, orden, id"
    ).fetchall()
    db.close()

    # Fix 04/07/2026: costo de materiales por unidad de cada ítem (analisis_sub),
    # para que la vista previa en vivo de paso 2 (JS) muestre MO+Materiales en vez
    # de items_obra.precio_ars (el catálogo viejo — ver notas en _calcular_totales_finales).
    mat_por_unidad = _materiales_por_unidad_items()

    rubros_agrupados = {}
    for r in RUBROS_DEFAULT:
        items_r = [dict(i) for i in items_rows if i['rubro_num'] == r['num']]
        for it in items_r:
            key = ANALISIS_NAME_MAP.get(normalize_nombre(it['nombre']), normalize_nombre(it['nombre']))
            it['mat_ars'] = round(mat_por_unidad.get(key, 0), 2)
        rubros_agrupados[r['num']] = {
            **r,
            'items': items_r,
        }

    if request.method == 'POST':
        rubros_data = []
        hh_total = 0.0
        hh_g4    = 0.0   # replica Items!G4: SUM[(hof+hay)*qty / g_factor]
        superficie = float(request.form.get('superficie', 0) or 0)

        total_mo_items  = 0.0   # RESUMEN!E3: SUM(precio_mo_ars × qty)
        total_mat_items = 0.0   # RESUMEN!E2: SUM((precio_ars - precio_mo_ars) × qty)

        for r in RUBROS_DEFAULT:
            items_rubro = []
            total_rubro = 0
            hh_rubro = 0.0

            for it in rubros_agrupados[r['num']]['items']:
                iid = it['id']
                cant_str = request.form.get('item_{}'.format(iid), '').strip()
                cant = float(cant_str) if cant_str else 0.0
                if cant > 0:
                    # Fix 04/07/2026: precio unitario = MO (precio_mo_ars) + Materiales
                    # (analisis_sub, ver mat_ars más arriba). Ya NO se usa items_obra.precio_ars.
                    precio_mo  = float(it['precio_mo_ars']) if it['precio_mo_ars'] else 0.0
                    precio_mat = float(it.get('mat_ars', 0) or 0)
                    precio_unit = precio_mo + precio_mat
                    subtotal = round(cant * precio_unit)
                    hh_item = round(cant * (it['hof'] + it['hay']), 2)
                    items_rubro.append({
                        'id': iid,
                        'nombre': it['nombre'],
                        'unidad': it['unidad'],
                        'cantidad': cant,
                        'precio_unit': round(precio_unit, 2),
                        'subtotal': subtotal,
                        'hh': hh_item,
                    })
                    total_rubro += subtotal
                    hh_rubro += hh_item
                    # hh_g4: aplica factor de paralelismo para instalaciones especiales
                    g_factor = ITEMS_G_FACTOR.get(normalize_nombre(it['nombre']), 1.0)
                    hh_g4 += (it['hof'] + it['hay']) * cant / g_factor
                    # MO y Materiales (RESUMEN!E3/E2), ahora exactos (antes E2 era una
                    # aproximación: precio_ars - precio_mo_ars)
                    total_mo_items  += precio_mo * cant
                    total_mat_items += precio_mat * cant

            rubros_data.append({
                'num': r['num'],
                'nombre': r['nombre'],
                'items': items_rubro,
                'total_rubro': total_rubro,
                'total_local': total_rubro,
                'total_usd': round(total_rubro / tasa, 2) if tasa else 0,
                'hh_rubro': hh_rubro,
            })
            hh_total += hh_rubro

        p['rubros']    = rubros_data
        p['superficie'] = superficie
        p['tipo_cambio'] = tasa
        p['simbolo']   = simbolo
        p['hh_total']  = round(hh_total, 2)
        # hh_g4 replica Items!G4:
        #   SUM[((hof+hay)*qty / g_factor)] donde g_factor=1 para ítems normales
        #   y g_factor=3.8 (Desagues/Agua/Gas) o 2.263 (Eléctrica) para especialidades.
        # días = ceil(hh_g4 / (workers * 8)) → mismo resultado que G4 del Excel.
        p['hh_g4']        = round(hh_g4, 2)
        p['hh_oficiales'] = round(hh_g4, 2)

        # ── RESUMEN!E3 y E2: MO y Materiales desde precio_mo_ars (Análisis sheet) ──
        # precio_mo_ars se calcula en _actualizar_mo_analisis() al arrancar la app.
        # Para ítems sin dato en Análisis, usa fallback hof×$10k + hay×$5k.
        p['total_mo_analisis'] = round(total_mo_items)
        p['total_materiales']  = round(total_mat_items)

        # ── Lista de materiales para paso6 (desde analisis_sub) ───────────────
        try:
            db2 = get_db()
            subs_rows = db2.execute(
                "SELECT item_nombre, sub_nombre, cant_por_unit, precio_ars, es_material "
                "FROM analisis_sub WHERE es_material=1"
            ).fetchall()
            db2.close()

            analisis_mat = {}
            for row in subs_rows:
                key = ANALISIS_NAME_MAP.get(normalize_nombre(row['item_nombre']),
                                            normalize_nombre(row['item_nombre']))
                analisis_mat.setdefault(key, []).append({
                    'nombre': row['sub_nombre'],
                    'cant':   row['cant_por_unit'],
                    'precio': row['precio_ars'],
                })

            mat_acum = {}
            for rubro in rubros_data:
                for it in rubro['items']:
                    qty = it.get('cantidad', 0)
                    if qty <= 0:
                        continue
                    key = ANALISIS_NAME_MAP.get(normalize_nombre(it['nombre']),
                                                normalize_nombre(it['nombre']))
                    for sub in analisis_mat.get(key, []):
                        mn = sub['nombre']
                        if mn not in mat_acum:
                            mat_acum[mn] = {'cantidad': 0.0, 'precio': sub['precio']}
                        mat_acum[mn]['cantidad'] += sub['cant'] * qty

            materiales_calc = [
                {
                    'nombre':       nombre,
                    'cantidad':     round(vals['cantidad'], 3),
                    'unidad':       '',
                    'precio_local': round(vals['precio']),
                    'subtotal':     round(vals['cantidad'] * vals['precio']),
                }
                for nombre, vals in sorted(mat_acum.items())
                if vals['cantidad'] > 0
            ]
            if materiales_calc:
                p['materiales'] = materiales_calc
                # Usar el total del analisis (más preciso que precio_ars - precio_mo_ars)
                p['total_materiales'] = sum(m['subtotal'] for m in materiales_calc)

        except Exception as e_mat:
            print(f"[analisis] error lista materiales: {e_mat}")

        p = _guardar_borrador(p, 2)
        # Guardar en cookie solo datos esenciales para no superar limite 4KB.
        # materiales y detalles de rubros quedan en DB session_json.
        p_cookie = {k: v for k, v in p.items()
                    if k not in ('materiales', 'rubros')}
        p_cookie['_pid'] = p.get('_pid')
        p_cookie['hh_total'] = p.get('hh_total')
        p_cookie['hh_g4'] = p.get('hh_g4')
        p_cookie['total_mo_analisis'] = p.get('total_mo_analisis')
        p_cookie['total_materiales'] = p.get('total_materiales')
        # costo_directo = suma de (MO+Materiales)×qty por rubro (fix 04/07/2026).
        # Ya no se usa como fuente de este cálculo en paso 5 (ver _calcular_totales_finales),
        # queda solo de referencia/compatibilidad.
        p_cookie['costo_directo'] = sum(r.get('total_local', 0) for r in p.get('rubros', []))
        # Guardar rubros en forma compacta (solo id+cantidad, sin sub-datos)
        p_cookie['rubros_cant'] = {
            str(it['id']): it['cantidad']
            for r in p.get('rubros', [])
            for it in r.get('items', [])
            if it.get('cantidad', 0) > 0
        }
        session['presup'] = p_cookie
        return _redir_next(url_for('presupuesto.subcontratos'))

    # GET: reconstruir cantidades desde DB si el cookie no trae rubros completos
    cantidades = {}
    # Prioridad 1: cookie compacto (rubros_cant)
    if p.get('rubros_cant'):
        cantidades = {int(k): v for k, v in p['rubros_cant'].items()}
    # Prioridad 2: rubros completos en cookie (flujo antiguo)
    elif p.get('rubros'):
        for r in p.get('rubros', []):
            for it in r.get('items', []):
                cantidades[it['id']] = it['cantidad']
    # Prioridad 3: recargar desde DB session_json
    elif p.get('_pid'):
        try:
            db3 = get_db()
            row3 = db3.execute(
                "SELECT session_json FROM presupuestos WHERE id=?", (p['_pid'],)
            ).fetchone()
            db3.close()
            if row3 and row3['session_json']:
                p_db = json.loads(row3['session_json'])
                for r in p_db.get('rubros', []):
                    for it in r.get('items', []):
                        cantidades[it['id']] = it['cantidad']
                # Actualizar session con datos frescos de DB (compacto).
                # Fix 05/07/2026: mergear con el cookie actual (p gana en
                # conflictivas) en vez de reemplazarlo entero por el snapshot
                # de DB — antes esto podía pisar valores más nuevos que
                # todavía no se habían vuelto a guardar en DB (ej. la
                # frecuencia de pago elegida en paso 7).
                session['presup'] = _session_compact({**p_db, **p})
        except Exception as e_reload:
            print(f"[rubros GET] error recargando desde DB: {e_reload}")

    return render_template('presupuesto/paso2_rubros.html',
                           rubros_agrupados=rubros_agrupados,
                           rubros_default=RUBROS_DEFAULT,
                           tasa=tasa, simbolo=simbolo,
                           cantidades=cantidades,
                           p=p, user=g.user)


# =========================================================================
# PASO 3: Subcontratos
# =========================================================================
@bp.route('/subcontratos', methods=['GET', 'POST'])
@login_required
def subcontratos():
    pais = session.get('pais', 'AR')
    tasa, simbolo = get_tipo_cambio(pais)
    p = session.get('presup', {})

    if request.method == 'POST':
        seleccionados = request.form.getlist('subc_sel')
        subc_data = []
        for sid in seleccionados:
            mo = float(request.form.get('subc_{}_mo'.format(sid), 0) or 0)
            mat = float(request.form.get('subc_{}_mat'.format(sid), 0) or 0)
            nombre = next((s['nombre'] for s in SUBCONTRATOS_SUGERIDOS if s['id'] == sid), sid)
            # Fix 05/07/2026: cantidad/unidad editables — para que el
            # subcontrato aparezca con su propia cantidad en la tabla de
            # "Items de obra" del PDF (ej. "3 Bocas", "1 Global"). Ver
            # _generar_descripcion_trabajos() y generar_pdf_propietario().
            try:
                cant_sc = float(request.form.get('subc_{}_cant'.format(sid), 1) or 1)
            except ValueError:
                cant_sc = 1
            unidad_sc = (request.form.get('subc_{}_unidad'.format(sid), 'Global') or 'Global').strip()
            subc_data.append({
                'id': sid, 'nombre': nombre,
                'mo_local': mo, 'mat_local': mat,
                'total_local': mo + mat,
                'total_usd': round((mo + mat) / tasa, 2) if tasa else 0,
                'cantidad': cant_sc,
                'unidad': unidad_sc or 'Global',
            })
        n = 0
        while n <= 20:
            nombre = request.form.get('custom_{}_nombre'.format(n), '').strip()
            if nombre:
                mo = float(request.form.get('custom_{}_mo'.format(n), 0) or 0)
                mat = float(request.form.get('custom_{}_mat'.format(n), 0) or 0)
                cant_sc = request.form.get('custom_{}_cant'.format(n), '1') or '1'
                unidad_sc = (request.form.get('custom_{}_unidad'.format(n), 'Global') or 'Global').strip()
                subc_data.append({
                    'id': 'custom_{}'.format(n), 'nombre': nombre,
                    'mo_local': mo, 'mat_local': mat,
                    'total_local': mo + mat,
                    'total_usd': round((mo + mat) / tasa, 2) if tasa else 0,
                    'cantidad': float(cant_sc) if cant_sc else 1,
                    'unidad': unidad_sc or 'Global',
                })
            n += 1

        p['subcontratos'] = subc_data
        p = _guardar_borrador(p, 3)
        session['presup'] = _session_compact(p)
        return _redir_next(url_for('presupuesto.indirectos'))

    return render_template('presupuesto/paso3_subcontratos.html',
                           sugeridos=SUBCONTRATOS_SUGERIDOS, simbolo=simbolo,
                           p=p, user=g.user)


# =========================================================================
# PASO 4: Solo indirectos (GG/Imp se mueven al paso 5)
# =========================================================================
@bp.route('/indirectos', methods=['GET', 'POST'])
@login_required
def indirectos():
    pais = session.get('pais', 'AR')
    _, simbolo = get_tipo_cambio(pais)
    p = session.get('presup', {})

    if request.method == 'POST':
        ind = {
            'movilidad':    float(request.form.get('movilidad', 0) or 0),
            'andamios':     float(request.form.get('andamios', 0) or 0),
            'herramientas': float(request.form.get('herramientas', 0) or 0),
        }
        for ni in range(20):
            nombre_extra = request.form.get('extra_{}_nombre'.format(ni), '').strip()
            monto_extra = float(request.form.get('extra_{}_monto'.format(ni), 0) or 0)
            if nombre_extra and monto_extra > 0:
                ind['extra_{}'.format(ni)] = monto_extra
        p['indirectos'] = ind
        p = _guardar_borrador(p, 4)
        session['presup'] = _session_compact(p)
        return _redir_next(url_for('presupuesto.modo_tiempo'))

    return render_template('presupuesto/paso4_indirectos.html',
                           simbolo=simbolo, p=p, user=g.user)


# =========================================================================
# PASO 5: Modo + Tiempo de obra
# =========================================================================
@bp.route('/modo-tiempo', methods=['GET', 'POST'])
@login_required
def modo_tiempo():
    p = session.get('presup', {})

    # 'rubros' no viaja en la cookie de sesión (_HEAVY_SESSION_KEYS) — recargar desde
    # DB si hace falta, igual que en paso 6, para poder recalcular materiales acá.
    if not p.get('rubros') and p.get('_pid'):
        try:
            db_rt = get_db()
            row_rt = db_rt.execute(
                "SELECT session_json FROM presupuestos WHERE id=?", (p['_pid'],)
            ).fetchone()
            db_rt.close()
            if row_rt and row_rt['session_json']:
                p = {**json.loads(row_rt['session_json']), **p}
        except Exception as e_rt:
            print(f"[modo_tiempo] error recargando rubros desde DB: {e_rt}")

    # Fix 04/07/2026: recalcular MO y Materiales SIEMPRE acá, en vivo (ver
    # _mo_materiales_frescos) — única fuente de verdad, ya no depende de valores
    # cacheados de paso 2 (aproximados) ni de items_obra.precio_ars.
    total_mo_fresco, total_mat_fresco, materiales_fresh = _mo_materiales_frescos(p)
    if p.get('rubros'):
        p['materiales'] = materiales_fresh
        p['total_materiales'] = total_mat_fresco
        p['total_mo_analisis'] = total_mo_fresco

    if request.method == 'POST':
        modo = request.form.get('modo', 'mo_mat')
        # Fix 04/07/2026: default 1 Oficial (antes 2) — pedido de Daniel.
        n_of = int(request.form.get('n_oficiales', 1))
        n_ay = int(request.form.get('n_ayudantes', 1))
        jornal_of = float(request.form.get('jornal_oficial', 0) or 0)
        jornal_ay = float(request.form.get('jornal_ayudante', 0) or 0)
        dias_obra = int(request.form.get('dias_obra') or 0)
        hh_total  = p.get('hh_total', 0)
        # Si el usuario no completó días, calcular desde HH totales
        if dias_obra <= 0 and hh_total > 0:
            _workers = n_of + n_ay
            if _workers > 0:
                dias_obra = math.ceil(hh_total / (_workers * 8))
        pct_gg_def, pct_imp_def = get_config_pct()
        pct_gg  = float(request.form.get('pct_gg', pct_gg_def))
        pct_imp = float(request.form.get('pct_imp', pct_imp_def))

        # RESUMEN!E3 = MO calculada desde Análisis (ya calculada en paso2)
        # Si existe total_mo_analisis (de analisis_sub), lo usa directamente.
        # Fallback: HH × jornal_horario (para presupuestos sin datos Análisis)
        total_mo_analisis = p.get('total_mo_analisis', 0)
        hh_total = p.get('hh_total', 0)
        n_total = n_of + n_ay
        if total_mo_analisis > 0:
            total_mo = total_mo_analisis
        elif n_total > 0 and hh_total > 0:
            jornal_horario = (n_of * jornal_of + n_ay * jornal_ay) / (n_total * 8)
            total_mo = round(jornal_horario * hh_total)
        else:
            total_mo = round((n_of * jornal_of + n_ay * jornal_ay) * dias_obra)

        # Operarios reales = lo que el constructor paga de su bolsillo
        operarios_reales = round((n_of * jornal_of + n_ay * jornal_ay) * dias_obra)

        p.update({
            'modo': modo,
            'n_oficiales':    n_of,
            'n_ayudantes':    n_ay,
            'jornal_oficial': jornal_of,
            'jornal_ayudante':jornal_ay,
            'dias_obra':      dias_obra,
            'total_mo':       total_mo,
            'pct_gg':         pct_gg,
            'pct_imp':        pct_imp,
            'operarios_reales': operarios_reales,
        })

        subc = p.get('subcontratos', [])
        ind  = p.get('indirectos', {})

        # Fix 04/07/2026: Costo Directo/Base/GG/Impuestos/TOTAL se calculan con la
        # única función compartida (_calcular_totales_finales), usada también en
        # paso 8 antes de guardar — ver nota en esa función.
        p['totales'] = _calcular_totales_finales(
            modo, total_mo, p.get('total_materiales', 0), subc, ind,
            pct_gg, pct_imp, operarios_reales
        )

        p = _guardar_borrador(p, 5)
        session['presup'] = _session_compact(p)
        if modo == 'solo_mo':
            return _redir_next(url_for('presupuesto.forma_pago'))
        else:
            return _redir_next(url_for('presupuesto.materiales'))

    hh_total     = p.get('hh_total', 0)
    hh_oficiales = p.get('hh_oficiales', 0)
    pais = session.get('pais', 'AR')
    _, simbolo = get_tipo_cambio(pais)
    pct_gg_def, pct_imp_def = get_config_pct()

    # Fix 04/07/2026: defaults pedidos por Daniel — 1 Oficial y 1 Ayudante
    # siempre (antes 2/1), y jornales pre-cargados con "la lista interna"
    # (Admin > Precios: jornal_oficial_dia/jornal_ayudante_dia) en vez de 0,0.
    jornal_of_def, jornal_ay_def = get_config_jornales()
    p.setdefault('n_oficiales', 1)
    p.setdefault('n_ayudantes', 1)
    if not p.get('jornal_oficial'):
        p['jornal_oficial'] = jornal_of_def
    if not p.get('jornal_ayudante'):
        p['jornal_ayudante'] = jornal_ay_def
    # Fix 05/07/2026: usar la MISMA función que el guardado final
    # (_calcular_totales_finales) para armar el contexto que ve el usuario acá
    # y alimenta el JS de esta página — antes este bloque reimplementaba el
    # cálculo a mano (cd_rubros = total_mo_analisis + mat_total) y podía
    # quedar levemente distinto del valor que finalmente se guarda/aparece en
    # el PDF, mostrando un TOTAL FINAL diferente en pantalla que en el PDF.
    subc_list   = p.get('subcontratos', [])
    ind_dict    = p.get('indirectos', {})
    totales_ctx = _calcular_totales_finales(
        p.get('modo', 'mo_mat'),
        p.get('total_mo_analisis', 0),
        p.get('total_materiales', 0),
        subc_list, ind_dict,
        p.get('pct_gg', pct_gg_def), p.get('pct_imp', pct_imp_def),
        p.get('operarios_reales', 0),
    )
    return render_template('presupuesto/paso5_modo_tiempo.html',
                           p=p, hh_total=hh_total, hh_oficiales=hh_oficiales,
                           simbolo=simbolo, user=g.user,
                           pct_gg=p.get('pct_gg', pct_gg_def),
                           pct_imp=p.get('pct_imp', pct_imp_def),
                           totales=totales_ctx,
                           total_mo_analisis=p.get('total_mo_analisis', 0))


# =========================================================================
# PASO 6: Materiales
# =========================================================================
@bp.route('/materiales', methods=['GET', 'POST'])
@login_required
def materiales():
    pais = session.get('pais', 'AR')
    tasa, simbolo = get_tipo_cambio(pais)
    p = session.get('presup', {})

    if request.method == 'POST':
        # Recibir materiales editados (índice i = posición)
        mat_data = []
        total_mat = 0
        i = 0
        while True:
            nombre = request.form.get('mat_{}_nombre'.format(i))
            if nombre is None:
                break
            nombre = nombre.strip()
            if nombre:
                cant_str = request.form.get('mat_{}_cant'.format(i), '0')
                precio_str = request.form.get('mat_{}_precio'.format(i), '0')
                cant = float(cant_str or 0)
                precio = float(precio_str or 0)
                subtotal = round(cant * precio)
                if cant > 0:
                    total_mat += subtotal
                    mat_data.append({
                        'nombre': nombre,
                        'unidad': request.form.get('mat_{}_unidad'.format(i), ''),
                        'cantidad': cant,
                        'precio_local': round(precio),
                        'subtotal': subtotal,
                    })
            i += 1
        p['materiales'] = mat_data
        p['total_materiales'] = total_mat
        p = _guardar_borrador(p, 6)
        session['presup'] = _session_compact(p)
        return _redir_next(url_for('presupuesto.forma_pago'))

    # GET: recalcular materiales desde rubros (pueden estar en DB, no en cookie)
    p_full = p
    if not p.get('rubros') and p.get('_pid'):
        try:
            db_m = get_db()
            row_m = db_m.execute(
                "SELECT session_json FROM presupuestos WHERE id=?", (p['_pid'],)
            ).fetchone()
            db_m.close()
            if row_m and row_m['session_json']:
                p_full = {**json.loads(row_m['session_json']), **p}
        except Exception:
            pass
    if p_full.get('rubros'):
        mats_previos = _calcular_materiales_desde_rubros(p_full)
    else:
        mats_previos = p.get('materiales', [])
    total_calc = sum(m.get('subtotal', 0) for m in mats_previos)
    return render_template('presupuesto/paso6_materiales.html',
                           mats_previos=mats_previos, total_calc=total_calc,
                           simbolo=simbolo, tasa=tasa,
                           p=p, user=g.user)


# =========================================================================
# PASO 7: Forma de pago
# =========================================================================
@bp.route('/forma-pago', methods=['GET', 'POST'])
@login_required
def forma_pago():
    p = session.get('presup', {})
    simbolo = p.get('simbolo', '$')
    totales = p.get('totales', {})
    total = totales.get('total_final', 0)

    if request.method == 'POST':
        pct_ant = float(request.form.get('pct_anticipo', 30))
        pct_fin = float(request.form.get('pct_final', 20))
        frecuencia = request.form.get('frecuencia', 'mensual')
        dias_obra = p.get('dias_obra', 0)
        n_cuotas = calcular_cuotas(dias_obra, frecuencia)
        cuadro = calcular_cuadro_pago(total, pct_ant, pct_fin, n_cuotas)
        p.update({
            'pct_anticipo': pct_ant,
            'pct_final':    pct_fin,
            'frecuencia':   frecuencia,
            'n_cuotas':     n_cuotas,
            'cuadro_pago':  cuadro,
        })
        p = _guardar_borrador(p, 7)
        session['presup'] = _session_compact(p)
        # Fix 05/07/2026: unificado con _redir_next() — "Anterior" ahora manda
        # su destino en el campo genérico "_next" (antes era el flag propio
        # "ir_atras", solo cubría este botón y no los íconos del wizard).
        return _redir_next(url_for('presupuesto.resumen'))

    dias_obra = p.get('dias_obra', 0)
    n_cuotas_prev = calcular_cuotas(dias_obra, p.get('frecuencia', 'mensual'))
    return render_template('presupuesto/paso7_pago.html',
                           p=p, total=total, simbolo=simbolo,
                           n_cuotas=n_cuotas_prev, user=g.user)


# =========================================================================
# PASO 8: Resumen y guardar
# =========================================================================
@bp.route('/resumen', methods=['GET', 'POST'])
@login_required
def resumen():
    p = session.get('presup', {})
    simbolo = p.get('simbolo', '$')

    # Fix 05/07/2026: recargar rubros/materiales desde DB si faltan en el
    # cookie (heavy keys) y recalcular p['totales'] SIEMPRE fresco acá (mismo
    # criterio que el guardado final más abajo) — así lo que se ve en esta
    # pantalla coincide exactamente con lo que se guarda y con lo que
    # después lee el PDF, sin importar si se editaron materiales en paso 6
    # después de que paso 5 calculó por última vez.
    if (not p.get('rubros') or not p.get('materiales')) and p.get('_pid'):
        try:
            db_r = get_db()
            row_r = db_r.execute(
                "SELECT session_json FROM presupuestos WHERE id=?", (p['_pid'],)
            ).fetchone()
            db_r.close()
            if row_r and row_r['session_json']:
                p = {**json.loads(row_r['session_json']), **p}
        except Exception as e_r:
            print(f"[resumen] error recargando desde DB: {e_r}")

    _mat_resumen = sum(m.get('subtotal', 0) for m in p.get('materiales', [])) \
                   or p.get('total_materiales', 0)
    p['total_materiales'] = _mat_resumen
    p['totales'] = _calcular_totales_finales(
        p.get('modo', 'mo_mat'),
        p.get('total_mo', 0),
        _mat_resumen,
        p.get('subcontratos', []),
        p.get('indirectos', {}),
        p.get('pct_gg', 20),
        p.get('pct_imp', 7),
        p.get('operarios_reales', 0),
    )

    # Fix 05/07/2026: si todavía no hay descripción de trabajos (ya no se pide
    # en paso 1), se autogenera acá desde los ítems cargados.
    # Fix 05/07/2026 (cont. 5): antes solo se autogeneraba si estaba
    # TOTALMENTE vacía, así que editar un presupuesto ya guardado y agregar
    # un ítem/subcontrato nuevo no lo sumaba al texto. Ahora se usa
    # _actualizar_descripcion_con_faltantes(), que agrega solo lo que falta
    # (ítems o "SC {nombre}" no mencionados todavía) sin pisar el resto del
    # texto ya escrito/editado a mano.
    p['descripcion_trabajos'] = _actualizar_descripcion_con_faltantes(
        p.get('descripcion_trabajos', ''), p.get('rubros', []), p.get('subcontratos', [])
    )

    if request.method == 'POST':
        # Permite editar descripcion_trabajos desde el resumen
        if 'descripcion_trabajos' in request.form:
            p['descripcion_trabajos'] = request.form.get('descripcion_trabajos', '')
            session['presup'] = _session_compact(p)

        db = get_db()
        pid = p.get('_pid')

        # MERGE: la sesión compacta no tiene rubros/materiales (stripea _session_compact).
        # Cargar desde session_json en DB para que rubros_json y materiales_json se guarden completos.
        if pid:
            _row_merge = db.execute(
                "SELECT session_json FROM presupuestos WHERE id=? AND user_id=?",
                (pid, g.user['id'])
            ).fetchone()
            if _row_merge and _row_merge['session_json'] and _row_merge['session_json'] != '{}':
                try:
                    p_db = json.loads(_row_merge['session_json'])
                    p = {**p_db, **p}   # sesión cookie gana en conflicto, DB aporta rubros/materiales
                except Exception:
                    pass

        # Fix 04/07/2026: recalcular TOTALES una última vez acá, justo antes de
        # guardar. Si el usuario editó materiales a mano en paso 6 (paso6 corre
        # DESPUÉS de paso5, donde se calculó 'totales' por primera vez), ese cambio
        # no se reflejaba en costo_directo/total_final sin este recálculo final.
        # Es la misma función que usa paso 5 — única fuente de verdad para el total.
        _mat_final = sum(m.get('subtotal', 0) for m in p.get('materiales', [])) \
                     or p.get('total_materiales', 0)
        p['totales'] = _calcular_totales_finales(
            p.get('modo', 'mo_mat'),
            p.get('total_mo', 0),
            _mat_final,
            p.get('subcontratos', []),
            p.get('indirectos', {}),
            p.get('pct_gg', 20),
            p.get('pct_imp', 7),
            p.get('operarios_reales', 0),
        )
        p['total_materiales'] = _mat_final
        session['presup'] = _session_compact(p)

        totales = p.get('totales', {})

        # Generar nro solo si es nuevo (sin _editando_nro)
        nro = p.get('_editando_nro') or None
        if not nro:
            year = date.today().year
            count = db.execute(
                "SELECT COUNT(*) as c FROM presupuestos WHERE user_id=? AND status='completo' AND strftime('%Y',created_at)=?",
                (g.user['id'], str(year))
            ).fetchone()['c'] + 1
            nro = '{}-{}'.format(year, str(count).zfill(3))

        campos = {
            'cliente_nombre':    p.get('cliente_nombre'),
            'cliente_tel':       p.get('cliente_tel'),
            'cliente_email':     p.get('cliente_email'),
            'obra_descripcion':  p.get('obra_descripcion'),
            'obra_direccion':    p.get('obra_direccion'),
            'obra_tipo':         p.get('obra_tipo'),
            'fecha_presup':      p.get('fecha_presup'),
            'validez':           p.get('validez', 15),
            'modo':              p.get('modo', 'mo_mat'),
            'superficie':        p.get('superficie', 0),
            'rubros_json':       json.dumps(p.get('rubros', [])),
            'subcontratos_json': json.dumps(p.get('subcontratos', [])),
            'indirectos_json':   json.dumps(p.get('indirectos', {})),
            'materiales_json':   json.dumps(p.get('materiales', [])),
            'hh_total':          p.get('hh_total', 0),
            'n_oficiales':       p.get('n_oficiales', 2),
            'n_ayudantes':       p.get('n_ayudantes', 1),
            'jornal_oficial':    p.get('jornal_oficial', 0),
            'jornal_ayudante':   p.get('jornal_ayudante', 0),
            'dias_obra':         p.get('dias_obra', 0),
            'pct_gg':            p.get('pct_gg', 20),
            'pct_impuestos':     p.get('pct_imp', 7),
            'pct_anticipo':      p.get('pct_anticipo', 30),
            'pct_final':         p.get('pct_final', 20),
            'frecuencia_pago':   p.get('frecuencia', 'mensual'),
            'tipo_cambio':       p.get('tipo_cambio', 1),
            'costo_directo':     totales.get('costo_directo', 0),
            'total_subcontratos': totales.get('total_subc', 0),
            'total_indirectos':  totales.get('total_ind', 0),
            'total_mo':          p.get('total_mo', 0),
            'total_materiales':  p.get('total_materiales', 0),
            'total_presupuesto': totales.get('total_final', 0),
            'descripcion_trabajos': p.get('descripcion_trabajos', ''),
            'fecha_actualizacion': date.today().isoformat(),
            'status':            'completo',
            'wizard_step':       8,
            'session_json':      '{}',
        }

        if pid:
            sets = ', '.join('{}=?'.format(k) for k in campos)
            vals_final = list(campos.values()) + [pid, g.user['id']]
            db.execute(
                "UPDATE presupuestos SET {}, updated_at=datetime('now', 'localtime') WHERE id=? AND user_id=?".format(sets),
                vals_final
            )
            db.execute(
                "UPDATE presupuestos SET nro=? WHERE id=? AND (nro='' OR nro IS NULL)",
                (nro, pid)
            )
            db.commit()
        else:
            db.execute(
                """
            INSERT INTO presupuestos
            (user_id, nro, cliente_nombre, cliente_tel, cliente_email,
             obra_descripcion, obra_direccion, obra_tipo, fecha_presup, validez,
             modo, superficie, rubros_json, subcontratos_json, indirectos_json,
             materiales_json, hh_total, n_oficiales, n_ayudantes,
             jornal_oficial, jornal_ayudante, dias_obra, pct_gg, pct_impuestos,
             pct_anticipo, pct_final, frecuencia_pago, tipo_cambio,
             costo_directo, total_subcontratos, total_indirectos,
             total_mo, total_materiales, total_presupuesto,
             descripcion_trabajos, fecha_actualizacion, status, wizard_step, session_json)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                tuple(campos.values())
            )
            db.commit()
            pid = db.execute("SELECT last_insert_rowid() as id").fetchone()['id']
            nro = '{}-{:03d}'.format(date.today().year, pid)
            db.execute(
                "UPDATE presupuestos SET nro=? WHERE id=? AND (nro='' OR nro IS NULL)",
                (nro, pid)
            )
            db.commit()

        db.close()
        session.pop('presup', None)
        flash('Presupuesto {} guardado correctamente.'.format(nro or ''), 'success')
        return redirect(url_for('presupuesto.ver', pid=pid))

    return render_template('presupuesto/paso8_resumen.html',
                           p=p, simbolo=simbolo, user=g.user)


# =========================================================================
# VER presupuesto
# =========================================================================
@bp.route('/<int:pid>')
@login_required
def ver(pid):
    db = get_db()
    pres = db.execute(
        "SELECT * FROM presupuestos WHERE id=? AND user_id=?", (pid, g.user['id'])
    ).fetchone()
    cfg_precios = db.execute(
        "SELECT valor FROM config WHERE clave='precios_updated_at'"
    ).fetchone()
    db.close()
    if not pres:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(url_for('dashboard.index'))

    p = dict(pres)
    for campo in ('rubros_json', 'subcontratos_json', 'indirectos_json', 'materiales_json'):
        p[campo.replace('_json', '')] = json.loads(p.get(campo) or '[]')

    # ── Calcular días transcurridos y si hay precios nuevos ──────────────
    hoy = date.today()
    ref_fecha_str = p.get('fecha_actualizacion') or p.get('fecha_presup') or ''
    try:
        ref_fecha = datetime.strptime(ref_fecha_str[:10], '%Y-%m-%d').date()
    except Exception:
        ref_fecha = hoy
    dias_transcurridos = (hoy - ref_fecha).days

    precios_updated_str = cfg_precios['valor'] if cfg_precios else None
    precios_mas_nuevos = False
    if precios_updated_str:
        try:
            precios_date = datetime.strptime(precios_updated_str[:10], '%Y-%m-%d').date()
            precios_mas_nuevos = precios_date > ref_fecha
        except Exception:
            pass

    necesita_actualizacion = dias_transcurridos > 30 or precios_mas_nuevos
    # ─────────────────────────────────────────────────────────────────────

    pais = session.get('pais', 'AR')
    tasa, simbolo = get_tipo_cambio(pais)
    cuadro = calcular_cuadro_pago(
        p['total_presupuesto'],
        p['pct_anticipo'], p['pct_final'],
        calcular_cuotas(p['dias_obra'], p['frecuencia_pago'])
    )
    return render_template('presupuesto/ver.html',
                           p=p, cuadro=cuadro, simbolo=simbolo, user=g.user,
                           dias_transcurridos=dias_transcurridos,
                           precios_mas_nuevos=precios_mas_nuevos,
                           necesita_actualizacion=necesita_actualizacion)


# =========================================================================
# ELIMINAR borrador
# =========================================================================
@bp.route('/borrador/<int:pid>/eliminar', methods=['POST'])
@login_required
def eliminar_borrador(pid):
    db = get_db()
    db.execute(
        "DELETE FROM presupuestos WHERE id=? AND user_id=? AND status='borrador'",
        (pid, g.user['id'])
    )
    db.commit()
    db.close()
    flash('Borrador eliminado.', 'info')
    return redirect(url_for('dashboard.index'))
