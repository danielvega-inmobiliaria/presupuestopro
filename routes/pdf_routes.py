import json
import re
from urllib.parse import quote
from flask import Blueprint, send_file, g, redirect, url_for, flash, render_template
from utils.auth import login_required
from utils.trial import trial_required
from utils.verificacion import verificacion_required
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
    # Fix 08/08/2026: para que el fallback de materiales de acá abajo también
    # respete el precio de zona (no solo el general), igual que Paso 6/Costo m2.
    user_row = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
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
            p['materiales'] = _calcular_materiales_desde_rubros(p, user=user_row)
        except Exception:
            p['materiales'] = []
    empresa = dict(empresa_row) if empresa_row else {}
    # Fix 03/08/2026 (pedido de Daniel): el presupuesto de ejemplo del tour
    # (routes/presupuesto.py::demo(), marcado con es_demo=1 — ver migración
    # en database.py) usa datos de CLIENTE de ejemplo ("Juan Pérez
    # (ejemplo)"), pero hasta ahora el PDF mostraba el perfil de EMPRESA real
    # del usuario logueado — vacío en una cuenta que todavía no cargó Nombre
    # de empresa, así que el header salía sin logo ni marca. Se reemplaza acá
    # por datos de empresa también de ejemplo, consistente con el resto del
    # presupuesto — "Constructora Ejemplo" da iniciales "CE" en el placeholder
    # de logo (ver utils/pdf_generator.py::iniciales_empresa).
    if p.get('es_demo'):
        empresa = {
            'nombre':   'Constructora Ejemplo',
            'slogan':   'Calidad y confianza en cada obra',
            'contacto': 'Juan Constructor (ejemplo)',
            'telefono': '11-5555-1234',
            'logo_data': '',
            'logo_filename': '',
        }
    return p, empresa

@bp.route('/<int:pid>/propietario-preview')
@login_required
@verificacion_required
@trial_required
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
                           simbolo=p.get('simbolo', '$'),
                           wa_url=wa_url,
                           tiene_tel=bool(tel_digits))


@bp.route('/<int:pid>/constructor-preview')
@login_required
@verificacion_required
@trial_required
def constructor_preview(pid):
    """Fix 02/08/2026 (pedido de Daniel): el PDF Constructor es un binario
    real — en el modal de ver.html (iframe) eso forzaba la descarga en vez
    de mostrarse en mobile, y encima no era "una imagen con todos los datos
    del PDF" como había pedido. Esta vista es el mismo contenido que
    utils/pdf_generator.py::generar_pdf_constructor, en HTML — se puede ver
    completo sin descargar nada, con un botón para bajar el PDF real."""
    p, empresa = cargar_presupuesto(pid, g.user['id'])
    if not p:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(url_for('dashboard.index'))

    pct_gg = p.get('pct_gg', 20)
    pct_imp = p.get('pct_impuestos', 7)
    total_mo = p.get('total_mo', 0)
    total_subc = p.get('total_subcontratos', 0)
    total_ind = p.get('total_indirectos', 0)
    costo_directo = total_mo + p.get('total_materiales', 0)
    if p.get('modo') == 'solo_mo':
        base = total_mo + total_subc + total_ind
    else:
        base = costo_directo + total_subc + total_ind
    beneficio = round(base * pct_gg / 100)
    impuestos = round(base * pct_imp / 100)

    # Fix 03/08/2026 (pedido de Daniel: barra fija con "Enviar por WhatsApp"
    # también en esta vista): a diferencia del PDF Propietario, este es el
    # desglose INTERNO (con el % de Beneficio/Ganancia real) — no debería
    # mandarse por default al teléfono del cliente. Se arma el link de
    # WhatsApp SIN destinatario precargado (wa.me/?text=...), para que quien
    # lo mande elija a mano a quién (él mismo, un socio, etc.), y no repetir
    # el error de mandarle sin querer los márgenes internos al cliente.
    msg = f"Desglose interno (uso del constructor) — Presupuesto N° {p.get('nro','')} — {p.get('cliente_nombre','')}."
    wa_url = f"https://wa.me/?text={quote(msg)}"

    return render_template('presupuesto/pdf_preview_constructor.html',
                           p=p, empresa=empresa,
                           simbolo=p.get('simbolo', '$'),
                           costo_directo=costo_directo,
                           beneficio=beneficio,
                           impuestos=impuestos,
                           wa_url=wa_url)


@bp.route('/<int:pid>/propietario')
@login_required
@verificacion_required
@trial_required
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
@verificacion_required
@trial_required
def constructor(pid):
    p, empresa = cargar_presupuesto(pid, g.user['id'])
    if not p:
        flash('Presupuesto no encontrado.', 'error')
        return redirect(url_for('dashboard.index'))
    buf = generar_pdf_constructor(p, empresa)
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f"Presupuesto_{p['nro']}_Constructor.pdf")
