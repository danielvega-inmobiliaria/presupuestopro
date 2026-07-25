import os
from datetime import datetime, timedelta
from flask import Flask
from config import Config
from database import init_db, migrate_db
from routes import auth, dashboard, presupuesto, admin, pdf_routes, perfil, pagos, landing, costo_m2, sugerencias, manual, whatsapp_bot


def local_dt(value, fmt='%d/%m %H:%M'):
    """Fix 24/07/2026: Daniel detectó un desfasaje de exactamente 3 horas
    entre la hora real de un WhatsApp y la que mostraba Admin > Seguimiento.
    Causa: `created_at` se guarda en UTC (default de SQLite) pero se
    mostraba tal cual, sin convertir a hora de Argentina (UTC-3, sin
    horario de verano, así que un offset fijo alcanza). Filtro Jinja para
    usar en cualquier template: {{ x.created_at|local_dt }}."""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(str(value).replace(' ', 'T'))
    except ValueError:
        return value
    return (dt - timedelta(hours=3)).strftime(fmt)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.jinja_env.filters['local_dt'] = local_dt

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(presupuesto.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(pdf_routes.bp)
    app.register_blueprint(perfil.bp)
    app.register_blueprint(pagos.bp)
    app.register_blueprint(landing.bp)
    app.register_blueprint(costo_m2.bp)
    app.register_blueprint(sugerencias.bp)
    app.register_blueprint(manual.bp)
    app.register_blueprint(whatsapp_bot.bp)

    with app.app_context():
        init_db()
        migrate_db()

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=port)
