import math
import re
import unicodedata

def normalize_nombre(name):
    """Normaliza nombre de ítem para matching robusto:
    quita tildes, minúsculas, colapsa espacios, elimina espacios tras punto."""
    nfkd = unicodedata.normalize('NFKD', str(name))
    sin_tildes = ''.join(c for c in nfkd if not unicodedata.combining(c))
    collapsed = ' '.join(sin_tildes.lower().split()).rstrip('.')
    # "Ho.Ado. viga" → "Ho.Ado.viga"  (espacio tras punto interno)
    collapsed = re.sub(r'\.\s+', '.', collapsed)
    return collapsed

# Mapeo explícito: normalize_nombre(items_obra) → normalize_nombre(analisis_sub)
# Para casos donde los nombres son estructuralmente distintos
ANALISIS_NAME_MAP = {
    # Instalaciones
    'instalacion desague':           'instalacion desagues',
    # Cemento → nombre real en analisis
    'cemento: piso alisado':         'piso cto.alisado',
    'cemento: piso rodillado':       'piso cemento rodillado',
    'cemento: revoque':              'revoque cemento',
    'cemento: toma de juntas':       'toma de juntas',
    'cemento: zocalo 10cm':          'zocalo cemento 10cm',
    'cemento: azotado':              'azotado impermeable',
    'cemento: capa aisladora s/muros': 'capa aisladora hor.y vertical',
    # Otros
    'carpeta bajo piso':             'carpeta b/piso',
    'banquina ho pobre 10cm':        'banquina h pobre 10cm',
    'rebajo de cordon':              'rebaje de cordon',
    'revest.texturado':              'revest texturado',
    'revest. texturado':             'revest texturado',
    'colocacion de aberturas':       'colocacion de aberturas',
    # Mampostería con unidades distintas (cm vs metros)
    'mamp.ladrillo comun 15cm':      'mamp.ladrillo comun 0,15m',
    'mamp.ladrillo comun 30cm':      'mamp.ladrillo comun 0,30m',
    'mamp.ladrillo vista 15cm':      'mamp.ladrillo vista 0,15m',
    'mamp.ladrillo vista 30cm':      'mamp.ladrillo vista 0,30m',
    # Revoques — diferencia de nombre: "3-6m" en items_obra vs "3 a 6m" en analisis
    'estructura cielo suspendido (3-6m)': 'estructura cielo suspendido (3 a 6m)',
    # Mampostería — Tabiques (items_obra usa "Tabique..." pero analisis usa "Mamp....")
    'tabique ladrillo comun 8cm':           'mamp.ladrillo comun 0,075m',
    'tabique ladrillo hueco 8x18x33':       'mamp.ladrillo hueco 8cm',
    'tabique ladrillo hueco 12x18x33':      'mamp.ladrillo hueco 12cm',
    'tabique ladrillo hueco 18x18x33':      'mamp.ladrillo hueco 18cm',
    'tabique hueco portante 12x19x33cm':    'mamp.ladrillo hueco portante 12x18x33cm',
    'tabique hueco portante 18x19x33cm':    'mamp.ladrillo hueco portante 18x18x33cm',
    # Dinteles — diferencia tipográfica: "30 cm" en analisis vs "30cm" en items_obra
    'dinteles pared 30cm':                  'dinteles pared 30 cm',
    # Hormigón elaborado — Hormigón elaborado colado es MATERIAL HOJA (no expandir)
    'hormigon comun':                'hormigon comun colado (6,00hh)',
    # Losa premoldeada H.Elab. → clave real en analisis_sub
    'h.elab.losa premoldeada':       'h.elab.losa ceramica',
    # Demolicion hormigon: nombre en items_obra != nombre en analisis_sub
    'demolicion hormigon armado':    'demolicion hormigon ado',
    # Sub-ítems compuestos de Ho.Ado./H.Elab. → se expanden recursivamente
    'hormigon colado':               'hormigon comun colado (6,00hh)',
    'armadura colocada':             'armadura colocada (0,20hh)',
    'encofrado':                     'encofrado (2,60hh)',
    # Ho.Ado. → nombres en items_obra (largo) → clave en analisis_sub (abreviado)
    'ho.ado.viga fundacion (75-7)':  'ho.ado.viga fund (75-7)',
    'ho.ado.tabique 10cm (110-20)':  'ho.ado.tab.10cm (110-20)',
    'ho.ado.tabique 15cm (110-13)':  'ho.ado.tab.15cm (110-13,33)',
    'ho.ado.tanque (90-13)':         'ho.ado.tanque (90-13,33)',
    'ho.ado.losa 15cm (75-6.66)':    'ho.ado.losa 15cm (75-7)',
    # H.Elab. → nombres en items_obra → clave en analisis_sub
    'h.elab.viga fundacion (75-7)':  'h.elab.viga fund (75-7)',
    'h.elab.tabique 10cm (110-20)':  'h.elab.tab.10cm.(110-14)',
    'h.elab.tabique 15cm (110-13)':  'h.elab.tab.15cm.(110-7)',
    'h.elab.tanque (90-13)':         'h.elab.tanque (90-14)',
    'h.elab.losa 10cm (80-10)':      'h.elab.losa 10cm.(80-10)',
    'h.elab.losa 15cm (75-6.66)':    'h.elab.losa 15cm.(75-7)',
}

# Factor divisor extra en fórmula G del Excel para instalaciones especiales.
# Items!G_item = (((HOF+HAY)/8) / (F$3+H$3)) / g_factor
# Factor > 1 indica que la especialidad trabaja en paralelo con el equipo principal.
ITEMS_G_FACTOR = {
    # Forma del Excel (Items sheet)
    'instalacion desagues':  3.8,
    'instalacion agua f/c':  3.8,
    'instalacion gas':       3.8,
    'instalacion electrica': 2.263,
    # Forma de items_obra (sin tilde, variaciones de nombre)
    'instalacion desague':   3.8,
    'instalacion agua':      3.8,
}

PAISES = {
    'AR': {'moneda': 'ARS', 'simbolo': '$',   'nombre': 'Argentina'},
    'CL': {'moneda': 'CLP', 'simbolo': '$',   'nombre': 'Chile'},
    'UY': {'moneda': 'UYU', 'simbolo': '$U',  'nombre': 'Uruguay'},
    'BR': {'moneda': 'BRL', 'simbolo': 'R$',  'nombre': 'Brasil'},
    'PY': {'moneda': 'PYG', 'simbolo': 'Gs',  'nombre': 'Paraguay'},
}

RUBROS_DEFAULT = [
    {'num': '01', 'nombre': 'Preliminares',                         'es_cubierta': False},
    {'num': '02', 'nombre': 'Fundaciones',                          'es_cubierta': False},
    {'num': '03', 'nombre': 'Hormigón Armado (Ho.Ado.)',            'es_cubierta': False},
    {'num': '04', 'nombre': 'Hormigón Elaborado (H.Elab.)',         'es_cubierta': False},
    {'num': '05', 'nombre': 'Cemento',                              'es_cubierta': False},
    {'num': '06', 'nombre': 'Mampostería',                          'es_cubierta': False},
    {'num': '07', 'nombre': 'Contrapisos',                          'es_cubierta': False},
    {'num': '08', 'nombre': 'Revoques',                             'es_cubierta': False},
    {'num': '09', 'nombre': 'Revestimientos',                       'es_cubierta': False},
    {'num': '10', 'nombre': 'Techos',                               'es_cubierta': True},
    {'num': '11', 'nombre': 'Instalaciones',                        'es_cubierta': False},
    {'num': '12', 'nombre': 'Cerámicos y Porcellanatos',            'es_cubierta': True},
    {'num': '13', 'nombre': 'Pintura',                              'es_cubierta': True},
]

SUBCONTRATOS_SUGERIDOS = [
    {'id': 'electricidad', 'nombre': 'Electricidad',  'icono': 'bolt'},
    {'id': 'plomeria',     'nombre': 'Plomería',       'icono': 'droplet'},
    {'id': 'gas',          'nombre': 'Gas',             'icono': 'flame'},
    {'id': 'carpinteria',  'nombre': 'Carpintería',     'icono': 'door'},
    {'id': 'herreria',     'nombre': 'Herrería',        'icono': 'tool'},
    {'id': 'pintura',      'nombre': 'Pintura',         'icono': 'brush'},
]

def calcular_dias_obra(hh_g4, n_oficiales, n_ayudantes=0):
    """Items!G4 = REDONDEAR.MAS( SUM_items[(HOF_i + HAY_i) / (8 * (of+ay))], 0 )
    hh_g4 = suma de horas Oficial + Ayudante de todos los ítems con cantidad > 0.
    Se excluyen horas de equipo/transporte/otras especialidades."""
    workers = n_oficiales + n_ayudantes
    if workers <= 0:
        return 0
    return math.ceil(hh_g4 / (workers * 8))

def calcular_cuotas(dias_obra, frecuencia):
    """Calcula número de cuotas intermedias según frecuencia.
    Usa días calendario completos: semanal=7, quincenal=15, mensual=30.
    El último período es siempre el pago final, por eso (dias_obra-1)//período
    evita contar el día de cierre como cuota intermedia.
    Ej: 24 días semanal → pagos en días 7,14,21 → 3 cuotas intermedias."""
    if frecuencia == 'semanal':
        periodos = (dias_obra - 1) // 7
    elif frecuencia == 'quincenal':
        periodos = (dias_obra - 1) // 15
    else:  # mensual
        periodos = (dias_obra - 1) // 30
    return max(0, periodos)

# NOTA (fix 04/07/2026): la vieja calcular_totales() de acá quedó eliminada — usaba
# sum(rubro.total_local), es decir items_obra.precio_ars, el catálogo de precios que
# ninguna migración actualiza (la misma causa raíz que el bug de Costo Directo
# reportado por Daniel). Estaba importada en routes/presupuesto.py pero nunca se
# llamaba — código muerto. La única fuente de verdad ahora es
# routes/presupuesto.py::_calcular_totales_finales(), que usa total_mo (de
# items_obra.precio_mo_ars) + total_materiales (de analisis_sub, vía
# _calcular_materiales_desde_rubros / _mo_materiales_frescos).

def calcular_cuadro_pago(total, pct_ant, pct_final, n_cuotas):
    """Genera el cuadro de pagos. saldo_final absorbe el remanente para garantizar
    que anticipo + cuotas + saldo == total (sin diferencia de redondeo)."""
    monto_ant = round(total * pct_ant / 100)
    if n_cuotas > 0:
        monto_final_nominal = round(total * pct_final / 100)
        resto_cuotas = total - monto_ant - monto_final_nominal
        monto_cuota  = round(resto_cuotas / n_cuotas)
    else:
        monto_cuota = 0
    # saldo absorbe todo lo que reste tras anticipo + cuotas (cubre redondeo y % faltante)
    monto_final = total - monto_ant - monto_cuota * n_cuotas
    return {
         'anticipo':     monto_ant,
        'cuotas':       [monto_cuota] * n_cuotas,
        'n_cuotas':     n_cuotas,
        'monto_cuota':  monto_cuota,
        'saldo_final':  monto_final,
        'verificacion': monto_ant + monto_cuota * n_cuotas + monto_final,
    }

def fmt_moneda(valor, simbolo='$'):
    """Formatea un numero como moneda local."""
    return f"{simbolo} {valor:,.0f}".replace(',', '.')
