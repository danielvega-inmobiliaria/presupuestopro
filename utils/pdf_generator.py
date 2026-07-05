import base64
from io import BytesIO
from fpdf import FPDF

AZUL    = (15, 30, 60)
AZUL_M  = (29, 68, 170)
GRIS    = (55, 65, 81)
GRIS_C  = (243, 244, 246)
AMAR    = (234, 179, 8)
VERDE   = (22, 101, 52)
NARANJA = (234, 88, 12)


def fmt(n, simbolo='$'):
    try:
        return f"{simbolo} {int(round(float(n))):,}".replace(',', '.')
    except Exception:
        return f"{simbolo} 0"


def fmt_cant(n):
    """Formatea una cantidad (no moneda) con separador decimal AR (coma) y
    sin decimales innecesarios cuando el valor es entero."""
    try:
        n = float(n)
    except Exception:
        return str(n)
    if n == int(n):
        return f"{int(n):,}".replace(',', '.')
    txt = f"{n:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return txt


def _iniciales_empresa(nombre):
    """2 iniciales a partir del nombre de la empresa (ej. 'Vega Construcciones' -> 'VC'),
    usadas como placeholder de logo cuando la empresa no cargó uno (fix 05/07/2026)."""
    palabras = [w for w in (nombre or '').strip().split() if w]
    if not palabras:
        return ''
    if len(palabras) == 1:
        return palabras[0][:2].upper()
    return (palabras[0][0] + palabras[1][0]).upper()


def _conectar_ultima(lista):
    """Une una lista de palabras con comas y 'y'/'e' antes de la última
    (regla gramatical: 'e' si la última palabra empieza con sonido 'i')."""
    lista = [x for x in lista if x]
    if not lista:
        return ''
    if len(lista) == 1:
        return lista[0]
    conectivo = 'e' if lista[-1][:1].lower() == 'i' else 'y'
    return ', '.join(lista[:-1]) + f' {conectivo} ' + lista[-1]


class PDF(FPDF):
    def __init__(self, titulo, nro, simbolo='$', empresa=None, banner_claro=False):
        super().__init__()
        self.simbolo = simbolo
        self.titulo  = titulo
        self.nro     = nro
        self.empresa = empresa or {}
        # Fix 05/07/2026: banner_claro=True (PDF propietario) usa un tono de
        # azul más claro (AZUL_M) para el banner de presentación en vez del
        # azul oscuro original (AZUL) — pedido de Daniel, solo para el
        # PDF de cara al cliente. El PDF constructor sigue con el tono original.
        self.banner_claro = banner_claro
        # Pre-decodificar logo una sola vez
        self._logo_bytes = None
        logo_b64 = self.empresa.get('logo_data', '')
        if logo_b64:
            try:
                self._logo_bytes = base64.b64decode(logo_b64)
            except Exception:
                self._logo_bytes = None
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(True, margin=15)
        self.add_page()

    def header(self):
        empresa_nombre = self.empresa.get('nombre', '').strip()
        empresa_slogan = self.empresa.get('slogan', '').strip()
        tiene_empresa  = empresa_nombre or self._logo_bytes

        # Altura del banner: 22 sin empresa, 32 con nombre/logo (espacio para contacto/tel)
        banner_h = 32 if tiene_empresa else 22

        color_banner = AZUL_M if self.banner_claro else AZUL
        self.set_fill_color(*color_banner)
        self.rect(0, 0, 210, banner_h, 'F')

        x_texto = 15
        logo_w  = 0

        # Logo (izquierda)
        if self._logo_bytes:
            try:
                logo_buf = BytesIO(self._logo_bytes)
                logo_h   = banner_h - 6          # margen vertical
                self.image(logo_buf, x=15, y=3, h=logo_h)
                logo_w = logo_h * 2.5            # estimado ancho proporcional
                x_texto = 15 + logo_w + 4
            except Exception:
                pass
        elif empresa_nombre:
            # Fix 05/07/2026: sin logo cargado → placeholder con las iniciales
            # de la empresa (ej. "Vega Construcciones" -> "VC") en vez de
            # dejar el espacio vacío.
            iniciales = _iniciales_empresa(empresa_nombre)
            if iniciales:
                logo_h = banner_h - 6
                logo_w = logo_h
                self.set_fill_color(*AMAR)
                self.rect(15, 3, logo_w, logo_h, 'F')
                self.set_text_color(*AZUL)
                self.set_font('Helvetica', 'B', logo_h * 2.1)
                self.set_xy(15, 3 + logo_h * 0.24)
                self.cell(logo_w, logo_h * 0.55, iniciales, align='C')
                x_texto = 15 + logo_w + 4

        # Nombre empresa (línea superior) — fix 05/07/2026: tamaño de fuente
        # aumentado de 11 a 14 (pedido "un poco más grande").
        if empresa_nombre:
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(*AMAR)
            self.set_xy(x_texto, 3.5)
            self.cell(0, 6.5, empresa_nombre, ln=1)
            if empresa_slogan:
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(200, 210, 230)
                self.set_x(x_texto)
                self.cell(0, 4, empresa_slogan, ln=1)
            # Contacto y teléfono
            contacto  = self.empresa.get('contacto', '').strip()
            telefono  = self.empresa.get('telefono', '').strip()
            info_line = ' | '.join(filter(None, [contacto, telefono]))
            if info_line:
                self.set_font('Helvetica', '', 8)
                self.set_text_color(200, 210, 230)
                self.set_x(x_texto)
                self.cell(0, 4, info_line, ln=1)
            # Titulo del PDF
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(255, 255, 255)
            self.set_x(x_texto)
            self.cell(140, 5, self.titulo, ln=0)
            self.set_font('Helvetica', '', 9)
            self.set_text_color(200, 210, 230)
            self.cell(0, 5, f"N {self.nro}", align='R', ln=1)
        else:
            # Sin datos empresa: diseño original
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(*AMAR)
            self.set_xy(x_texto, 5)
            self.cell(120, 12, self.titulo, ln=0)
            self.set_font('Helvetica', '', 10)
            self.set_text_color(255, 255, 255)
            self.cell(0, 12, f"N {self.nro}", align='R', ln=1)

        self.set_y(banner_h + 3)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*GRIS)
        empresa_nombre = self.empresa.get('nombre', '').strip()
        pie = empresa_nombre if empresa_nombre else 'PresupuestoPRO'
        self.cell(0, 8, f'{pie}  |  Pagina {self.page_no()}', align='C')

    def seccion(self, titulo):
        self.set_fill_color(*AZUL)
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 7, f'  {titulo}', fill=True, ln=1)
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def fila_kv(self, key, val, bold_val=False):
        self.set_font('Helvetica', '', 9)
        self.set_text_color(*GRIS)
        self.cell(55, 6, key, ln=0)
        if bold_val:
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(*AZUL_M)
        else:
            self.set_text_color(0, 0, 0)
        self.cell(0, 6, str(val), ln=1)
        self.set_text_color(0, 0, 0)

    def tabla_header(self, cols):
        self.set_fill_color(*GRIS)
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 8)
        for texto, ancho, alin in cols:
            self.cell(ancho, 6, texto, fill=True, align=alin, border=0)
        self.ln()
        self.set_text_color(0, 0, 0)

    def tabla_fila(self, cols, fill=False):
        if fill:
            self.set_fill_color(*GRIS_C)
        self.set_font('Helvetica', '', 8)
        for texto, ancho, alin in cols:
            self.cell(ancho, 5.5, str(texto), fill=fill, align=alin, border=0)
        self.ln()

    def tabla_total(self, label, valor):
        self.set_fill_color(*AZUL)
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 9)
        self.cell(140, 7, label, fill=True, align='R', border=0)
        self.cell(40, 7, valor, fill=True, align='R', border=0)
        self.ln()
        self.set_text_color(0, 0, 0)


# ---- PDF PROPIETARIO --------------------------------------------------------
def _fmt_fecha(fecha_iso):
    """Convierte 'YYYY-MM-DD' a 'DD-MM-AAAA'."""
    try:
        y, m, d = fecha_iso.split('-')
        return f"{d}-{m}-{y}"
    except Exception:
        return fecha_iso


def generar_pdf_propietario(p, empresa=None):
    simbolo = p.get('simbolo', '$')
    total   = p.get('total_presupuesto', 0)
    cuadro  = p.get('cuadro_pago', {})
    modo    = p.get('modo', 'mo_mat')

    # Fix 05/07/2026: banner_claro=True — tono de banner más claro pedido por
    # Daniel, solo para el PDF de cara al propietario/cliente.
    pdf = PDF('PRESUPUESTO DE CONSTRUCCION', p.get('nro', ''), simbolo, empresa, banner_claro=True)

    pdf.seccion('Datos del cliente y la obra')
    pdf.fila_kv('Cliente:',   p.get('cliente_nombre', ''))
    # Fix 05/07/2026: omitir filas vacías (Telefono/Email) — antes siempre se
    # imprimían aunque no hubiera dato, gastando espacio de página sin
    # necesidad (ver nota de "hoja en blanco" más abajo, junto a Forma de pago).
    if (p.get('cliente_tel') or '').strip():
        pdf.fila_kv('Telefono:', p.get('cliente_tel', ''))
    if (p.get('cliente_email') or '').strip():
        pdf.fila_kv('Email:', p.get('cliente_email', ''))
    pdf.fila_kv('Obra:',      p.get('obra_descripcion', ''))
    pdf.fila_kv('Direccion:', p.get('obra_direccion', ''))
    pdf.fila_kv('Tipo:',      p.get('obra_tipo', ''))
    pdf.fila_kv('Fecha:',     _fmt_fecha(p.get('fecha_presup', '')))
    pdf.fila_kv('Validez:',   f"{p.get('validez', 15)} dias desde emision")
    desc_trab = p.get('descripcion_trabajos', '').strip()
    if desc_trab:
        pdf.ln(2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*GRIS)
        pdf.cell(0, 5, 'Descripcion de trabajos:', ln=1)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, desc_trab)
    pdf.ln(3)

    pdf.seccion('Resumen economico')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*GRIS)
    # Fix 05/07/2026: texto dinámico según lo realmente presupuestado (antes era
    # fijo y siempre mencionaba materiales/subcontratos aunque no correspondiera).
    _partes_incluye = ['mano de obra']
    if modo != 'solo_mo':
        _partes_incluye.append('materiales')
    if p.get('subcontratos'):
        _partes_incluye.append('subcontratos')
    if (p.get('pct_gg', 0) or 0) > 0:
        _partes_incluye.append('gastos generales')
    if (p.get('pct_impuestos', 0) or 0) > 0:
        _partes_incluye.append('impuestos')
    pdf.multi_cell(0, 5,
        f"Incluye {_conectar_ultima(_partes_incluye)}. No incluye IVA.")
    pdf.ln(3)

    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(*AMAR)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 10, f"TOTAL:  {fmt(total, simbolo)}", fill=True, align='C', ln=1)
    pdf.ln(2)
    pdf.set_text_color(*GRIS)
    pdf.set_font('Helvetica', '', 8)
    tc = p.get('tipo_cambio', 1) or 1
    usd_equiv = int(total / tc)
    fecha_fmt = _fmt_fecha(p.get('fecha_presup', ''))
    pdf.cell(0, 5,
        f"Tiempo estimado: {p.get('dias_obra', 0)} dias  |  Equiv. USD: USD {usd_equiv:,}  |  Precios al {fecha_fmt}".replace(',', '.'),
        ln=1)
    pdf.ln(3)

    # Fix 05/07/2026: detalle de items de obra a realizar, por item (no por
    # rubro como en el resumen interno) — solo unidades presupuestadas, sin
    # detalle de costo unitario (ese detalle queda para el PDF constructor).
    items_pdf = [it for rubro in p.get('rubros', []) for it in rubro.get('items', [])
                 if it.get('cantidad', 0) > 0]
    if items_pdf:
        pdf.seccion('Items de obra a realizar')
        pdf.tabla_header([('Item', 110, 'L'), ('Cantidad', 35, 'C'), ('Unidad', 35, 'C')])
        fill = False
        for it in items_pdf:
            pdf.tabla_fila([
                (it.get('nombre', ''), 110, 'L'),
                (fmt_cant(it.get('cantidad', 0)), 35, 'C'),
                (it.get('unidad', ''), 35, 'C'),
            ], fill=fill)
            fill = not fill
        pdf.ln(3)

    # Fix 05/07/2026: lista de materiales — antes solo se mostraba en modo
    # "Solo mano de obra". Ahora se muestra siempre que haya datos (también
    # en "MO + Materiales", donde el propietario igual quiere ver el detalle
    # de qué materiales y cantidades componen el total, tal como ya se
    # mostraba en pantalla en paso 8 — resumen interno). El título cambia
    # según el modo: en solo_mo el propietario los compra él mismo; en
    # mo_mat es solo a título informativo (ya están incluidos en el TOTAL).
    if p.get('materiales'):
        titulo_mat = ('Materiales a comprar (a cargo del propietario)' if modo == 'solo_mo'
                      else 'Materiales incluidos en el presupuesto (detalle)')
        pdf.seccion(titulo_mat)
        pdf.tabla_header([('Material', 75, 'L'), ('Cant.', 25, 'C'), ('Unidad', 25, 'C'),
                           ('Precio unit.', 30, 'R'), ('Subtotal', 25, 'R')])
        fill = False
        total_mat_pdf = 0
        for m in p.get('materiales', []):
            pdf.tabla_fila([
                (m.get('nombre', ''), 75, 'L'),
                (fmt_cant(m.get('cantidad', 0)), 25, 'C'),
                (m.get('unidad', ''), 25, 'C'),
                (fmt(m.get('precio_local', 0), simbolo), 30, 'R'),
                (fmt(m.get('subtotal', 0), simbolo), 25, 'R'),
            ], fill=fill)
            fill = not fill
            total_mat_pdf += m.get('subtotal', 0)
        pdf.ln(1)
        label_total_mat = 'TOTAL MATERIALES A COMPRAR:' if modo == 'solo_mo' else 'TOTAL MATERIALES (incluido en el TOTAL):'
        pdf.tabla_total(label_total_mat, fmt(total_mat_pdf, simbolo))
        pdf.ln(4)

    # Fix 05/07/2026: evitar que el bloque "Forma de pago" + firma quede
    # partido entre 2 páginas (ej. el título y 1 fila en una hoja, el resto y
    # las firmas en la siguiente, con la hoja nueva casi vacía). Se calcula
    # la altura aproximada de todo el bloque y si no entra en lo que queda de
    # la página actual, se fuerza un salto de página ANTES de empezar, para
    # que el bloque completo quede junto (y prolijo) en una sola página.
    _alto_bloque_pago = 9 + 8*3 + 2 + 5 + 8 + 15   # seccion + 3 filas + notas + firma
    if pdf.get_y() + _alto_bloque_pago > (pdf.h - pdf.b_margin):
        pdf.add_page()

    pdf.seccion('Forma de pago')
    pdf.set_font('Helvetica', '', 9)

    n_cuotas   = cuadro.get('n_cuotas', 0)
    monto_c    = cuadro.get('monto_cuota', 0)
    frec_raw   = p.get('frecuencia_pago', 'mensual')
    frec_label = {'semanal': 'semanales', 'quincenal': 'quincenales', 'mensual': 'mensuales'}.get(frec_raw, frec_raw)

    # Fila 1: Anticipo
    pdf.set_fill_color(*VERDE)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(120, 8, '  Anticipo - al inicio', fill=True, border=0)
    pdf.cell(60, 8, fmt(cuadro.get('anticipo', 0), simbolo), fill=True, align='R', border=0, ln=1)

    # Fila 2: Cuotas (resumen en 1 línea con monto por cuota)
    if n_cuotas > 0:
        cuota_txt = f'  {n_cuotas} cuota{"s" if n_cuotas > 1 else ""} {frec_label} de {fmt(monto_c, simbolo)} c/u'
    else:
        cuota_txt = '  Sin cuotas intermedias'
    pdf.set_fill_color(*GRIS_C)
    pdf.set_text_color(*GRIS)
    pdf.cell(120, 8, cuota_txt, fill=True, border=0)
    pdf.set_text_color(*AZUL_M)
    pdf.set_font('Helvetica', 'B', 9)
    total_cuotas_txt = fmt(monto_c * n_cuotas, simbolo) if n_cuotas > 0 else '-'
    pdf.cell(60, 8, total_cuotas_txt, fill=True, align='R', border=0, ln=1)
    pdf.set_font('Helvetica', '', 9)

    # Fila 3: Saldo final
    pdf.set_fill_color(*NARANJA)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(120, 8, '  Saldo final - al terminar obra', fill=True, border=0)
    pdf.cell(60, 8, fmt(cuadro.get('saldo_final', 0), simbolo), fill=True, align='R', border=0, ln=1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(*GRIS)
    fecha = _fmt_fecha(p.get('fecha_presup', ''))
    if n_cuotas > 0:
        pdf.cell(0, 5, f"{n_cuotas} cuotas {frec_label} de {fmt(monto_c, simbolo)} c/u  |  Precios al {fecha}  |  Sin IVA", ln=1)
    else:
        pdf.cell(0, 5, f"Precios al {fecha}  |  Sin IVA", ln=1)
    pdf.ln(8)

    pdf.set_draw_color(*GRIS)
    y = pdf.get_y()
    pdf.line(15, y, 105, y)
    pdf.line(115, y, 195, y)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(*GRIS)
    pdf.set_y(y + 2)
    pdf.cell(90, 5, 'Firma del Constructor', ln=0)
    pdf.cell(0, 5, 'Firma del Propietario / Aclaracion', ln=1)

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf


# ---- PDF CONSTRUCTOR --------------------------------------------------------
def generar_pdf_constructor(p, empresa=None):
    simbolo      = p.get('simbolo', '$')
    totales_base = p.get('total_presupuesto', 0)
    pct_gg       = p.get('pct_gg', 20)
    pct_imp      = p.get('pct_impuestos', 7)
    modo         = p.get('modo', 'mo_mat')

    # Costo Directo = total_mo + total_materiales (analisis_sub). Fix 04/07/2026:
    # antes usaba p.get('costo_directo') / sum(rubros total_local), que es
    # items_obra.precio_ars×qty — un catálogo de precios que ninguna migración
    # de precios actualiza. Ver misma corrección en routes/presupuesto.py.
    rubros_list      = p.get('rubros', [])
    total_subc       = p.get('total_subcontratos', 0)
    total_ind        = p.get('total_indirectos', 0)
    total_mo         = p.get('total_mo', 0)
    costo_directo    = total_mo + p.get('total_materiales', 0)

    # Base segun modo: solo_mo usa la MO como base de calculo, mo_mat usa rubros
    if modo == 'solo_mo':
        base = total_mo + total_subc + total_ind
    else:
        base = costo_directo + total_subc + total_ind

    beneficio    = round(base * pct_gg / 100)

    pdf = PDF('DESGLOSE INTERNO - USO DEL CONSTRUCTOR', p.get('nro', ''), simbolo, empresa)

    pdf.seccion('Datos de la obra')
    pdf.fila_kv('Cliente:',   p.get('cliente_nombre', ''))
    pdf.fila_kv('Obra:',      p.get('obra_descripcion', ''))
    pdf.fila_kv('Direccion:', p.get('obra_direccion', ''))
    modo_txt = 'MO + Materiales' if p.get('modo') == 'mo_mat' else 'Solo mano de obra'
    pdf.fila_kv('Modo:',      modo_txt)
    pdf.fila_kv('Operarios:', f"{p.get('n_oficiales', 0)} oficiales + {p.get('n_ayudantes', 0)} ayudantes")
    pdf.fila_kv('Tiempo:',    f"{p.get('dias_obra', 0)} dias estimados")
    desc_trab = p.get('descripcion_trabajos', '').strip()
    if desc_trab:
        pdf.ln(2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*GRIS)
        pdf.cell(0, 5, 'Descripcion de trabajos:', ln=1)
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, desc_trab)
    pdf.ln(4)

    # Items / Rubros
    pdf.seccion('Items de obra')
    pdf.tabla_header([
        ('N', 12, 'C'), ('Rubro', 138, 'L'), ('Monto', 30, 'R')
    ])
    for i, r in enumerate(rubros_list):
        if r.get('total_local', 0) > 0:
            pdf.tabla_fila([
                (r['num'], 12, 'C'),
                (r['nombre'], 138, 'L'),
                (fmt(r['total_local'], ''), 30, 'R'),
            ], fill=(i % 2 == 0))
    pdf.tabla_total('COSTO DIRECTO', fmt(costo_directo, simbolo))
    pdf.ln(4)

    # Subcontratos
    if p.get('subcontratos'):
        pdf.seccion('Subcontratos')
        pdf.tabla_header([
            ('Rubro', 70, 'L'), ('MO', 35, 'R'), ('Materiales', 35, 'R'), ('Total', 40, 'R')
        ])
        for i, s in enumerate(p['subcontratos']):
            pdf.tabla_fila([
                (s['nombre'], 70, 'L'),
                (fmt(s['mo_local'], ''), 35, 'R'),
                (fmt(s['mat_local'], ''), 35, 'R'),
                (fmt(s['total_local'], simbolo), 40, 'R'),
            ], fill=(i % 2 == 0))
        pdf.tabla_total('TOTAL SUBCONTRATOS', fmt(p.get('total_subcontratos', 0), simbolo))
        pdf.ln(4)

    # Indirectos
    ind = p.get('indirectos', {})
    if any(ind.get(k, 0) for k in ('movilidad', 'andamios', 'herramientas')):
        pdf.seccion('Costos indirectos')
        for k, label in [
            ('movilidad',    'Movilidad'),
            ('andamios',     'Alquiler andamios'),
            ('herramientas', 'Alquiler herramientas'),
        ]:
            v = ind.get(k, 0)
            if v:
                pdf.set_font('Helvetica', '', 9)
                pdf.cell(130, 5.5, f'  {label}', ln=0)
                pdf.cell(0, 5.5, fmt(v, simbolo), align='R', ln=1)
        pdf.tabla_total('TOTAL INDIRECTOS', fmt(p.get('total_indirectos', 0), simbolo))
        pdf.ln(4)

    # Materiales
    mats = p.get('materiales', [])
    if mats:
        pdf.seccion('Lista de materiales con precios')
        pdf.tabla_header([
            ('Material', 70, 'L'), ('Unidad', 22, 'C'),
            ('Cantidad', 20, 'R'), ('P. Unit.', 30, 'R'), ('Subtotal', 38, 'R')
        ])
        for i, m in enumerate(mats):
            pdf.tabla_fila([
                (m['nombre'], 70, 'L'),
                (m['unidad'], 22, 'C'),
                (m['cantidad'], 20, 'R'),
                (fmt(m['precio_local'], simbolo), 30, 'R'),
                (fmt(m['subtotal'], simbolo), 38, 'R'),
            ], fill=(i % 2 == 0))
        pdf.tabla_total('TOTAL MATERIALES', fmt(p.get('total_materiales', 0), simbolo))
        pdf.ln(4)

    # Resumen economico
    pdf.seccion('Resumen economico del constructor')
    rows = [
        ('Total MO a pagar',            p.get('total_mo', 0)),
        ('Subcontratos a pagar',         p.get('total_subcontratos', 0)),
        ('Indirectos a pagar',           p.get('total_indirectos', 0)),
    ]
    if p.get('modo') == 'mo_mat':
        rows.append(('Total materiales incluidos', p.get('total_materiales', 0)))
    rows.append(('Impuestos y seguros', round(base * pct_imp / 100)))

    for label, val in rows:
        pdf.set_font('Helvetica', '', 9)
        pdf.cell(130, 5.5, f'  {label}', ln=0)
        pdf.cell(0, 5.5, fmt(val, simbolo), align='R', ln=1)

    pdf.set_fill_color(*VERDE)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(130, 8, '  BENEFICIO (GG + Ganancia)', fill=True, border=0)
    pdf.cell(0, 8, fmt(beneficio, simbolo), fill=True, align='R', border=0, ln=1)
    pdf.set_text_color(0, 0, 0)

    pdf.tabla_total('TOTAL PRESUPUESTO', fmt(totales_base, simbolo))

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf
