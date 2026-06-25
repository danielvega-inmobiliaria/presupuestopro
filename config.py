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
