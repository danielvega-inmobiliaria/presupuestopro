# Webhook de mail entrante — Cloudflare Email Worker

Este Worker intercepta el mail que llega a `contacto@presupuestopro.com.ar`,
lo sigue reenviando a `presupuestopro.app@gmail.com` (como hace hoy la regla
de Email Routing) y ADEMÁS manda una copia parseada (remitente, asunto,
texto) a la app, para que aparezca en **Admin > Email**.

Nada de lo que ya funciona se rompe: mientras este Worker no esté
desplegado y la regla de routing no se cambie, todo sigue exactamente igual
que hoy.

## Paso a paso para desplegarlo

Requiere Node.js instalado (`node -v` para chequear) y una cuenta de
Cloudflare con el dominio `presupuestopro.com.ar` ya agregado (ya lo está).

### 1. Instalar dependencias
```bash
cd cloudflare_email_worker
npm install
```

### 2. Login en Cloudflare (una sola vez)
```bash
npx wrangler login
```
Abre el navegador, pide autorizar — es la misma cuenta donde está el
dominio y la regla de Email Routing actual.

### 3. Cargar el secreto compartido
Elegí un string largo y random (por ejemplo, generalo con
`openssl rand -hex 32` o cualquier generador de contraseñas). Este mismo
valor va acá Y en Railway (variable `EMAIL_WEBHOOK_SECRET`, paso 5).
```bash
npx wrangler secret put EMAIL_WEBHOOK_SECRET
```
Te va a pedir que pegues el valor.

### 4. Deployar el Worker
```bash
npx wrangler deploy
```
Al terminar, confirma con un mensaje tipo
`Uploaded presupuestopro-email-webhook` y te da la URL del Worker (no hace
falta usarla directamente — Email Routing la conecta por nombre en el
paso siguiente).

### 5. Cargar `EMAIL_WEBHOOK_SECRET` en Railway
Mismo valor exacto que en el paso 3. Railway > proyecto de PresupuestoPRO >
Variables > agregar `EMAIL_WEBHOOK_SECRET`.

### 6. Cambiar la regla de Email Routing para que use el Worker
Hoy la regla de `contacto@presupuestopro.com.ar` dice "Send to email" →
`presupuestopro.app@gmail.com`. Hay que cambiarla a "Send to a Worker":

1. Cloudflare Dashboard > `presupuestopro.com.ar` > **Email** > **Email Routing** > **Routing rules**.
2. Editar la regla de `contacto@presupuestopro.com.ar`.
3. Acción: cambiar de "Send to an email" a **"Send to a Worker"**.
4. Elegir el Worker `presupuestopro-email-webhook` (el que se deployó en el paso 4).
5. Guardar.

**Importante:** el reenvío a Gmail no se pierde — ahora lo hace el propio
Worker (`message.forward(...)` en `src/index.js`), así que el resultado
final para vos es el mismo mail en Gmail de siempre, más el registro nuevo
en la app.

### 7. Probar
Mandate un mail de prueba a `contacto@presupuestopro.com.ar` desde
cualquier cuenta (puede ser tu Gmail personal). Confirmá dos cosas:
- Llegó a `presupuestopro.app@gmail.com` como siempre.
- Apareció en **Admin > Email** de la app (con el remitente cruzado contra
  `users` si ese mail ya está registrado).

Si no aparece en la app: revisar en Cloudflare Dashboard > Workers >
`presupuestopro-email-webhook` > Logs, para ver si el POST a Railway falló
(típicamente, `EMAIL_WEBHOOK_SECRET` no coincide entre los dos lados).
