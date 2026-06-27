import os

class Config:
    # SECRET_KEY: en producción setear como variable de entorno en Railway.
    # Cambiar solo si se quiere invalidar TODAS las sesiones activas.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'presupuestopro-dev-key-2026-fixed'

    # DATABASE: en Railway usar DATABASE_PATH=/data/presupuestopro.db (volumen persistente).
    # En local usa el archivo en la misma carpeta que este config.py.
    DATABASE = os.environ.get('DATABASE_PATH') or os.path.join(os.path.dirname(__file__), 'presupuestopro.db')

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400 * 30  # 30 días

    # En producción Railway setea PORT automáticamente; debug desactivado.
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'

    # Mercado Pago — cargar en Railway como variables de entorno
    MP_ACCESS_TOKEN = os.environ.get('MP_ACCESS_TOKEN', '')
    MP_PUBLIC_KEY   = os.environ.get('MP_PUBLIC_KEY', '')
    MP_APP_ID       = os.environ.get('MP_APP_ID', '')
    # Precio de la suscripción mensual en ARS (ajustar según necesidad)
    MP_PRECIO_ARS   = float(os.environ.get('MP_PRECIO_ARS', '12500'))
    MP_PLAN_NOMBRE  = os.environ.get('MP_PLAN_NOMBRE', 'PresupuestoPRO — Plan Mensual')
    # Solo en sandbox: email de la cuenta test-comprador de MP (test_user_USERID@testuser.com).
    # En producción dejar vacío o no setear.
    MP_TEST_PAYER_EMAIL = os.environ.get('MP_TEST_PAYER_EMAIL', '')
    # URL base de la app (para back_url del webhook)
    APP_BASE_URL    = os.environ.get('APP_BASE_URL', 'https://web-production-0c9c1.up.railway.app')
