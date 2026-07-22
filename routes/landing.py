"""
Blueprint: landing
Rutas: POST /contacto (formulario de contacto de la landing real, templates/landing.html)
       GET/POST /registro (alta gratis — campaña de lanzamiento, 06/07/2026)

Fix 06/07/2026: se eliminó la landing vieja (GET/POST /landing, variable
LANDING_HTML con el formulario de pago directo por Mercado Pago) — era código
muerto, no la enlazaba nada del sitio actual (el modelo pasó a ser lanzamiento
gratis). La landing real y en uso hoy es templates/landing.html, servida desde
dashboard.index(). Se conserva solo contacto(), que sigue viva.

Agregado 06/07/2026: /registro — alta pública de autoservicio para la campaña
de lanzamiento con prueba gratis (3 presupuestos o 14 días, ver utils/trial.py).
No pide pago; crea la cuenta con es_trial=1 y loguea directo. Daniel: para usar
esto en la campaña, apuntá el botón/link de "Probála gratis" de tu landing o
publicidad a esta URL (/registro).
"""

import logging
import os
from datetime import date, timedelta
import resend
from werkzeug.security import generate_password_hash
from flask import Blueprint, g, redirect, render_template, request, url_for

from database import get_db
from utils.auth import login_user, login_required
from utils.trial import TRIAL_MAX_DIAS, TRIAL_MAX_PRESUPUESTOS
from utils.normalizacion import PROVINCIAS_AR, clave_normalizada, telefono_normalizado
from utils.verificacion import (
    crear_codigo, enviar_codigo_email, enviar_codigo_whatsapp,
    validar_codigo, verificacion_activa, get_verificacion_status,
    whatsapp_configurado,
)

bp = Blueprint('landing', __name__)
logger = logging.getLogger(__name__)

COMO_NOS_CONOCIO_OPCIONES = [
    'Facebook', 'Instagram', 'Recomendación de alguien', 'Búsqueda en Google', 'Otro',
]

COMO_PRESUPUESTABA_OPCIONES = [
    'A mano (papel)', 'Excel o planilla', 'Otra app', 'Todavía no presupuesto', 'Otro',
]


def _guardar_localidad(ciudad_libre, provincia):
    """Agrupa `ciudad_libre` contra lo ya cargado por otros usuarios (misma
    clave normalizada = mismo lugar) y devuelve el nombre a guardar en
    users.ciudad: si ya existía, reusa la grafía canónica; si es nueva, usa
    tal cual la escribió este usuario y queda como canónica para el próximo.

    Fix 10/07/2026: si esa clave fue fusionada a mano por Daniel (Admin >
    Localidades) hacia otra entrada, sigue la cadena hasta la canónica final
    en vez de reusar la vieja — así una fusión hecha hoy también agrupa a
    los usuarios que se registren después."""
    ciudad_libre = (ciudad_libre or '').strip()
    if not ciudad_libre:
        return ''
    clave = clave_normalizada(ciudad_libre)
    if not clave:
        return ciudad_libre
    db = get_db()
    existente = db.execute(
        "SELECT clave_normalizada, nombre_display, merged_en FROM localidades WHERE clave_normalizada=?",
        (clave,)
    ).fetchone()
    if existente:
        destino = existente
        visitados = {existente['clave_normalizada']}
        while destino['merged_en'] and destino['merged_en'] not in visitados:
            siguiente = db.execute(
                "SELECT clave_normalizada, nombre_display, merged_en FROM localidades WHERE clave_normalizada=?",
                (destino['merged_en'],)
            ).fetchone()
            if not siguiente:
                break
            visitados.add(siguiente['clave_normalizada'])
            destino = siguiente
        db.execute(
            "UPDATE localidades SET veces_usada = veces_usada + 1 WHERE clave_normalizada=?",
            (destino['clave_normalizada'],)
        )
        db.commit()
        db.close()
        return destino['nombre_display']
    db.execute(
        "INSERT INTO localidades (clave_normalizada, nombre_display, provincia, veces_usada) VALUES (?,?,?,1)",
        (clave, ciudad_libre, provincia or '')
    )
    db.commit()
    db.close()
    return ciudad_libre


@bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        db = get_db()
        localidades = [r['nombre_display'] for r in db.execute(
            "SELECT nombre_display FROM localidades ORDER BY veces_usada DESC LIMIT 500"
        ).fetchall()]
        db.close()
        return render_template('registro.html',
                                max_presupuestos=TRIAL_MAX_PRESUPUESTOS,
                                max_dias=TRIAL_MAX_DIAS,
                                provincias=PROVINCIAS_AR,
                                como_opciones=COMO_NOS_CONOCIO_OPCIONES,
                                presupuestaba_opciones=COMO_PRESUPUESTABA_OPCIONES,
                                localidades=localidades,
                                whatsapp_disponible=whatsapp_configurado())

    f = request.form
    nombre    = f.get('nombre', '').strip()
    apellido  = f.get('apellido', '').strip()
    telefono  = f.get('telefono', '').strip()
    email     = f.get('email', '').strip().lower()
    ciudad    = f.get('ciudad', '').strip()
    provincia = f.get('provincia', '').strip()
    password  = f.get('password', '')
    como_conocio       = f.get('como_nos_conocio', '').strip()
    como_conocio_otro  = f.get('como_nos_conocio_otro', '').strip()
    presupuestaba      = f.get('como_presupuestaba', '').strip()
    presupuestaba_otro = f.get('como_presupuestaba_otro', '').strip()
    metodo_verif       = f.get('metodo_verificacion', 'email').strip()
    if metodo_verif not in ('email', 'whatsapp'):
        metodo_verif = 'email'

    prev = dict(nombre=nombre, apellido=apellido, telefono=telefono,
                email=email, ciudad=ciudad, provincia=provincia,
                como_nos_conocio=como_conocio, como_presupuestaba=presupuestaba,
                metodo_verificacion=metodo_verif)

    def _error(msg):
        return render_template('registro.html', error=msg, prev=prev,
                                max_presupuestos=TRIAL_MAX_PRESUPUESTOS,
                                max_dias=TRIAL_MAX_DIAS,
                                provincias=PROVINCIAS_AR,
                                como_opciones=COMO_NOS_CONOCIO_OPCIONES,
                                presupuestaba_opciones=COMO_PRESUPUESTABA_OPCIONES,
                                localidades=[],
                                whatsapp_disponible=whatsapp_configurado())

    if not nombre or not apellido or not email or not password:
        return _error("Completá los campos obligatorios.")
    if not telefono:
        return _error("Completá tu teléfono / WhatsApp.")
    if not ciudad:
        return _error("Completá tu ciudad.")
    if not provincia:
        return _error("Elegí tu provincia.")
    if not como_conocio:
        return _error("Contanos cómo nos conociste.")
    if como_conocio == 'Otro' and not como_conocio_otro:
        return _error("Contanos cómo nos conociste (detalle de 'Otro').")
    if not presupuestaba:
        return _error("Contanos cómo venís presupuestando.")
    if presupuestaba == 'Otro' and not presupuestaba_otro:
        return _error("Contanos cómo venís presupuestando (detalle de 'Otro').")
    if len(password) < 6:
        return _error("La contraseña debe tener al menos 6 caracteres.")
    if metodo_verif == 'whatsapp' and not telefono:
        return _error("Para validar por WhatsApp necesitamos tu teléfono.")

    if como_conocio == 'Otro' and como_conocio_otro:
        como_conocio_final = f"Otro: {como_conocio_otro}"
    else:
        como_conocio_final = como_conocio

    if presupuestaba == 'Otro' and presupuestaba_otro:
        presupuestaba_final = f"Otro: {presupuestaba_otro}"
    else:
        presupuestaba_final = presupuestaba

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        db.close()
        return _error("Ya existe una cuenta con ese email. Iniciá sesión en vez de registrarte de nuevo.")

    # Fix 10/07/2026 (pedido de Daniel): controlar también por teléfono, no
    # solo por email — evita altas duplicadas de la misma persona con otro
    # email (ej. para sacar más presupuestos gratis de la prueba). Se compara
    # normalizado (últimos 10 dígitos) para que no importe el formato en que
    # cada uno lo escribió. No hay columna indexada para esto — se compara en
    # Python contra los teléfonos ya cargados, suficiente para el volumen
    # actual de usuarios.
    if telefono:
        tel_clave = telefono_normalizado(telefono)
        if tel_clave:
            existentes_tel = db.execute("SELECT telefono FROM users WHERE telefono != ''").fetchall()
            if any(telefono_normalizado(r['telefono']) == tel_clave for r in existentes_tel):
                db.close()
                return _error("Ya existe una cuenta registrada con ese teléfono. Si es tuya, iniciá sesión; "
                               "si creés que es un error, escribinos.")
    db.close()

    # Localidad: agrupa contra lo ya cargado por otros usuarios (ver docstring
    # de _guardar_localidad). Provincia ya viene de una lista cerrada (select
    # en registro.html), no necesita normalización.
    ciudad_final = _guardar_localidad(ciudad, provincia)

    db = get_db()
    try:
        password_hash = generate_password_hash(password)
        vence = (date.today() + timedelta(days=TRIAL_MAX_DIAS)).isoformat()
        cursor = db.execute(
            """INSERT INTO users
               (email, password_hash, nombre, apellido, telefono, ciudad, provincia,
                pais, active, es_trial, trial_visto, subscription_expires,
                como_nos_conocio, como_presupuestaba, metodo_verificacion)
               VALUES (?,?,?,?,?,?,?,?,1,1,0,?,?,?,?)""",
            (email, password_hash, nombre, apellido, telefono, ciudad_final, provincia,
             'AR', vence, como_conocio_final, presupuestaba_final, metodo_verif)
        )
        user_id = cursor.lastrowid
        db.commit()
        logger.info(f"[Registro] Nueva cuenta de prueba {email} id={user_id}")
    except Exception as e:
        db.close()
        logger.error(f"[Registro] Error creando cuenta {email}: {e}")
        return _error("Error al crear la cuenta. Intentá de nuevo.")
    db.close()

    _notificar_registro(nombre, apellido, telefono, email, ciudad_final, provincia)

    # Validación de cuenta (fix 10/07/2026): si está activada, mandamos el
    # código ya mismo por el canal elegido. WhatsApp cae a email automático
    # si todavía no están las credenciales de Meta configuradas (ver
    # utils/verificacion.py::enviar_codigo_whatsapp).
    if verificacion_activa():
        canal_real = metodo_verif
        codigo = crear_codigo(user_id, canal_real)
        enviado = False
        if canal_real == 'whatsapp':
            enviado = enviar_codigo_whatsapp(telefono, codigo)
            if not enviado:
                canal_real = 'email'
                codigo = crear_codigo(user_id, canal_real)
                enviado = enviar_codigo_email(email, nombre, codigo)
        else:
            enviado = enviar_codigo_email(email, nombre, codigo)
        if not enviado:
            logger.error(f"[Registro] No se pudo enviar código de verificación a {email}")
        # Fix 10/07/2026: si hubo fallback whatsapp->email, persistir el canal
        # real en la DB. Si no se actualiza, get_verificacion_status() sigue
        # leyendo 'whatsapp' de users.metodo_verificacion y la pantalla de
        # validar-cuenta muestra el mensaje equivocado ("te mandamos por
        # WhatsApp") Y compara el código ingresado contra canal='whatsapp' en
        # vez de 'email' — el código correcto (el que llegó por mail) queda
        # imposible de validar. Bug detectado por Daniel probando en
        # producción 10/07/2026.
        if canal_real != metodo_verif:
            db_canal = get_db()
            db_canal.execute("UPDATE users SET metodo_verificacion=? WHERE id=?", (canal_real, user_id))
            db_canal.commit()
            db_canal.close()

    login_user(user_id)
    # Nota 07/07/2026: se saca el flash() de bienvenida de acá a propósito —
    # duplicaba el cartel "¡Bienvenido a PresupuestoPRO!" que ya muestra
    # dashboard.html (mostrar_bienvenida_trial) en el primer login, con más
    # detalle (Costo/m2, PDFs, etc.). Un solo mensaje de bienvenida, no dos.
    # Fix 08/07/2026: se agrega ?nuevo_registro=1 para que dashboard.html
    # dispare fbq('track','CompleteRegistration') una sola vez (Meta Pixel,
    # campaña de lanzamiento) — ver templates/dashboard.html bloque scripts.
    if verificacion_activa():
        return redirect(url_for('landing.validar_cuenta'))
    return redirect(url_for('dashboard.index', nuevo_registro=1))


@bp.route('/validar-cuenta', methods=['GET', 'POST'])
@login_required
def validar_cuenta():
    status = get_verificacion_status(g.user)
    if status['verificado']:
        return redirect(url_for('dashboard.index'))

    error = None
    ok_reenvio = None
    if request.method == 'POST':
        accion = request.form.get('accion', 'validar')
        if accion == 'reenviar':
            codigo = crear_codigo(g.user['id'], status['metodo'])
            if status['metodo'] == 'whatsapp':
                enviado = enviar_codigo_whatsapp(g.user['telefono'], codigo)
                if not enviado:
                    codigo = crear_codigo(g.user['id'], 'email')
                    enviado = enviar_codigo_email(g.user['email'], g.user['nombre'], codigo)
                    status['metodo'] = 'email'
                    # Fix 10/07/2026 (mismo bug que en registro()): persistir
                    # el fallback a email, si no queda desincronizado con la DB.
                    db_canal = get_db()
                    db_canal.execute("UPDATE users SET metodo_verificacion='email' WHERE id=?", (g.user['id'],))
                    db_canal.commit()
                    db_canal.close()
            else:
                enviado = enviar_codigo_email(g.user['email'], g.user['nombre'], codigo)
            ok_reenvio = "Te reenviamos el código." if enviado else "No pudimos reenviar el código, probá de nuevo en un rato."
        else:
            codigo_ingresado = request.form.get('codigo', '').strip()
            if validar_codigo(g.user['id'], status['metodo'], codigo_ingresado):
                # Fix 22/07/2026: con verificacion_activa=ON el registro nuevo
                # pasa por acá (no por el redirect de registro()) y nunca
                # llevaba ?nuevo_registro=1 — el Pixel de Meta (CompleteRegistration
                # en dashboard.html) no disparaba para NINGÚN registro validado
                # desde que se prendió el switch (18/07/2026). Bug detectado
                # por el aviso de Ads Manager "sin actividad del píxel en 7+ días".
                return redirect(url_for('dashboard.index', nuevo_registro=1))
            error = "Código incorrecto o vencido. Podés pedir uno nuevo."

    return render_template('validar_cuenta.html', user=g.user, metodo=status['metodo'],
                            error=error, ok_reenvio=ok_reenvio)


def _notificar_registro(nombre, apellido, telefono, email, ciudad, provincia):
    """Aviso al admin de cada alta nueva de prueba gratis (mismo patrón que
    routes/dashboard.py::_enviar_notificacion para leads)."""
    api_key = os.environ.get('RESEND_API_KEY')
    admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')
    if not api_key:
        print(f"[registro] Sin RESEND_API_KEY — nueva cuenta trial: {nombre} {apellido} | {email}")
        return
    try:
        resend.api_key = api_key
        payload = {
            "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
            "to": [admin_email],
            "subject": f"🎉 Nueva cuenta de prueba gratis: {nombre} {apellido}",
            "text": (
                f"Nueva cuenta de prueba gratis en PresupuestoPRO\n\n"
                f"Nombre:    {nombre} {apellido}\n"
                f"Teléfono:  {telefono or '(no indicó)'}\n"
                f"Email:     {email}\n"
                f"Ciudad:    {ciudad or '-'}, {provincia or '-'}\n\n"
                f"Ver todos los usuarios:\n"
                f"https://web-production-0c9c1.up.railway.app/admin/usuarios"
            ),
        }
        if email:
            payload["reply_to"] = [email]
        resend.Emails.send(payload)
    except Exception as e:
        print(f"[registro] Error enviando email: {e}")


@bp.route('/contacto', methods=['POST'])
def contacto():
    f = request.form
    nombre   = f.get('nombre', '').strip()
    apellido = f.get('apellido', '').strip()
    telefono = f.get('telefono', '').strip()
    email    = f.get('email', '').strip()
    ciudad   = f.get('ciudad', '').strip()
    provincia= f.get('provincia', '').strip()
    mensaje  = f.get('mensaje', '').strip()

    if nombre and mensaje:
        try:
            db = get_db()
            db.execute(
                """INSERT INTO contactos (nombre, apellido, telefono, email, ciudad, provincia, mensaje)
                   VALUES (?,?,?,?,?,?,?)""",
                (nombre, apellido, telefono, email, ciudad, provincia, mensaje)
            )
            db.commit()
            db.close()
            logger.info(f"[Contacto] Mensaje de {nombre} {apellido} / {email}")
        except Exception as e:
            logger.error(f"[Contacto] Error: {e}")

        # Notificación email al admin
        try:
            api_key = os.environ.get('RESEND_API_KEY')
            admin_email = os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')
            if api_key:
                resend.api_key = api_key
                payload = {
                    "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
                    "to": [admin_email],
                    "subject": f"💬 Nuevo mensaje de contacto: {nombre} {apellido}",
                    "text": (
                        f"Nuevo mensaje de contacto en PresupuestoPRO\n\n"
                        f"Nombre:    {nombre} {apellido}\n"
                        f"Teléfono:  {telefono or '(no indicó)'}\n"
                        f"Email:     {email or '(no indicó)'}\n"
                        f"Ciudad:    {ciudad or '-'}, {provincia or '-'}\n\n"
                        f"Mensaje:\n{mensaje}\n\n"
                        f"Ver todos los mensajes:\n"
                        f"https://web-production-0c9c1.up.railway.app/admin/contactos"
                    ),
                }
                # Fix 05/07/2026: Reply-To al email de contacto, para responder
                # directo con un Reply en vez de a noreply@.
                if email:
                    payload["reply_to"] = [email]
                resend.Emails.send(payload)
        except Exception as e:
            logger.error(f"[Contacto] Error enviando email: {e}")

    # Fix 14/07/2026: '/landing' ya no existe (se borró 06/07/2026). Corregido
    # a la home real, tal como quedó anotado como pendiente.
    return redirect('/?contacto_ok=1#contacto')


@bp.route('/terminos')
def terminos():
    return render_template('terminos.html')


@bp.route('/privacidad')
def privacidad():
    return render_template('privacidad.html')
