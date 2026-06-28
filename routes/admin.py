import json
import urllib.request
from datetime import date
from flask import Blueprint, render_template, render_template_string, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash
from utils.auth import admin_required
from database import get_db

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
    }
    proximos = db.execute(
        "SELECT * FROM users WHERE subscription_expires >= date('now') AND is_admin=0 ORDER BY subscription_expires LIMIT 5"
    ).fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats, proximos=proximos, user=g.user)

# ─── USUARIOS ────────────────────────────────────────────────────────────────
@bp.route('/usuarios')
@admin_required
def usuarios():
    db = get_db()
    users = db.execute(
        "SELECT * FROM users WHERE is_admin=0 ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return render_template('admin/usuarios.html', users=users, user=g.user)

@bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@admin_required
def usuario_nuevo():
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        nombre   = request.form.get('nombre', '')
        password = request.form.get('password', '')
        pais     = request.form.get('pais', 'AR')
        vence    = request.form.get('subscription_expires', '')
        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (email, password_hash, nombre, pais, active, subscription_expires) VALUES (?,?,?,?,1,?)",
                (email, generate_password_hash(password), nombre, pais, vence or None)
            )
            db.commit()
            flash(f'Usuario {email} creado.', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
        finally:
            db.close()
        return redirect(url_for('admin.usuarios'))
    return render_template('admin/usuario_form.html', u=None, user=g.user)

@bp.route('/usuarios/<int:uid>/editar', methods=['GET', 'POST'])
@admin_required
def usuario_editar(uid):
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not u:
        db.close(); return redirect(url_for('admin.usuarios'))

    if request.method == 'POST':
        nombre  = request.form.get('nombre', '')
        pais    = request.form.get('pais', 'AR')
        active  = 1 if request.form.get('active') else 0
        vence   = request.form.get('subscription_expires', '')
        new_pw  = request.form.get('password', '').strip()
        if new_pw:
            db.execute(
                "UPDATE users SET nombre=?, pais=?, active=?, subscription_expires=?, password_hash=? WHERE id=?",
                (nombre, pais, active, vence or None, generate_password_hash(new_pw), uid)
            )
        else:
            db.execute(
                "UPDATE users SET nombre=?, pais=?, active=?, subscription_expires=? WHERE id=?",
                (nombre, pais, active, vence or None, uid)
            )
        # Si se desactiva, invalidar sesión
        if not active:
            db.execute("UPDATE users SET session_token=NULL WHERE id=?", (uid,))
        db.commit()
        flash('Usuario actualizado.', 'success')
        db.close()
        return redirect(url_for('admin.usuarios'))

    db.close()
    return render_template('admin/usuario_form.html', u=u, user=g.user)

# ─── CONTACTOS ───────────────────────────────────────────────────────────────
@bp.route('/contactos')
@admin_required
def contactos():
    db = get_db()
    msgs = db.execute("SELECT * FROM contactos ORDER BY created_at DESC").fetchall()
    # Marcar no leídos DESPUÉS de capturar el estado (para mostrar badge "NUEVO")
    db.execute("UPDATE contactos SET leido=1 WHERE leido=0")
    db.commit()
    db.close()
    return render_template_string("""
<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mensajes — Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  .card-nuevo  { border-left: 4px solid #0d6efd; }
  .card-leido  { border-left: 4px solid #dee2e6; }
  .card-contest{ border-left: 4px solid #198754; }
</style>
</head><body class="bg-light">
<div class="container py-4" style="max-width:760px">
  <a href="/admin/" class="btn btn-outline-secondary btn-sm mb-3">← Volver</a>
  <h4 class="fw-bold mb-1">Mensajes de contacto</h4>
  <p class="text-muted small mb-3">
    <span class="badge bg-primary">{{ msgs|length }} total</span>
    <span class="badge bg-success ms-1">{{ msgs|selectattr('contestado','equalto',1)|list|length }} contestados</span>
    <span class="badge bg-warning text-dark ms-1">{{ msgs|selectattr('leido','equalto',0)|list|length }} nuevos</span>
  </p>
  {% if not msgs %}
  <p class="text-muted">No hay mensajes aún.</p>
  {% endif %}
  {% for m in msgs %}
  {% set card_class = 'card-contest' if m.contestado else ('card-nuevo' if not m.leido else 'card-leido') %}
  <div class="card mb-3 shadow-sm {{ card_class }}">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-1">
        <div>
          <strong>{{ m.nombre }} {{ m.apellido or '' }}</strong>
          {% if not m.leido %}<span class="badge bg-primary ms-2">NUEVO</span>{% endif %}
          {% if m.contestado %}<span class="badge bg-success ms-2">✓ Contestado</span>{% endif %}
        </div>
        <small class="text-muted text-nowrap ms-2">{{ m.created_at[:16] }}</small>
      </div>
      <div class="text-muted small mb-2">
        {% if m.email %}📧 <a href="mailto:{{ m.email }}">{{ m.email }}</a>&nbsp;{% endif %}
        {% if m.telefono %}📱 {{ m.telefono }}&nbsp;{% endif %}
        {% if m.ciudad or m.provincia %}📍 {{ m.ciudad or '' }}{% if m.ciudad and m.provincia %}, {% endif %}{{ m.provincia or '' }}{% endif %}
      </div>
      <p class="mb-3 border rounded p-2 bg-white">{{ m.mensaje }}</p>
      <div class="d-flex gap-2 flex-wrap">
        {% if m.email %}
        <a href="mailto:{{ m.email }}?subject=Re: Tu consulta en PresupuestoPRO&body=Hola {{ m.nombre }},%0A%0AGracias por tu mensaje.%0A%0A----%0ATu mensaje: {{ m.mensaje|urlencode }}"
           class="btn btn-sm btn-outline-primary">
          ✉️ Responder por email
        </a>
        {% endif %}
        {% if m.telefono %}
        <a href="https://wa.me/{{ m.telefono | replace(' ','') | replace('-','') | replace('+','') | replace('(','') | replace(')','') }}?text=Hola%20{{ m.nombre | urlencode }}%2C%20te%20contactamos%20desde%20PresupuestoPRO%20en%20relaci%C3%B3n%20a%20tu%20consulta."
           target="_blank" class="btn btn-sm btn-outline-success">
          💬 WhatsApp
        </a>
        {% endif %}
        <form method="POST" action="/admin/contactos/{{ m.id }}/contestado" style="display:inline">
          <button type="submit" class="btn btn-sm {{ 'btn-success' if m.contestado else 'btn-outline-success' }}">
            {% if m.contestado %}✓ Contestado{% else %}Marcar contestado{% endif %}
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

# ─── PRECIOS MATERIALES ───────────────────────────────────────────────────────
@bp.route('/precios')
@admin_required
def precios():
    db = get_db()
    mats = db.execute("SELECT * FROM materiales ORDER BY categoria, nombre").fetchall()
    tasa = db.execute("SELECT tasa FROM tipos_cambio WHERE pais='AR'").fetchone()
    tasa_ars = tasa['tasa'] if tasa else 1
    db.close()
    return render_template('admin/precios.html', materiales=mats, tasa_ars=tasa_ars, user=g.user)

@bp.route('/precios/actualizar', methods=['POST'])
@admin_required
def precios_actualizar():
    db = get_db()
    tasa = db.execute("SELECT tasa FROM tipos_cambio WHERE pais='AR'").fetchone()
    tasa_ars = tasa['tasa'] if tasa else 1
    for key, val in request.form.items():
        if key.startswith('precio_'):
            mid = key.replace('precio_', '')
            try:
                precio_ars = float(val)
                precio_usd = round(precio_ars / tasa_ars, 6)
                db.execute(
                    "UPDATE materiales SET precio_usd=?, updated_at=datetime('now', 'localtime') WHERE id=?",
                    (precio_usd, int(mid))
                )
            except:
                pass
    db.commit()
    db.close()
    flash('Precios actualizados.', 'success')
    return redirect(url_for('admin.precios'))

# ─── TIPOS DE CAMBIO ─────────────────────────────────────────────────────────
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
    """Obtiene cotizaciones desde dolarapi.com (AR oficial) y exchangerate-api (resto)."""
    db = get_db()
    errores = []
    actualizados = []

    # Dólar oficial Argentina
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

    # Otras monedas LATAM (exchangerate-api free, base USD)
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
        flash(f"Cotizaciones actualizadas desde la web: {', '.join(actualizados)}", 'success')
    if errores:
        flash(f"Algunos errores: {'; '.join(errores)}", 'error')

    return redirect(url_for('admin.tipos_cambio'))


# ─── RENDIMIENTOS ITEMS OBRA (HOF / HAY) ─────────────────────────────────────
@bp.route('/rendimientos')
@admin_required
def rendimientos():
    db = get_db()
    items = db.execute(
        "SELECT * FROM items_obra ORDER BY rubro_num, id"
    ).fetchall()
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
    db.commit()
    db.close()
    flash('Rendimientos actualizados correctamente.', 'success')
    return redirect(url_for('admin.rendimientos'))


# ─── FIX DB: aplica correcciones pendientes ──────────────────────────────────
@bp.route('/fix-db')
def fix_db():
    """Aplica todas las correcciones pendientes a la DB. Sin auth requerida (uso interno)."""
    db = get_db()
    log = []

    # 1. Eliminar items_obra
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

    # 2. MO Pintura (ids 97-101): $7681 → $5000
    r = db.execute("UPDATE items_obra SET precio_mo_ars=5000 WHERE id IN (97,98,99,100,101)")
    log.append(f"UPD pintura MO ×{r.rowcount}")

    # 3. MO Cerámicos
    ceramicos = {82:11550, 83:11550, 84:21800, 87:4050, 88:4050, 92:14650, 93:14650}
    for iid, mo in ceramicos.items():
        db.execute("UPDATE items_obra SET precio_mo_ars=? WHERE id=?", (mo, iid))
    log.append(f"UPD ceramicos MO ×{len(ceramicos)}")

    # 4. Precios analisis_sub
    db.execute("UPDATE analisis_sub SET precio_ars=1500 WHERE sub_nombre='Salpicrete'")
    db.execute("UPDATE analisis_sub SET precio_ars=1166.67 WHERE sub_nombre='Super Iggam'")
    log.append("UPD Salpicrete $1500, Super Iggam $1166.67")

    # 4b. Unificación de nombres duplicados en analisis_sub
    unif = [
        # (sub_nombre_viejo, sub_nombre_nuevo)  — renombra todas las ocurrencias
        ('Arena',                           'Arena común'),
        ('Cascotes ladrillos',              'Granza'),
        ('Cem Albañ',                       'Cemento Albañilería'),
        ('Cemento portland en bolsas',      'Cemento portland bolsas'),
        ('Cemento',                         'Cemento portland bolsas'),   # exacto, no toca 'Cemento Albañilería'
        ('Clavos',                          'Clavos 2"'),
        ('Junta (equivalente de encofrado)','Junta (Pavimento Hormigón)'),
        ('Ladrillo telgopor 12*38*1m',      'Ladrillo Telgopor 12*38*1m'),
        ('Ladrillo Telgopor',               'Ladrillo Telgopor 12*38*1m'),
        ('Cal aérea',                       'Cal aérea Milagro'),
        ('DeckAr',                          'Rev Text.'),
        ('Piedra partida',                  'Piedra Granítica'),
    ]
    for old_n, new_n in unif:
        r = db.execute("UPDATE analisis_sub SET sub_nombre=? WHERE sub_nombre=?", (new_n, old_n))
        if r.rowcount:
            log.append(f"UNIF analisis_sub: '{old_n}' → '{new_n}' ×{r.rowcount}")

    # 5. Renombrar sub_nombres genéricos en analisis_sub usando item_nombre como filtro
    renames_sub = [
        # (sub_nombre_actual, item_nombre_filtro, sub_nombre_nuevo)
        ('Accesorios', 'Instalación Desagues',  'Accesorios Desagues'),
        ('Accesorios', 'Instalacion Desagues',  'Accesorios Desagues'),
        ('Accesorios', 'Instalación Agua F/C',  'Accesorios TF'),
        ('Accesorios', 'Instalacion Agua F/C',  'Accesorios TF'),
        ('Accesorios', 'Instalación Gas',        'Accesorios Gas'),
        ('Accesorios', 'Instalacion Gas',        'Accesorios Gas'),
        ('Llaves de Paso', 'Instalación Agua F/C', 'Llaves de Paso Agua'),
        ('Llaves de Paso', 'Instalacion Agua F/C', 'Llaves de Paso Agua'),
        ('Llaves de Paso', 'Instalación Gas',       'Llaves de Paso Gas'),
        ('Llaves de Paso', 'Instalacion Gas',       'Llaves de Paso Gas'),
    ]
    for sub_old, item_nombre, sub_new in renames_sub:
        r = db.execute(
            "UPDATE analisis_sub SET sub_nombre=? WHERE sub_nombre=? AND item_nombre=?",
            (sub_new, sub_old, item_nombre)
        )
        if r.rowcount:
            log.append(f"RENAME analisis_sub [{item_nombre}]: {sub_old} → {sub_new}")

    db.commit()

    # Verificación
    cnt = db.execute("SELECT COUNT(*) FROM items_obra").fetchone()[0]
    sal = db.execute("SELECT precio_ars FROM analisis_sub WHERE sub_nombre='Salpicrete'").fetchone()
    ayuda = db.execute("SELECT COUNT(*) FROM items_obra WHERE nombre='Ayuda gremios y varios'").fetchone()[0]
    db.close()

    log.append(f"VERIFY → items_obra:{cnt}, Salpicrete:{sal[0] if sal else 'N/A'}, Ayuda:{ayuda}")
    from flask import jsonify
    return jsonify({'ok': True, 'cambios': log})


# ─── CONFIGURACIÓN (% GG, Imp) ───────────────────────────────────────────────
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
        db.commit()
        db.close()
        flash('Configuración guardada.', 'success')
        return redirect(url_for('admin.dashboard'))
    cfg = {r['clave']: r['valor'] for r in db.execute("SELECT * FROM config").fetchall()}
    db.close()
    return render_template('admin/configuracion.html', cfg=cfg, user=g.user)


# ─── LEADS / INSCRIPTOS ──────────────────────────────────────────────────────
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
