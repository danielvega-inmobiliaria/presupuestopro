# Deploy PresupuestoPRO en Railway

## Archivos creados/modificados para este deploy
- `Procfile` — cómo arrancar gunicorn
- `requirements.txt` — agregado gunicorn
- `runtime.txt` — Python 3.11.9
- `config.py` — DATABASE_PATH y DEBUG desde env vars
- `app.py` — PORT desde env var, debug controlado
- `.gitignore` — excluye .db, Excel, __pycache__

---

## PASO 1 — Subir a GitHub

### 1a. Crear repo en GitHub
1. Ir a https://github.com/new
2. Nombre: `presupuestopro` (o el que prefieras)
3. Privado (recomendado para código de negocio)
4. Sin README, sin .gitignore (ya los tenemos)
5. Click "Create repository"

### 1b. Subir el código desde Windows (CMD)
```cmd
cd /d D:\ESCRITORIO\CLAUDE\APP_PRESUPUESTOPRO
git init
git add .
git commit -m "Initial deploy setup"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/presupuestopro.git
git push -u origin main
```
> Reemplazá TU_USUARIO con tu usuario de GitHub (ej: danielvega-inmobiliaria)

---

## PASO 2 — Crear proyecto en Railway

1. Ir a https://railway.app y loguearse con GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Seleccionar el repo `presupuestopro`
4. Railway detecta el Procfile automáticamente y arranca el deploy

---

## PASO 3 — Agregar volumen persistente para SQLite

> SIN esto la DB se borra en cada deploy.

1. En el proyecto Railway → click en el servicio (el cuadrado de tu app)
2. Tab "Volumes" → "Add Volume"
3. Mount path: `/data`
4. Click "Add"

---

## PASO 4 — Configurar variables de entorno

En Railway → tab "Variables" → agregar:

| Variable | Valor |
|---|---|
| `SECRET_KEY` | Una clave larga y random (ej: `presupuestopro-prod-2026-xK9mN2pQ`) |
| `DATABASE_PATH` | `/data/presupuestopro.db` |

> NO setear FLASK_DEBUG (queda en 0 = producción por defecto)

---

## PASO 5 — Subir la DB actual al volumen

La primera vez hay que copiar `presupuestopro.db` al volumen `/data/`.

### Opción A: Via Railway CLI (recomendada)
```cmd
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Copiar la DB al volumen
railway run --service presupuestopro cp /path/local/presupuestopro.db /data/presupuestopro.db
```

### Opción B: Script de carga inicial (más simple)
Agregar temporalmente esta ruta en `routes/admin.py` o correr una vez:
```python
# Ruta temporal: GET /admin/upload-db-init
# Solo usar una vez para subir la DB, luego eliminar
```
> Te puedo generar esto si lo necesitás.

### Opción C (más fácil): Dejar que init_db() cree una DB nueva
Si no necesitás los presupuestos de prueba que tenés en local, simplemente
dejá que Railway arranque con la DB vacía — init_db() crea todas las tablas
y carga los items_obra, analisis_sub, etc. automáticamente.
**Esta es la opción recomendada para el primer deploy.**

---

## PASO 6 — Obtener la URL pública

1. En Railway → tab "Settings" → "Domains"
2. Click "Generate Domain" → te da algo como `presupuestopro-production.up.railway.app`
3. O podés agregar tu propio dominio (ej: `app.presupuestopro.com`)

---

## Flujo de actualizaciones futuras

```cmd
cd /d D:\ESCRITORIO\CLAUDE\APP_PRESUPUESTOPRO
git add .
git commit -m "descripcion del cambio"
git push
```
Railway redeploya automáticamente en ~1 minuto.

---

## Costos estimados Railway

- Plan Hobby: ~$5 USD/mes (incluye 512MB RAM, 1GB storage)
- El volumen para SQLite: +$0.25/GB/mes (mínimo)
- Total estimado: **~$6-7 USD/mes**

Con el primer cliente a $10 USD/mes ya está cubierto.
