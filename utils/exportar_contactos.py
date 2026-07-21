"""
Exportar usuarios a contactar (retención) — agregado 15/07/2026, pedido de
Daniel. Extendido varias veces el mismo mes:
  - 15/07/2026: Segmento C ("validado sin actividad") + hoja "Todos los usuarios".
  - 20/07/2026: Segmento D ("validado, solo usó Costo/m², nunca presupuestó")
    + columna "Segmento" en la hoja "Todos los usuarios". Antes, un usuario
    validado que solo había consultado Costo/m² (0 presupuestos, 0
    borradores, 1+ costo/m²) no caía en ningún segmento — ni B (pedía
    presup+borr==1) ni C (pedía costo/m²==0) — y quedaba invisible para la
    campaña de retención. Daniel lo pidió explícitamente: la lista tiene que
    cubrir a TODOS los usuarios, no dejar a nadie afuera de algún segmento.

Antes esto se armaba a mano: entrar a Admin > Usuarios, sacar capturas de
pantalla de la tabla y transcribir fila por fila a un Excel (lento y con
riesgo de error, sobre todo en teléfonos y contadores que se leían muy
chicos en la captura). Ahora se arma directo desde la base, en un click, con
la MISMA lógica que ya usa la tabla de Admin > Usuarios.

Segmentación (cubre el 100% de los usuarios is_admin=0, sin huecos):

  Segmento A — "Sin validar (email)": u.email_verificado = 0.
  (Se usa email_verificado y no el badge visual de la tabla porque el badge
  no se muestra cuando u.metodo_verificacion está vacío — cuentas viejas
  "grandfatheradas", ver utils/verificacion.py::get_verificacion_status.
  email_verificado sigue siendo la señal real de si activó la cuenta por
  mail o no, esté vacío el método o no.)

  Entre los validados (email_verificado = 1):
    Segmento B — hizo exactamente 1 presupuesto o borrador en total
      (n_presupuestos + n_borradores) == 1.
    Segmento C — CERO actividad de cualquier tipo: 0 presupuestos,
      0 borradores, 0 consultas de costo/m².
    Segmento D — nunca presupuestó (0 presupuestos, 0 borradores) pero SÍ
      usó la calculadora de Costo/m² al menos una vez. Es el hueco que
      había antes de 20/07/2026.
    Sin segmento de retención — 2 o más presupuestos/borradores en total:
      ya es un usuario activo de la app, no es el público de esta campaña,
      pero igual aparece listado en "Todos los usuarios" (con esa etiqueta)
      para que Daniel tenga el panorama completo.
"""
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

APP_URL = 'https://web-production-0c9c1.up.railway.app/login'

# 21/07/2026: los emails de retención salen de noreply@presupuestopro.com.ar
# sin reply_to (nadie lee las respuestas a ese mail). Para que el usuario
# pueda contestar y así abrir la ventana de 24h de WhatsApp (y quedar
# habilitado para mensajes libres desde el 2009), cada mensaje de email suma
# esta línea con el link de WhatsApp al final.
WA_LINK = 'https://wa.me/5493417542009'
WA_CTA = (f"\n\nEste mail es solo informativo — no lo respondas, esa casilla no la "
          f"lee nadie. Para hablar con nosotros, escribinos por WhatsApp: {WA_LINK}")

HEADERS_SEGMENTO = ["Nombre", "Email", "Teléfono", "Ciudad", "Provincia", "País",
                     "Presup.", "Borr.", "Costo/m²", "Estado activación", "Creado", "Vence",
                     "Mensaje WhatsApp sugerido", "Mensaje email sugerido"]

HEADERS_TODOS = ["Nombre", "Email", "Teléfono", "Ciudad", "Provincia", "País",
                  "Presup.", "Borr.", "Costo/m²", "Estado activación", "Segmento",
                  "Creado", "Vence"]

HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
HEADER_FILL = PatternFill("solid", fgColor="1F2937")
BODY_FONT = Font(name="Arial", size=10)
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

SEG_A = "A - Sin validar email"
SEG_B = "B - 1 presup./borrador en total"
SEG_C = "C - Validado, cero actividad"
SEG_D = "D - Validado, solo usó Costo/m2"
SEG_ACTIVO = "Activo (2+ presup./borr.) - no prioritario"


def _segmento(u):
    if not u['email_verificado']:
        return SEG_A
    total = u['n_presupuestos'] + u['n_borradores']
    if total == 1:
        return SEG_B
    if total == 0 and u['n_costo_m2'] == 0:
        return SEG_C
    if total == 0 and u['n_costo_m2'] > 0:
        return SEG_D
    return SEG_ACTIVO


def _mensaje_activacion(nombre):
    nombre = nombre or ''
    wa = (f"Hola {nombre}! Somos de PresupuestoPRO. Vimos que te registraste pero "
          f"todavía no activaste tu cuenta por mail. Si te trabó algo del proceso "
          f"contanos, te ayudamos. Y si preferís, te reenviamos el mail de "
          f"activación. Ingresá en: {APP_URL}")
    email = (f"Hola {nombre}, notamos que todavía no confirmaste tu cuenta en "
             f"PresupuestoPRO. Es un paso rápido y te deja usar la app sin "
             f"restricciones. Si tuviste alguna dificultad para activarla, "
             f"contanos." + WA_CTA)
    return wa, email


def _mensaje_seguimiento(nombre):
    nombre = nombre or ''
    wa = (f"Hola {nombre}! Vimos que hiciste tu primer presupuesto en PresupuestoPRO. "
          f"¿Qué te pareció? ¿Tuviste alguna dificultad usando la app? Nos ayuda "
          f"mucho tu opinión, y si necesitás una mano con el próximo presupuesto "
          f"contanos.")
    email = (f"Hola {nombre}, gracias por probar PresupuestoPRO. Nos gustaría saber "
             f"qué te pareció y si encontraste alguna dificultad al usarla. Tu "
             f"feedback nos ayuda a mejorar, y estamos para ayudarte con tu "
             f"próximo presupuesto." + WA_CTA)
    return wa, email


def _mensaje_sin_uso(nombre):
    nombre = nombre or ''
    wa = (f"Hola {nombre}! Vimos que activaste tu cuenta en PresupuestoPRO pero "
          f"todavía no hiciste tu primer presupuesto. ¿Te trabaste en algún paso o "
          f"tuviste alguna duda? Contanos y te ayudamos a armarlo — no lleva más de "
          f"unos minutos. Ingresá en: {APP_URL}")
    email = (f"Hola {nombre}, notamos que activaste tu cuenta en PresupuestoPRO pero "
             f"todavía no armaste tu primer presupuesto. Si tuviste alguna dificultad "
             f"para empezar, contanos — te ayudamos con el primero." + WA_CTA)
    return wa, email


def _mensaje_solo_costo_m2(nombre):
    nombre = nombre or ''
    wa = (f"Hola {nombre}! Vimos que probaste la calculadora de Costo/m² en "
          f"PresupuestoPRO pero todavía no armaste un presupuesto completo. Es el "
          f"paso siguiente natural y no lleva mucho más tiempo — ¿te ayudamos a "
          f"armar el primero?")
    email = (f"Hola {nombre}, notamos que usaste la calculadora de Costo/m² en "
             f"PresupuestoPRO pero todavía no armaste un presupuesto completo. Si "
             f"querés, te ayudamos a dar ese paso — contanos si tuviste alguna duda." + WA_CTA)
    return wa, email


def _mensaje_prueba_por_vencer(nombre):
    """Agregado 20/07/2026, pedido de Daniel — trigger por ciclo de vida
    (prueba gratis), no por uso, así que no participa de _segmento()."""
    nombre = nombre or ''
    wa = (f"Hola {nombre}! Tu prueba gratis de PresupuestoPRO está por terminar. Si "
          f"te sirvió, podés suscribirte desde la app para seguir usándola sin "
          f"cortes. Cualquier duda sobre el pago, contanos.")
    email = (f"Hola {nombre}, tu prueba gratis de PresupuestoPRO está por terminar. "
             f"Si te resultó útil, podés suscribirte desde la app para seguir "
             f"usándola sin interrupciones." + WA_CTA)
    return wa, email


def _mensaje_suscripcion_vencida(nombre):
    """Agregado 20/07/2026, pedido de Daniel — trigger por ciclo de vida
    (suscripción paga que no se renovó), no por uso."""
    nombre = nombre or ''
    wa = (f"Hola {nombre}! Notamos que tu suscripción a PresupuestoPRO venció y no "
          f"se renovó. ¿Tuviste algún problema con el pago o alguna duda? Contanos "
          f"— si querés reactivarla, te ayudamos.")
    email = (f"Hola {nombre}, notamos que tu suscripción a PresupuestoPRO venció. Si "
             f"tuviste algún problema con el pago o decidiste no continuar, nos "
             f"ayuda mucho que nos cuentes por qué. Y si querés reactivarla, avisanos." + WA_CTA)
    return wa, email


def _escribir_hoja_segmento(ws, usuarios, mensaje_fn):
    for c, h in enumerate(HEADERS_SEGMENTO, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER

    for r, u in enumerate(usuarios, start=2):
        wa_msg, email_msg = mensaje_fn(u['nombre'])
        estado = 'Validado' if u['email_verificado'] else 'Sin validar (email)'
        row = [
            u['nombre'] or '—', u['email'], u['telefono'] or '', u['ciudad'] or '',
            u['provincia'] or '', u['pais'] or '', u['n_presupuestos'], u['n_borradores'],
            u['n_costo_m2'], estado, (u['created_at'] or '')[:10],
            u['subscription_expires'] or '∞', wa_msg, email_msg,
        ]
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)

    widths = [18, 30, 18, 20, 20, 8, 8, 8, 9, 18, 12, 12, 55, 55]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def _escribir_hoja_todos(ws, usuarios):
    for c, h in enumerate(HEADERS_TODOS, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER

    for r, u in enumerate(usuarios, start=2):
        estado = 'Validado' if u['email_verificado'] else 'Sin validar (email)'
        row = [
            u['nombre'] or '—', u['email'], u['telefono'] or '', u['ciudad'] or '',
            u['provincia'] or '', u['pais'] or '', u['n_presupuestos'], u['n_borradores'],
            u['n_costo_m2'], estado, _segmento(u), (u['created_at'] or '')[:10],
            u['subscription_expires'] or '∞',
        ]
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)

    widths = [18, 30, 18, 20, 20, 8, 8, 8, 9, 18, 32, 12, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def generar_excel_usuarios_a_contactar(usuarios):
    """usuarios: lista de sqlite3.Row con al menos email_verificado,
    n_presupuestos, n_borradores, n_costo_m2, nombre, email, telefono,
    ciudad, provincia, pais, created_at, subscription_expires (ver query en
    routes/admin.py::usuarios_exportar_contactar).

    Devuelve (BytesIO, download_name) listo para send_file.
    """
    segmento_a = [u for u in usuarios if _segmento(u) == SEG_A]
    segmento_b = [u for u in usuarios if _segmento(u) == SEG_B]
    segmento_c = [u for u in usuarios if _segmento(u) == SEG_C]
    segmento_d = [u for u in usuarios if _segmento(u) == SEG_D]

    wb = Workbook()
    ws_todos = wb.active
    ws_todos.title = "Todos los usuarios"
    _escribir_hoja_todos(ws_todos, usuarios)

    ws_a = wb.create_sheet("A - Sin validar email")
    _escribir_hoja_segmento(ws_a, segmento_a, _mensaje_activacion)

    ws_b = wb.create_sheet("B - 1 presup o borrador")
    _escribir_hoja_segmento(ws_b, segmento_b, _mensaje_seguimiento)

    ws_c = wb.create_sheet("C - Validado sin actividad")
    _escribir_hoja_segmento(ws_c, segmento_c, _mensaje_sin_uso)

    ws_d = wb.create_sheet("D - Solo uso Costo-m2")
    _escribir_hoja_segmento(ws_d, segmento_d, _mensaje_solo_costo_m2)

    notas = wb.create_sheet("Leer primero")
    notas_font = Font(name="Arial", size=11)
    titulo_font = Font(name="Arial", size=13, bold=True)
    lineas = [
        ("Exportado automáticamente desde Admin > Usuarios", titulo_font),
        ("", notas_font),
        (f"Generado el {date.today().isoformat()}. Total de usuarios registrados: "
         f"{len(usuarios)}.", notas_font),
        ("", notas_font),
        ("Hoja 'Todos los usuarios': listado completo, con columna 'Segmento' para ver "
         "de un vistazo en qué grupo cae cada uno (ninguno queda afuera).", notas_font),
        ("Hoja 'A - Sin validar email': cuentas con email_verificado=0.", notas_font),
        ("Hoja 'B - 1 presup o borrador': cuentas validadas con exactamente 1 "
         "presupuesto o borrador en total.", notas_font),
        ("Hoja 'C - Validado sin actividad': cuentas validadas que nunca hicieron nada "
         "(0 presupuestos, 0 borradores, 0 consultas de costo/m²).", notas_font),
        ("Hoja 'D - Solo uso Costo/m2': cuentas validadas que nunca presupuestaron pero "
         "sí usaron la calculadora de costo/m² — antes de hoy quedaban afuera de "
         "cualquier segmento.", notas_font),
        ("Los que tienen 2+ presupuestos/borradores no entran en ningún segmento de "
         "retención (ya son usuarios activos) pero figuran en 'Todos los usuarios' "
         "igual, etiquetados como tal.", notas_font),
        ("", notas_font),
        ("Cada fila de A/B/C/D ya trae un mensaje de WhatsApp y de email sugeridos, "
         "personalizados con el nombre — listos para copiar y pegar.", notas_font),
    ]
    for i, (texto, font) in enumerate(lineas, start=1):
        c = notas.cell(row=i, column=1, value=texto)
        c.font = font
    notas.column_dimensions["A"].width = 95

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    download_name = f"PresupuestoPRO_usuarios_a_contactar_{date.today().isoformat()}.xlsx"
    return buf, download_name
