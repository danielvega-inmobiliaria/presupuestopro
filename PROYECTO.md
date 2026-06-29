# PresupuestoPRO — Contexto del Proyecto

## Stack
- Flask + Python 3.11 · SQLite en `/data/presupuestopro.db` · Railway (US West)
- Repo: `danielvega-inmobiliaria/presupuestopro` (branch `main`)
- URL prod: `https://web-production-0c9c1.up.railway.app`
- Carpeta local: `D:\ESCRITORIO\CLAUDE\APP_PRESUPUESTOPRO`

## Regla crítica de commits (NUNCA ignorar)
El bash (FUSE mount) ve versiones **stale** de archivos Windows.
- **NUNCA commitear `database.py` desde bash** — tiene mojibake
- Solo commitear archivos escritos directamente desde bash con Python script
- Archivos editados desde Windows (Edit tool) → commitear desde Git Bash del usuario
- Comando para limpiar lock si hay problemas: `rm -f .git/index.lock` (Git Bash, no CMD)

## Variables de entorno en Railway
| Variable | Estado |
|---|---|
| `RESEND_API_KEY` | ✅ Configurada (`re_hTDGcDLu_...`) |
| `MP_ACCESS_TOKEN` | ✅ Configurada |
| `MP_PUBLIC_KEY` | ✅ Configurada |
| `SECRET_KEY` | ✅ Configurada |
| `ADMIN_EMAIL` | ⚠️ No confirmada (default: `danve61@gmail.com`) |
| `APP_BASE_URL` | ⚠️ Verificar si está |

## Email — Estado actual ✅
- Dominio `presupuestopro.com.ar` verificado en Resend (29/06/2026 19:07 ART)
- Todos los emails salen como `PresupuestoPRO <noreply@presupuestopro.com.ar>`
- DNS en Cloudflare: MX, DKIM, SPF y DMARC configurados y verificados
- Emails a usuarios externos (hotmail, gmail, etc.) ahora funcionan correctamente
- Fallback admin sigue activo en `pagos.py` por si hay error inesperado

## Schema DB — tabla `users` (columnas relevantes)
```
id, email, password_hash, nombre, pais, active,
subscription_expires, session_token, session_expires,
is_admin, created_at, mp_preapproval_id,
apellido, telefono, ciudad, provincia  ← agregadas por migrate_db()
```
`database.py` las agrega via `migrate_db()` con ALTER TABLE si no existen.

## Features implementadas (commiteadas)
- [x] `routes/pagos.py`: `_enviar_email_activacion()` + fallback admin + llamada en `_activar_suscripcion()`
- [x] `routes/admin.py`: ruta `/usuarios/<uid>/enviar-activacion` + guarda telefono/ciudad/provincia en edit y nuevo
- [x] `routes/auth.py`: rutas `/recuperar` y `/restablecer/<token>` (reset contraseña)
- [x] `templates/login.html`: link "¿Olvidaste tu contraseña?"
- [x] `templates/admin/usuarios.html`: muestra telefono + ciudad/provincia + botón WhatsApp (formato 549XXXXXXXXXX)
- [x] `templates/admin/usuario_form.html`: campos telefono, ciudad, provincia

## Pendientes / Ideas
- [ ] Confirmar variable `APP_BASE_URL` en Railway
- [ ] Test completo del flujo pago MP → activación → email (con dominio propio)
- [ ] Apuntar presupuestopro.com.ar a Railway (registro A/CNAME en Cloudflare)

## Estado al cerrar sesión (29/06/2026 ~20:00)
- WhatsApp funciona ✅
- URL login en `/login` ✅
- Dominio verificado en Resend ✅ — emails salen desde `noreply@presupuestopro.com.ar`
- DNS Cloudflare: MX, DKIM, SPF, DMARC todos activos ✅
- Próximo paso: test end-to-end del flujo de pago + email de activación

## Cómo commitear desde Git Bash (usuario)
```bash
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add <archivo1> <archivo2>   # usar / no \
git commit -m "descripción"
git push
```
