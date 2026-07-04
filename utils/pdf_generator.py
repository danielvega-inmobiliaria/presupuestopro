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


class PDF(FPDF):
    def __init__(self, titulo, nro, simbolo='$', empresa=None):
        super().__init__()
        self.simbolo = simbolo
        self.titulo  = titulo
        self.nro     = nro
        self.empresa = empresa or {}
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

        self.set_fill_color(*AZUL)
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

        # Nombre empresa (línea superior)
        if empresa_nombre:
            self.set_font('Helvetica', 'B', 11)
            self.set_text_color(*AMAR)
            self.set_xy(x_texto, 4)
            self.cell(0, 5, empresa_nombre, ln=1)
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

    pdf = PDF('PRESUPUESTO DE CONSTRUCCION', p.get('nro', ''), simbolo, empresa)

    pdf.seccion('Datos del cliente y la obra')
    pdf.fila_kv('Cliente:',   p.get('cliente_nombre', ''))
    pdf.fila_kv('Telefono:',  p.get('cliente_tel', ''))
    pdf.fila_kv('Email:',     p.get('cliente_email', ''))
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
    pdf.ln(4)

    pdf.seccion('Resumen economico')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(0, 5,
        'Incluye mano de obra, materiales, subcontratos, gastos generales e impuestos. No incluye IVA.')
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
    pdf.ln(5)

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
