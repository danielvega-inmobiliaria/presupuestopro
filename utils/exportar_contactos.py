"""
Exportar usuarios a contactar (retención) — agregado 15/07/2026, pedido de
Daniel.

Antes esto se armaba a mano: entrar a Admin > Usuarios, sacar capturas de
pantalla de la tabla y transcribir fila por fila a un Excel (lento y con
riesgo de error, sobre todo en teléfonos y contadores de Presup./Borr. que
se leían muy chicos en la captura). Ahora se arma directo desde la base, en
un click, con la MISMA lógica que ya usa la tabla de Admin > Usuarios:

  Segmento A — "Sin validar (email)": u.email_verificado = 0.
  (Se usa email_verificado y no el badge visual de la tabla porque el badge
  no se muestra cuando u.metodo_verificacion está vacío — cuentas viejas
  "grandfatheradas", ver utils/verificacion.py::get_verificacion_status.
  email_verificado sigue siendo la señal real de si activó la cuenta por
  mail o no, esté vacío el método o no.)

  Segmento B — activó la cuenta pero hizo exactamente 1 presupuesto o
  borrador en total y no volvió: (n_presupuestos + n_borradores) == 1 y
  email_verificado = 1. Se excluyen los del Segmento A para no duplicar
  (si no validó el mail, el mensaje prioritario es el de activación).

  Usuarios con 0 actividad total o 2+ presupuestos/borradores no entran en
  ninguno de los dos segmentos (no fueron pedidos explícitamente).
"""
from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

APP_URL = 'https://web-production-0c9c1.up.railway.app/login'

HEADERS = ["Nombre", "Email", "Teléfono", "Ciudad", "Provincia", "País",
           "Presup.", "Borr.", "Creado", "Vence", "Mensaje WhatsApp sugerido",
           "Mensaje email sugerido"]

HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
HEADER_FILL = PatternFill("solid", fgColor="1F2937")
BODY_FONT = Font(name="Arial", size=10)
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _mensaje_activacion(nombre):
    nombre = nombre or ''
    wa = (f"Hola {nombre}! Somos de PresupuestoPRO. Vimos que te registraste pero "
          f"todavía no activaste tu cuenta por mail. Si te trabó algo del proceso "
          f"contanos, te ayudamos. Y si preferís, te reenviamos el mail de "
          f"activación. Ingresá en: {APP_URL}")
    email = (f"Hola {nombre}, notamos que todavía no confirmaste tu cuenta en "
             f"PresupuestoPRO. Es un paso rápido y te deja usar la app sin "
             f"restricciones. Si tuviste alguna dificultad para activarla, "
             f"respondé este mail y te ayudamos.")
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
             f"próximo presupuesto.")
    return wa, email


def _escribir_hoja(ws, usuarios, mensaje_fn):
    for c, h in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER

    for r, u in enumerate(usuarios, start=2):
        wa_msg, email_msg = mensaje_fn(u['nombre'])
        row = [
            u['nombre'] or '—',
            u['email'],
            u['telefono'] or '',
            u['ciudad'] or '',
            u['provincia'] or '',
            u['pais'] or '',
            u['n_presupuestos'],
            u['n_borradores'],
            (u['created_at'] or '')[:10],
            u['subscription_expires'] or '∞',
            wa_msg,
            email_msg,
        ]
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)

    widths = [18, 30, 18, 20, 20, 8, 8, 8, 12, 12, 55, 55]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def generar_excel_usuarios_a_contactar(usuarios):
    """usuarios: lista de sqlite3.Row con al menos email_verificado,
    n_presupuestos, n_borradores, nombre, email, telefono, ciudad,
    provincia, pais, created_at, subscription_expires (ver query en
    routes/admin.py::usuarios_exportar_contactar).

    Devuelve (BytesIO, download_name) listo para send_file.
    """
    segmento_a = [u for u in usuarios if not u['email_verificado']]
    segmento_b = [u for u in usuarios
                  if u['email_verificado']
                  and (u['n_presupuestos'] + u['n_borradores']) == 1]

    wb = Workbook()
    ws_a = wb.active
    ws_a.title = "A - Sin validar email"
    _escribir_hoja(ws_a, segmento_a, _mensaje_activacion)

    ws_b = wb.create_sheet("B - 1 presup o borrador")
    _escribir_hoja(ws_b, segmento_b, _mensaje_seguimiento)

    notas = wb.create_sheet("Leer primero")
    notas_font = Font(name="Arial", size=11)
    titulo_font = Font(name="Arial", size=13, bold=True)
    lineas = [
        ("Exportado automáticamente desde Admin > Usuarios", titulo_font),
        ("", notas_font),
        (f"Generado el {date.today().isoformat()}.", notas_font),
        ("", notas_font),
        ("Hoja 'A - Sin validar email': cuentas con email_verificado=0. Son las que "
         "no completaron la activación por mail.", notas_font),
        ("Hoja 'B - 1 presup o borrador': cuentas activadas con exactamente 1 "
         "presupuesto o borrador en total (sin actividad después). Se excluyen las "
         "de la hoja A para no duplicar mensajes.", notas_font),
        ("", notas_font),
        ("Cada fila ya trae un mensaje de WhatsApp y de email sugeridos, personalizados "
         "con el nombre — listos para copiar y pegar.", notas_font),
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
