import os
from flask import Flask
from config import Config
from database import init_db, migrate_db
from routes import auth, dashboard, presupuesto, admin, pdf_routes, perfil, pagos, landing


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(presupuesto.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(pdf_routes.bp)
    app.register_blueprint(perfil.bp)
    app.register_blueprint(pagos.bp)
    app.register_blueprint(landing.bp)

    with app.app_context():
        init_db()
        migrate_db()

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=port)
