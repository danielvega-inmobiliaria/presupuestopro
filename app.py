import os
from datetime import datetime, timedelta
from flask import Flask
from config import Config
from database import init_db, migrate_db
from routes import auth, dashboard, presupuesto, admin, pdf_routes, perfil, pagos, landing, costo_m2, sugerencias, manual, whatsapp_bot, social_bot, email_bot, webhooks_resend
from utils.pdf_generator import iniciales_empresa
from utils.recordatorios import enviar_recordatorios_inactividad


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
    # Fix 03/08/2026 (tour, paso "Tu logo"): mismo cálculo de iniciales que
    # usa el PDF real (utils/pdf_generator.py), expuesto como filtro Jinja
    # para poder mostrar la burbuja de iniciales también en templates/perfil/perfil.html.
    app.jinja_env.filters['iniciales_empresa'] = iniciales_empresa

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
    app.register_blueprint(social_bot.bp)
    app.register_blueprint(email_bot.bp)
    app.register_blueprint(webhooks_resend.bp)

    with app.app_context():
        init_db()
        migrate_db()

    _iniciar_scheduler(app)

    return app


def _iniciar_scheduler(app):
    """Recordatorio automático de inactividad (utils/recordatorios.py) —
    pedido de Daniel 04/08/2026 (cont. 20). Corre cada 60 min, en CADA
    worker de gunicorn por separado (Procfile usa --workers 2) -- no hay
    forma simple de compartir un único scheduler entre procesos con
    gunicorn prefork, así que se acepta que el job corra 2 veces por hora
    en vez de 1. La protección contra mandar el mail 2 veces está en el
    UPDATE atómico DENTRO de enviar_recordatorios_inactividad(), no acá.

    Guard con WERKZEUG_RUN_MAIN: `python app.py` en local con debug=True usa
    el reloader de Werkzeug, que arranca 2 procesos (padre "vigía" + hijo
    real) -- sin este guard, el scheduler arrancaría 2 veces también en
    local (una por proceso). El proceso hijo real es el único que tiene
    WERKZEUG_RUN_MAIN='true'; el padre no lo tiene seteado. En producción
    (gunicorn, sin reloader, app.debug=False) esta condición es falsa y el
    scheduler arranca normal en cada worker, como corresponde."""
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        print("[scheduler] apscheduler no instalado -- recordatorios de inactividad OFF")
        return

    def _job():
        with app.app_context():
            n = enviar_recordatorios_inactividad()
            if n:
                print(f"[scheduler] recordatorios de inactividad mandados: {n}")

    scheduler = BackgroundScheduler(daemon=True)
    # next_run_time explícito: sin esto, APScheduler espera un intervalo
    # completo (60 min) antes de la 1ra corrida -- con esto arranca ~1 min
    # después del deploy, y de ahí en más cada 60 min.
    scheduler.add_job(_job, 'interval', minutes=60,
                       next_run_time=datetime.now() + timedelta(minutes=1))
    scheduler.start()


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=port)
