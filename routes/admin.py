import json
import os
import urllib.request
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, render_template_string, request, redirect, url_for, flash, g, send_file
from werkzeug.security import generate_password_hash
from utils.auth import admin_required
from utils.calculations import PAISES
from utils.normalizacion import PROVINCIAS_AR, telefono_normalizado
from utils.exportar_contactos import (
    generar_excel_usuarios_a_contactar, _segmento, SEG_A, SEG_B, SEG_C, SEG_D,
    _mensaje_activacion, _mensaje_seguimiento, _mensaje_sin_uso, _mensaje_solo_costo_m2,
    _mensaje_prueba_por_vencer, _mensaje_suscripcion_vencida,
)
from database import get_db, recalcular_precio_mo_ars

# Admin > Seguimiento (20/07/2026): nombres de plantilla EXACTOS que hay que
# dar de alta en Meta Business Manager para que esto funcione — ver
# conversación del proyecto para el texto completo de cada una.
TEMPLATES_WHATSAPP = {
    'A': 'retencion_activar_cuenta',
    'B': 'retencion_primer_presupuesto',
    'C': 'retencion_sin_uso',
    'D': 'retencion_solo_costo_m2',
    'trial': 'retencion_prueba_por_vencer',
    'vencido': 'retencion_suscripcion_vencida',
}

MENSAJES_EMAIL = {
    'A': _mensaje_activacion,
    'B': _mensaje_seguimiento,
    'C': _mensaje_sin_uso,
    'D': _mensaje_solo_costo_m2,
    'trial': _mensaje_prueba_por_vencer,
    'vencido': _mensaje_suscripcion_vencida,
}

TIPO_LABEL = {
    'A': 'Activar cuenta',
    'B': '1 presup./borrador',
    'C': 'Sin actividad',
    'D': 'Solo Costo/m²',
    'trial': 'Prueba por vencer',
    'vencido': 'Suscripción vencida',
}

SEG_A_CODE = {SEG_A: 'A', SEG_B: 'B', SEG_C: 'C', SEG_D: 'D'}


def _tipos_aplicables(fila):
    """Devuelve la lista de tipos de mensaje que aplican a esta fila (0, 1 o
    2: el segmento de uso A/B/C/D es mutuamente excluyente, pero los
    triggers de ciclo de vida -- prueba por vencer / suscripción vencida --
    son independientes y pueden sumarse al mismo usuario)."""
    tipos = []
    code = SEG_A_CODE.get(fila['segmento'])
    if code:
        tipos.append(code)
    if fila.get('trial_por_vencer'):
        tipos.append('trial')
    if fila.get('suscripcion_vencida'):
        tipos.append('vencido')
    return tipos

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@admin_required
def dashboard():
    db = get_db()
    stats = {
        'total_users':   db.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=0").fetchone()['c'],
        'activos':       db.execute("SELECT COUNT(*) as c FROM users WHERE active=1 AND is_admin=0").fetchone()['c'],
        'vencidos':      db.execute("SELECT COUNT(*) as c FROM users WHERE subscription_expires < date('now') AND is_admin=0").fetchone()['c'],
        'presupuestos':  db.execute("SELECT COUNT(*) as c FROM presupuestos").fetchone()['c'],
        'mensajes_nuevos': db.execute("SELECT COUNT(*) as c FROM contactos WHERE leido=0").fetchone()['c'],
        'sugerencias_nuevas': db.execute("SELECT COUNT(*) as c FROM sugerencias WHERE leido=0").fetchone()['c'],
        # Fix 08/07/2026: badge de inscriptos nuevos — el botón "Inscriptos"
        # ya existía en el dashboard pero sin ningún contador, así que un
        # inscripto nuevo (ej. Ricardo Jordan) pasaba desapercibido salvo que
        # Daniel entrara a revisar la lista sin motivo aparente.
        'leads_nuevos': db.execute("SELECT COUNT(*) as c FROM leads WHERE estado='nuevo'").fetchone()['c'],
        # Fix 20/07/2026, pedido de Daniel: badge de consultas de WhatsApp sin
        # responder (el bot no supo contestar y quedaron para revisión manual
        # -- ver admin.whatsapp_inbox).
        'whatsapp_pendientes': db.execute(
            "SELECT COUNT(*) as c FROM whatsapp_consultas_sin_responder WHERE respondida=0"
        ).fetchone()['c'],
    }
    # Fix 20/07/2026, pedido de Daniel: badge de usuarios con algo pendiente
    # en Admin > Seguimiento (segmento A/B/C/D, prueba por vencer o
    # suscripción vencida). Se calcula en Python (no en SQL) porque el
    # segmento sale de utils.exportar_contactos._segmento — misma lógica
    # que usa esa pantalla, sin duplicar la regla acá.
    stats['seguimiento_pendientes'] = len([f for f in _usuarios_seguimiento() if f['tipos']])
    proximos = db.execute(
        "SELECT * FROM users WHERE subscription_expires >= date('now') AND is_admin=0 ORDER BY subscription_expires LIMIT 5"
    ).fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats, proximos=proximos, user=g.user)

# USUARIOS
@bp.route('/usuarios')
@admin_required
def usuarios():
    """Fix 05/07/2026: agregado conteo de presupuestos completos/borradores y
    consultas de Costo/m2 por usuario, + filtros por localidad/provincia/pais
    (pedido de Daniel para tener a mano el uso real de cada usuario)."""
    f_ciudad    = (request.args.get('f_ciudad') or '').strip()
    f_provincia = (request.args.get('f_provincia') or '').strip()
    f_pais      = (request.args.get('f_pais') or '').strip()

    where = ["is_admin=0"]
    params = []
    if f_ciudad:
        where.append("ciudad LIKE ?")
        params.append(f"%{f_ciudad}%")
    if f_provincia:
        # Fix 10/07/2026: provincia ya es lista cerrada (select) — match exacto,
        # no LIKE. Con LIKE, "Buenos Aires" también traía a los de "Ciudad
        # Autónoma de Buenos Aires" por ser substring.
        where.append("provincia = ?")
        params.append(f_provincia)
    if f_pais:
        where.append("pais = ?")
        params.append(f_pais)

    db = get_db()
    users = db.execute(
        f"""SELECT u.*,
                   (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='completo') AS n_presupuestos,
                   (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='borrador')  AS n_borradores,
                   (SELECT COUNT(*) FROM costo_m2_consultas c WHERE c.user_id=u.id)                    AS n_costo_m2
            FROM users u
            WHERE {' AND '.join(where)}
            ORDER BY u.created_at DESC""",
        params
    ).fetchall()

    # Fix 10/07/2026 (cont. 8, pedido de Daniel): el badge "Usuarios" del
    # encabezado tiene que marcar SIEMPRE el total de la base (sin filtrar),
    # no la cantidad de filas que quedaron después de aplicar los filtros
    # (eso ya lo muestra `users|length` en la tabla misma).
    total_usuarios = db.execute("SELECT COUNT(*) as c FROM users WHERE is_admin=0").fetchone()['c']

    # Fix 10/07/2026 (2da vuelta, pedido de Daniel): en vez de un cartel de
    # "también en" aparte, mostrar la cantidad de cada nivel (ciudad,
    # provincia, país) pegada al lado de su propio label. Cuando un nivel no
    # está elegido explícitamente, se infiere del nivel más específico que sí
    # esté activo (ciudad -> su provincia; provincia -> su país), tomando la
    # provincia/país más frecuente entre los usuarios que matchean, por si
    # hay datos mezclados. Si no hay nada de qué inferir, ese contador queda
    # en None y el template no muestra badge.
    contadores = {'ciudad': None, 'provincia': None, 'pais': None}

    def _mas_frecuente(campo, where_extra, params_extra):
        filas = db.execute(
            f"SELECT {campo} as v, COUNT(*) as c FROM users WHERE is_admin=0 AND {where_extra} AND {campo} != '' "
            f"GROUP BY {campo} ORDER BY c DESC LIMIT 1",
            params_extra
        ).fetchone()
        return filas['v'] if filas else None

    if f_ciudad:
        contadores['ciudad'] = db.execute(
            "SELECT COUNT(*) as c FROM users WHERE is_admin=0 AND ciudad LIKE ?", (f"%{f_ciudad}%",)
        ).fetchone()['c']

    provincia_efectiva = f_provincia or (
        _mas_frecuente('provincia', "ciudad LIKE ?", (f"%{f_ciudad}%",)) if f_ciudad else None
    )
    if provincia_efectiva:
        contadores['provincia'] = {
            'nombre': provincia_efectiva,
            'cantidad': db.execute(
                "SELECT COUNT(*) as c FROM users WHERE is_admin=0 AND provincia=?", (provincia_efectiva,)
            ).fetchone()['c'],
        }

    pais_efectivo = f_pais or (
        _mas_frecuente('pais', "provincia=?", (provincia_efectiva,)) if provincia_efectiva else
        (_mas_frecuente('pais', "ciudad LIKE ?", (f"%{f_ciudad}%",)) if f_ciudad else None)
    )
    if pais_efectivo:
        contadores['pais'] = {
            'nombre': PAISES.get(pais_efectivo, {}).get('nombre', pais_efectivo),
            'cantidad': db.execute(
                "SELECT COUNT(*) as c FROM users WHERE is_admin=0 AND pais=?", (pais_efectivo,)
            ).fetchone()['c'],
        }

    # Fix 10/07/2026: antes esto era un DISTINCT de lo cargado en users.provincia
    # (texto libre, con duplicados). Provincia ahora es lista cerrada — se
    # usa PROVINCIAS_AR para que el filtro sea un <select> real, igual que País.
    # Localidad sigue siendo abierta, pero ahora hay tabla `localidades`
    # autoalimentada (fix de hoy) para ofrecer autocompletado real, no el
    # autocompletado del navegador que Daniel vio antes.
    # Fix 12/07/2026: antes ordenaba por uso (veces_usada DESC) -> las
    # sugerencias del filtro de Localidad aparecían desordenadas. Pedido de
    # Daniel: alfabético, para elegir más fácil desde el celular.
    localidades_lista = [r['nombre_display'] for r in db.execute(
        "SELECT nombre_display FROM localidades WHERE merged_en='' ORDER BY nombre_display COLLATE NOCASE ASC"
    ).fetchall()]
    db.close()

    return render_template('admin/usuarios.html', users=users, user=g.user,
                            provincias=PROVINCIAS_AR, localidades_lista=localidades_lista, paises=PAISES,
                            f_ciudad=f_ciudad, f_provincia=f_provincia, f_pais=f_pais,
                            contadores=contadores, total_usuarios=total_usuarios)


@bp.route('/usuarios/exportar-contactar')
@admin_required
def usuarios_exportar_contactar():
    """Pedido de Daniel 15/07/2026: antes esta lista se armaba a mano
    (capturas de pantalla de esta misma tabla + transcripción manual a un
    Excel — lento y con riesgo de error en teléfonos/contadores). Este botón
    arma el mismo Excel en un click, leyendo directo de la base. Ver
    utils/exportar_contactos.py para la lógica de segmentación exacta
    (incluye Segmento C — validado sin ninguna actividad — agregado el mismo
    día a pedido de Daniel, por eso también se trae n_costo_m2 acá)."""
    db = get_db()
    usuarios = db.execute(
        """SELECT u.*,
                  (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='completo') AS n_presupuestos,
                  (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='borrador')  AS n_borradores,
                  (SELECT COUNT(*) FROM costo_m2_consultas c WHERE c.user_id=u.id)                    AS n_costo_m2
           FROM users u
           WHERE u.is_admin=0
           ORDER BY u.created_at DESC"""
    ).fetchall()
    db.close()

    buf, download_name = generar_excel_usuarios_a_contactar(usuarios)
    return send_file(buf,
                      mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                      as_attachment=True, download_name=download_name)


def _usuarios_seguimiento():
    """Arma la lista de usuarios con su segmento de uso (A/B/C/D, misma
    lógica que el Excel de utils/exportar_contactos.py) + los dos triggers
    de ciclo de vida que pidió Daniel 20/07/2026: prueba gratis por vencer
    (usa el mismo criterio que utils/trial.py, calculado acá para no abrir
    una conexión a DB por usuario) y suscripción vencida (mismo criterio que
    el contador 'vencidos' del dashboard). Devuelve la lista ya con
    'segmento', 'trial_por_vencer', 'dias_restantes', 'presup_restantes',
    'suscripcion_vencida', 'ultimo_contacto' y 'ultimo_resultado' agregados
    a cada fila. 'ultimo_resultado' (21/07/2026, pedido de Daniel) es para
    poder mostrar si el último envío salió bien o mal directo en la lista,
    sin depender de que el flash message se vea (ver nota en seguimiento())."""
    db = get_db()
    usuarios = db.execute(
        """SELECT u.*,
                  (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='completo') AS n_presupuestos,
                  (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='borrador')  AS n_borradores,
                  (SELECT COUNT(*) FROM costo_m2_consultas c WHERE c.user_id=u.id)                    AS n_costo_m2,
                  (SELECT MAX(created_at) FROM retencion_contactos rc WHERE rc.user_id=u.id)          AS ultimo_contacto,
                  (SELECT resultado FROM retencion_contactos rc WHERE rc.user_id=u.id
                     ORDER BY rc.created_at DESC LIMIT 1)                                              AS ultimo_resultado
           FROM users u
           WHERE u.is_admin=0
           ORDER BY u.created_at DESC"""
    ).fetchall()
    db.close()

    hoy_str = date.today().isoformat()
    ahora = datetime.utcnow()
    filas = []
    for u in usuarios:
        fila = dict(u)
        fila['segmento'] = _segmento(u)

        trial_por_vencer = False
        dias_restantes = presup_restantes = None
        if u['es_trial']:
            try:
                creado = datetime.fromisoformat((u['created_at'] or '').replace(' ', 'T'))
                dias_pasados = (ahora - creado).days
            except (ValueError, TypeError):
                dias_pasados = 0
            dias_restantes = max(0, 14 - dias_pasados)
            presup_restantes = max(0, 3 - u['n_presupuestos'])
            vencido_trial = u['n_presupuestos'] >= 3 or dias_pasados >= 14
            trial_por_vencer = (not vencido_trial) and (dias_restantes <= 3 or presup_restantes <= 1)
        fila['trial_por_vencer'] = trial_por_vencer
        fila['dias_restantes'] = dias_restantes
        fila['presup_restantes'] = presup_restantes

        fila['suscripcion_vencida'] = bool(u['subscription_expires']) and u['subscription_expires'] < hoy_str

        fila['tipos'] = _tipos_aplicables(fila)
        filas.append(fila)
    return filas


_FLASH_BLOCK = """
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
  <div class="mb-3">
    {% for category, msg in messages %}
    <div class="alert alert-{{ 'danger' if category=='error' else category }} py-2 mb-1">{{ msg }}</div>
    {% endfor %}
  </div>
  {% endif %}
{% endwith %}
"""


@bp.route('/seguimiento')
@admin_required
def seguimiento():
    """Pedido de Daniel 20/07/2026: en vez de bajar la planilla, poder ver a
    todos los usuarios con su segmento y mandarles el WhatsApp (plantilla
    aprobada por Meta) o el email ya redactado, directo desde acá. Por
    default solo muestra a quien tiene algo para hacer (algún tipo en
    'tipos'); ?todos=1 muestra la lista completa igual que Admin > Usuarios.

    Fix 21/07/2026 (pedido de Daniel): esta vista antes NO mostraba el
    resultado de un envío -- flash() no se ve en nada si el template no lo
    imprime, y esta pantalla al ser render_template_string standalone (no
    extiende base.html) no traía ese bloque. Se agregó _FLASH_BLOCK acá y en
    whatsapp_inbox por el mismo motivo. También se agregó Creado/Vence por
    fila, y un link "Ver" a admin.seguimiento_detalle para poder repasar
    toda la actividad del usuario y editar el mensaje antes de mandarlo."""
    mostrar_todos = request.args.get('todos') == '1'
    filas = _usuarios_seguimiento()
    if not mostrar_todos:
        filas = [f for f in filas if f['tipos']]

    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Seguimiento - Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
<style>
  .badge-seg { font-size: .72rem; }
</style>
</head><body class="bg-light">
<div class="container-fluid py-4" style="max-width:1100px">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <div>
      <a href="/admin/" class="btn btn-outline-secondary btn-sm mb-2">Volver</a>
      <h4 class="fw-bold mb-0">Seguimiento de usuarios</h4>
    </div>
    <a href="{{ url_for('admin.seguimiento', todos=0 if mostrar_todos else 1) }}" class="btn btn-outline-primary btn-sm">
      {% if mostrar_todos %}Ver solo accionables{% else %}Ver todos los usuarios{% endif %}
    </a>
  </div>
  """ + _FLASH_BLOCK + """
  <div class="alert alert-warning small">
    <i class="bi bi-exclamation-triangle"></i> El botón de WhatsApp solo funciona una vez que la
    plantilla correspondiente esté <strong>aprobada en Meta Business Manager</strong> con el nombre
    exacto. Hasta entonces va a devolver error acá arriba (ahora sí se ve el error). Mientras tanto
    usá el email, o entrá a "Ver" para mandar el WhatsApp a mano con el texto ya cargado.
  </div>
  <p class="text-muted small">{{ filas|length }} usuario{{ 's' if filas|length != 1 else '' }}
    {% if not mostrar_todos %}con algo para hacer{% endif %}</p>

  {% for f in filas %}
  <div class="card mb-2 shadow-sm">
    <div class="card-body py-2">
      <div class="row align-items-center g-2">
        <div class="col-md-3">
          <div class="fw-semibold">{{ f.nombre or '—' }}</div>
          <div class="small text-muted">{{ f.email }}</div>
          {% if f.telefono %}<div class="small text-success"><i class="bi bi-whatsapp"></i> {{ f.telefono }}</div>{% endif %}
          <div class="small text-muted">Registrado: {{ (f.created_at or '')[:10] }} · Vence: {{ f.subscription_expires or '∞' }}</div>
        </div>
        <div class="col-md-3">
          <span class="badge bg-secondary badge-seg">{{ f.segmento }}</span>
          {% if f.trial_por_vencer %}
          <span class="badge bg-warning text-dark badge-seg">Prueba: {{ f.dias_restantes }}d / {{ f.presup_restantes }} presup. restantes</span>
          {% endif %}
          {% if f.suscripcion_vencida %}
          <span class="badge bg-danger badge-seg">Suscripción vencida ({{ f.subscription_expires }})</span>
          {% endif %}
        </div>
        <div class="col-md-2 small text-muted">
          {% if f.ultimo_contacto %}
            Último contacto:<br>{{ f.ultimo_contacto[:16] }}
            {% if f.ultimo_resultado == 'ok' %}<span class="badge bg-success">enviado</span>
            {% elif f.ultimo_resultado == 'error' %}<span class="badge bg-danger">error</span>{% endif %}
          {% else %}Sin contactar todavía{% endif %}
        </div>
        <div class="col-md-3">
          {% for tipo in f.tipos %}
          <div class="d-flex gap-1 mb-1 align-items-center">
            <span class="small text-muted" style="min-width:110px">{{ tipo_label[tipo] }}:</span>
            <form method="POST" action="{{ url_for('admin.seguimiento_whatsapp', uid=f.id) }}">
              <input type="hidden" name="tipo" value="{{ tipo }}">
              <button type="submit" class="btn btn-sm btn-success" {{ 'disabled title=Sin teléfono' if not f.telefono }}>
                <i class="bi bi-whatsapp"></i>
              </button>
            </form>
            <form method="POST" action="{{ url_for('admin.seguimiento_email', uid=f.id) }}">
              <input type="hidden" name="tipo" value="{{ tipo }}">
              <button type="submit" class="btn btn-sm btn-outline-primary">
                <i class="bi bi-envelope"></i>
              </button>
            </form>
          </div>
          {% endfor %}
        </div>
        <div class="col-md-1 text-end">
          <a href="{{ url_for('admin.seguimiento_detalle', uid=f.id) }}" class="btn btn-sm btn-outline-secondary">Ver</a>
        </div>
      </div>
    </div>
  </div>
  {% else %}
  <p class="text-muted text-center py-4">No hay usuarios {{ 'registrados' if mostrar_todos else 'con algo pendiente para hacer' }}.</p>
  {% endfor %}
</div></body></html>
""", filas=filas, mostrar_todos=mostrar_todos, tipo_label=TIPO_LABEL, user=g.user)


@bp.route('/seguimiento/<int:uid>')
@admin_required
def seguimiento_detalle(uid):
    """Agregado 21/07/2026, pedido de Daniel: poder ver toda la actividad de
    un usuario (perfil, presupuestos/borradores/costo_m2, historial de
    contactos previos) y el texto sugerido de cada mensaje EN UN TEXTAREA
    EDITABLE antes de mandarlo -- para agregar algo puntual o corregir, en
    vez de que se mande el texto fijo de una. El email manda lo que quede
    escrito en el textarea al momento de tocar "Enviar" (ver
    seguimiento_email). El WhatsApp por plantilla NO puede llevar texto
    editado -- Meta solo permite rellenar las variables ({{1}}=nombre) de
    una plantilla ya aprobada, no cambiar el cuerpo -- así que para el
    textarea de WhatsApp se ofrece en cambio "Abrir en WhatsApp (manual)":
    abre wa.me con el texto editado, listo para que Daniel lo mande él
    mismo desde su teléfono, sin depender de que la plantilla esté
    aprobada. Esa opción funciona HOY."""
    db = get_db()
    u = db.execute(
        """SELECT u.*,
                  (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='completo') AS n_presupuestos,
                  (SELECT COUNT(*) FROM presupuestos p WHERE p.user_id=u.id AND p.status='borrador')  AS n_borradores,
                  (SELECT COUNT(*) FROM costo_m2_consultas c WHERE c.user_id=u.id)                    AS n_costo_m2
           FROM users u WHERE u.id=?""",
        (uid,)
    ).fetchone()
    if not u:
        db.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('admin.seguimiento'))

    historial = db.execute(
        "SELECT * FROM retencion_contactos WHERE user_id=? ORDER BY created_at DESC", (uid,)
    ).fetchall()
    db.close()

    fila = dict(u)
    fila['segmento'] = _segmento(u)
    hoy_str = date.today().isoformat()
    ahora = datetime.utcnow()
    trial_por_vencer = False
    dias_restantes = presup_restantes = None
    if u['es_trial']:
        try:
            creado = datetime.fromisoformat((u['created_at'] or '').replace(' ', 'T'))
            dias_pasados = (ahora - creado).days
        except (ValueError, TypeError):
            dias_pasados = 0
        dias_restantes = max(0, 14 - dias_pasados)
        presup_restantes = max(0, 3 - u['n_presupuestos'])
        vencido_trial = u['n_presupuestos'] >= 3 or dias_pasados >= 14
        trial_por_vencer = (not vencido_trial) and (dias_restantes <= 3 or presup_restantes <= 1)
    fila['trial_por_vencer'] = trial_por_vencer
    fila['dias_restantes'] = dias_restantes
    fila['presup_restantes'] = presup_restantes
    fila['suscripcion_vencida'] = bool(u['subscription_expires']) and u['subscription_expires'] < hoy_str
    tipos = _tipos_aplicables(fila)

    mensajes = {}
    for tipo in tipos:
        wa_msg, email_msg = MENSAJES_EMAIL[tipo](u['nombre'])
        mensajes[tipo] = {'wa': wa_msg, 'email': email_msg}

    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ f.nombre or f.email }} - Seguimiento</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
</head><body class="bg-light">
<div class="container py-4" style="max-width:760px">
  <a href="{{ url_for('admin.seguimiento', todos=1) }}" class="btn btn-outline-secondary btn-sm mb-3">Volver a Seguimiento</a>
  """ + _FLASH_BLOCK + """
  <div class="card mb-3">
    <div class="card-body">
      <h5 class="fw-bold mb-1">{{ f.nombre or '—' }}</h5>
      <div class="text-muted">{{ f.email }}</div>
      {% if f.telefono %}<div class="text-success"><i class="bi bi-whatsapp"></i> {{ f.telefono }}</div>{% endif %}
      <div class="small text-muted mt-1">
        {{ f.ciudad or '' }}{% if f.ciudad and f.provincia %}, {% endif %}{{ f.provincia or '' }}
      </div>
      <hr>
      <div class="row small">
        <div class="col-4"><strong>Registrado:</strong><br>{{ (f.created_at or '')[:10] }}</div>
        <div class="col-4"><strong>Vence:</strong><br>{{ f.subscription_expires or '∞' }}</div>
        <div class="col-4"><strong>Segmento:</strong><br><span class="badge bg-secondary">{{ f.segmento }}</span></div>
      </div>
      <div class="row small mt-2">
        <div class="col-4"><strong>Presupuestos:</strong> {{ f.n_presupuestos }}</div>
        <div class="col-4"><strong>Borradores:</strong> {{ f.n_borradores }}</div>
        <div class="col-4"><strong>Costo/m² usados:</strong> {{ f.n_costo_m2 }}</div>
      </div>
      {% if f.trial_por_vencer %}
      <div class="alert alert-warning small mt-2 mb-0">Prueba gratis por vencer: {{ f.dias_restantes }} días
        o {{ f.presup_restantes }} presupuesto(s) restantes.</div>
      {% endif %}
      {% if f.suscripcion_vencida %}
      <div class="alert alert-danger small mt-2 mb-0">Suscripción vencida el {{ f.subscription_expires }}.</div>
      {% endif %}
    </div>
  </div>

  {% if not tipos %}
  <p class="text-muted">Este usuario no tiene ningún mensaje de retención sugerido en este momento
    (ya es un usuario activo, o no encaja en ningún segmento).</p>
  {% endif %}

  {% for tipo in tipos %}
  <div class="card mb-3">
    <div class="card-header fw-bold">{{ tipo_label[tipo] }}</div>
    <div class="card-body">
      <form method="POST" action="{{ url_for('admin.seguimiento_email', uid=f.id) }}" class="mb-3">
        <input type="hidden" name="tipo" value="{{ tipo }}">
        <label class="form-label small text-muted">Mensaje por email (editable):</label>
        <textarea name="mensaje" class="form-control mb-2" rows="4">{{ mensajes[tipo].email }}</textarea>
        <button type="submit" class="btn btn-sm btn-primary"><i class="bi bi-envelope"></i> Enviar email</button>
      </form>
      <div>
        <label class="form-label small text-muted">Mensaje por WhatsApp:</label>
        <textarea id="wa-{{ tipo }}" class="form-control mb-2" rows="3">{{ mensajes[tipo].wa }}</textarea>
        <button type="button" class="btn btn-sm btn-success"
                onclick="abrirWhatsapp('{{ f.telefono|e }}', document.getElementById('wa-{{ tipo }}').value)"
                {{ 'disabled title=Sin teléfono' if not f.telefono }}>
          <i class="bi bi-whatsapp"></i> Abrir en WhatsApp (manual, funciona ya)
        </button>
        <form method="POST" action="{{ url_for('admin.seguimiento_whatsapp', uid=f.id) }}" class="d-inline">
          <input type="hidden" name="tipo" value="{{ tipo }}">
          <button type="submit" class="btn btn-sm btn-outline-success" {{ 'disabled title=Sin teléfono' if not f.telefono }}>
            Enviar por plantilla API (necesita aprobación de Meta)
          </button>
        </form>
      </div>
    </div>
  </div>
  {% endfor %}

  <div class="card">
    <div class="card-header fw-bold">Historial de contactos</div>
    <ul class="list-group list-group-flush">
      {% for h in historial %}
      <li class="list-group-item small">
        <strong>{{ h.created_at[:16] }}</strong> — {{ h.canal }} ({{ tipo_label.get(h.segmento, h.segmento) }})
        <span class="badge {{ 'bg-success' if h.resultado == 'ok' else 'bg-danger' }}">{{ h.resultado }}</span>
        <div class="text-muted">{{ h.mensaje }}</div>
      </li>
      {% else %}
      <li class="list-group-item text-muted small">Sin contactos registrados todavía.</li>
      {% endfor %}
    </ul>
  </div>
</div>
<script>
function abrirWhatsapp(tel, mensaje) {
  let num = (tel || '').replace(/[^0-9+]/g, '');
  if (!num.startsWith('+') && !num.startsWith('54')) num = '549' + num;
  else if (num.startsWith('54') && !num.startsWith('549')) num = '549' + num.slice(2);
  num = num.replace(/^\\+/, '');
  window.open('https://wa.me/' + num + '?text=' + encodeURIComponent(mensaje), '_blank');
}
</script>
</body></html>
""", f=fila, tipos=tipos, mensajes=mensajes, tipo_label=TIPO_LABEL, historial=historial, user=g.user)


@bp.route('/seguimiento/<int:uid>/whatsapp', methods=['POST'])
@admin_required
def seguimiento_whatsapp(uid):
    tipo = request.form.get('tipo', '')
    plantilla = TEMPLATES_WHATSAPP.get(tipo)
    volver = request.form.get('volver') or url_for('admin.seguimiento')
    if not plantilla:
        flash('Tipo de mensaje no reconocido.', 'error')
        return redirect(volver)

    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(volver)
    if not u['telefono']:
        db.close()
        flash(f'{u["email"]} no tiene teléfono cargado.', 'error')
        return redirect(volver)

    from routes.whatsapp_bot import enviar_plantilla_whatsapp
    ok, detalle = enviar_plantilla_whatsapp(u['telefono'], plantilla, parametros={'nombre': u['nombre'] or ''})
    # Fix 21/07/2026: antes solo se guardaba 'ok'/'error' sin el motivo real
    # de Meta, y el flash mostraba un mensaje genérico adivinando la causa.
    # Ahora el detalle real (código + mensaje de la Graph API) queda en el
    # campo 'mensaje' del historial (visible en Seguimiento > Ver) y en el
    # flash de esta pantalla — 'resultado' se deja intacto ('ok'/'error')
    # porque los badges de la lista comparan ese valor exacto.
    mensaje_guardado = plantilla if ok else f"{plantilla} — ERROR: {detalle}"
    db.execute(
        "INSERT INTO retencion_contactos (user_id, canal, segmento, mensaje, resultado) VALUES (?,?,?,?,?)",
        (uid, 'whatsapp', tipo, mensaje_guardado, 'ok' if ok else 'error')
    )
    db.commit()
    db.close()
    if ok:
        flash(f'WhatsApp ({plantilla}) enviado a {u["nombre"] or u["email"]}.', 'success')
    else:
        flash(f'No se pudo enviar "{plantilla}": {detalle}. Mientras tanto usá "Abrir en WhatsApp '
              f'(manual)" desde el detalle del usuario.', 'error')
    return redirect(request.referrer or url_for('admin.seguimiento'))


@bp.route('/seguimiento/<int:uid>/email', methods=['POST'])
@admin_required
def seguimiento_email(uid):
    """Fix 21/07/2026, pedido de Daniel: antes esto SIEMPRE regeneraba el
    texto fijo de la plantilla interna, ignorando cualquier edición. Ahora,
    si el form manda 'mensaje' (viene del textarea editable de
    seguimiento_detalle), se usa ESE texto tal cual; si no viene (por
    ejemplo el botón rápido de la lista, que no tiene textarea), se genera
    el texto por default como antes."""
    tipo = request.form.get('tipo', '')
    generador = MENSAJES_EMAIL.get(tipo)
    if not generador:
        flash('Tipo de mensaje no reconocido.', 'error')
        return redirect(request.referrer or url_for('admin.seguimiento'))

    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(request.referrer or url_for('admin.seguimiento'))

    mensaje_editado = (request.form.get('mensaje') or '').strip()
    if mensaje_editado:
        cuerpo_email = mensaje_editado
    else:
        _, cuerpo_email = generador(u['nombre'])

    ok = False
    api_key = os.environ.get('RESEND_API_KEY')
    if api_key:
        try:
            import resend
            resend.api_key = api_key
            resend.Emails.send({
                "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
                "to": [u['email']],
                "subject": "PresupuestoPRO",
                "text": cuerpo_email,
            })
            ok = True
        except Exception as e:
            print(f"[seguimiento_email] error enviando a {u['email']}: {e}")

    db.execute(
        "INSERT INTO retencion_contactos (user_id, canal, segmento, mensaje, resultado) VALUES (?,?,?,?,?)",
        (uid, 'email', tipo, cuerpo_email[:500], 'ok' if ok else 'error')
    )
    db.commit()
    db.close()
    if ok:
        flash(f'Email enviado a {u["email"]}.', 'success')
    else:
        flash('No se pudo enviar el email (revisar RESEND_API_KEY en Railway).', 'error')
    return redirect(request.referrer or url_for('admin.seguimiento'))


@bp.route('/localidades')
@admin_required
def localidades():
    db = get_db()
    filas = db.execute("SELECT * FROM localidades ORDER BY merged_en != '', veces_usada DESC").fetchall()
    # Para poder mostrar "fusionada en: <nombre>" en vez de solo la clave.
    por_clave = {f['clave_normalizada']: f for f in filas}
    db.close()
    return render_template('admin/localidades.html', filas=filas, por_clave=por_clave, user=g.user)


@bp.route('/localidades/<int:lid>/renombrar', methods=['POST'])
@admin_required
def localidad_renombrar(lid):
    nuevo_nombre = (request.form.get('nombre_display') or '').strip()
    if not nuevo_nombre:
        flash('El nombre no puede quedar vacío.', 'error')
        return redirect(url_for('admin.localidades'))
    db = get_db()
    fila = db.execute("SELECT * FROM localidades WHERE id=?", (lid,)).fetchone()
    if not fila:
        db.close()
        flash('No se encontró esa localidad.', 'error')
        return redirect(url_for('admin.localidades'))
    # Los usuarios que ya tenían la grafía vieja se actualizan también, para
    # que no quede desincronizado lo que ve Daniel acá vs. lo que dice cada
    # usuario en Admin > Usuarios.
    db.execute("UPDATE users SET ciudad=? WHERE ciudad=?", (nuevo_nombre, fila['nombre_display']))
    db.execute("UPDATE localidades SET nombre_display=? WHERE id=?", (nuevo_nombre, lid))
    db.commit()
    db.close()
    flash(f'Renombrada a "{nuevo_nombre}".', 'success')
    return redirect(url_for('admin.localidades'))


@bp.route('/localidades/fusionar', methods=['POST'])
@admin_required
def localidad_fusionar():
    """Fusiona `origen_id` hacia `destino_id`: todos los usuarios que tenían
    la grafía de origen pasan a la de destino, y de acá en más cualquiera que
    se registre escribiendo la clave de origen también cae en destino (ver
    routes/landing.py::_guardar_localidad, sigue la cadena `merged_en`)."""
    try:
        origen_id = int(request.form.get('origen_id'))
        destino_id = int(request.form.get('destino_id'))
    except (TypeError, ValueError):
        flash('Elegí las dos localidades a fusionar.', 'error')
        return redirect(url_for('admin.localidades'))
    if origen_id == destino_id:
        flash('Elegí dos localidades distintas.', 'error')
        return redirect(url_for('admin.localidades'))

    db = get_db()
    origen = db.execute("SELECT * FROM localidades WHERE id=?", (origen_id,)).fetchone()
    destino = db.execute("SELECT * FROM localidades WHERE id=?", (destino_id,)).fetchone()
    if not origen or not destino:
        db.close()
        flash('No se encontró alguna de las dos localidades.', 'error')
        return redirect(url_for('admin.localidades'))

    db.execute("UPDATE users SET ciudad=? WHERE ciudad=?", (destino['nombre_display'], origen['nombre_display']))
    db.execute(
        "UPDATE localidades SET merged_en=?, veces_usada=0 WHERE id=?",
        (destino['clave_normalizada'], origen_id)
    )
    db.execute(
        "UPDATE localidades SET veces_usada = veces_usada + ? WHERE id=?",
        (origen['veces_usada'], destino_id)
    )
    db.commit()
    db.close()
    flash(f'"{origen["nombre_display"]}" fusionada en "{destino["nombre_display"]}".', 'success')
    return redirect(url_for('admin.localidades'))

@bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@admin_required
def usuario_nuevo():
    if request.method == 'POST':
        email     = request.form.get('email', '').strip().lower()
        nombre    = request.form.get('nombre', '')
        telefono  = request.form.get('telefono', '').strip()
        ciudad    = request.form.get('ciudad', '').strip()
        provincia = request.form.get('provincia', '').strip()
        password  = request.form.get('password', '')
        pais      = request.form.get('pais', 'AR')
        vence     = request.form.get('subscription_expires', '')
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (email, password_hash, nombre, telefono, ciudad, provincia, pais, active, subscription_expires) VALUES (?,?,?,?,?,?,?,1,?)",
                (email, generate_password_hash(password), nombre, telefono, ciudad, provincia, pais, vence or None)
            )
            db.commit()
            flash(f'Usuario {email} creado.', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        finally:
            db.close()
        return redirect(url_for('admin.usuarios'))
    return render_template('admin/usuario_form.html', u=None, user=g.user,
                           now_date=date.today(), timedelta=timedelta)

@bp.route('/usuarios/<int:uid>/editar', methods=['GET', 'POST'])
@admin_required
def usuario_editar(uid):
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close(); return redirect(url_for('admin.usuarios'))

    if request.method == 'POST':
        nombre    = request.form.get('nombre', '')
        telefono  = request.form.get('telefono', '').strip()
        ciudad    = request.form.get('ciudad', '').strip()
        provincia = request.form.get('provincia', '').strip()
        pais      = request.form.get('pais', 'AR')
        active    = 1 if request.form.get('active') else 0
        vence     = request.form.get('subscription_expires', '')
        new_pw    = request.form.get('password', '').strip()
        if new_pw:
            db.execute(
                "UPDATE users SET nombre=?, telefono=?, ciudad=?, provincia=?, pais=?, active=?, subscription_expires=?, password_hash=? WHERE id=?",
                (nombre, telefono, ciudad, provincia, pais, active, vence or None, generate_password_hash(new_pw), uid)
            )
        else:
            db.execute(
                "UPDATE users SET nombre=?, telefono=?, ciudad=?, provincia=?, pais=?, active=?, subscription_expires=? WHERE id=?",
                (nombre, telefono, ciudad, provincia, pais, active, vence or None, uid)
            )
        if not active:
            db.execute("UPDATE users SET session_token=NULL WHERE id=?", (uid,))
        db.commit()
        flash('Usuario actualizado.', 'success')
        db.close()
        return redirect(url_for('admin.usuarios'))

    db.close()
    return render_template('admin/usuario_form.html', u=u, user=g.user)

@bp.route('/usuarios/<int:uid>/eliminar', methods=['POST'])
@admin_required
def usuario_eliminar(uid):
    """Borra un usuario y todo lo asociado. Agregado 10/07/2026 — pedido de
    Daniel para poder limpiar las cuentas ficticias/de prueba que va cargando
    mientras testea el flujo de validación de cuenta, sin tener que pedirle
    a un dev que lo haga a mano en la base. Irreversible: borra en cascada
    presupuestos, suscripciones, consultas de costo/m2, sugerencias, perfil
    de empresa, tokens de reset de password y códigos de verificación del
    usuario, antes de borrar la fila de users."""
    db = get_db()
    u = db.execute("SELECT email, nombre, is_admin FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('admin.usuarios'))
    if u['is_admin']:
        db.close()
        flash('No se puede eliminar una cuenta de administrador desde acá.', 'error')
        return redirect(url_for('admin.usuarios'))

    for tabla in ('presupuestos', 'suscripciones', 'costo_m2_consultas', 'sugerencias',
                  'empresa_perfil', 'password_reset_tokens', 'verificacion_codigos'):
        db.execute(f"DELETE FROM {tabla} WHERE user_id=?", (uid,))
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    db.close()
    flash(f"Usuario {u['email']} eliminado.", 'success')
    return redirect(url_for('admin.usuarios'))


@bp.route('/usuarios/<int:uid>/enviar-activacion', methods=['POST'])
@admin_required
def usuario_enviar_activacion(uid):
    db = get_db()
    u = db.execute("SELECT email, nombre, subscription_expires FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('admin.usuarios'))

    # Si no tiene fecha de vencimiento, asignar hoy + 30 días y activar
    exp_str = u['subscription_expires']
    if not exp_str:
        exp_str = (date.today() + timedelta(days=30)).isoformat()
        db.execute(
            "UPDATE users SET active=1, subscription_expires=? WHERE id=?",
            (exp_str, uid)
        )
        db.commit()

    db.close()

    from routes.pagos import _enviar_email_activacion
    from datetime import datetime
    exp_display = exp_str
    try:
        exp_display = datetime.strptime(exp_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except Exception:
        pass

    ok = _enviar_email_activacion(
        user_email=u['email'],
        user_nombre=u['nombre'],
        fecha_vencimiento=exp_display,
    )
    if ok:
        flash(f'Email de activacion enviado a {u["email"]}.', 'success')
    else:
        flash('No se pudo enviar el email (revisar RESEND_API_KEY).', 'error')
    return redirect(url_for('admin.usuarios'))


# CONTACTOS
@bp.route('/contactos')
@admin_required
def contactos():
    db = get_db()
    msgs = db.execute("SELECT * FROM contactos ORDER BY created_at DESC").fetchall()
    db.execute("UPDATE contactos SET leido=1 WHERE leido=0")
    db.commit()
    db.close()
    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mensajes - Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  .card-nuevo  { border-left: 4px solid #0d6efd; }
  .card-leido  { border-left: 4px solid #dee2e6; }
  .card-contest{ border-left: 4px solid #198754; }
</style>
</head><body class="bg-light">
<div class="container py-4" style="max-width:760px">
  <a href="/admin/" class="btn btn-outline-secondary btn-sm mb-3">Volver</a>
  <h4 class="fw-bold mb-1">Mensajes de contacto</h4>
  <p class="text-muted small mb-3">
    <span class="badge bg-primary">{{ msgs|length }} total</span>
    <span class="badge bg-success ms-1">{{ msgs|selectattr('contestado','equalto',1)|list|length }} contestados</span>
    <span class="badge bg-warning text-dark ms-1">{{ msgs|selectattr('leido','equalto',0)|list|length }} nuevos</span>
  </p>
  {% if not msgs %}<p class="text-muted">No hay mensajes aun.</p>{% endif %}
  {% for m in msgs %}
  {% set card_class = 'card-contest' if m.contestado else ('card-nuevo' if not m.leido else 'card-leido') %}
  <div class="card mb-3 shadow-sm {{ card_class }}">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-1">
        <div>
          <strong>{{ m.nombre }} {{ m.apellido or '' }}</strong>
          {% if not m.leido %}<span class="badge bg-primary ms-2">NUEVO</span>{% endif %}
          {% if m.contestado %}<span class="badge bg-success ms-2">Contestado</span>{% endif %}
        </div>
        <small class="text-muted text-nowrap ms-2">{{ m.created_at[:16] }}</small>
      </div>
      <div class="text-muted small mb-2">
        {% if m.email %}<a href="mailto:{{ m.email }}">{{ m.email }}</a>&nbsp;{% endif %}
        {% if m.telefono %}{{ m.telefono }}&nbsp;{% endif %}
        {% if m.ciudad or m.provincia %}{{ m.ciudad or '' }}{% if m.ciudad and m.provincia %}, {% endif %}{{ m.provincia or '' }}{% endif %}
      </div>
      <p class="mb-3 border rounded p-2 bg-white">{{ m.mensaje }}</p>
      <div class="d-flex gap-2 flex-wrap">
        {% if m.email %}
        <a href="mailto:{{ m.email }}" class="btn btn-sm btn-outline-primary">Responder</a>
        {% endif %}
        <form method="POST" action="/admin/contactos/{{ m.id }}/contestado" style="display:inline">
          <button type="submit" class="btn btn-sm {{ 'btn-success' if m.contestado else 'btn-outline-success' }}">
            {% if m.contestado %}Contestado{% else %}Marcar contestado{% endif %}
          </button>
        </form>
      </div>
    </div>
  </div>
  {% endfor %}
</div></body></html>
""", msgs=msgs, user=g.user)

@bp.route('/contactos/<int:mid>/contestado', methods=['POST'])
@admin_required
def contacto_contestado(mid):
    db = get_db()
    row = db.execute("SELECT contestado FROM contactos WHERE id=?", (mid,)).fetchone()
    if row:
        nuevo = 0 if row['contestado'] else 1
        db.execute("UPDATE contactos SET contestado=? WHERE id=?", (nuevo, mid))
        db.commit()
    db.close()
    return redirect(url_for('admin.contactos'))

# SUGERENCIAS (05/07/2026)
@bp.route('/sugerencias')
@admin_required
def sugerencias():
    db = get_db()
    msgs = db.execute("""
        SELECT s.*, u.nombre as user_nombre, u.email as user_email
        FROM sugerencias s LEFT JOIN users u ON u.id = s.user_id
        ORDER BY s.created_at DESC
    """).fetchall()
    db.execute("UPDATE sugerencias SET leido=1 WHERE leido=0")
    db.commit()
    db.close()
    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sugerencias - Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  .card-nuevo  { border-left: 4px solid #0d6efd; }
  .card-leido  { border-left: 4px solid #dee2e6; }
  .card-resp   { border-left: 4px solid #198754; }
</style>
</head><body class="bg-light">
<div class="container py-4" style="max-width:760px">
  <a href="/admin/" class="btn btn-outline-secondary btn-sm mb-3">Volver</a>
  <h4 class="fw-bold mb-1">Sugerencias de usuarios</h4>
  <p class="text-muted small mb-3">
    <span class="badge bg-primary">{{ msgs|length }} total</span>
    <span class="badge bg-success ms-1">{{ msgs|selectattr('respondida','equalto',1)|list|length }} respondidas</span>
    <span class="badge bg-warning text-dark ms-1">{{ msgs|selectattr('leido','equalto',0)|list|length }} nuevas</span>
  </p>
  {% if not msgs %}<p class="text-muted">No hay sugerencias aun.</p>{% endif %}
  {% for m in msgs %}
  {% set card_class = 'card-resp' if m.respondida else ('card-nuevo' if not m.leido else 'card-leido') %}
  <div class="card mb-3 shadow-sm {{ card_class }}">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-1">
        <div>
          <strong>{{ m.user_nombre or m.user_email or 'Usuario #' ~ m.user_id }}</strong>
          {% if not m.leido %}<span class="badge bg-primary ms-2">NUEVA</span>{% endif %}
          {% if m.respondida %}<span class="badge bg-success ms-2">Respondida</span>{% endif %}
        </div>
        <small class="text-muted text-nowrap ms-2">{{ m.created_at[:16] }}</small>
      </div>
      <div class="text-muted small mb-2">
        {% if m.user_email %}<a href="mailto:{{ m.user_email }}">{{ m.user_email }}</a>{% endif %}
      </div>
      <p class="mb-3 border rounded p-2 bg-white">{{ m.mensaje }}</p>
      <div class="d-flex gap-2 flex-wrap">
        {% if m.user_email %}
        <a href="mailto:{{ m.user_email }}" class="btn btn-sm btn-outline-primary">Responder</a>
        {% endif %}
        <form method="POST" action="/admin/sugerencias/{{ m.id }}/respondida" style="display:inline">
          <button type="submit" class="btn btn-sm {{ 'btn-success' if m.respondida else 'btn-outline-success' }}">
            {% if m.respondida %}Respondida{% else %}Marcar respondida{% endif %}
          </button>
        </form>
      </div>
    </div>
  </div>
  {% endfor %}
</div></body></html>
""", msgs=msgs, user=g.user)

@bp.route('/sugerencias/<int:mid>/respondida', methods=['POST'])
@admin_required
def sugerencia_respondida(mid):
    db = get_db()
    row = db.execute("SELECT respondida FROM sugerencias WHERE id=?", (mid,)).fetchone()
    if row:
        nuevo = 0 if row['respondida'] else 1
        db.execute("UPDATE sugerencias SET respondida=? WHERE id=?", (nuevo, mid))
        db.commit()
    db.close()
    return redirect(url_for('admin.sugerencias'))


# WHATSAPP (bandeja de respuesta manual, 20/07/2026)
@bp.route('/whatsapp')
@admin_required
def whatsapp_inbox():
    """Bandeja para responder a mano las consultas que el bot de WhatsApp
    (routes/whatsapp_bot.py) no supo contestar solo. Pedido de Daniel
    20/07/2026.

    Importante — regla de Meta que no depende de nuestro código: se puede
    mandar texto libre por acá SOLO dentro de las 24hs desde que la persona
    escribió (columna `dentro_ventana` de abajo); pasadas esas 24hs, Meta
    rechaza el envío de texto libre y exige una plantilla (template)
    pre-aprobada — igual que ya pasa con el código de verificación en
    utils/verificacion.py::enviar_codigo_whatsapp.

    Actualizado 21/07/2026: esta bandeja SÍ sirve para la campaña de
    retención — antes solo servía para conversaciones que la otra persona
    arrancaba de cero, pero una vez que un usuario de retención RESPONDE al
    mensaje que le mandamos (plantilla aprobada por Cloud API), esa
    respuesta entra por el mismo webhook y cae acá igual que cualquier otro
    mensaje entrante, abriendo la ventana de 24hs para contestarle texto
    libre de verdad. Para dar contexto de quién escribe, se cruza el
    teléfono contra `users` (incluso si vino con formato distinto:
    telefono_normalizado se queda con los últimos 10 dígitos) y contra el
    último envío de `retencion_contactos` para ese usuario."""
    db = get_db()
    consultas = db.execute(
        """SELECT c.*, v.ultima_interaccion
           FROM whatsapp_consultas_sin_responder c
           LEFT JOIN whatsapp_conversaciones v ON v.telefono = c.telefono
           ORDER BY c.respondida ASC, c.created_at DESC"""
    ).fetchall()

    usuarios_por_tel = {}
    for u in db.execute("SELECT id, nombre, email, telefono FROM users WHERE telefono IS NOT NULL AND telefono != ''").fetchall():
        usuarios_por_tel[telefono_normalizado(u['telefono'])] = dict(u)

    ultimo_contacto_por_user = {}
    for r in db.execute(
        """SELECT rc.user_id, rc.segmento, rc.mensaje, rc.canal, rc.created_at
           FROM retencion_contactos rc
           ORDER BY rc.created_at DESC"""
    ).fetchall():
        ultimo_contacto_por_user.setdefault(r['user_id'], dict(r))
    db.close()

    ahora = datetime.utcnow()
    filas = []
    for c in consultas:
        dentro_ventana = None
        if c['ultima_interaccion']:
            try:
                ultima = datetime.fromisoformat(str(c['ultima_interaccion']))
                dentro_ventana = (ahora - ultima) <= timedelta(hours=24)
            except ValueError:
                dentro_ventana = None
        fila = dict(c)
        fila['dentro_ventana'] = dentro_ventana
        usuario = usuarios_por_tel.get(telefono_normalizado(c['telefono']))
        fila['usuario'] = usuario
        fila['retencion'] = ultimo_contacto_por_user.get(usuario['id']) if usuario else None
        filas.append(fila)

    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WhatsApp - Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
<style>
  .card-pendiente { border-left: 4px solid #ffc107; }
  .card-respondida { border-left: 4px solid #198754; }
</style>
</head><body class="bg-light">
<div class="container py-4" style="max-width:760px">
  <a href="/admin/" class="btn btn-outline-secondary btn-sm mb-3">Volver</a>
  <h4 class="fw-bold mb-1">WhatsApp — consultas sin responder por el bot</h4>
  """ + _FLASH_BLOCK + """
  <p class="text-muted small mb-3">
    <span class="badge bg-warning text-dark">{{ consultas|selectattr('respondida','equalto',0)|list|length }} pendientes</span>
    <span class="badge bg-success ms-1">{{ consultas|selectattr('respondida','equalto',1)|list|length }} respondidas</span>
  </p>
  <div class="alert alert-info small">
    <i class="bi bi-info-circle"></i> Solo se puede responder texto libre si la persona escribió
    hace menos de 24hs (columna "ventana"). Pasado ese plazo, Meta exige una plantilla aprobada —
    no es algo que se pueda evitar desde acá.
  </div>
  {% if not consultas %}<p class="text-muted">No hay consultas todavía.</p>{% endif %}
  {% for c in consultas %}
  <div class="card mb-3 shadow-sm {{ 'card-respondida' if c.respondida else 'card-pendiente' }}">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-1">
        <div>
          <strong>{{ c.usuario.nombre if c.usuario and c.usuario.nombre else c.telefono }}</strong>
          {% if c.usuario %}<small class="text-muted">({{ c.telefono }})</small>{% endif %}
          {% if not c.respondida %}<span class="badge bg-warning text-dark ms-2">PENDIENTE</span>{% endif %}
          {% if c.respondida %}<span class="badge bg-success ms-2">Respondida</span>{% endif %}
          {% if c.dentro_ventana %}
          <span class="badge bg-success ms-1"><i class="bi bi-clock-history"></i> dentro de ventana (24hs)</span>
          {% elif c.dentro_ventana is not none %}
          <span class="badge bg-danger ms-1"><i class="bi bi-clock-history"></i> fuera de ventana</span>
          {% endif %}
        </div>
        <small class="text-muted text-nowrap ms-2">{{ c.created_at[:16] }}</small>
      </div>
      {% if c.retencion %}
      <p class="mb-1 small text-primary">
        <i class="bi bi-reply"></i> Responde a un mensaje de retención — Segmento {{ c.retencion.segmento }},
        enviado por {{ c.retencion.canal }} el {{ c.retencion.created_at[:10] }}
      </p>
      {% endif %}
      {% if c.usuario %}
      <p class="mb-1 small"><a href="{{ url_for('admin.seguimiento_detalle', uid=c.usuario.id) }}">Ver perfil completo en Seguimiento →</a></p>
      {% endif %}
      <p class="mb-2 border rounded p-2 bg-white">{{ c.mensaje }}</p>
      {% if c.respondida %}
      <p class="mb-0 small text-muted"><strong>Tu respuesta:</strong> {{ c.respuesta_admin }}</p>
      {% else %}
      <form method="POST" action="{{ url_for('admin.whatsapp_responder', cid=c.id) }}">
        <div class="input-group">
          <textarea name="respuesta" class="form-control" rows="2" placeholder="Escribí la respuesta..." required></textarea>
          <button type="submit" class="btn btn-success">Enviar</button>
        </div>
      </form>
      {% endif %}
    </div>
  </div>
  {% endfor %}
</div></body></html>
""", consultas=filas, user=g.user)


@bp.route('/whatsapp/<int:cid>/responder', methods=['POST'])
@admin_required
def whatsapp_responder(cid):
    texto = (request.form.get('respuesta') or '').strip()
    if not texto:
        flash('Escribí un mensaje antes de enviar.', 'error')
        return redirect(url_for('admin.whatsapp_inbox'))

    db = get_db()
    consulta = db.execute("SELECT * FROM whatsapp_consultas_sin_responder WHERE id=?", (cid,)).fetchone()
    if not consulta:
        db.close()
        flash('Consulta no encontrada.', 'error')
        return redirect(url_for('admin.whatsapp_inbox'))

    from routes.whatsapp_bot import enviar_mensaje_whatsapp
    ok, detalle = enviar_mensaje_whatsapp(consulta['telefono'], texto)
    if ok:
        db.execute(
            "UPDATE whatsapp_consultas_sin_responder SET respondida=1, respuesta_admin=? WHERE id=?",
            (texto, cid)
        )
        db.commit()
        flash('Respuesta enviada.', 'success')
    else:
        flash(f'No se pudo enviar: {detalle}. Si ya pasaron las 24hs desde que esa persona '
              'escribió, Meta exige una plantilla aprobada para mandarle texto libre (no es un '
              'error nuestro).', 'error')
    db.close()
    return redirect(url_for('admin.whatsapp_inbox'))


# PRECIOS MATERIALES
_LISTA_PRECIOS = [
    ('CORRALÓN - Áridos y Cemento', [
        'Cemento portland bolsas', 'Cemento Albañilería', 'Cal hidráulica hidratada',
        'Cal aérea Milagro', 'Hidrófugo', 'Arena común', 'Tierra Colorada',
        'Piedra Partida (Calc. ó Granít.)', 'Granza (mediana)', 'Hormigon elaborado colado',
        'Perlitas Telgopor (75 Lts)',
    ]),
    ('CORRALÓN - Ladrillos y Mampostería', [
        'Ladrillos comunes', 'Ladrillos vista',
        'Ladrillo hueco 8x18x33cm', 'Ladrillo hueco 12X18X33cm',
        'Ladrillo hueco 18X18X33cm', 'Ladrillo hueco Portante 12x18x33cm',
        'Ladrillo hueco Portante 18x18x33cm',
    ]),
    ('CORRALÓN - Hierros y Ferretería', [
        'Hierro redondo d=10mm', 'Alambre negro',
        'Clavos 2"', 'Clavos 2" 1/2', 'Clavos 3"', 'Clavos 4"',
    ]),
    ('CORRALÓN - Viguetas', [
        'Viga Vipret 4m.', 'Ladrillo Telgopor 12*38*1m',
    ]),
    ('Maderera', [
        'Palito 1"x1"', 'Metal desplegado', 'Saligna   1"x2"', 'Saligna 1"x4"',
        'Saligna 3"x3"', 'Pino encofrado 1"', 'Tirantes 2x6', 'Pino tabla machimbre',
        'Escurridores 1/2 x 2', 'Issolant', 'Clavadores 2 x 2', 'Chapas Techo',
        'Tornillo c/arand goma', 'Chapas Cerco', 'Zocalo de madera', 'Tarugo 6',
        'Tornillo',
    ]),
    ('Instalaciones - Electricas', [
        'Cano Corrugado 1"', 'Cano Corrugado 3/4"', 'Cajas Metalicas',
        'Cable 2,5 mm', 'Cable 1,5 mm',
    ]),
    ('Instalaciones - Sanitarias', [
        'Cano Awaduct 110', 'Cano Awaduct 63', 'Cano Awaduct 50',
        'Cano Awaduct 40', 'Accesorios Desagues',
    ]),
    ('Instalaciones - Agua F/C', [
        'Cano TF 25', 'Cano TF 20', 'Accesorios TF', 'Llaves de Paso Agua',
    ]),
    ('Instalaciones - Gas', [
        'Cano Epoxi 3/4', 'Cano epoxi 1/2', 'Accesorios Gas', 'Llaves de Paso Gas',
    ]),
    ('Revestimientos y Pisos', [
        'Klaukol', 'Pastina',
        'Rvto.ceramico 1', 'Rvto.ceramico 2', 'Rvto.ceramico 3 (porcellanato)',
        'Piso ceramico 1', 'Piso ceramico 2', 'Piso ceramico 3 (porcellanato)',
        'Mosaico calcareo', 'Loseta cemento 60x40cm', 'Baldosa ceramica azotea',
        'Zocalo ceramico 1', 'Zocalo ceramico 2', 'Zocalo ceramico 3 (Porcellanato)',
    ]),
    ('Pinturas y Terminaciones', [
        'Pintura latex exterior', 'Pintura latex interior', 'Pintura latex cielos',
        'Esmalte albalux', 'Pintura especial 1', 'Pintura especial 2',
        'Pintura satinol', 'Color pintura cal', 'Enduido sintetico',
    ]),
    ('Materiales Especiales', [
        'Super Iggam', 'Salpicrete', 'Rev Text.', 'Fondo Base',
    ]),
    ('Servicios y Varios', [
        'Transporte material suelto', 'Martillo neumatico',
    ]),
]

@bp.route('/precios')
@admin_required
def precios():
    db = get_db()
    rows = db.execute(
        "SELECT sub_nombre, MAX(precio_ars) as precio_ars "
        "FROM analisis_sub WHERE es_material=1 GROUP BY sub_nombre"
    ).fetchall()
    cfg_jo = db.execute("SELECT valor FROM config WHERE clave='jornal_oficial_dia'").fetchone()
    cfg_ja = db.execute("SELECT valor FROM config WHERE clave='jornal_ayudante_dia'").fetchone()
    db.close()
    precios_dict = {r['sub_nombre']: r['precio_ars'] for r in rows}

    jornal_oficial_dia  = int(float(cfg_jo['valor'])) if cfg_jo else 80000
    jornal_ayudante_dia = int(float(cfg_ja['valor'])) if cfg_ja else 40000

    # ⚠️ Cemento portland, Cemento Albañilería, Cal aérea, Klaukol, Salpicrete y
    # Super Iggam YA están en analisis_sub como precio por bolsa (migraciones 2j/2k/2l
    # en database.py). No van en este diccionario: si se los vuelve a multiplicar acá
    # por el factor de bolsa queda una DOBLE CONVERSIÓN y el precio comercial sale
    # 25-30 veces más caro de lo real (mismo bug que había en paso6_materiales).
    COMERCIAL = {
        'cal hidr':     (25,   'bolsa 25kg'),   # sin migrar — sigue en $/kg
        'cal viv':      (25,   'bolsa 25kg'),   # sin migrar — sigue en $/kg
        'perlitas':     (75,   'bolsa 75Lt'),   # sin migrar — sigue en $/lt
        'revear':       (30,   'balde 30kg'),   # sin migrar — sigue en $/kg
        'hierro':       (7.44, 'barra 12m'),    # sin migrar — sigue en $/kg
        'pastina':      (5,    'bolsa 5kg'),    # sin migrar — sigue en $/kg
    }

    def _info_comercial(nombre):
        n = nombre.lower()
        for kw, (factor, unidad) in COMERCIAL.items():
            if kw in n:
                return factor, unidad
        return 1, ''

    sectores = []
    for sector, nombres in _LISTA_PRECIOS:
        items = []
        for n in nombres:
            precio_calc = precios_dict.get(n, 0)
            factor, unidad_com = _info_comercial(n)
            precio_com = round(precio_calc * factor) if factor != 1 else precio_calc
            items.append({
                'nombre':      n,
                'precio':      precio_calc,
                'precio_com':  precio_com,
                'factor':      factor,
                'unidad_com':  unidad_com,
            })
        sectores.append({'sector': sector, 'items': items})

    return render_template('admin/precios.html', sectores=sectores, user=g.user,
                           jornal_oficial_dia=jornal_oficial_dia,
                           jornal_ayudante_dia=jornal_ayudante_dia)

@bp.route('/precios/actualizar', methods=['POST'])
@admin_required
def precios_actualizar():
    db = get_db()
    actualizados = 0
    jornal_cambio = False
    for key, val in request.form.items():
        if key.startswith('calc_'):
            sub_nombre = key[5:]
            try:
                precio_ars = float(val)
                if precio_ars >= 0:
                    db.execute(
                        "UPDATE analisis_sub SET precio_ars=? WHERE sub_nombre=?",
                        (precio_ars, sub_nombre)
                    )
                    actualizados += 1
            except:
                pass
        elif key in ('jornal_oficial_dia', 'jornal_ayudante_dia'):
            try:
                valor = float(val)
                if valor > 0:
                    db.execute(
                        "INSERT OR REPLACE INTO config (clave, valor) VALUES (?, ?)",
                        (key, str(int(valor)))
                    )
                    actualizados += 1
                    jornal_cambio = True
            except:
                pass
    # Fix 07/07/2026: si se tocó el jornal, recalcular precio_mo_ars de TODOS
    # los ítems con los jornales nuevos — antes esta pantalla guardaba el
    # jornal en `config` pero nada volvía a leerlo, así que ningún ítem
    # cambiaba de costo de MO. Ver database.py::recalcular_precio_mo_ars.
    if jornal_cambio:
        n_mo = recalcular_precio_mo_ars(db)
        actualizados += n_mo
    db.commit()
    db.close()
    flash(f'Precios actualizados ({actualizados} ítems).', 'success')
    return redirect(url_for('admin.precios'))

# TIPOS DE CAMBIO
@bp.route('/tipos-cambio', methods=['GET', 'POST'])
@admin_required
def tipos_cambio():
    db = get_db()
    if request.method == 'POST':
        for key, val in request.form.items():
            if key.startswith('tasa_'):
                pais = key.replace('tasa_', '')
                try:
                    db.execute(
                        "UPDATE tipos_cambio SET tasa=?, updated_at=datetime('now', 'localtime') WHERE pais=?",
                        (float(val), pais)
                    )
                except:
                    pass
        db.commit()
        flash('Tipos de cambio actualizados.', 'success')
        db.close()
        return redirect(url_for('admin.tipos_cambio'))
    tcs = db.execute("SELECT * FROM tipos_cambio ORDER BY pais").fetchall()
    db.close()
    return render_template('admin/tipos_cambio.html', tcs=tcs, user=g.user)


@bp.route('/tipos-cambio/fetch-web')
@admin_required
def tipos_cambio_fetch():
    db = get_db()
    errores = []
    actualizados = []

    try:
        req = urllib.request.Request(
            'https://dolarapi.com/v1/dolares/oficial',
            headers={'User-Agent': 'PresupuestoPRO/1.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        tasa_ar = round(float(data.get('venta', 0)), 2)
        if tasa_ar > 0:
            db.execute("UPDATE tipos_cambio SET tasa=?, updated_at=datetime('now', 'localtime') WHERE pais='AR'",
                       (tasa_ar,))
            actualizados.append(f"ARS: {tasa_ar:.2f}")
    except Exception as e:
        errores.append(f"ARS: {e}")

    try:
        req2 = urllib.request.Request(
            'https://open.er-api.com/v6/latest/USD',
            headers={'User-Agent': 'PresupuestoPRO/1.0'}
        )
        with urllib.request.urlopen(req2, timeout=5) as r:
            rates = json.loads(r.read()).get('rates', {})
        mapa = {'CL': 'CLP', 'UY': 'UYU', 'BR': 'BRL', 'PY': 'PYG'}
        for pais, moneda in mapa.items():
            tasa = rates.get(moneda)
            if tasa:
                tasa_r = round(float(tasa), 2)
                db.execute(
                    "UPDATE tipos_cambio SET tasa=?, updated_at=datetime('now', 'localtime') WHERE pais=?",
                    (tasa_r, pais)
                )
                actualizados.append(f"{pais}: {tasa_r}")
    except Exception as e:
        errores.append(f"LATAM: {e}")

    db.commit()
    db.close()

    if actualizados:
        flash(f"Cotizaciones actualizadas: {', '.join(actualizados)}", 'success')
    if errores:
        flash(f"Errores: {'; '.join(errores)}", 'error')

    return redirect(url_for('admin.tipos_cambio'))


# RENDIMIENTOS
@bp.route('/rendimientos')
@admin_required
def rendimientos():
    db = get_db()
    items = db.execute("SELECT * FROM items_obra ORDER BY rubro_num, id").fetchall()
    db.close()
    from utils.calculations import RUBROS_DEFAULT
    return render_template('admin/rendimientos.html', items=items,
                           rubros=RUBROS_DEFAULT, user=g.user)

@bp.route('/rendimientos/actualizar', methods=['POST'])
@admin_required
def rendimientos_actualizar():
    db = get_db()
    for key, val in request.form.items():
        if key.startswith('hof_') or key.startswith('hay_'):
            tipo, iid = key.split('_', 1)
            try:
                if tipo == 'hof':
                    db.execute("UPDATE items_obra SET hof=? WHERE id=?", (float(val), int(iid)))
                else:
                    db.execute("UPDATE items_obra SET hay=? WHERE id=?", (float(val), int(iid)))
            except Exception:
                pass
    # Fix 07/07/2026: al cambiar HOF/HAY hay que recalcular precio_mo_ars con
    # esos valores nuevos (usando el jornal vigente en `config`) — antes
    # quedaba desactualizado hasta la próxima migración manual (ver bug
    # documentado en PROYECTO.md, sesión 04/07, y database.py::recalcular_precio_mo_ars).
    recalcular_precio_mo_ars(db)
    db.commit()
    db.close()
    flash('Rendimientos actualizados correctamente.', 'success')
    return redirect(url_for('admin.rendimientos'))


# FIX DB
@bp.route('/fix-db')
def fix_db():
    db = get_db()
    log = []
    items_borrar = [
        'Ayuda gremios y varios',
        'Rvto. marmol',
        'Ho.Ado. tanque (90-13)',
        'H.Elab. tanque (90-13)',
        'Cemento: revoque tanque',
    ]
    for nombre in items_borrar:
        r = db.execute("DELETE FROM items_obra WHERE nombre=?", (nombre,))
        if r.rowcount:
            log.append(f"DEL items_obra: {nombre}")

    r = db.execute("UPDATE items_obra SET precio_mo_ars=5000 WHERE id IN (97,98,99,100,101)")
    log.append(f"UPD pintura MO x{r.rowcount}")

    ceramicos = {82:11550, 83:11550, 84:21800, 87:4050, 88:4050, 92:14650, 93:14650}
    for iid, mo in ceramicos.items():
        db.execute("UPDATE items_obra SET precio_mo_ars=? WHERE id=?", (mo, iid))
    log.append(f"UPD ceramicos MO x{len(ceramicos)}")

    db.commit()
    cnt = db.execute("SELECT COUNT(*) FROM items_obra").fetchone()[0]
    db.close()
    log.append(f"VERIFY items_obra:{cnt}")
    from flask import jsonify
    return jsonify({'ok': True, 'cambios': log})


# CONFIGURACION
@bp.route('/configuracion', methods=['GET', 'POST'])
@admin_required
def configuracion():
    db = get_db()
    if request.method == 'POST':
        for clave in ('pct_gg', 'pct_impuestos'):
            val = request.form.get(clave)
            if val:
                db.execute(
                    "INSERT OR REPLACE INTO config (clave, valor) VALUES (?,?)",
                    (clave, val)
                )
        # Fix 10/07/2026: validación de cuenta (email/WhatsApp) — checkbox no
        # tildado no manda el campo en el form, por eso se chequea presencia
        # en vez de leer el valor.
        verificacion_val = '1' if request.form.get('verificacion_activa') == 'on' else '0'
        verificacion_previa = db.execute(
            "SELECT valor FROM config WHERE clave='verificacion_activa'"
        ).fetchone()
        se_esta_prendiendo = verificacion_val == '1' and (not verificacion_previa or verificacion_previa['valor'] != '1')
        db.execute(
            "INSERT OR REPLACE INTO config (clave, valor) VALUES ('verificacion_activa', ?)",
            (verificacion_val,)
        )
        # Fix 10/07/2026: al PRENDER el switch (no antes), se marca como
        # validado a cualquiera que ya tuviera cuenta y todavía no hubiera
        # validado — el bloqueo arranca a regir recién de acá para adelante,
        # nunca retroactivo a alguien que se registró antes de que el switch
        # estuviera prendido (Daniel lo pidió explícitamente 10/07/2026).
        if se_esta_prendiendo:
            n_grandfather = db.execute(
                "UPDATE users SET email_verificado=1, phone_verificado=1 "
                "WHERE metodo_verificacion != '' AND (email_verificado=0 OR phone_verificado=0)"
            ).rowcount
            if n_grandfather:
                print(f"[admin.configuracion] verificacion_activa prendida: "
                      f"{n_grandfather} cuenta(s) existente(s) marcadas como ya validadas (no retroactivo)")

        # Fix 18/07/2026: switch aparte para mostrar "Por WhatsApp" en el
        # registro, desacoplado de si las variables de entorno están
        # cargadas (ver utils/verificacion.py::whatsapp_configurado).
        whatsapp_val = '1' if request.form.get('whatsapp_validacion_habilitada') == 'on' else '0'
        db.execute(
            "INSERT OR REPLACE INTO config (clave, valor) VALUES ('whatsapp_validacion_habilitada', ?)",
            (whatsapp_val,)
        )
        db.commit()
        db.close()
        if se_esta_prendiendo and n_grandfather:
            flash(f'Configuracion guardada. Validación activada — {n_grandfather} cuenta(s) que ya '
                  f'existían quedaron marcadas como validadas (no se les exige validar retroactivamente).',
                  'success')
        else:
            flash('Configuracion guardada.', 'success')
        return redirect(url_for('admin.dashboard'))
    cfg = {r['clave']: r['valor'] for r in db.execute("SELECT * FROM config").fetchall()}
    pendientes_validar = db.execute(
        "SELECT COUNT(*) c FROM users WHERE metodo_verificacion != '' "
        "AND ((metodo_verificacion='email' AND email_verificado=0) "
        "OR (metodo_verificacion='whatsapp' AND phone_verificado=0))"
    ).fetchone()['c']
    db.close()
    return render_template('admin/configuracion.html', cfg=cfg, user=g.user,
                           pendientes_validar=pendientes_validar)


# LEADS
@bp.route('/leads')
@admin_required
def leads():
    db = get_db()
    todos = db.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template('admin/leads.html', leads=todos, user=g.user)

@bp.route('/leads/<int:lid>/estado', methods=['POST'])
@admin_required
def lead_estado(lid):
    estado = request.form.get('estado', 'nuevo')
    notas  = request.form.get('notas', '')
    db = get_db()
    db.execute("UPDATE leads SET estado=?, notas=? WHERE id=?", (estado, notas, lid))
    db.commit()
    db.close()
    flash('Lead actualizado.', 'success')
    return redirect(url_for('admin.leads'))
