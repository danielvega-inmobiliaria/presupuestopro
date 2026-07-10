"""
Validación de cuenta por email o WhatsApp — fix 10/07/2026.

Se puede activar/desactivar sin redeployar: config.verificacion_activa
('1'/'0' en la tabla `config`, editable desde Admin > Configuración).
Arranca en '0' (apagado) a propósito — activarla corta el acceso a la app
para cualquiera que no valide, así que Daniel la prende cuando probó el
flujo con su propia cuenta y está conforme.

Dos canales:
  - email: funciona YA (usa Resend, ya integrado en el resto de la app).
  - whatsapp: requiere que Daniel complete la verificación del negocio en
    Meta Business Manager + de de alta el número 341 754-2009 en WhatsApp
    Business Platform (Cloud API) + tenga aprobado un template de mensaje
    de autenticación (Meta exige template pre-aprobado para mensajes que
    arranca la empresa, no el usuario). Sin WHATSAPP_TOKEN/WHATSAPP_PHONE_ID
    configurados en las variables de entorno, enviar_codigo_whatsapp()
    devuelve False y el registro cae automáticamente a email — no rompe
    nada, solo no manda el WhatsApp real hasta que esas variables existan.
"""
import json
import os
import secrets
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from functools import wraps

import resend
from flask import g, redirect, url_for

from database import get_db

CODIGO_EXPIRA_MIN = 15


def _config(clave, default=None):
    db = get_db()
    row = db.execute("SELECT valor FROM config WHERE clave=?", (clave,)).fetchone()
    db.close()
    return row['valor'] if row else default


def verificacion_activa():
    return _config('verificacion_activa', '0') == '1'


def generar_codigo():
    """Código numérico de 6 dígitos, generado con secrets (no random) porque
    se usa para autenticar — mismo criterio que los tokens de sesión."""
    return f"{secrets.randbelow(1_000_000):06d}"


def crear_codigo(user_id, canal):
    """canal: 'email' o 'whatsapp'. Invalida códigos anteriores sin usar del
    mismo usuario/canal y crea uno nuevo. Devuelve el código en texto plano
    (se manda una sola vez, no se vuelve a leer de la DB)."""
    codigo = generar_codigo()
    expira = (datetime.utcnow() + timedelta(minutes=CODIGO_EXPIRA_MIN)).isoformat()
    db = get_db()
    db.execute(
        "UPDATE verificacion_codigos SET usado=1 WHERE user_id=? AND canal=? AND usado=0",
        (user_id, canal)
    )
    db.execute(
        "INSERT INTO verificacion_codigos (user_id, canal, codigo, expira_at) VALUES (?,?,?,?)",
        (user_id, canal, codigo, expira)
    )
    db.commit()
    db.close()
    return codigo


def validar_codigo(user_id, canal, codigo_ingresado):
    """Devuelve True/False. Si es correcto y no venció, lo marca usado y
    marca el canal correspondiente como verificado en users."""
    db = get_db()
    row = db.execute(
        """SELECT id, expira_at FROM verificacion_codigos
           WHERE user_id=? AND canal=? AND codigo=? AND usado=0
           ORDER BY id DESC LIMIT 1""",
        (user_id, canal, codigo_ingresado.strip())
    ).fetchone()
    if not row:
        db.close()
        return False
    try:
        vencido = datetime.utcnow() > datetime.fromisoformat(row['expira_at'])
    except ValueError:
        vencido = True
    if vencido:
        db.close()
        return False
    db.execute("UPDATE verificacion_codigos SET usado=1 WHERE id=?", (row['id'],))
    campo = 'email_verificado' if canal == 'email' else 'phone_verificado'
    db.execute(f"UPDATE users SET {campo}=1 WHERE id=?", (user_id,))
    db.commit()
    db.close()
    return True


def enviar_codigo_email(email, nombre, codigo):
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        print(f"[verificacion] Sin RESEND_API_KEY — código para {email}: {codigo}")
        return False
    try:
        resend.api_key = api_key
        resend.Emails.send({
            "from": "PresupuestoPRO <noreply@presupuestopro.com.ar>",
            "to": [email],
            "subject": f"Tu código de verificación: {codigo}",
            "text": (
                f"Hola {nombre},\n\n"
                f"Tu código para validar tu cuenta en PresupuestoPRO es:\n\n"
                f"{codigo}\n\n"
                f"Vence en {CODIGO_EXPIRA_MIN} minutos. Si no lo pediste vos, ignorá este mensaje."
            ),
        })
        return True
    except Exception as e:
        print(f"[verificacion] Error enviando email a {email}: {e}")
        return False


def enviar_codigo_whatsapp(telefono, codigo):
    """Manda el código por WhatsApp Business Platform (Meta Cloud API).
    Devuelve False (sin excepción) si falta configurar las credenciales o si
    falla el envío — el llamador debe hacer fallback a email en ese caso."""
    token = os.environ.get('WHATSAPP_TOKEN')
    phone_id = os.environ.get('WHATSAPP_PHONE_ID')
    template = os.environ.get('WHATSAPP_TEMPLATE_OTP', 'verificacion_codigo')
    if not token or not phone_id or not telefono:
        print(f"[verificacion] WhatsApp no configurado (falta WHATSAPP_TOKEN/WHATSAPP_PHONE_ID) "
              f"— código para {telefono}: {codigo}")
        return False
    try:
        numero = ''.join(c for c in telefono if c.isdigit())
        if not numero.startswith('54'):
            numero = '54' + numero  # Argentina
        body = {
            "messaging_product": "whatsapp",
            "to": numero,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": "es_AR"},
                "components": [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": codigo}]
                }]
            }
        }
        req = urllib.request.Request(
            f"https://graph.facebook.com/v20.0/{phone_id}/messages",
            data=json.dumps(body).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        print(f"[verificacion] Error WhatsApp API ({e.code}): {e.read()}")
        return False
    except Exception as e:
        print(f"[verificacion] Error enviando WhatsApp a {telefono}: {e}")
        return False


def get_verificacion_status(user):
    """dict con el estado de validación de `user` para mostrar en pantalla."""
    metodo = (user['metodo_verificacion'] or '') if user else ''
    if metodo == 'whatsapp':
        verificado = bool(user['phone_verificado'])
    else:
        verificado = bool(user['email_verificado'])
    return {
        'metodo': metodo or 'email',
        'verificado': verificado if metodo else True,  # sin método elegido = cuenta vieja, no se bloquea
    }


def verificacion_required(f):
    """Igual patrón que utils/trial.py::trial_required. Va DESPUÉS de
    @login_required. Si la validación está apagada (config flag en '0'),
    no bloquea a nadie."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not verificacion_activa():
            return f(*args, **kwargs)
        status = get_verificacion_status(g.user)
        if not status['verificado']:
            return redirect(url_for('landing.validar_cuenta'))
        return f(*args, **kwargs)
    return decorated
