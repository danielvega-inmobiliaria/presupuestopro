# PresupuestoPRO — Contexto del Proyecto

## Cómo usar este archivo
- **Al empezar un chat nuevo:** pegá → `Leé PROYECTO.md y continuá desde donde quedamos`
- **Al terminar un chat:** pedí → `Actualizá PROYECTO.md con lo que hicimos hoy`

---

## Descripción del proyecto
PresupuestoPRO (presupuestopro.com.ar) es una app web para calcular presupuestos de obra de construcción en minutos: carga de rubros e ítems, cálculo automático de materiales, mano de obra (oficial y ayudante) y costo por m², con precios actualizados para el mercado argentino. Funciona por suscripción mensual vía Mercado Pago ($12.500 ARS). Lanzada el 01/07/2026, apunta a contratistas, albañiles y profesionales de la construcción que hoy arman presupuestos a mano o en planillas. Slogan: "De los metros a los pesos, en minutos."

---

_Última actualización: 18/07/2026 — 22:58 ART_

### Sesión 16-18/07/2026 — Formulario de registro: nueva pregunta + todo obligatorio + fix WhatsApp prematuro ✅ COMMITEADO (parte 1) / ✅ COMMITEADO Y PROBADO (parte 2)
Pedido de Daniel: agregar al formulario de registro una pregunta sobre el método actual del usuario (app, Excel/planilla, a mano), para tener ese dato de producto/marketing. Implementado con el mismo patrón que "¿Cómo nos conociste?" (select cerrado + "Otro" con texto libre).
**Hecho:**
- `database.py`: migración `2w` — agrega columna `users.como_presupuestaba TEXT DEFAULT ''`.
- `routes/landing.py`: constante `COMO_PRESUPUESTABA_OPCIONES` (`A mano (papel)`, `Excel o planilla`, `Otra app`, `Todavía no presupuesto`, `Otro`); lee `como_presupuestaba`/`como_presupuestaba_otro` del form, arma el valor final (igual que `como_conocio`) y lo guarda en el INSERT de `users`.
- `templates/registro.html`: nuevo select "¿Cómo venís presupuestando?" al lado del de "cómo nos conociste", con su campo "Otro" y el mismo toggle JS.
- `templates/admin/usuarios.html`: se muestra el dato en la ficha de cada usuario (ícono calculadora), igual que "cómo nos conoció".
- `templates/manual.html`: actualizada la sección de registro para mencionar el nuevo campo (regla de mantener el Manual al día).
- **Actualización (mismo día):** Daniel detectó que un usuario nuevo se registró sin que aparecieran ni "cómo nos conoció" ni "cómo presupuestaba" — eran opcionales (ni el `<select>` tenía `required` ni el backend los validaba), así que el usuario los dejó en blanco y la ficha de Admin no muestra la línea si está vacío (comportamiento esperado, no bug). Pedido explícito: pasar ambos a **obligatorios**. ✅ Hecho: `required` agregado a los dos `<select>` en `templates/registro.html` + validación server-side en `routes/landing.py` (`_error` si falta cualquiera de los dos).
- **Actualización 18/07/2026:** mismo patrón — Daniel notó que a otro usuario nuevo no le figuraban Ciudad ni Provincia (también eran opcionales). Pedido: pasar **las 4 restantes a obligatorias** (Teléfono, Ciudad, Provincia, y el texto libre de "Otro" en ambos selects). ✅ Hecho:
  - `templates/registro.html`: `required` agregado a Teléfono, Ciudad y Provincia. Los inputs "Contanos cuál" (de "cómo nos conociste" y "cómo presupuestaba") ahora se marcan `required` por JS solo cuando están visibles (cuando el select correspondiente vale "Otro") — si no, el navegador no puede validar un campo oculto con `d-none`.
  - `routes/landing.py`: validación server-side agregada para Teléfono, Ciudad, Provincia, y para el texto libre de "Otro" en ambos selects (si eligió "Otro" pero no completó el detalle, rechaza el registro).
  - Con esto, del formulario de registro **todos los campos son obligatorios excepto el método de validación** (hoy fijo en email, radio oculto).
**Archivos tocados (parte 1):** `database.py`, `routes/landing.py`, `templates/registro.html`, `templates/admin/usuarios.html`, `templates/manual.html`.
**✅ Confirmado por Daniel 18/07/2026: "Ya está todo commiteado".**

**Parte 2 — fix del switch de WhatsApp prematuro (mismo día, después del commit de arriba):** Daniel notó en producción que el registro dejaba elegir "Por WhatsApp" para validar la cuenta — no debía pasar todavía (sigue esperando la aprobación de Meta). Causa: había cargado `WHATSAPP_TOKEN`/`WHATSAPP_PHONE_ID`/`WHATSAPP_VERIFY_TOKEN` en Railway de antemano (para tenerlas listas), y `whatsapp_configurado()` solo miraba esas 2 variables de entorno — apenas estuvieron, la opción se mostró sola. Daniel preguntó cómo recuperar las variables si las borraba; en vez de eso se agregó un switch para no depender de tocar Railway:
  - `utils/verificacion.py::whatsapp_configurado()`: ahora exige TAMBIÉN el config flag `whatsapp_validacion_habilitada='1'` (además de las 2 variables de entorno). Apagado por defecto.
  - `templates/admin/configuracion.html`: nuevo switch "Mostrar 'Por WhatsApp' como opción de validación en el registro".
  - `routes/admin.py::configuracion()`: guarda el nuevo flag (mismo patrón que `verificacion_activa`).
  - Con esto, las credenciales pueden quedar cargadas en Railway sin riesgo — la opción no aparece a los usuarios hasta que Daniel prenda el switch a mano desde Admin > Configuración, el día que Meta apruebe y se pruebe en vivo.
**Archivos tocados (parte 2):** `utils/verificacion.py`, `templates/admin/configuracion.html`, `routes/admin.py`.
**✅ Confirmado por Daniel 18/07/2026: ya estaba commiteado y probado — "Por WhatsApp" ya no aparece en `/registro` (switch apagado por defecto en Admin > Configuración).**

**Dos cosas que Daniel reportó como "bug" durante las pruebas y NO lo eran (sin cambios de código):**
- Email de validación no llegaba a `itaauto03@gmail.com` → revisado en el dashboard de Resend: **Bounced** en el primer envío, **Suppressed** en el reintento (Resend deja de mandarle a una dirección que ya rebotó). El dominio y Resend están bien (la notificación al admin llegó `Delivered` sin problema) — probablemente typo en esa dirección de prueba.
- "El mail ya está en uso" al re-registrar después de borrar una cuenta de prueba → Daniel confirmó que en realidad no la había borrado. El botón "Eliminar" de Admin > Usuarios sí libera el email al instante cuando se usa.

### Sesión 15/07/2026 — Bot de FAQ por WhatsApp: primera versión del código ⚠️ SIN COMMITEAR
Trabajo hecho desde el proyecto paralelo `CHATBOT_WHATSAPP_BUSINESS` (ver ese `PROYECTO.md` para el contexto completo de por qué y las preguntas/respuestas fuente en `FAQ_BOT.md`). Se dejó preparada la arquitectura técnica aunque el número 341 754-2009 todavía no está dado de alta en Meta — no se puede probar en vivo todavía.

**Hecho:**
1. **`routes/whatsapp_bot.py` (nuevo):** blueprint `whatsapp_bot`, `url_prefix='/webhook/whatsapp'`.
   - `GET` → verificación del webhook ante Meta (compara `hub.verify_token` contra `WHATSAPP_VERIFY_TOKEN`).
   - `POST` → recibe mensajes entrantes, busca match por palabras clave contra `FAQ_DATA` (~21 preguntas, mismo contenido que `FAQ_BOT.md`), responde por WhatsApp si matchea; si no, guarda la consulta en `whatsapp_consultas_sin_responder` y manda la respuesta de fallback.
   - `buscar_respuesta()`: normaliza (minúsculas, sin tildes) y hace matching por substring simple — decidido así con Daniel (rápido/gratis, se revisa si resulta muy rígido en el uso real).
   - `enviar_mensaje_whatsapp()`: mensaje de texto libre vía Cloud API (distinto de `enviar_codigo_whatsapp()` en `utils/verificacion.py`, que manda un template pre-aprobado — este no necesita template porque responde dentro de la ventana de 24hs de una conversación que inició el usuario).
2. **`database.py`, migración `2v`:** tabla nueva `whatsapp_consultas_sin_responder` (id, telefono, mensaje, respondida, created_at) — donde caen las consultas que el bot no supo responder, para revisión manual (no hay pantalla de Admin para verlas todavía, queda pendiente).
3. **`app.py`:** registrado `whatsapp_bot.bp`.
4. Verificado con `py_compile` (sintaxis OK) y con un test manual de `buscar_respuesta()` con 4 mensajes de prueba — matchearon bien las 3 preguntas reales y la 4ta (sin sentido) devolvió `None` como se esperaba.

**Variables de entorno que van a faltar en Railway cuando el número esté aprobado** (ninguna cargada todavía):
- `WHATSAPP_TOKEN`
- `WHATSAPP_PHONE_ID`
- `WHATSAPP_VERIFY_TOKEN` (Daniel elige cualquier string, se lo repite a Meta al configurar el webhook)

**Archivos tocados:** `routes/whatsapp_bot.py` (nuevo), `database.py`, `app.py`.
**Pendiente:**
- Commitear y deployar (comando abajo). El código no rompe nada de lo existente: sin las 3 variables de entorno, el bot simplemente no puede responder (mismo patrón que `whatsapp_configurado()`).
- Una vez que Meta apruebe el negocio y se dé de alta el número: configurar el webhook en Meta Business Manager apuntando a `https://presupuestopro.com.ar/webhook/whatsapp` (o la URL de Railway), cargar las 3 variables en Railway, y probar en vivo con un mensaje real.
- Pantalla en Admin para ver/marcar como respondidas las filas de `whatsapp_consultas_sin_responder` (no existe todavía).
```bash
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add routes/whatsapp_bot.py app.py database.py
git commit -m "feat: bot de FAQ por WhatsApp (webhook Cloud API, matching por palabras clave, fallback a whatsapp_consultas_sin_responder)"
git push
```

### Sesión 14/07/2026 — Datos legales publicados en el sitio (bloqueante para verificación Meta Business) ✅ COMMITEADO Y PUSHEADO (confirmado 15/07/2026, commit `3df2d75`, `origin/main` = `HEAD`)
En el proyecto paralelo `CHATBOT_WHATSAPP_BUSINESS` se detectó que el sitio no tenía ningún dato legal publicado (razón social, CUIT, dirección, contacto) ni páginas de Términos/Privacidad — esto traba la verificación de Meta Business Manager, que exige que esos datos coincidan entre Meta y el sitio.
**Hecho:**
- Footer de `templates/landing.html`: agregado bloque con "PresupuestoPRO — Daniel Vega — CUIT 23-14055838-9 · Milstein 2652, Roldán, Santa Fe, Argentina · presupuestopro.app@gmail.com" + links a Términos y Privacidad.
- Nuevas páginas `templates/terminos.html` y `templates/privacidad.html` (rutas `GET /terminos` y `GET /privacidad` en `routes/landing.py`).
- Fix del bug ya documentado (sesión 06/07): `contacto()` redirigía a `/landing` (ruta borrada) → ahora redirige a `/?contacto_ok=1#contacto`.
- Confirmado: el dominio ya tiene la meta tag de verificación de Facebook (`meta-facebook-domain-verification`), así que ese paso ya estaba resuelto.
**Archivos tocados:** `templates/landing.html`, `templates/terminos.html` (nuevo), `templates/privacidad.html` (nuevo), `routes/landing.py`.
**Pendiente:** verificar que `presupuestopro.com.ar/terminos` y `/privacidad` respondan en producción (deploy automático de Railway tras el push); después reintentar/completar la verificación de Meta Business Manager con esos mismos datos (razón social Daniel Vega, CUIT 23-14055838-9, domicilio Milstein 2652 Roldán, email presupuestopro.app@gmail.com).

### Sesión 13/07/2026 (cont. 15) — 2 bugs reales más en el dropdown de Localidad ⚠️ SIN COMMITEAR
Daniel mandó capturas (PC + celu) confirmando que el fix de cont. 14 SÍ está deployado (verificado con `git fetch`: `origin/main` = `HEAD` = commit `5fac7f0`), pero el dropdown propio tenía 2 bugs reales de mi implementación:
1. **Clickear el campo vacío no mostraba nada.** El JS solo abría el dropdown si ya había texto tipeado (`input`/`focus` chequeaban `input.value.trim()`). ✅ Fix: con el campo vacío, foco o borrar todo el texto ahora muestran la lista completa de localidades (como un `<select>` nativo al abrirlo).
2. **Localidades que matcheaban la letra podían no aparecer.** `render()` cortaba a los primeros 30 resultados (`.slice(0, 30)`) — si había más de 30 matches alfabéticos, los que venían después (alfabéticamente) del puesto 30 nunca se mostraban. ✅ Fix: se sacó el corte — el dropdown ya es scrolleable (`max-height:220px`), no hace falta limitarlo.

**Archivo tocado:** `templates/admin/usuarios.html`.
**Pendiente:** commitear vía Git Bash y deployar; Daniel prueba: (a) click en el campo vacío muestra la lista completa, (b) tipear una letra con muchos matches (ej. "a") muestra TODAS las localidades que la contienen, no solo las primeras alfabéticas.
```bash
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add templates/admin/usuarios.html
git commit -m "fix: dropdown Localidad — mostrar lista completa en foco/campo vacio, sacar el corte de 30 resultados que ocultaba matches"
git push
```
✅ **CONFIRMADO 13/07/2026 por Daniel: "Anda perfecto".** El dropdown de Localidad en Admin > Usuarios queda resuelto (foco vacío muestra lista completa, sin corte de 30 resultados). Con esto se da por cerrado todo el bloque de bugs de Admin > Usuarios de esta sesión (encabezado fijo mobile, orden alfabético, autofill de Chrome, foco vacío/corte de 30).

**Estado de "conectar WhatsApp Business" al cierre de esta sesión (13/07/2026):**
- ✅ Perfil personal (celu): foto, descripción, migración del número y WhatsApp Web — todo confirmado hecho por Daniel.
- ✅ Resuelto en PC: se puede tener el WhatsApp Desktop (personal, 7371) y una pestaña de `web.whatsapp.com` vinculada a WhatsApp Business (PP) al mismo tiempo — son clientes separados.
- ⏳ **Sigue pendiente:** el trámite de Meta Cloud API (verificar negocio en Meta Business Manager, dar de alta el número 341 754-2009, template de autenticación, tokens) — no se arrancó todavía, quedó para retomar en el próximo chat.

## 📅 Hitos del proyecto (confirmado 11/07/2026 con capturas del chat original)
- **Inicio:** 17/06/2026 23:24 ART — primer mensaje de Daniel compartiendo el Excel de presupuestos para revisar. El mensaje que Daniel marcó como "acá empezamos" (arranque formal de la idea de la app) fue 18/06/2026 00:06 ART.
- **Primer deploy a producción:** 25/06/2026 08:49 ART (primer commit "Initial deploy setup").
- **Dominio propio funcionando:** 30/06/2026 (presupuestopro.com.ar).
- **Lanzamiento:** 01/07/2026 — publicaciones en Facebook e Instagram.

## Identidad de marca (usar siempre en piezas gráficas)
- **Nombre:** PresupuestoPRO (Presupuesto en blanco + PRO en naranja `#F97316`)
- **Logo:** escudo con grúa — archivo de referencia `IMAGENES/LOGO SOLO limpio v3.png` (fondo transparente)
- **Slogan:** "De los metros a los pesos, en minutos."
- **Pieza de referencia para layout de marca:** `IMAGENES/Portada_Facebook_1640x856_v2.png` (logo arriba + wordmark + slogan, fondo azul oscuro degradado)
- Cualquier lámina/gráfica nueva debe llevar los 3 elementos (logo + nombre + slogan) en el encabezado, con esta misma composición.

## Credenciales admin
- Login app (`/admin`): `admin@presupuestopro.com` / `admin1234` (`is_admin=1`, creado en `init_db()` de `database.py`)

## Stack
- Flask + Python 3.11 · SQLite en `/data/presupuestopro.db` · Railway (US West)
- Repo: `danielvega-inmobiliaria/presupuestopro` (branch `main`)
- URL prod: `https://web-production-0c9c1.up.railway.app`
- Dominio: `presupuestopro.com.ar` (comprado en NIC.ar, DNS gestionado por **Cloudflare**)
- Carpeta local: `D:\ESCRITORIO\CLAUDE\APP_PRESUPUESTOPRO`

---

## ⚠️ REGLA CRÍTICA DE COMMITS (NUNCA ignorar)
El bash (FUSE mount) ve versiones **stale** de archivos Windows.
- **NUNCA commitear `database.py` desde bash** — tiene mojibake
- Archivos editados desde Windows (Edit tool) → commitear desde **Git Bash del usuario**
- Comando para limpiar lock si hay problemas: `rm -f .git/index.lock` (Git Bash, no CMD)

```bash
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add <archivo1> <archivo2>   # usar / no \
git commit -m "descripción"
git push
```

---

## ⚠️ REGLA — Features nuevas vs. fixes, dónde se prueban (definido 10/07/2026)
- **Fix de un cálculo/bug en algo que ya existe** (ej. el fix de Costo/m2 del 10/07) → directo a la versión actual en producción, como veníamos haciendo.
- **Feature nueva** (algo que la app no hace hoy: cálculo de escaleras, WhatsApp Business, proveedores zonales, etc.) → **primero se prueba en una versión paralela**, no se toca la producción actual hasta que esté validada.
- **Mecanismo definido 10/07/2026 (cont. 9):** branch de git aparte (ej. `dev`) + un 2do servicio en Railway apuntando a ese branch, con su propia URL de prueba y su propia base de datos. Producción (`main`) queda intacta mientras se prueba. Cuando la feature esté validada, se mergea `dev` → `main`. **Falta:** crear el branch `dev` y dar de alta el 2do servicio en Railway (queda para cuando arranque la primera feature nueva de la lista).
- **Excepción aplicada 10/07/2026 (validación de cuenta + cómo-conoció + localidad/provincia):** se shippeó directo a producción en vez de armar la versión paralela, PERO detrás de un feature flag apagado (`config.verificacion_activa='0'`) — el código convive con producción sin cambiar el comportamiento hasta que Daniel lo prenda a mano desde Admin. Este patrón (flag apagado por default) es una alternativa válida a la versión paralela cuando el cambio se puede aislar así; usarlo quirúrgicamente, no como regla general.

## ⚠️ REGLA — Mantener el Manual del Usuario al día (definido 12/07/2026, cont. 14)
Cada vez que un cambio en la app toque algo que el Manual del Usuario (`templates/manual.html`) describe o debería describir (flujo de registro, login, wizard de presupuesto, Costo/m², Mi Empresa, instalación PWA, etc.), corregir/actualizar el Manual en el mismo momento — no esperar a que Daniel pregunte.
- Si el cambio de la sesión modificó algo relevante para el Manual: avisar explícitamente qué se actualizó ahí, para que Daniel lo commitee junto con el resto (un solo commit, como pidió).
- Si el cambio fue interno/admin (no afecta lo que ve o hace un usuario común, ej. fixes solo en `/admin`), aclarar que el Manual no aplica en ese caso — para que quede claro que no se lo pasó por alto.

---

## Variables de entorno en Railway
| Variable | Estado |
|---|---|
| `RESEND_API_KEY` | ✅ Configurada |
| `MP_ACCESS_TOKEN` | ✅ **PRODUCCIÓN** (`APP_USR-...`) — confirmado por captura de Railway 10/07/2026 |
| `MP_PUBLIC_KEY` | ✅ **PRODUCCIÓN** (`APP_USR-...`) — confirmado por captura de Railway 10/07/2026 |
| `MP_APP_ID` | ✅ Configurada (3111479646589398) |
| `MP_PRECIO_ARS` | ✅ Configurada (12500) |
| `APP_BASE_URL` | ✅ Configurada |
| `SECRET_KEY` | ✅ Configurada |
| `ADMIN_EMAIL` | ✅ Seteada a `presupuestopro.app@gmail.com` en Railway (confirmado por Daniel, ya le llegó) |

### Sesión 06/07/2026 — Borrado de la landing vieja (código muerto en routes/landing.py)
- Instrucción que venía del hilo de marketing (mismo repo, chat aparte): confirmar que el Reply-To seguía sin commitear (confirmado: sí, seguía pendiente) y borrar la landing vieja obsoleta en `routes/landing.py` — la variable `LANDING_HTML` (~300 líneas de HTML embebido) + la vista `landing()` (`GET/POST /landing`) + el helper `_render()`, con un formulario de pago directo por Mercado Pago que no corresponde al modelo actual (lanzamiento gratis). Visible en `web-production-0c9c1.up.railway.app/landing`, sin ningún link real del sitio apuntando ahí — la landing real y en uso es `templates/landing.html`, servida por `dashboard.index()`.
- **Hecho:** eliminados `LANDING_HTML`, `_render()`, `landing()` y `PROVINCIAS_AR` (solo se usaba ahí). Limpiados los imports que quedaban sin uso (`current_app`, `render_template_string`, `session`, `url_for`, `generate_password_hash` de werkzeug, `login_user` de utils.auth). Se conservó `contacto()` intacta, sin tocar una sola línea, tal como se pidió explícitamente. Confirmado con grep en toda la app que nada más referencia `PROVINCIAS_AR`, `LANDING_HTML` ni el endpoint `landing.landing` — el borrado es seguro.
- **⚠️ Punto pendiente de confirmar con Daniel (no se tocó, por respetar "no tocar contacto()"):** `contacto()` termina con `return redirect('/landing?contacto_ok=1#contacto')` — esa ruta ya no existe. Hoy no importa porque ningún template llama a `/contacto` (se confirmó con grep que `templates/landing.html` actual NO tiene ningún formulario apuntando ahí), pero el día que se conecte un formulario de contacto real a este endpoint, ese redirect va a dar 404 en vez de volver a la home con el cartel de "mensaje enviado". Fix de una línea cuando se confirme: cambiar el redirect a `/?contacto_ok=1#contacto` (la home real).
- **Archivo tocado:** `routes/landing.py` (reescrito completo, de ~457 a 84 líneas).
- **Pendiente:** commitear (junto con el Reply-To de la sesión anterior, que sigue sin subir) y deployar; probar que `web-production-0c9c1.up.railway.app/landing` ya no responde (404 o vacío) y que el resto del sitio (`/`, `/contacto` si se usa) sigue funcionando igual.

### Sesión 05/07/2026 (cont. 10) — Reply-To en notificaciones por email
- Daniel confirmó que `ADMIN_EMAIL=presupuestopro.app@gmail.com` ya funciona. Preguntó si al responder una notificación la respuesta le llega al usuario o a noreply@ — no llegaba a nadie útil: ninguno de los 6 envíos de email (`sugerencias.py`, `landing.py::contacto`, `dashboard.py::_enviar_notificacion` leads, `pagos.py` x2, `auth.py` recuperar contraseña) tenía `reply_to` seteado, así que un Reply iba a `noreply@presupuestopro.com.ar` (nadie lo lee).
- **Fix aplicado (Reply-To al email del usuario/contacto/inscripto) en las 3 notificaciones que tienen sentido:**
  - `routes/sugerencias.py::_enviar_notificacion()`: `reply_to = [user['email']]` si existe.
  - `routes/landing.py::contacto()`: `reply_to = [email]` (el que cargó en el form de contacto) si existe.
  - `routes/dashboard.py::_enviar_notificacion()` (leads/inscriptos): `reply_to = [email]` si existe.
  - No se tocó `pagos.py` ni `auth.py` (esos mails van del sistema al usuario, no son notificaciones al admin que tenga sentido "responder").
  - Aclarado a Daniel: el Reply-To solo autocompleta el "Para" al tocar Responder — el mail de respuesta sale igual desde su casilla real (`presupuestopro.app@gmail.com`), no desde noreply@.
- **Archivos tocados:** `routes/sugerencias.py`, `routes/landing.py`, `routes/dashboard.py`.
- **Pendiente:** commitear y deployar; probar: escribir un mensaje de contacto/sugerencia con un email de prueba, y confirmar que al tocar "Responder" en el mail de notificación el campo "Para" ya viene con ese email (no con noreply@).

---

## Email — Estado ✅
- Dominio `presupuestopro.com.ar` verificado en Resend (29/06/2026)
- Todos los emails salen como `PresupuestoPRO <noreply@presupuestopro.com.ar>`
- DNS Cloudflare: MX, DKIM, SPF y DMARC configurados y verificados
- Emails a usuarios externos (hotmail, gmail, etc.) funcionan correctamente

## Dominio — Estado ✅ FUNCIONANDO (30/06/2026)
- `presupuestopro.com.ar` resuelve y muestra la landing correctamente
- NIC.ar registrar → DNS gestionado por Cloudflare → apunta a Railway
- CNAME `@` configurado en Cloudflare con proxy OFF (DNS only)

---

## Schema DB

### Tabla `users`
```
id, email, password_hash, nombre, pais, active,
subscription_expires, session_token, session_expires,
is_admin, created_at, mp_preapproval_id,
apellido, telefono, ciudad, provincia
```

### Tabla `items_obra`
```
id, rubro_num, rubro_nombre, nombre, unidad, precio_ars,
precio_mo_ars, hof, hay, orden, m2_factor
```
- `hof`: horas oficial por unidad (m3, m2, etc.)
- `hay`: horas ayudante por unidad
- `m2_factor`: factor conversión m3→m2 (NULL = sin conversión). Ej: pared 30cm → 0.30

### Tabla `analisis_sub`
```
id, item_nombre, sub_nombre, cant_por_unit, precio_ars, es_material
```
- Materiales y MO desglosados por ítem
- Poblada por `_actualizar_mo_analisis()` leyendo el Excel en `/data/`
- **⚠️ El Excel no está en Railway** → analisis_sub está VACÍA en producción

---

## Tarifa de jornales en la app
| Rol | Por hora | Por día (8hs) |
|---|---|---|
| Oficial | $10.000 | $80.000 |
| Ayudante | $5.000 | $40.000 |

Usadas en: cálculo de `precio_mo_ars`, feature COSTO/M2, presupuesto.

---

## Features implementadas

### Pagos / Suscripción (`routes/pagos.py`) — Actualizado 03/07/2026
- Integración Mercado Pago Preapproval (suscripciones automáticas)
- Rutas: `/pagos/planes`, `/pagos/crear-suscripcion`, `/pagos/retorno`, `/pagos/webhook`, `/pagos/estado`
- Tabla `suscripciones` en DB + columna `users.mp_preapproval_id`
- `_activar_suscripcion()`: extiende `subscription_expires` +30 días, activa `users.active=1`
- `_cancelar_suscripcion()`: marca estado='cancelled' en tabla suscripciones
- Webhook en `/pagos/webhook` (público, sin auth) — procesa `subscription_preapproval`
- Página `/pagos/planes` muestra precio desde `MP_PRECIO_ARS` ($12.500 ARS/mes actual)
- **Credenciales actuales:** sandbox/TEST (para cambiar a producción: reemplazar tokens en Railway)
- Admin: admin@presupuestopro.com / admin1234

### Admin (`routes/admin.py`)
- `usuario_enviar_activacion`: auto-setea `subscription_expires = hoy+30d` si es NULL antes de enviar
- `usuario_nuevo`: template recibe `now_date` y `timedelta` para default de fecha

### Presupuesto — Paso 2 (`templates/presupuesto/paso2_rubros.html`)
- Inputs de cantidad: `type="text" inputmode="decimal"` (soporte coma en Android)
- Función `normVal(v)` normaliza coma → punto antes de parsear
- Submit listener convierte todas las comas a puntos antes de enviar el form

### Dashboard (`templates/dashboard.html`)
- Botón "Costo/m²" junto a "Nuevo presupuesto" → `url_for('costo_m2.index')`

---

## Feature COSTO/M2 — Estado actual (30/06/2026)

### Cómo funciona
1. Usuario selecciona un ítem de la lista (radio button, un solo ítem a la vez)
2. Se abre ventana nueva con el resultado calculado
3. Los jornales son editables; recalcula en tiempo real (evento `input`)

### Archivos
- `routes/costo_m2.py` — Blueprint en `/costo-m2/`
- `templates/costo_m2/index.html` — lista de ítems agrupados por rubro
- `templates/costo_m2/resultado.html` — ventana de resultado
- Registrado en `app.py`: `app.register_blueprint(costo_m2.bp)`

### Lógica de conversión m3→m2
```python
# Si item tiene m2_factor y unidad='m3':
display_unit = 'm2'
factor_conv  = m2_factor  # e.g. 0.30 para pared de 30cm
mo_per_m2    = (hof × jornal_hora_of + hay × jornal_hora_ay) × factor_conv
mat_per_m2   = cant_por_unit × factor_conv  (para cada material)
```

### Cálculo completo en resultado.html
```
MO/m2          = (hof × jo_hs + hay × ja_hs) × factor_conv
MAT/m2         = suma(cant × precio) × factor_conv  [de analisis_sub]
costo_directo  = MO + MAT
Beneficio      = costo_directo × pct_gg   (default 10%, editable)
Seguros        = costo_directo × pct_imp  (default 5%, editable)
TOTAL          = costo_directo + Beneficio + Seguros
```

### UI de resultado.html
- **Tarjeta azul**: valor TOTAL único (MO + MAT + adicionales), sub-líneas MO y MAT
- **Tarjeta verde**: costo de materiales/m2 (solo si total_mat > 0)
- **Adicionales editables**: Beneficio % y Seguros %
- **Tabla desglose**: Material | Cant | $ | Costo Comercial (solo si hay analisis_sub)
- Sin botón Recalcular — recalcula al escribir

### Items con m2_factor configurado
| Ítem | Factor |
|---|---|
| Demolicion mamposteria 0,15 | 0.15 |
| Demolicion mamposteria 0,30 | 0.30 |
| Relleno y Compactacion C/15cm | 0.15 |
| H.Elab. tabique 10cm (110-20) | 0.10 |
| H.Elab. tabique 15cm (110-13) | 0.15 |
| H.Elab. losa 10cm (80-10) | 0.10 |
| H.Elab. losa 15cm (75-6.66) | 0.15 |
| Mamp. ladrillo comun 15cm | 0.15 |
| Mamp. ladrillo comun 30cm | 0.30 |
| Mamp. ladrillo vista 15cm | 0.15 |
| Mamp. ladrillo vista 30cm | 0.30 |

---

## ✅ RESUELTO (confirmado 10/07/2026, cont. 9) — HH y materiales incorrectos
Esta sección quedó desactualizada: describe el estado ANTES del fix. El "Fix a implementar (próximo chat)" de más abajo se hizo — quedó documentado en el historial de migraciones (`2h`, `2m`, `2n`, `2o`, `2p`, `2q`, `2r`, ver sección "Migraciones en database.py" al final del archivo) y **verificado por Daniel contra Excel real** (sesión 04/07/2026, cochera de Ezequiel Petrini): MO coincide EXACTO con el Excel ($5.902.594) y Costo Directo quedó ~1.3% cerca (diferencia considerada tolerable por Daniel). Se deja el detalle original abajo como registro histórico, no como pendiente activo.

## ~~PROBLEMA CRÍTICO PENDIENTE~~ (histórico, ver nota de arriba) — HH y materiales incorrectos

### Root cause
El Excel `PRESUPUESTO HOTMART.xlsx` (hoja "Análisis") NO está en Railway (`/data/`).
La migración `_actualizar_mo_analisis()` lo busca ahí, no lo encuentra, y usa el fallback hardcodeado.

**Consecuencias:**
1. `analisis_sub` está VACÍA → no hay desglose de materiales en COSTO/M2
2. Los valores `hof`/`hay` iniciales en `init_db()` son **incorrectos** para varios ítems

### Ejemplo concreto verificado: Mamp. ladrillo comun 30cm
| | Valor en código (fallback) | Valor real del Excel |
|---|---|---|
| hof (hs oficial/m3) | 22.0 | **9.40** |
| hay (hs ayudante/m3) | 11.0 | **4.70** |
| MO/m2 resultante | $82.500 ❌ | **$35.250** ✓ |

### Materiales del Excel para este ítem (por m3):
| Material | Cant | Precio | Total |
|---|---|---|---|
| Ladrillos comunes | 400 | $230 | $92.000 |
| Cemento Albañilería | 67 | $296 | $19.832 |
| Arena común | 0.50 | $31.000 | $15.500 |
| **MAT/m3 total** | | | **$127.332** |
| **MAT/m2 (×0.30)** | | | **$38.200** |

Con valores correctos:
- MO/m2 = $35.250 · MAT/m2 = $38.200 · Total = $73.450 × 1.15 = **$84.468**

### Fix a implementar (próximo chat)
**Hardcodear en `database.py`** todos los datos del Excel como SQL estático:
- Corregir `hof`/`hay` en `init_db()` para todos los ítems (via migración 2h que haga UPDATE)
- Poblar `analisis_sub` directamente en la migración con los materiales reales
- Así la app es autosuficiente sin depender del Excel en Railway

Para esto se necesita el Excel completo (o los datos de todos los ítems con sus HH y materiales).

---

### Sesión 10/07/2026 (cont. 6) — Bug de validación por WhatsApp + limpieza de usuarios de prueba ⚠️ SIN COMMITEAR
Daniel probó el switch de validación con una cuenta nueva eligiendo WhatsApp. Reportó dos cosas:
1. **Bug encontrado probando en producción:** eligió validar por WhatsApp, la pantalla decía "te mandamos el código por WhatsApp al 341 3412325" pero el código llegó por EMAIL (WhatsApp real sigue sin funcionar, cae a email automático). Causa raíz: el fallback whatsapp→email nunca actualizaba `users.metodo_verificacion` en la DB, así que `validar_cuenta` seguía comparando el código ingresado contra canal='whatsapp' en vez de 'email' — **el código correcto quedaba imposible de validar**. Bloqueaba a cualquiera que eligiera WhatsApp mientras no esté Meta configurado. ✅ **Fix aplicado** en `routes/landing.py` (alta y reenvío de código): ahora persiste el canal real en la DB cuando hay fallback.
2. **Ocultar la opción "Por WhatsApp" hasta tener Meta configurado** (pedido explícito de Daniel, para no repetir el problema con usuarios reales): ✅ agregada `utils/verificacion.py::whatsapp_configurado()` (chequea `WHATSAPP_TOKEN`/`WHATSAPP_PHONE_ID`). `templates/registro.html` ahora oculta el radio "Por WhatsApp" y fuerza `metodo_verificacion=email` (input hidden) mientras esas variables no estén en Railway. **Se reactiva solo** el día que Daniel cargue esas 2 variables — no hace falta tocar código de nuevo.
3. **Pedido: limpiar usuarios ficticios de prueba** — no existía ninguna forma de borrar usuarios desde Admin. ✅ agregado botón "Eliminar" (ícono tacho, confirmación con `confirm()`) en cada fila de **Admin > Usuarios**, ruta `POST /admin/usuarios/<id>/eliminar` (`routes/admin.py::usuario_eliminar`). Borra en cascada presupuestos, suscripciones, consultas de costo/m2, sugerencias, perfil de empresa, tokens de reset y códigos de verificación del usuario, antes de borrar la fila de `users`. Bloqueado para cuentas admin (no se puede autoeliminar ni eliminar otro admin desde ahí). Irreversible, sin papelera — la confirmación lo aclara.

**Archivos tocados:** `routes/landing.py`, `routes/admin.py`, `templates/admin/usuarios.html`, `templates/registro.html`, `utils/verificacion.py`.
**Pendiente:** commitear vía Git Bash y deployar; luego Daniel: (a) usar el botón nuevo de Eliminar para borrar las cuentas de prueba que ya cargó, (b) prender el switch de validación de nuevo (esto valida automáticamente cualquier cuenta que haya quedado a medio validar) y (c) registrar una cuenta de prueba nueva para confirmar que ahora sí valida bien por email.
```
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add routes/landing.py routes/admin.py templates/admin/usuarios.html templates/registro.html utils/verificacion.py
git commit -m "fix: persistir canal real en fallback whatsapp->email + ocultar opcion WhatsApp hasta configurar Meta + boton eliminar usuario en Admin"
git push
```

### Sesión 10/07/2026 (cont. 7) — Admin > Usuarios: encabezado fijo, filtros fijos + auto-filtrado, contadores por nivel ⚠️ SIN COMMITEAR (último cambio de la sesión)
1. **Encabezado de tabla fijo al scrollear** — 1er intento con `position: sticky` en los `<th>` tuvo un bug de ghosting/tearing (típico de sticky dentro de `.table-responsive`, overflow-x:auto). ✅ **Commiteado y funcionando** (confirmado por Daniel) con 2do enfoque: clon del `<thead>` en un `<div id="thead-clon">` aparte con `position:fixed`, sincronizado por JS (ancho de columnas + mostrar/ocultar según scroll).
2. **Formulario de filtros (Localidad/Provincia/País) también fijo al scrollear** — ✅ commiteado, `position: sticky` normal (sin el bug de arriba porque no está dentro de `.table-responsive`). El clon del encabezado de la tabla se posiciona debajo del navbar + del formulario de filtros.
3. **Bug reportado por Daniel — "el filtro no cambia nada":** no era bug, no estaba tocando el botón "Filtrar" (probó escribiendo/seleccionando sin enviar el form). Confirmado con captura que el filtro sí funciona.
4. **Simplificación pedida por Daniel a partir de eso:** sacar el botón "Filtrar" (auto-enviar el form al cambiar cualquier campo), achicar las 3 columnas para que entren en una sola línea, y mostrar la cantidad de usuarios al lado de cada label (Localidad/Provincia/País) en vez de un cartel aparte de "también en". ✅ **implementado, todavía sin commitear:**
   - `routes/admin.py::usuarios()`: variable `contadores` (dict con `ciudad`/`provincia`/`pais`) — cada nivel se infiere del más específico que esté activo si no fue elegido explícitamente (ciudad → su provincia más frecuente; provincia → su país más frecuente), tomando el valor más frecuente entre los usuarios que matchean por si hay datos mezclados.
   - `templates/admin/usuarios.html`: columnas Localidad/Provincia/País pasan a `col-md-4/4/3` + ícono chico de "Limpiar" (`col-md-1`), sin botón Filtrar visible (queda un `<button class="visually-hidden">` para accesibilidad/Enter). Badge con la cantidad al lado de cada label. JS nuevo: `change` en los 3 campos hace `requestSubmit()` automático.

**Archivos tocados (acumulado de toda la sesión "cont. 7"):** `templates/admin/usuarios.html`, `routes/admin.py`.
**Pendiente:** commitear vía Git Bash y deployar; Daniel prueba: (a) que auto-filtra al elegir Provincia/País y al tabular fuera de Localidad, (b) que los contadores calculan bien en combinaciones (solo ciudad, solo provincia, ciudad+provincia explícita, etc.), (c) que "Limpiar" resetea los 3 campos.
```
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add templates/admin/usuarios.html routes/admin.py
git commit -m "feat: auto-filtrar usuarios sin boton (change event), contadores por nivel geografico al lado de cada campo"
git push
```

### Sesión 10/07/2026 (cont. 8) — Admin > Usuarios: contador total + nombre de provincia/país inferido ⚠️ SIN COMMITEAR
Retomando el pendiente de "cont. 7" (auto-filtrado + contadores), Daniel pidió 2 ajustes puntuales antes de commitear:
1. **El badge "Usuarios" del encabezado tiene que marcar siempre el TOTAL de la base**, no la cantidad de filas que quedan después de filtrar (eso ya lo dice la tabla misma). Antes usaba `{{ users|length }}` (filtrado). ✅ **Fix:** `routes/admin.py::usuarios()` ahora calcula `total_usuarios` (COUNT sin filtros, is_admin=0) y lo pasa al template; `templates/admin/usuarios.html` usa `{{ total_usuarios }}` en el badge del `<h4>`.
2. **Al elegir una ciudad, mostrar también el nombre de la provincia/país inferidos**, no solo la cantidad. El backend (`contadores.provincia.nombre` / `contadores.pais.nombre`, de la sesión "cont. 7") ya calculaba el nombre pero el template no lo mostraba. ✅ **Fix:** al lado del badge de cantidad se agrega el nombre en texto muted — pero **solo cuando ese nivel está inferido, no elegido explícitamente** (`{% if not f_provincia %}` / `{% if not f_pais %}`), para no duplicar lo que ya se ve en el `<select>` cuando Daniel elige Provincia/País a mano.

**Archivos tocados (sesión completa "cont. 8"):** `routes/admin.py`, `templates/admin/usuarios.html`.
**Pendiente:** commitear vía Git Bash y deployar (incluye también el auto-filtrado + contadores de "cont. 7", que seguía sin commitear); Daniel prueba: (a) que "Usuarios" arriba siempre muestra el total aunque haya filtro aplicado, (b) que al elegir solo una Localidad aparece el nombre de la provincia y el país correspondientes al lado de sus contadores, (c) que si además elige Provincia o País a mano desde el `<select>`, no se duplica el nombre (el select ya lo muestra).
```bash
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add routes/admin.py templates/admin/usuarios.html
git commit -m "feat: badge Usuarios muestra total fijo + nombre de provincia/pais inferido junto al contador"
git push
```

### Sesión 11/07/2026 (cont. 11) — Cambiar contraseña propia (self-service) ⚠️ SIN COMMITEAR
Daniel vio en Chrome que la contraseña de `admin@presupuestopro.com` (`admin1234`) aparece en una filtración de datos conocida y hay que cambiarla. Al revisar, la app **no tenía ninguna forma de cambiar la propia contraseña estando logueado** — solo existía el flujo "olvidé mi contraseña" (`/recuperar`) que manda un link por email, y no está garantizado que `admin@presupuestopro.com` reciba correo (el dominio verificado en Resend es `presupuestopro.com.ar`, no `presupuestopro.com`).
- ✅ **Agregado:** `routes/perfil.py::cambiar_password()` (`GET/POST /perfil/cambiar-password`) — pide contraseña actual + nueva (2 veces), valida mínimo 6 caracteres y que coincidan, y actualiza `password_hash` del usuario logueado (`g.user`, sirve para cualquier cuenta, incluida la de admin).
- ✅ Template nuevo `templates/perfil/cambiar_password.html`.
- ✅ Link "Cambiar contraseña" agregado al menú desplegable del usuario en `templates/base.html`, junto a "Mi empresa".
- ✅ **Fix de paso:** `perfil.ver()` no le pasaba `user` al template — sin eso, el navbar no se mostraba en la página "Mi empresa". Corregido.

**Archivos tocados:** `routes/perfil.py`, `templates/perfil/cambiar_password.html` (nuevo), `templates/base.html`.
**Pendiente:** commitear vía Git Bash y deployar; después Daniel: entra con la cuenta admin → menú de usuario (arriba a la derecha) → "Cambiar contraseña" → cambia `admin1234` por algo fuerte y único.
```bash
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add routes/perfil.py templates/perfil/cambiar_password.html templates/base.html
git commit -m "feat: cambiar contraseña propia (self-service) desde el menú de usuario + fix navbar en Mi empresa"
git push
```
✅ **CONFIRMADO 12/07/2026 (cont. 12):** commit `f9ca0e6` es el HEAD actual de `main`, pusheado — esta feature y todo lo anterior (cont. 6/7/8) están en producción. Daniel probó cambiar la contraseña y funciona bien.

### Sesión 12/07/2026 (cont. 12) — Feedback de Daniel probando en producción + arranque WhatsApp Business
1. **Cambiar contraseña propia** ✅ probado por Daniel, funciona bien.
2. **Validación de cuenta por email** ✅ probado por Daniel, valida bien (fix del fallback WhatsApp→email confirmado en producción).
3. **Admin > Usuarios (auto-filtro + contadores)** ✅ funciona, pero Daniel reportó 2 problemas **solo en mobile**:
   - 🐞 **Encabezado/menú fijo desaparece al hacer scroll en celu** (en desktop sí queda fijo). Pendiente de fix — revisar el JS del clon de `<thead>` (`position:fixed`, sincronizado por scroll) en viewport mobile.
   - 🐞 **Sugerencias de Localidad (datalist) se muestran en horizontal (3 visibles) arriba del teclado en mobile.** Daniel pidió que se muestren en **vertical y ordenadas alfabéticamente** para elegir más fácil. Nota técnica a validar: el orden de opciones sí lo controlamos (query del backend), pero el layout horizontal/vertical de la barra de sugerencias sobre el teclado es una UI nativa del navegador/Android sobre `<datalist>` — puede no ser 100% controlable por CSS; evaluar alternativa (dropdown propio en JS) si el navegador no cede el layout.
4. **Contenido de marketing sin commitear** (carrusel, historias de origen, docx) — Daniel confirmó: **queda para el chat/proyecto de Marketing**, no se toca acá.
5. **Expansión Regional** — Daniel avisa cuando esté terminada esa investigación para evaluar integrarla a la app.
6. **Arranca el trabajo de conectar WhatsApp Business** (siguiente tema de este chat).

**Pendiente:** decidir con Daniel por dónde arrancar dentro de "conectar WhatsApp Business" (terminar perfil personal del celu vs. trámite Meta Business Manager vs. los 2 bugs de Admin > Usuarios reportados arriba).

### Sesión 12/07/2026 (cont. 13) — Fix de los 2 bugs mobile de Admin > Usuarios + botón de instalación PWA + Manual actualizado
Daniel eligió arrancar por los 2 bugs reportados antes de seguir con WhatsApp Business.

1. **Datalist de Localidad — orden alfabético + layout vertical.** Root cause: `routes/admin.py::usuarios()` ordenaba `localidades_lista` por `veces_usada DESC` (frecuencia de uso, no alfabético) — ✅ cambiado a `ORDER BY nombre_display COLLATE NOCASE ASC`. Además, la tira horizontal de 3 sugerencias arriba del teclado en mobile era el `<datalist>` nativo del navegador (Chrome/Android dibuja esa UI, no se puede forzar vertical por CSS) — ✅ reemplazado por un dropdown propio en JS (`templates/admin/usuarios.html`): lista vertical, con scroll, ya alfabética desde el backend, con click para seleccionar.
2. **Encabezado de tabla fijo que desaparecía en mobile al scrollear.** Root cause: el enfoque anterior (clon de `<thead>` con `position:fixed` + JS de scroll/resize) dependía de recalcular la posición contra el scroll de toda la página — poco confiable en mobile con teclado virtual y cambios de viewport. ✅ **Reescrito con el patrón estándar** de tabla con scroll propio: `.table-responsive` pasa a tener `max-height: 65vh; overflow-y: auto` y el `<thead>` usa `position: sticky; top: 0` normal, DENTRO de ese contenedor (no de la página). Se eliminaron ~90 líneas de JS frágil (el clon + los listeners de scroll/resize).
3. **Botón de instalación PWA (pedido nuevo, ligado al Punto 10 del Manual).** Agregado en `templates/base.html`: ítem "Instalar app" en el menú de usuario (oculto si la app ya corre instalada/standalone). Captura `beforeinstallprompt` → en Android/Chrome/desktop dispara el instalador nativo del navegador. iOS Safari no tiene ese evento (no lo soporta), así que ahí el botón abre un modal (`#modalInstalarApp`) con los mismos pasos que el Manual.
4. **Manual del Usuario actualizado** (`templates/manual.html`) para reflejar el estado real de la app:
   - Corregido dato **erróneo**: Costo/m² decía que los jornales "no son editables" — en realidad sí lo son y recalculan en vivo (fix del 07/07/2026, el manual había quedado desactualizado).
   - Agregado: campo "cómo nos conociste" en el registro, mención de validación de cuenta por email, "Cambiar contraseña" desde el menú de usuario, y el nuevo botón "Instalar app" (Punto 10).

**Archivos tocados:** `routes/admin.py`, `templates/admin/usuarios.html`, `templates/base.html`, `templates/manual.html`.
**Pendiente:** commitear vía Git Bash y deployar; Daniel prueba en el celu: (a) que el dropdown de Localidad sale vertical y alfabético, (b) que el encabezado de la tabla queda fijo al scrollear en mobile (ya no desaparece), (c) que aparece "Instalar app" en el menú y funciona (en Android dispara instalación real; en iPhone abre el modal con los pasos), (d) repasar el Manual actualizado.
```bash
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add routes/admin.py templates/admin/usuarios.html templates/base.html templates/manual.html
git commit -m "fix: datalist localidad alfabetico+vertical, encabezado tabla fijo en mobile (sticky real), boton Instalar app (PWA), correcciones Manual del Usuario"
git push
```

### Sesión 12/07/2026 (cont. 14) — Fix real del dropdown de Localidad (era autofill de Chrome, no nuestro código) ⚠️ SIN COMMITEAR
Daniel deployó lo de cont. 13 y probó en el celu (capturas): el Manual ya mostraba los cambios, pero en Admin > Usuarios seguía viendo "Rosario" / "Roldán" en el mismo lugar horizontal, y no encontraba "Instalar app".
1. **Root cause real del dropdown de Localidad:** no era nuestro `<datalist>` (ya sacado en cont. 13) — era el **autofill nativo de Chrome**, que recuerda valores tipeados antes en un campo con el mismo `name` ("f_ciudad") y los sugiere en su propia UI (una tira horizontal arriba del teclado), **ignorando `autocomplete="off"`** (comportamiento documentado de Chrome Android, no arreglable solo con ese atributo). ✅ **Fix:** el input visible de Localidad ya no tiene `name` (nada que Chrome pueda asociar a historial), se agregó un `<input type="hidden" name="f_ciudad">` que es el que realmente viaja en el filtro — Chrome nunca le ofrece autofill a un campo oculto. El dropdown propio (vertical, alfabético) sigue funcionando igual, sincronizado por JS con el hidden.
2. **"No encuentro Instalar app":** lo más probable es que Daniel no haya tocado el desplegable de usuario (aparece como "Administrador ▾" al final del menú mobile colapsado, sin expandir en la captura) — "Instalar app" vive ahí adentro, junto a "Mi empresa"/"Cambiar contraseña". Otra posibilidad: si ese número de celu ya tiene la app agregada a la pantalla de inicio de una sesión anterior, el botón se oculta a propósito (no tiene sentido reinstalar). Pendiente confirmar cuál de las dos es.

**Archivo tocado:** `templates/admin/usuarios.html`.
**Pendiente:** commitear vía Git Bash y deployar; Daniel confirma que el dropdown de Localidad ya no repite Rosario/Roldán fantasma.
✅ **"Instalar app" — resuelto sin cambios de código:** Daniel confirmó que tocando "Administrador ▾" no aparecía porque el celu ya tenía la app instalada de una sesión anterior (comportamiento esperado — el botón se oculta a propósito si ya está instalada). Desinstaló para confirmar que el botón aparece en ese caso. No aplica cambio al Manual (es un detalle de comportamiento, no un paso nuevo para el usuario).
```bash
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add templates/admin/usuarios.html
git commit -m "fix: dropdown de Localidad — separar input visible (sin name) de hidden f_ciudad para evitar que Chrome autofill nativo pise las sugerencias"
git push
```

## Pendientes / Ideas

### 🔴 CRÍTICO
- [x] **Commit + push de la feature de prueba gratis** ✅ CONFIRMADO 07/07/2026 21:26 ART.
- [x] **Commitear database.py con todas las migraciones pendientes (2l, 2q, 2r, 2s, etc.)** ✅ CONFIRMADO.
- [x] **Configurar Webhook en MP Developers** ✅ confirmado por Daniel 10/07/2026 (cont. 9) — ya venía probando con pagos reales, así que el webhook está andando.
- [x] **Test flujo completo MP** ✅ confirmado por Daniel 10/07/2026 (cont. 9) — ya hizo pagos reales.
- [x] **Pasar a producción MP** ✅ CONFIRMADO 10/07/2026 (cont. 9) — captura de Railway → Variables muestra `MP_ACCESS_TOKEN` y `MP_PUBLIC_KEY` arrancando con `APP_USR-` (formato de producción, no `TEST-`). Los pagos que viene haciendo Daniel ya son reales.
- [x] **DNS Cloudflare** ✅ presupuestopro.com.ar funcionando (30/06/2026)

> **Nota CONFIRMADA 10/07/2026 22:45 ART (cont. 9):** `git fetch origin main` desde Git Bash real (no el mount stale) — `HEAD` local y `origin/main` apuntan al mismo commit `1909015` ("feat: badge Usuarios muestra total fijo..."), `git diff` entre ambos vacío. **Todo el código de TODAS las sesiones anteriores hasta hoy está pusheado**, incluyendo lo que en su momento quedó marcado "⚠️ SIN COMMITEAR" en las sesiones de abajo (cont. 6, cont. 7, cont. 8, validación de cuenta, cómo-nos-conoció, localidad/provincia normalizada, Sugerencias, y todo lo anterior a esas). Esas marcas y los "Pendiente: commitear..." de sesiones pasadas quedan como registro histórico de qué incluía cada tanda, **no como pendientes reales** — no hace falta volver a commitear nada de eso.

### 🟡 IMPORTANTE
- [ ] **Post Facebook de lanzamiento** — redactar post con screenshots del app para grupos de albañiles → landing page → MP. Pendiente de tomar screenshots: dashboard, costo/m2, ver presupuesto. (Daniel: dejar en pendientes por ahora, 10/07/2026 cont. 9.)
- [ ] Confirmar variable `APP_BASE_URL` en Railway — Daniel cree que ya está funcionando en la web (10/07/2026 cont. 9), pero queda como pendiente de confirmación formal (no verificable desde acá sin acceso a Railway).
- [ ] Test completo flujo pago MP → activación → email — Daniel cree que ya está, pero lo deja explícitamente en pendientes para probarlo formalmente (10/07/2026 cont. 9).
- [x] **Resincronizar cantidades de materiales en `analisis_sub`** ✅ hecho 04/07/2026 con migración 2n (ver abajo).

### 🟢 IDEAS FUTURAS
- [ ] Unificar landing_presupuestopro.md con posts para marketing
- [ ] **Permitir sesión simultánea celu + compu** — hoy `login_user()` en `utils/auth.py` invalida cualquier sesión anterior de la cuenta (sesión única). Decisión 04/07/2026: dejarlo como está por ahora, pero evaluar cambiarlo (guardar múltiples tokens por usuario en vez de uno solo) si vuelve a ser un problema.

#### Tanda 10/07/2026 — lista de ideas que Daniel pasó para revisar/priorizar más adelante
- [ ] Cálculo de escaleras (nuevo tipo de ítem/feature)
- [ ] Proveedores zonales (afiliaciones) — incorporar y que el listado de materiales los nombre
- [ ] Para quien piensa construir (sin arquitecto/constructor), que la app le dé una idea del gasto total antes de arrancar
- [ ] Marcar en Google Maps las ciudades donde está operando la app
- [x] Validar la cuenta con celu y/o mail al registrarse — ✅ código implementado y **pusheado** (confirmado 10/07/2026 cont. 9, ver nota de git fetch arriba). WhatsApp real todavía bloqueado por trámite en Meta (ver ítem nuevo de abajo).
- [x] En el registro, que la localidad/provincia se filtre de una lista ya cargada (no texto libre) — ✅ implementado y pusheado.
- [ ] Conectar la app con WhatsApp Business (API oficial) — 🟡 **EN CURSO desde 12/07/2026.** Perfil personal del celu y PC ya resueltos (13/07). Sigue pendiente el trámite de Meta Cloud API (checklist más abajo) — no arrancado todavía.
- ✅ **Aparte, 10-11/07/2026 (cont. 9-10): el WhatsApp COMÚN (personal) del número que usa "Enviar WhatsApp de activación" en Admin > Usuarios quedó "Cuenta en revisión" el 10/07 (sospecha: mismo texto plantilla repetido a no-contactos vía `wa.me`) y Daniel la recuperó.** Buenas prácticas para no repetirlo — ver sección dedicada más abajo ("WhatsApp — buen uso, definido 11/07/2026").
- ✅ **Reorganización de números/celulares — PLAN FINAL, EN CURSO 11/07/2026:** se probaron y descartaron 2 caminos antes de llegar al definitivo:
  1. ~~2 cuentas dentro de la misma WhatsApp Business del celu de PP~~ — descartado: esa versión de WhatsApp Business no expone "Agregar cuenta" (tocar el perfil arriba de Ajustes abre "Editar perfil", no un selector de cuentas).
  2. ~~Clonar WhatsApp Business con Dual Messenger (Samsung)~~ — descartado: Dual Messenger del celu solo tiene disponibles para clonar WhatsApp normal, Facebook y Messenger — WhatsApp Business no aparece en la lista.
  3. ~~Mover "Directo a Vos" (el WhatsApp Business existente, número prepago) al celu personal~~ — descartado: Daniel no tiene el chip físico del prepago, y sin él es imposible recibir el código de verificación para reactivarlo en otro celu (no se puede evitar este paso).
  - **✅ Plan final (sin necesitar el chip perdido):** "Directo a Vos" queda intacto en el celu de PP, sin tocar nada (Daniel ya hizo backup por las dudas — Google Drive, cuenta `directoavos0361@gmail.com`, 461 MB). El número de PP se configura como WhatsApp Business en el **celu personal** (instalando la app ahí, aparte del WhatsApp normal de la línea 7371 — 2 apps distintas en el mismo celu, sin clonar nada, 100% soportado). Al verificar el número de PP ahí, se muda solo desde el WhatsApp normal del celu de PP (con opción de transferir el historial). Para operar sin depender de tener el celu personal siempre a mano, se vincula WhatsApp Web/Escritorio a esa cuenta.
  - **Progreso 11/07/2026 (mismo día):** Daniel ya está armando el perfil de empresa de WhatsApp Business para PP en el celu personal — categoría elegida: **Contratista de albañilería + Producto/servicio + Empresa de software**; horario configurado como **"Siempre abierto"** (pensado para cuando se sume un chatbot, que pueda responder a cualquier hora sin que la cuenta figure "cerrada").
  - **Pendiente:** terminar de configurar el perfil (foto, descripción, etc.), confirmar que el número de PP quedó migrado a Business, vincular WhatsApp Web, y — más adelante — evaluar el chatbot mencionado (todavía sin definir con qué herramienta).
- [ ] Armar un recorrido guiado por la app explicando el funcionamiento — en PC, mostrar un mensaje al pasar el mouse por la celda
- [x] Cuando alguien se inscribe, preguntarle cómo nos conoció — ✅ implementado y pusheado.
- [x] Agregar nota en la app: si el usuario encuentra un error o diferencia de precios, que mande un mensaje desde Sugerencias (menú) — ✅ implementado y pusheado, ver `templates/sugerencias.html`.
- [ ] Publicar la app en Google Play y App Store (requiere empaquetado nativo/TWA, cuenta de developer en cada tienda, cumplir sus requisitos de revisión)
- [ ] Ofrecer/vender la app también desde Mercado Libre, como canal de venta adicional (mismo grupo que Google Play/App Store — aclarado por Daniel 10/07/2026: es de la app, no de marketing)

**Nota:** "Se buscan albañiles" y la "Historia de 2 jóvenes recién egresados y un abuelo" (de la tanda original) ya están concretadas (carrusel crónica e `HISTORIA_ORIGEN_PRESUPUESTOPRO.md`, ver `PROYECTO_MARKETING.md`).

#### 📱 WhatsApp — buen uso, definido 11/07/2026 (para no repetir la revisión de cuenta del 10/07)
Reglas a seguir con el número que se usa para mandar activaciones/avisos desde Admin > Usuarios:
1. **Variar el texto** entre envíos — no mandar el mismo mensaje plantilla palabra por palabra a varias personas seguidas. Cambiar el orden de las frases o agregar algo del contexto de cada usuario.
2. **Espaciar los envíos** — no varios `wa.me` seguidos en pocos minutos. Dejar minutos entre uno y otro si son varios usuarios el mismo día.
3. **Guardar como contacto** antes de escribir, cuando se pueda — mensajes a números guardados generan mucha menos sospecha que a desconocidos.
4. **Limitar mensajes nuevos a desconocidos por día** — no hay un número oficial público, pero como regla práctica conviene no pasar de un puñado por día con un número nuevo/poco usado, e ir escalando de a poco.
5. **Frenar de inmediato** ese patrón de envíos si alguien bloquea o reporta el número — seguir mandando en ese momento es lo que más rápido escala a suspensión.
6. **A mediano plazo, migrar este flujo a la API oficial de WhatsApp Business (Meta Cloud API)** — pensada justamente para mandar mensajes a muchos destinatarios con reglas propias (plantillas aprobadas, opt-in), sin arriesgar un número personal. Es el trámite que ya está en curso con Meta (ver ítem "Conectar la app con WhatsApp Business" arriba).

#### 🟣 Cola de ideas para MARKETING (pendiente de trasladar a PROYECTO_MARKETING.md)
Daniel las va pasando por este chat para no interrumpir el hilo — quedan acá anotadas hasta que se abra el chat de marketing y se carguen allá. No confundir con las de arriba (son de la app, no de difusión).
- [ ] Hacer calcos con QR
- [ ] Aclarar en cada lámina/post que es una app para Albañiles y Constructores
- [ ] Hacer historieta completa de los jóvenes y el abuelo (extender la historia de origen a formato historieta)

## Cambios recientes comprometidos (HEAD actual en Railway)

### Sesión 10/07/2026 (cont. 5) — Segunda ronda de feedback tras deployar cont. 4 ✅ COMMITEADO Y DEPLOYADO
1. **Burbuja celeste "3 de 3 presupuestos Y 14 de 14 días"** — ✅ arreglado: `templates/dashboard.html` línea ~30, "y" → "o" (coherente con "lo que se cumpla primero").
2. **Sigue pudiendo crear presupuesto sin validar el mail, otra vez después de deployar** — todavía no confirmado si es bug: la explicación más probable sigue siendo que el switch `verificacion_activa` (Admin > Configuración) sigue apagado. Le quedó preguntado a Daniel de nuevo, explícito esta vez, con la ruta exacta.
3. **Localidad se despliega distinto a Provincia, sin flechita** — no es bug, es una limitación real: Provincia es un `<select>` (control nativo del navegador, con flechita); Localidad tiene que seguir siendo texto libre con sugerencias (`<datalist>`) porque es una lista abierta que se autoalimenta — ningún navegador le pone flechita a un datalist, son controles distintos por diseño. Además, la entrada con ícono de persona ("Roldán — Santa Fe") y el link "Administrar direcciones..." que aparecen mezclados en la lista son el autocompletado de direcciones DE CHROME superpuesto al datalist de la app (pasa incluso con `autocomplete="off"` puesto, Chrome lo ignora bastante seguido en campos que él interpreta como parte de un formulario de dirección). No hay un fix confiable para eso del lado del código — explicado a Daniel, sin acción de código.
4. **Daniel no encontraba dónde estaba el switch de validación** — el botón en Admin > Acceso rápido decía solo "Configuración (GG%, Imp%)", sin mencionar validación, por eso no lo relacionó. ✅ arreglado el texto del botón a "Configuración (GG%, Imp%, validación de cuenta)" (`templates/admin/dashboard.html`). Ruta completa: **menú de arriba → "Admin" (ícono engranaje) → tarjeta "Acceso rápido" → ese botón → switch al final de la página** (`/admin/configuracion`).

**Archivos tocados:** `templates/dashboard.html`, `templates/admin/dashboard.html`.
```
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add templates/dashboard.html templates/admin/dashboard.html
git commit -m "fix: texto burbuja prueba gratis (y -> o) + boton de Configuracion menciona validacion de cuenta para que se encuentre"
git push
```
**✅ COMMITEADO Y DEPLOYADO 10/07/2026 16:11 ART** — el primer deploy del commit `8ed88716` había fallado en Railway ("Deployment failed during build process" con 0 build logs, instantáneo). El diagnóstico automático de Railway lo marcó como **Infrastructure Error / transitorio** (no relacionado al código: el commit solo tocaba texto HTML, no puede romper un build de Python; el mismo código había buildeado bien 26 min antes). No existe opción "Redeploy" para deployments que fallaron en build (solo aplica a exitosos), así que se resolvió disparando un build nuevo con un commit vacío:
```
git commit --allow-empty -m "chore: retry deploy tras error transitorio de infraestructura"
git push
```
Resultado: ACTIVE / Deployment successful. Texto burbuja (y→o) y botón "Configuración (GG%, Imp%, validación de cuenta)" ya en producción.
**Pendiente:** Daniel confirma si prendió el switch de validación en `/admin/configuracion`.

### Sesión 10/07/2026 (cont. 3) — Validación de cuenta + cómo-nos-conoció + localidad/provincia normalizada ✅ COMMITEADO Y DEPLOYADO (confirmado por captura de pantalla de Daniel probando en producción — pedirle `git log --oneline -5` para anotar el hash acá)
Implementación de 3 de los 4 puntos de la "tanda rápida" (el 4to, nota en Sugerencias, es un cambio de una línea, ver más abajo aparte). Esto es una FEATURE nueva que toca el flujo de registro/login — más grande de lo que parecía al principio, sobre todo la validación de cuenta (terminó incluyendo integración con WhatsApp Business/Meta). Por eso se armó con **feature flag apagado por default**, para no arriesgar nada en producción hasta que Daniel la pruebe.

**Provincia → lista cerrada.** `templates/registro.html` pasa de campo de texto libre a `<select>` con las 24 provincias argentinas (`utils/normalizacion.py::PROVINCIAS_AR`). Elimina el problema de raíz (no puede haber "Pba" vs "Buenos Aires" si no se puede escribir texto libre).

**Localidad → autoalimentada y normalizada.** Sigue siendo texto libre (no se puede cerrar una lista de miles de localidades), pero ahora hay una tabla nueva `localidades` que se autoalimenta: cuando alguien escribe una ciudad, se normaliza (minúsculas, sin tildes, sin puntuación — `utils/normalizacion.py::clave_normalizada()`) y si ya existe una entrada con esa misma clave normalizada, se reusa la grafía ya cargada (así "Rosario" y "rosario" quedan como un solo registro). El campo de registro tiene autocompletado (`<datalist>`) con las localidades ya cargadas.

**Limpieza de datos viejos:** la migración 2t (`database.py`) recorre TODOS los `users.ciudad`/`users.provincia` existentes al momento de correr, agrupa localidades duplicadas y mapea provincias a su nombre canónico donde hay match confiable (diccionario de sinónimos: pba/caba/bs as/etc. — ver `utils/normalizacion.py`). Las provincias sin match automático quedan sin tocar y se listan en el log de Railway para revisar a mano.

**Cómo nos conociste:** nuevo campo en el registro (`users.como_nos_conocio`), lista fija (Facebook, Instagram, Recomendación de alguien, Búsqueda en Google, Otro) + texto libre si elige "Otro". Visible en Admin > Usuarios.

**Validación de cuenta (email/WhatsApp):** en el registro, el usuario elige validar por email o WhatsApp. Se manda un código de 6 dígitos (`utils/verificacion.py`), y mientras no lo confirme, queda bloqueado para crear presupuestos, usar Costo/m² y descargar PDFs (mismo patrón que el bloqueo de prueba gratis vencida, `utils/trial.py`) — puede entrar al dashboard igual, con la pantalla `templates/validar_cuenta.html` pidiéndole el código.
- Email: funciona YA, usa Resend (mismo que el resto de la app).
- WhatsApp: el código para mandarlo por Meta Cloud API está escrito (`utils/verificacion.py::enviar_codigo_whatsapp`), pero **no puede mandar mensajes reales todavía** — devuelve `False` y cae automático a email mientras no estén configuradas `WHATSAPP_TOKEN` / `WHATSAPP_PHONE_ID` en Railway. Ver checklist para Daniel más abajo.
- **341-301-7371 vs 341-754-2009 (pregunta de Daniel 10/07/2026):** el 301-7371 nunca necesitó configuración porque los mensajes que manda la app hoy (activación manual desde Admin, aviso de vencimiento) son links `wa.me/...` — abren WhatsApp con un mensaje precargado que **una persona** tiene que tocar "enviar" a mano (`templates/admin/usuarios.html::waActivacion()`, `routes/pdf_routes.py`, `routes/pagos.py`). Eso no manda nada solo, así que no requiere ninguna cuenta de empresa ni aprobación de Meta — es el WhatsApp normal de Daniel, con un mensaje ya escrito. El código de validación es distinto: lo tiene que mandar el SERVIDOR sin que nadie toque nada, y eso es justo lo que Meta exige verificar (WhatsApp Business Platform / Cloud API) antes de dejar mandar mensajes automáticos — por eso hace falta el trámite para el 754-2009.
- **¿Afecta a los ya inscriptos sin validar? No, nunca retroactivo — fix 10/07/2026:** el bloqueo se calcula en dos pasos para garantizar esto. (1) La migración 2t marca como validadas TODAS las cuentas que existan en el momento del deploy. (2) Además, `routes/admin.py::configuracion()` marca como validada a cualquier cuenta sin validar **en el instante exacto en que Daniel prende el switch** (no antes, no en el deploy) — así que aunque alguien se registre en el medio, con el switch todavía apagado, esa cuenta queda a salvo apenas se activa. El bloqueo rige solo para quien se registre **después** de que el switch ya esté prendido. El cartel de "Configuración guardada" avisa cuántas cuentas quedaron marcadas así, si hubo alguna.

**Interruptor general (`config.verificacion_activa`, arranca en `'0'` = apagado):** desde Admin > Configuración hay un switch "Validación de cuenta obligatoria". Con el switch apagado, nada de esto bloquea a nadie (el registro guarda igual el método elegido, para cuando se prenda). **Recomendación: probarlo primero con tu propia cuenta antes de prenderlo para todos.**

**⚠️ Checklist para Daniel — activar WhatsApp real (fuera del código, en Meta):**
1. Verificar el negocio en [Meta Business Manager](https://business.facebook.com) (puede tardar días).
2. Dar de alta el número **341 754-2009** en WhatsApp Business Platform (Cloud API) dentro de ese Business Manager.
3. Crear y esperar la aprobación de un **template de mensaje categoría "Autenticación"** (Meta exige plantilla pre-aprobada para mandar un código sin que el usuario haya escrito primero) — anotar el nombre exacto del template.
4. Conseguir el token de acceso permanente y el `phone_number_id` que da Meta.
5. Pasarme esos 3 datos (token, phone_number_id, nombre del template) para cargarlos como variables de entorno en Railway (`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_TEMPLATE_OTP`) — ahí sí queda funcionando el envío real, sin tocar código de nuevo.

**Archivos nuevos:** `utils/normalizacion.py`, `utils/verificacion.py`, `templates/validar_cuenta.html`.
**Archivos tocados:** `database.py` (migración 2t), `routes/landing.py` (registro + nueva vista `/validar-cuenta`), `templates/registro.html`, `routes/admin.py` + `templates/admin/configuracion.html` (switch), `templates/admin/usuarios.html` (badges), `routes/costo_m2.py`, `routes/presupuesto.py`, `routes/pdf_routes.py` (agregado `@verificacion_required` junto a `@trial_required`).
**Estado:** deployado. Daniel probó registrando un usuario nuevo y el bloqueo NO actuó — esperado, todavía no había prendido el switch `verificacion_activa` en Admin > Configuración (instrucción textual que se le dio: probar el registro CON el switch apagado primero). Falta que lo prenda para probar el bloqueo real.

### Sesión 10/07/2026 (cont. 4) — Fixes tras la primera prueba de Daniel ⚠️ SIN COMMITEAR
Daniel probó lo de arriba en producción y reportó varias cosas en un solo mensaje:
1. **Texto de la burbuja celeste de prueba gratis** ("...3 de 3 presupuestos y 14 de 14 días") — pidió dejarlo anotado para la próxima tanda de correcciones, no tocarlo ahora. **Pendiente para después:** `templates/dashboard.html` líneas 29-31, cambiar "y" por "o" (coherente con "lo que se cumpla primero").
2. **Pudo crear un presupuesto sin validar el email** — no es bug: el switch `verificacion_activa` seguía apagado (instrucción de la sesión anterior era probar el registro primero CON el switch apagado). Sin acción de código; falta que Daniel prenda el switch para probar el bloqueo real.
3. **"Próximos vencimientos" no muestra a todos los recién anotados** — no es bug de hoy: `routes/admin.py::dashboard()` siempre tuvo `LIMIT 5` ordenado por fecha de vencimiento más próxima (línea ~31). Con más de 5 cuentas por vencer, las de fecha más lejana quedan afuera del widget aunque sean más nuevas. Si Daniel quiere ver más, es un cambio de una línea (subir el LIMIT o agregar "ver todos").
4. **Filtros de Localidad/Provincia sin desplegable como País** — ✅ arreglado: Provincia pasa a `<select>` con las 24 provincias fijas (antes era texto libre con datalist, y además el filtro usaba `LIKE`, lo que hacía que filtrar "Buenos Aires" también trajera "Ciudad Autónoma de Buenos Aires" por ser substring — corregido a match exacto). Localidad ahora tiene datalist real alimentado por la tabla `localidades` (antes lo que aparecía era el autocompletado del navegador, no datos de la app).
5. **Pedido: poder controlar/corregir localidades duplicadas a mano** — ✅ nueva página **Admin > Localidades** (`templates/admin/localidades.html`, ruta `/admin/localidades`, link agregado en el dashboard de admin y en Usuarios). Permite renombrar una localidad (corrige la grafía en todos los usuarios que la tengan) y fusionar dos que sean el mismo lugar (ej. "Rosario" y "Rosario Norte", que la normalización automática no agrupa sola). Al fusionar, los usuarios existentes con la vieja pasan a la nueva, y de ahí en más cualquiera que se registre escribiendo la vieja también cae en la nueva (columna nueva `localidades.merged_en`, migración 2u).
6. **Aclaración de error de precios en la tarjeta de Costo/m²** — ✅ agregada al final de `templates/costo_m2/resultado.html` (debajo del desglose de materiales, `no-print` para no salir en el PDF exportado): "¿Ves un error de cálculo o un precio muy distorsionado? Contanos desde Sugerencias". Mismo mensaje que ya estaba en `/sugerencias`, repetido acá porque es donde el usuario más probablemente nota el precio raro (comparando $ Lista vs $ Costo).
7. **"Eduardo" duplicado — confirmado por Daniel:** fue una prueba suya con dos emails distintos, no un bug del formulario (no hay doble submit). A partir de esto, Daniel pidió controlar también por teléfono para evitar altas duplicadas de la misma persona con otro email — ✅ agregado: `routes/landing.py::registro()` ahora también rechaza el alta si el teléfono (normalizado a los últimos 10 dígitos, `utils/normalizacion.py::telefono_normalizado()`) ya está en otra cuenta, con el mismo mensaje de error que usa el email duplicado.

**Nota aparte:** un llamado a `AskUserQuestion` falló silenciosamente (error de la herramienta, no relacionado con el código) mientras se estaba por preguntar sobre "Eduardo" y sobre a qué se refería el punto 6 — Daniel lo aclaró directo en los siguientes mensajes, no hizo falta reintentar.

**Archivos nuevos:** `templates/admin/localidades.html`.
**Archivos tocados:** `database.py` (migración 2u), `routes/admin.py` (fix filtro provincia + rutas de localidades), `routes/landing.py` (`_guardar_localidad` sigue la cadena de fusión + control de teléfono duplicado), `utils/normalizacion.py` (`telefono_normalizado`), `templates/admin/usuarios.html` (filtros), `templates/admin/dashboard.html` (link nuevo), `templates/costo_m2/resultado.html` (nota de error de precios).
**Pendiente:** commitear vía Git Bash y deployar.
```
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add database.py routes/admin.py routes/landing.py utils/normalizacion.py templates/admin/localidades.html templates/admin/usuarios.html templates/admin/dashboard.html templates/costo_m2/resultado.html
git commit -m "fix: filtro de provincia (select fijo, match exacto) + localidad con datalist real + Admin > Localidades para fusionar duplicados a mano + nota de error de precios en Costo/m2 + control de telefono duplicado en registro"
git push
```


### Sesión 10/07/2026 (cont.) — 🐛 Bug de cálculo en Costo/m2: materiales redondeados a bolsa entera ✅ COMMITEADO, PUSHEADO Y VERIFICADO (commit `8748b42`)
Daniel detectó en la calculadora Costo/m2 (ítem "Mamp. ladrillo comun 30cm") que el Cemento de Albañilería se mostraba como 1 bolsa entera consumida por m2, cuando el consumo real ronda los 20kg (bien menos de una bolsa de 25kg). Arena y Ladrillos daban bien; solo se notaba con materiales tipo "Bolsas"/"U"/"Kg" cuando la cantidad fraccionaria por m2 caía por debajo de 1 unidad — más notorio en revoques, donde el consumo de cemento por m2 es chico.

**Causa raíz (confirmada leyendo el código, sin acceso a la DB de producción):** `_calcular_materiales_desde_rubros()` (`routes/presupuesto.py`) redondea SIEMPRE hacia arriba (`math.ceil`) la cantidad de materiales tipo Bolsas/U/Kg antes de calcular el subtotal — correcto para un presupuesto real (no se compra 0.8 bolsas), pero `routes/costo_m2.py` reutiliza esa misma función sobre un "presupuesto sintético" de 1 sola unidad (factor_conv chico, ej. 0.30 para el ítem de 30cm). Con cantidades tan chicas, el `ceil()` infla el costo de referencia (0.8 bolsas → redondeaba a 1 bolsa completa, ~25% de sobrecosto en este caso puntual, mucho peor en ítems donde el consumo por m2 es una fracción todavía más chica de una bolsa).

**Fix:** se agregó un parámetro `redondear=True/False` a `_calcular_materiales_desde_rubros()`. El presupuesto real y el PDF lo siguen llamando sin el parámetro (default `True`, sin cambios de comportamiento). Costo/m2 ahora llama con `redondear=False`, así usa la cantidad real fraccionaria (sin redondeo de compra) tanto para mostrar como para el subtotal.

**Archivos tocados:** `routes/presupuesto.py` (función `_calcular_materiales_desde_rubros`), `routes/costo_m2.py` (llamado con `redondear=False`).
**Estado:** ✅ commiteado y pusheado a `origin/main` (`8748b42`, 2 files changed, 34 insertions/6 deletions) — confirmado por Daniel el 10/07/2026. Probado en un ítem de revoque (cemento capa aisladora): da bien.

### Sesión 10/07/2026 — 🔴 BUG GRAVE: /admin/precios caído en producción (BuildError) ✅ COMMITEADO Y PUSHEADO (commit `09146a1`)
Daniel reportó que al entrar a "Precios de materiales" desde el panel admin, la página tira Internal Server Error. Confirmado con 3 clientes reales de prueba gratuita ya usando la app — antes de tocar nada se le explicó que los presupuestos ya generados guardan sus totales congelados en la base (no se recalculan con cambios de código), así que no corren riesgo con este tipo de fixes.

**Causa (confirmada con el traceback real de Railway, pedido por Deploy Logs):** `templates/admin/precios.html` línea 7 tenía `url_for('admin.index')` — ese endpoint no existe, la vista del dashboard admin se llama `admin.dashboard` (`routes/admin.py`, `@bp.route('/') def dashboard()`). Cualquier `url_for` a un endpoint inexistente rompe toda la página con `werkzeug.routing.exceptions.BuildError`, no solo el link — por eso toda la pantalla caía con 500 aunque el resto del código de la vista estuviera bien.

**Fix:** cambiado a `url_for('admin.dashboard')`. Verificado con grep en toda la app que no queda ningún otro `admin.index` suelto — era el único caso.

**Archivos tocados:** `templates/admin/precios.html`.
**Estado:** ✅ commiteado y pusheado a `origin/main` (`09146a1`) — confirmado por Daniel con `git log --oneline` el 10/07/2026. Pendiente deployar/verificar en Railway.

### Sesión 08/07/2026 (cont. 3) — Unificados los botones "Probá gratis" de la landing + limpieza del modal viejo ✅ COMMITEADO Y PUSHEADO (commit `875eb03`)
Seguimiento directo del bug de Ricardo Jordan: Daniel pidió controlar que **todos** los botones "Probar la App" de la landing lleven al mismo lugar, después de que otra prueba (Anibal Roca) sí funcionó pero por un botón distinto.

**Encontrado:** en `templates/landing.html` convivían 2 caminos de alta: el modal viejo `modalInscripcion` (activación manual, el que rompió con Ricardo) y `/registro` (alta instantánea, prueba gratis). 6 botones distintos en la página ("PROBALA GRATIS" en el nav x2, hero, sección PDF, precios y CTA final) apuntaban todavía al modal viejo vía `data-bs-toggle="modal" data-bs-target="#modalInscripcion"`.

**Fix:** los 6 botones ahora son `<a href="{{ url_for('landing.registro') }}">` (mismo patrón que ya usa `login.html`) — todos van al alta instantánea. Se confirmó con grep que no queda ningún botón apuntando al modal.

**Limpieza (código muerto, mismo criterio que en sesiones anteriores):** al no quedar nada que abra el modal, se sacó todo lo asociado: el bloque `<div id="modalInscripcion">` completo, las funciones JS `enviarInscripcion()`, `mostrarExito()` y `resetModal()`, y el CSS muerto `.modal-inscripcion` / `.success-box`. Verificado con grep que no queda ninguna referencia a `modalInscripcion`, `inpNombre/inpApellido/...` ni `success-box` en el archivo. El endpoint `/inscripcion` y la tabla `leads` (routes/dashboard.py, database.py) quedan igual, sin tocar — no hacen daño estar ahí por si se reusan, pero ya nada del sitio los llama.

**Respuesta a la otra pregunta de Daniel (instalar la app / caso Anibal Roca):** el cartel para "bajar/instalar la app" que apareció es el prompt nativo de Chrome/Android para instalar una PWA (Progressive Web App) — no es algo que el código dispare a propósito por cada alta nueva. `templates/base.html` registra un manifest (`manifest.json`) y un service worker en TODAS las páginas que extienden `base.html` (dashboard, login, registro, trial_vencido, etc.). Apenas un usuario llega a una de esas páginas en un navegador compatible (típicamente Chrome en Android), el navegador puede ofrecer instalarla como app — es comportamiento estándar del navegador, no algo exclusivo de una activación. La landing pública (`landing.html`) es standalone y NO dispara esto. Conclusión: sí, va a poder volver a pasar con cualquier usuario nuevo que entre al dashboard desde Chrome/Android — es normal y no es un bug.

**Archivos tocados:** `templates/landing.html`.
**Estado:** ✅ commiteado y pusheado a `origin/main` (`875eb03`, 1 file changed, 22 insertions) — confirmado por Daniel el 10/07/2026.

### Sesión 08/07/2026 (cont. 2) — 🔴 BUG GRAVE: tabla `leads` no existe en producción (caso Ricardo Jordan) ⚠️ SIN COMMITEAR
Daniel reportó: Ricardo Jordan completó la inscripción, le apareció el cartel de éxito ("en breve te activamos por WhatsApp o email"), pero no llegó ningún aviso ni aparece en ningún listado.

**Causa raíz encontrada — mismo patrón que el bug de `password_reset_tokens` (sesión 05/07):** la landing (`templates/landing.html`) todavía tiene el modal viejo "Quiero registrarme en PresupuestoPRO" (`modalInscripcion`, POST a `/inscripcion`) — un flujo ANTERIOR al de prueba gratis, donde el admin activa manualmente. La tabla `leads` está creada en `init_db()` pero **NUNCA se agregó a `migrate_db()`** — como la base de producción ya existía de antes, la tabla simplemente no existe ahí. `routes/dashboard.py::inscripcion()` hacía `INSERT INTO leads` sin try/except → tiraba 500. Pero el JS del modal (`enviarInscripcion()`) tiene un `.catch()` que **ignora cualquier error a propósito** ("el endpoint puede no existir aún") y muestra igual el cartel de éxito. Resultado: Ricardo vio "Registrado con éxito", pero no se guardó nada, no salió el mail al admin, y `/admin/leads` también hubiera roto si Daniel entraba (`SELECT * FROM leads` sobre una tabla inexistente).

**Nota:** el dato de Ricardo no se pudo recuperar — nunca llegó a guardarse en ningún lado. Hay que volver a contactarlo.

**Fix (3 partes):**
1. `database.py::migrate_db()`: se agrega `CREATE TABLE IF NOT EXISTS leads (...)` (mismo patrón que `password_reset_tokens`) — se crea sola en el próximo deploy, sin perder nada de lo que ya funciona.
2. `routes/dashboard.py::inscripcion()`: el INSERT ahora tiene try/except — si algo vuelve a fallar, devuelve 500 con log en vez de desaparecer en silencio (el frontend lo va a seguir ignorando, pero al menos queda registrado en los logs de Railway).
3. **El botón "🔔 Inscriptos" en el dashboard admin YA EXISTÍA** (no era invisible del todo), pero no tenía ningún contador — un inscripto nuevo no se notaba a simple vista. Se agregó `stats.leads_nuevos` (cuenta `estado='nuevo'`) en `routes/admin.py::dashboard()` y el badge correspondiente en `templates/admin/dashboard.html`, mismo patrón que "Mensajes de contacto"/"Sugerencias".

**Pendiente de decisión (no se tocó, es un cambio de UX/negocio):** la landing tiene DOS caminos de alta que compiten: el modal viejo "Inscripción" (activación manual, el que usó Ricardo) y `/registro` (prueba gratis instantánea, sin esperar a nadie — implementado 07/07). Sugerido a Daniel: reemplazar el modal viejo por un link directo a `/registro`, así cualquier nuevo interesado entra solo, al instante, sin depender de que alguien note el aviso. Queda para que Daniel decida.

**Archivos tocados:** `database.py`, `routes/dashboard.py`, `routes/admin.py`, `templates/admin/dashboard.html`.
**Pendiente:** commitear vía Git Bash y deployar; después del deploy, contactar a Ricardo Jordan para que se registre de nuevo (idealmente por `/registro`, acceso instantáneo) o cargarlo manualmente desde Admin > Nuevo usuario con sus datos.
```
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add database.py routes/dashboard.py routes/admin.py templates/admin/dashboard.html
git commit -m "fix: tabla leads no existia en produccion (bug critico, inscriptos se perdian en silencio) + badge de inscriptos nuevos"
git push
```

### Sesión 08/07/2026 (cont.) — Copy de medios de pago corregido + consulta sobre SUB_UNIT de MP ⚠️ SIN COMMITEAR
Daniel notó que `/pagos/planes` decía "Pagá con cualquier billetera o tarjeta" / "transferencia bancaria" y preguntó si Mercado Pago realmente ofrece transferencia en este tipo de cobro (Checkout Pro) — sospechaba que no.

- **Confirmado con la documentación oficial vigente de Mercado Pago Argentina** (`mercadopago.com.ar/developers/es/docs/checkout-pro/overview`, consultada hoy): los medios de pago de **Checkout Pro** (lo que usa `routes/pagos.py::crear_suscripcion()`, vía `sdk.preference().create()`) son **"Tarjeta de crédito o débito, Rapipago, Pago Fácil, Cuenta Mercado Pago y Cuotas sin Tarjeta"** — no incluye transferencia bancaria como medio propio de Checkout Pro. Daniel tenía razón.
- **Fix — copy actualizado** (sin tocar lógica, solo texto) en `routes/pagos.py`: pantalla `/pagos/planes` (bullet de features y texto al pie) y pantalla del link de pago en `crear_suscripcion()`. Ahora dicen: "dinero en cuenta, tarjeta débito/crédito o Rapipago/Pago Fácil" — se sacó toda mención a "transferencia bancaria" y "billetera digital" genérica.
- **Consulta aparte — aviso de Mercado Pago sobre el campo `SUB_UNIT`:** Daniel mostró una captura del panel de MP ("A partir del 13/07/2026, el campo 'Plataforma de cobro / sub_unit' va a tener nuevos valores: checkout_pro, checkout_api"). Investigado: `SUB_UNIT` es una columna de los **reportes descargables** de MP (Todas las transacciones / Resumen de ventas — se generan y bajan como Excel/CSV desde el panel de MP, no forman parte de ninguna respuesta de API ni webhook). Confirmado con grep en todo el repo que el código **no lee `sub_unit` en ningún lado** (ni en `webhook()`, ni en `_activar_suscripcion()`, ni en ningún otro lugar). **Conclusión: este cambio NO afecta nuestra integración ni requiere ningún cambio de código** — solo importa si Daniel filtra/analiza manualmente esos reportes descargados por esa columna (en ese caso, de ahora en más las operaciones de PresupuestoPRO deberían figurar como `checkout_pro`, más preciso que el valor genérico anterior).
- **Archivo tocado:** `routes/pagos.py` (solo copy/texto).
- **Pendiente:** commitear vía Git Bash y deployar; revisar visualmente `/pagos/planes` y la pantalla de link de pago con el texto nuevo.
  ```
  cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
  rm -f .git/index.lock
  git add routes/pagos.py
  git commit -m "fix: corregir copy de medios de pago en planes (Checkout Pro no ofrece transferencia bancaria)"
  git push
  ```

### Sesión 08/07/2026 — Prueba gratis: mensaje duplicado + bug grave de facturación ⚠️ SIN COMMITEAR
Daniel mandó 3 capturas del flujo real de un usuario de prueba con la prueba vencida por presupuestos (no por días). Encontré 3 cosas, la del medio es la más importante:

1. **Mensaje duplicado en `/prueba-terminada`:** al intentar Editar con la prueba vencida, la página mostraba "Tu prueba gratis terminó" DOS veces — una vez arriba (banner rosa) y otra en la tarjeta. Misma causa que el duplicado del registro (sesión anterior): `utils/trial.py::trial_required` hacía `flash('Tu prueba gratis terminó...')` antes de redirigir a `/prueba-terminada`, que YA explica lo mismo con más detalle (`templates/trial_vencido.html`, dice el motivo exacto). Se sacó el `flash()`.

2. **🔴 BUG GRAVE — `/pagos/planes` decía "Tu suscripción está activa hasta el 2026-07-22" a un usuario que NUNCA pagó nada, con la prueba vencida por presupuestos.** Causa: `subscription_expires` se usa para DOS cosas distintas sin distinguirlas — para cuentas de prueba guarda la fecha límite de la prueba (hoy+14 días al registrarse, seteada en `routes/landing.py::registro()`), y para cuentas pagas guarda el vencimiento real de la suscripción. `routes/pagos.py::planes()` comparaba esa fecha contra hoy sin mirar `es_trial`, así que CUALQUIER usuario de prueba (dentro de los 14 días, sea que ya gastó sus 3 presupuestos o no) veía "ya estás activo" y el botón cambiaba de "Pagar con Mercado Pago" a "Ir al Dashboard" — un loop sin salida: Dashboard lo bloquea → vuelve a Planes → dice que ya está activo → Dashboard de nuevo. **Esto rompía el cobro de cualquier trial que quisiera pagar antes del día 14.**
   - Peor aún: encontré que **`_activar_suscripcion()` (el pago SÍ exitoso) nunca ponía `es_trial=0`** — o sea que incluso un usuario que pagara de verdad seguía siendo tratado como "de prueba" para siempre, y `trial_required` lo iba a volver a bloquear en cuanto pasaran los 3 presupuestos/14 días de su prueba original, PESE a tener una suscripción paga vigente.
   - **Fix (2 partes):**
     - `routes/pagos.py::planes()` y `::estado()`: `sub_activa` ahora es siempre `False` mientras `es_trial=1` — un usuario de prueba nunca ve "ya estás activo", siempre ve el botón de pago.
     - `routes/pagos.py::_activar_suscripcion()`: el UPDATE de la activación ahora también pone `es_trial=0` — un pago real convierte la cuenta en paga de forma definitiva, dejando de estar sujeta a los límites de prueba.
3. **Confirmado con Daniel:** en la captura, la prueba estaba vencida por los 3 presupuestos (no por los 14 días) — la pantalla de Planes no tiene que contemplar el plazo de 14 días para nada, solo si hay o no un pago real.

**Archivos tocados:** `utils/trial.py`, `routes/pagos.py`.
**Pendiente:** commitear vía Git Bash y deployar; probar con una cuenta de prueba con presupuestos agotados: (1) `/prueba-terminada` muestra el mensaje una sola vez; (2) `/pagos/planes` muestra el botón de pago, NO dice "ya activa"; (3) simular un pago (o revisar en Admin) y confirmar que tras `_activar_suscripcion` el usuario queda con `es_trial=0` y ya no lo bloquea `trial_required`.
```
cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
rm -f .git/index.lock
git add utils/trial.py routes/pagos.py
git commit -m "fix: bienvenida duplicada en prueba-terminada + bug grave de facturacion (planes.html mentia sobre suscripcion activa)"
git push
```

### Sesión 07/07/2026 (cont. 4) — Costo/m2: Beneficio/Seguros van SOLO sobre la MO ⚠️ SIN COMMITEAR
**Corrige/reemplaza el criterio de la entrada "cont. 3" de abajo.** Daniel aclaró la regla de negocio real: Costo/m2 es una calculadora de referencia de **mano de obra** por unidad (con los materiales como dato aparte — cuánto hace falta y qué sale), y **solo en esta sección** (no en el presupuesto real, que sigue igual) Beneficio y Seguros se aplican **sobre la MO únicamente**, no sobre MO+Materiales.

- **Ejemplo confirmado** (Mamp. ladrillo comun 30cm, jornales 80.000/40.000, Beneficio 10%, Seguros 7%): MO pura $35.250 → Beneficio $3.525 + Seguros $2.467,5 → **MO neta $41.243** (verificado con Python: 35250×1.17=41242.5).
- **Fix:** en `routes/costo_m2.py`, `gg_monto`/`imp_monto` ahora se calculan sobre `mo_por_unit_display` solamente (antes: `mo_por_unit_display + total_mat_display`). `mo_neto = mo_por_unit_display + gg_monto + imp_monto`. `total_final = mo_neto + total_mat_display` (materiales sin adicionales). El presupuesto real (`routes/presupuesto.py`, `get_config_pct` + `_calcular_totales_finales`) **no se tocó** — sigue aplicando Beneficio/Seguros sobre MO+Materiales como siempre.
- **JS (`templates/costo_m2/resultado.html`, `recalcAll()`):** `gg`/`imp` ahora se calculan como `moSim * pct_gg` / `moSim * pct_imp` (antes sobre `moSim + totalMat`).
- **Archivos tocados:** `routes/costo_m2.py`, `templates/costo_m2/resultado.html`.
- **Pendiente:** commitear vía Git Bash y deployar; probar con Mamp. ladrillo comun 30cm que la MO neta dé $41.243 con los valores default (jornales 80.000/40.000, Beneficio 10%, Seguros 7%), y que cambiar Beneficio/Seguros ya NO se vea afectado por el precio de los materiales.
  ```
  cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
  rm -f .git/index.lock
  git add routes/costo_m2.py templates/costo_m2/resultado.html
  git commit -m "fix: Beneficio/Seguros en Costo/m2 se aplican solo sobre MO (no MO+Materiales)"
  git push
  ```

### Sesión 07/07/2026 (cont. 3) — Costo/m2: sin TOTAL final + limpieza jornales duplicados ⚠️ SIN COMMITEAR
Daniel señaló 2 cosas más sobre Costo/m2:
1. En la lista de ítems (`costo_m2/index.html`) el header no quedaba fijo, y pidió sacar las líneas de Oficial/Ayudante de ahí — ya están (editables) en la ventana de resultado.
2. Con el ejemplo de Mamp. ladrillo comun 30cm ($35.250 MO, jornales 80.000/40.000, Beneficio 10%/Seguros 7%): si sube Beneficio de 10% a 20%, "el precio" debería subir ~$7.500, pero el número que él mira ($35.250) no se mueve.

**Investigado — punto 1:** confirmado código muerto. `costo_m2/index.html` tenía una tarjeta "Jornales diarios" (Oficial/Ayudante) que mandaba `jornal_of`/`jornal_ay` por querystring a `costo_m2.resultado` — pero `routes/costo_m2.py::resultado()` **nunca lee esos parámetros** (usa los de la tabla `config`). Quedó vestigial del diseño viejo (pre-05/07, cuando la MO sí se recalculaba con un jornal en pantalla). Se sacó la tarjeta y el JS que armaba esos parámetros; el header (título + subtítulo) ahora es `sticky-top`.

**Investigado — punto 2 (el importante):** no es un bug de cálculo, es que **no existía un TOTAL que sumara todo**. La tarjeta azul de arriba es "MO / m2" a propósito puro (nunca incluyó Beneficio/Seguros — eso es correcto, es costo de mano de obra). Beneficio y Seguros solo se veían como montos sueltos y chicos en "Adicionales" (`a_gg`/`a_imp`, que SÍ se recalculaban bien al tocar el %) — pero como no había ningún número grande que los sumara a MO+Materiales, parecía que "no pasaba nada". Verificado con la cuenta de Daniel: MO $35.250 + MAT $38.200 = base $73.450; Beneficio 10%→20% = +$7.345 (coincide con "casi $7.500 más" que esperaba).
- **Fix:** nueva tarjeta "TOTAL FINAL / {{ display_unit }}" (`card-total`, borde naranja) = MO + Materiales + Beneficio + Seguros, debajo de "Adicionales". Se recalcula en vivo con `recalcAll()` cada vez que se toca jornal, precio de un material, Beneficio % o Seguros %. `routes/costo_m2.py` ahora calcula y pasa `total_final` al template.
- **Archivos tocados:** `templates/costo_m2/index.html` (limpieza + sticky), `templates/costo_m2/resultado.html` (tarjeta TOTAL + JS), `routes/costo_m2.py` (`total_final`).
- **Pendiente:** commitear vía Git Bash y deployar; probar: (1) lista de ítems con header fijo al scrollear y sin las líneas de jornal viejas; (2) en resultado, subir Beneficio de 10% a 20% en el ejemplo de Mamp. ladrillo comun 30cm y confirmar que el TOTAL FINAL sube ~$7.345 (de a ~$85.937 a ~$93.282, con jornales/materiales default).
  ```
  cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
  rm -f .git/index.lock
  git add templates/costo_m2/index.html templates/costo_m2/resultado.html routes/costo_m2.py
  git commit -m "fix: TOTAL final en Costo/m2 (Beneficio/Seguros no se reflejaban) + limpieza jornales duplicados"
  git push
  ```

### Sesión 07/07/2026 (cont. 2) — Costo/m2: MO no reaccionaba al jornal + UI ⚠️ SIN COMMITEAR
Daniel reportó con un caso concreto (Mampostería ladrillo común 30cm): cambiar el jornal no movía el precio de MO en Costo/m2. Pidió además: header fijo (sticky) hasta la línea de Ayudante con Oficial/Ayudante alineados verticalmente, que se indique "Jornales adoptados por usuario" (o poder editarlos ahí mismo con recálculo en vivo), y que Beneficio/Seguros también recalculen en vivo — igual que ya hacen los materiales.

- **Causa raíz (bug de fondo, no solo de Costo/m2):** la fórmula `precio_mo_ars = hof×10000 + hay×5000` estaba hardcodeada en `_actualizar_mo_analisis()` (database.py) y en las migraciones 2h/2r — literalmente los valores default del jornal. **Nada en toda la app volvía a leer la tabla `config` y recalcular** después de la migración inicial. Resultado: cambiar el jornal en Admin > Precios, o el rendimiento HOF/HAY en Admin > Rendimientos, no modificaba el costo de MO de NINGÚN ítem — ni en Costo/m2 ni en un presupuesto nuevo. Esto es más grave que un bug de pantalla: significa que el jornal configurado en Admin era cosmético, no afectaba ningún cálculo real.
- **Fix de fondo:** nueva función `recalcular_precio_mo_ars(db, jornal_of_dia=None, jornal_ay_dia=None)` en `database.py` — recalcula `items_obra.precio_mo_ars` para todos los ítems con HOF/HAY, usando los jornales pasados o los de `config` si no se pasan. Se llama desde `routes/admin.py`:
  - `precios_actualizar()`: si se tocó el jornal, recalcula TODOS los ítems con el jornal nuevo.
  - `rendimientos_actualizar()`: al tocar HOF/HAY de un ítem, recalcula con el jornal vigente.
- **Costo/m2 (`templates/costo_m2/resultado.html`, `routes/costo_m2.py` sin cambios de backend):**
  - Header + fila de jornales ahora en un bloque `position:sticky` (queda fijo arriba al scrollear el desglose de materiales).
  - Jornales Oficial/Ayudante en un grid alineado verticalmente (antes texto corrido en una línea).
  - Jornales vuelven a ser **editables** (label "Jornales adoptados por usuario"), pero solo para **simular en vivo** — no tocan la DB ni lo configurado en Admin (mismo criterio que el precio editable de cada material). Aparece un badge "simulado, no guarda" cuando se apartan del valor adoptado.
  - JS `recalcAll()` reescrito: la MO ahora se recalcula en vivo a partir de HOF/HAY originales × jornal editado; Beneficio/Seguros siguen aplicándose sobre MO(en vivo)+Materiales, así que ahora si cambiás jornal, Beneficio o Seguros, TODO se mueve en cadena — igual que ya pasaba con el precio de los materiales.
- **Nota importante:** este fix de fondo (`recalcular_precio_mo_ars`) va a cambiar precios de MO reales la primera vez que se guarde cualquier cambio en Admin > Precios o Admin > Rendimientos (hoy no cambia nada porque el jornal configurado coincide con el default hardcodeado 80000/40000 — recién se nota si Daniel edita esos valores). Los presupuestos YA GUARDADOS no se recalculan solos (mismo comportamiento que otros fixes de precios anteriores).
- **Archivos tocados:** `database.py` (función nueva), `routes/admin.py` (2 funciones), `templates/costo_m2/resultado.html`.
- **Pendiente:** commitear vía Git Bash y deployar; probar: (1) cambiar el jornal Oficial en Admin > Precios y confirmar que la MO de "Mamp. ladrillo comun 30cm" en Costo/m2 cambia; (2) en Costo/m2, editar los jornales ahí mismo y ver que la tarjeta azul de MO se mueve en vivo + aparece el badge "simulado"; (3) editar Beneficio/Seguros y confirmar que el monto se recalcula sobre la MO simulada + materiales; (4) confirmar visualmente el header sticky y la alineación Oficial/Ayudante en el celular.
  ```
  cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
  rm -f .git/index.lock
  git add database.py routes/admin.py templates/costo_m2/resultado.html
  git commit -m "fix: MO en Costo/m2 no reaccionaba al jornal (config nunca se releia) + UI sticky/editable"
  git push
  ```

### Sesión 07/07/2026 (cont.) — Fix: bienvenida duplicada al registrarse ⚠️ SIN COMMITEAR
Daniel reportó (captura) que al entrar por primera vez aparecían 2 mensajes de bienvenida casi iguales: un alert gris dismissible ("¡Bienvenido, Jorge! Tenés 3 presupuestos gratis o 14 días...") arriba de todo, y la tarjeta naranja ("¡Bienvenido a PresupuestoPRO!...") de `dashboard.html` debajo — más el banner azul persistente de estado de prueba (ese es intencional, no es el duplicado).
- **Causa:** `routes/landing.py::registro()` hacía `flash(...)` con un texto de bienvenida al crear la cuenta; ese flash se renderiza en `base.html` (alert Bootstrap dismissible) en la primera carga del dashboard — al mismo tiempo que `mostrar_bienvenida_trial` (tarjeta naranja, más completa) se dispara por primer login. Resultado: 2 carteles con el mismo mensaje.
- **Fix:** se sacó el `flash(...)` de `registro()` (y el import `flash` que quedó sin uso) — queda solo la tarjeta naranja de `dashboard.html`, que además explica más (Costo/m², PDFs sin límite). El banner azul persistente de estado de prueba no se tocó.
- **Archivo tocado:** `routes/landing.py`.
- **Pendiente:** commitear vía Git Bash y deployar; probar registrando una cuenta nueva y confirmar que ahora aparece un solo cartel de bienvenida (naranja) + el banner azul de estado.
  ```
  cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
  rm -f .git/index.lock
  git add routes/landing.py
  git commit -m "fix: unificar mensaje de bienvenida duplicado al registrarse"
  git push
  ```

### Sesión 07/07/2026 — Campaña de lanzamiento: prueba gratis ✅ COMMITEADA Y PUSHEADA
Feature completa implementada, verificada con Read tool. **Confirmado commit + push** el 07/07 21:26 ART vía `git fetch origin main` (commit `86f9260`, idéntico en local y en GitHub) — la más grande de la app hasta ahora.

**Regla de negocio:** 3 presupuestos completos guardados O 14 días desde el alta, lo que se cumpla primero. Solo afecta cuentas nuevas con `es_trial=1` (alta por `/registro`); cuentas existentes/admin quedan en `es_trial=0`, sin cambios.

**Bloqueo:** suave, no total. El usuario en prueba vencida puede seguir entrando y viendo el dashboard/sus presupuestos ya hechos, pero no puede: crear/editar presupuestos, usar Costo/m², ni ver/descargar PDFs. Cada intento redirige a `/prueba-terminada` con invitación a suscribirse.

**Archivos nuevos:**
- `utils/trial.py` — `TRIAL_MAX_PRESUPUESTOS=3`, `TRIAL_MAX_DIAS=14`, `get_trial_status(user)`, decorator `trial_required`.
- `templates/registro.html` — formulario público de alta gratis (nombre, apellido, teléfono, email, ciudad, provincia, contraseña).
- `templates/trial_vencido.html` — pantalla de aviso al vencer la prueba, con botón a `/pagos/planes`.

**Archivos modificados:**
- `database.py` — columnas `users.es_trial` y `users.trial_visto` (default 0, migración condicional).
- `utils/auth.py` — `get_current_user()` deja entrar a `es_trial=1` aunque `subscription_expires` haya vencido (el corte es soft, vía `trial_required`, no en el login).
- `routes/landing.py` — nueva ruta `GET/POST /registro` (crea cuenta `es_trial=1`, loguea directo, sin pago) + `_notificar_registro()` (email admin con Reply-To al nuevo usuario).
- `routes/presupuesto.py` — `@trial_required` en `nuevo()` y `editar()`.
- `routes/costo_m2.py` — `@trial_required` en `index()` y `resultado()`; de paso se cambió su `_login_required` local (no seteaba `g.user`, hubiera roto `trial_required`) por `utils.auth.login_required`.
- `routes/pdf_routes.py` — `@trial_required` en `propietario_preview()`, `propietario()`, `constructor()`.
- `routes/dashboard.py` — `index()` calcula `trial` (estado) y `mostrar_bienvenida_trial` (solo primer login, marca `trial_visto=1`); nueva ruta `/prueba-terminada` (`dashboard.trial_vencido`).
- `templates/dashboard.html` — cartel de bienvenida (primer login) + banner persistente de estado de prueba (presupuestos/días restantes, o aviso de vencida) con botón "Suscribirme".
- `templates/login.html` — link "¿No tenés cuenta? Probá gratis" → `/registro`.
- `templates/manual.html` — sección 1 reescrita (alta gratis + suscripción paga como 2 caminos separados); sección 7 (Costo/m²) corregida (ya no dice que los jornales son editables); nueva sección 10 "Agregar a pantalla de inicio del celular" (guía iOS Safari / Android Chrome, antes de FAQ que pasó a ser la 11).

**Verificado (Read tool, no bash):**
- `pagos.planes()` no depende de `g.user` (usa `_get_user(session['user_id'])` directo) → el CTA de `trial_vencido.html` funciona sin tocar `pagos.py`, pese a que también tiene un `_login_required` local que no setea `g.user` (mismo patrón que tenía `costo_m2.py`, pero acá no importa porque `planes()` no lo necesita).
- Todas las columnas usadas en el INSERT de `/registro` (`apellido`, `telefono`, `ciudad`, `provincia`, `pais`, `es_trial`, `trial_visto`) existen en `users` vía migraciones ya confirmadas en `database.py`.
- Decoradores `@trial_required` están después de `@login_required` en los 5 endpoints gateados (`nuevo`, `editar`, `costo_m2.index`, `costo_m2.resultado`, `pdf.propietario_preview`, `pdf.propietario`, `pdf.constructor` — 7 en total).

**Pendiente:**
- [x] ~~Commitear TODO lo de esta sesión~~ ✅ hecho, push confirmado (ver nota arriba).
- [ ] Confirmar en producción que `journal_mode=WAL` (sesión 06/07) no dio "disk I/O error" real en el volumen de Railway — si pasa, revertir a `DELETE` en `database.py`.
- [ ] Probar en producción (post-deploy): alta por `/registro`, contador de 3 presupuestos / 14 días, bloqueo suave en `/prueba-terminada`.
- Ideal a futuro: mostrar `es_trial`/estado de prueba en `/admin/usuarios` (no pedido explícitamente todavía).

### Sesión 06/07/2026 — Reply-To notificaciones + limpieza landing vieja
- Confirmado y agregado Reply-To (email del remitente real) en las 3 funciones de notificación: Sugerencias, Contacto, Leads/Inscripción — así responder un email de notificación llega directo a esa persona en vez de a `noreply@`.
- `routes/landing.py`: eliminado código muerto — variable `LANDING_HTML` (landing vieja de pago directo) y vista `landing()`, sin tocar `contacto()` (sigue viva). Ver nota pendiente dentro del archivo: el redirect de `contacto()` apunta a `/landing`, ruta ya eliminada — no es un bug activo hoy (nada la usa) pero hay que corregirlo si se reactiva ese formulario.

### Sesión 04/07/2026 (noche) — Investigación desvío MO/Materiales presupuesto Petrini (cochera)
- Daniel reportó: Excel COCHERA "MO+MAT" = $12.155.162 vs App "todo junto" = $10.589.412. Excel MO sola = $5.902.594 vs App MO = $8.736.994. App Materiales = $6.113.898. Suma manual App (MO+MAT) = $14.850.892 — ni siquiera coincide con el "todo junto" de la propia app ($10.589.412).
- **Bug #1 encontrado y corregido — `items_obra.precio_mo_ars` desactualizado (4 instalaciones):** `_actualizar_mo_analisis()` escribe `precio_mo_ars` UNA sola vez (guard: solo corre si hay ítems con `precio_mo_ars` NULL/0) y nunca se vuelve a llamar. La migración 2h sí recalculaba `precio_mo_ars` después de tocar `hof`/`hay`; la migración 2m (corrigió HOF/HAY de las 4 instalaciones) **no lo hizo** — quedó desactualizado. Fix: migración `2r` (recalcula `precio_mo_ars = hof×10000 + hay×5000` para las 4 instalaciones con los HOF/HAY ya corregidos por 2m).
  - ⚠️ **Importante:** el efecto neto de este fix sobre el total de MO **depende de qué instalaciones y en qué cantidad tiene el presupuesto de Petrini**. Con los valores viejos (stale) vs corregidos: Desagües pasa de $85.500 a $367.500/u (+282.000), Agua F/C de $85.500 a $475.050/u (+389.550), Gas de $85.500 a $405.000/u (+319.500), Eléctrica de $475.050 a $85.500/u (−389.550). Si el presupuesto tiene 1 de cada una, el fix en realidad **aumenta** el MO total (~+$601.500), alejándolo del valor del Excel en vez de acercarlo. Osea: este bug es real y hay que corregirlo, pero probablemente **no explica por sí solo** la brecha de MO que reportó Daniel — falta el desglose de ítems/cantidades del presupuesto de Petrini para confirmar.
- **Explicación probable #2 — modo "Solo mano de obra" excluye materiales del total:** en `routes/presupuesto.py` (paso 5, `modo_tiempo()`) y `templates/presupuesto/paso8_resumen.html` (líneas 36-56), cuando `modo == 'solo_mo'`, el total final (`total_final`) se calcula como `total_mo + subcontratos + indirectos + GG% + Imp%` — **sin materiales**. La lista de "Materiales a comprar" y la línea de Costo Directo (MO+MAT combinado) solo se muestran si `modo == 'mo_mat'`. Esto podría explicar por qué el "total" de la app no coincide con la suma manual de MO + Materiales que hizo Daniel — a confirmar qué modo tiene este presupuesto.
- **Confirmado por Daniel:** el presupuesto está en modo "Mano de obra + materiales" (no solo_mo) y los 3 números salen del mismo presupuesto (tocando el selector de modo). Además: el presupuesto se empezó el 03/07, ANTES de las correcciones de precios de esta sesión (2q/2r).
- **Bug #2 encontrado y corregido — arquitectura de precios desconectada (la causa real de la brecha grande):**
  En `routes/presupuesto.py`, "Costo Directo" (que arma el TOTAL final en modo mo_mat) se calculaba así:
  ```python
  costo_directo = (p.get('costo_directo')
                   or p.get('total_mo_analisis', 0) + (_mat_total or p.get('total_materiales', 0)))
  ```
  `p.get('costo_directo')` viene de paso 2: `sum(cantidad × items_obra.precio_ars)` — el precio unitario "todo incluido" (materiales+MO juntos) de `items_obra`. Ese valor SIEMPRE existe (nunca es None/0 con ítems cargados), así que el `or` **nunca** llegaba a usar el cálculo de `analisis_sub`. Y se confirmó que **ninguna migración (2a a 2r) actualiza `items_obra.precio_ars`** — sigue siendo el precio semilla original de `init_db()`. O sea: dos catálogos de precios sin sincronizar — "Costo Directo/TOTAL" usaba el catálogo viejo (`items_obra.precio_ars`), mientras "MO" y "Materiales" (las vistas separadas) usan el catálogo activo (`analisis_sub`, el que corregimos toda esta sesión). Por eso el TOTAL de la app quedaba muy por debajo de MO+Materiales sumados a mano, y por eso ninguna corrección de precios de esta sesión afectaba el TOTAL cotizado al cliente.
  - **Decisión de Daniel (04/07/2026):** Costo Directo pasa a ser SIEMPRE `total_mo_analisis + total_materiales`, dejando de usar `items_obra.precio_ars` para el total.
  - **Fix aplicado en 3 lugares** (mismo patrón, buscar comentario "Fix 04/07/2026"):
    - `routes/presupuesto.py` → `modo_tiempo()` POST (rama `mo_mat`, ~línea 868-877): ahora `costo_directo = total_mo_analisis + materiales`, sin el `or` al valor viejo.
    - `routes/presupuesto.py` → `modo_tiempo()` GET (contexto `totales_ctx` para el JS de paso 5, ~línea 908-915): misma corrección.
    - `utils/pdf_generator.py` → `generar_pdf_constructor()` (~línea 287-295): el PDF interno para el constructor tenía la MISMA lógica vieja duplicada e independiente — corregido igual, sino el PDF hubiera mostrado un Costo Directo distinto al de la pantalla.
  - **Efecto esperado:** los presupuestos nuevos en modo "Mano de obra + materiales" van a dar un TOTAL más alto que antes (más realista, alineado con MO+Materiales de `analisis_sub`). Los presupuestos YA GUARDADOS no se recalculan solos — mantienen el total congelado de cuando se guardaron, a menos que se abran y regraben.
- **Pendiente:** commitear `routes/presupuesto.py` y `utils/pdf_generator.py` (además de `database.py` con 2q+2r) vía Git Bash. Después del deploy, rehacer o reabrir el presupuesto de la cochera de Petrini para validar que el nuevo TOTAL se acerca al del Excel ($12.155.162 MO+MAT).

### Sesión 04/07/2026 (noche, cont.) — Refactor completo: única fuente de verdad para los totales
- Daniel volvió a probar el presupuesto de la cochera (recién recargado) y seguía viendo números distintos en distintas pantallas de la MISMA carga: paso 5 mostraba Costo Directo $12.593.801 (¡ya cerca del Excel, $12.155.162!) pero paso 2 seguía mostrando "COSTO DIRECTO TOTAL" $10.589.412 (el número viejo). Pidió una solución definitiva, no más parches sueltos.
- **Encontrados 5 lugares distintos calculando el mismo total, cada uno a su manera:**
  1. `paso2_rubros.html` (JS en el navegador) — vista previa en vivo mientras cargás cantidades, calculaba `cantidad × items_obra.precio_ars` (dato embebido en `data-precio`). Nunca pasaba por el servidor.
  2. `rubros()` POST (paso 2, servidor) — guardaba `total_rubro`/`total_local` también con `precio_ars`, y una lista de materiales aproximada (sin expandir Hormigón/Armadura/Encofrado).
  3. `modo_tiempo()` POST/GET (paso 5) — ya arreglado en la sesión anterior, pero dependía de `total_materiales` calculado en el paso 2 (el aproximado), no del más preciso de paso 6 — bug de orden: paso 5 corre ANTES que paso 6 en el wizard.
  4. `generar_pdf_constructor()` — tenía su propia copia de la lógica vieja (ya arreglada).
  5. `calcular_totales()` en `utils/calculations.py` — importada pero nunca usada; mismo bug viejo.
- **Refactor aplicado (todo en `routes/presupuesto.py` salvo aclaración):**
  - Nueva función `_mo_materiales_frescos(p)`: única fuente de verdad para MO (`items_obra.precio_mo_ars` en vivo) y Materiales (`_calcular_materiales_desde_rubros`, con expansión recursiva completa). Se llama en `modo_tiempo()` (paso 5) ANTES de calcular nada, así ya no importa que corra antes que paso 6.
  - Nueva función `_calcular_totales_finales(modo, total_mo, total_materiales, subc, ind, pct_gg, pct_imp, operarios_reales)`: única fuente de verdad para Costo Directo/Base/GG/Impuestos/TOTAL. La usan `modo_tiempo()` (paso 5) Y `resumen()` (paso 8, recalculado una última vez justo antes de guardar — por si se editaron materiales a mano en paso 6 después de paso 5).
  - Nueva función `_materiales_por_unidad_items()`: costo de materiales por 1 unidad de cada ítem (con expansión recursiva), usada para que la vista previa en vivo de paso 2 (JS) muestre MO+Materiales reales en vez de `items_obra.precio_ars`.
  - `rubros()` (paso 2): cada ítem ahora trae `mat_ars` (materiales por unidad) además de `precio_mo_ars` (ya existía en items_obra). El subtotal por ítem, por rubro y "COSTO DIRECTO TOTAL" de paso 2 pasan a ser MO+Materiales, iguales a los de paso 5/8.
  - `paso2_rubros.html`: JS y HTML actualizados — `data-mo`/`data-mat` en vez de `data-precio`; columnas "P. Unit" y "Subtotal" muestran MO+Materiales.
  - `utils/calculations.py`: eliminada `calcular_totales()` (código muerto con el bug viejo); import correspondiente removido en `routes/presupuesto.py`.
- **Resultado:** ahora hay UNA sola fuente de verdad para MO, UNA para Materiales, y UNA para Costo Directo/Total — usadas de punta a punta en paso 2, paso 5, paso 8 y los PDFs. `items_obra.precio_ars` dejó de usarse en cualquier cálculo de costos.
- **Pendiente:** commitear todos los archivos tocados en esta sesión vía Git Bash (`database.py`, `routes/presupuesto.py`, `utils/pdf_generator.py`, `utils/calculations.py`, `templates/presupuesto/paso2_rubros.html`, `PROYECTO.md`) y volver a probar el presupuesto de la cochera desde cero (borrador nuevo, no uno viejo) para confirmar que las 3 pantallas (paso 2, paso 5, paso 8) muestran el mismo número, y que ese número se acerca al Costo Directo del Excel ($12.155.162).
- **Ojo — el Excel de Petrini usa una estructura de márgenes distinta a la app**, esto NO es un bug, es una diferencia de fórmula a tener en cuenta al comparar el TOTAL final (no el Costo Directo): el Excel aplica I.Brutos 1% + Seguros 3% + Otros 3% + G.Grales/Beneficio 20% (27% en total) calculados **como % del TOTAL final** (fórmula circular: TOTAL = COSTO_TOTAL / (1 − 0,27)), mientras la app aplica %GG y %Impuestos **como % del Costo Directo/Base** (forma directa: TOTAL = Base × (1 + %GG + %Imp)). Además la captura del Excel usa G.Grales/Beneficio=20% + Impuestos=7% (I.Brutos+Seguros+Otros), y la app por defecto trae 10%/7%. Con Costo Directo ya alineado, para que el TOTAL FINAL también se acerque al del Excel hay que cargar los mismos porcentajes (20% en vez de 10% en "Gastos generales/Beneficio") — la diferencia de fórmula (circular vs directa) va a dejar igual un resto de diferencia menor, no es corregible sin rehacer la fórmula de márgenes de la app.

### Sesión 04/07/2026 (noche, cont. 2) — Botones ocultos paso 2 + defaults paso 5
- Daniel confirmó por capturas que MO ya coincide EXACTO con el Excel ($5.902.594) y Costo Directo quedó ~1.3% cerca — aclaró que esa diferencia chica es tolerable, no perseguirla más ("no es cuestión de vida o muerte"). Pidió 2 arreglos nuevos, menores:
- **Fix #1 — Botones "Anterior/Siguiente" tapados en paso 2:** en `templates/presupuesto/paso2_rubros.html`, la tarjeta "Barra total sticky" tenía `position:sticky; top:60px; z-index:100`, casi el mismo `top` que la barra global `.wizard-sticky-nav` (`static/css/style.css`, `top:56px; z-index:99`) pero con z-index más alto → la tapaba completo. Corregido: `top:106px; z-index:90` (queda debajo de la barra de navegación y no se solapa).
- **Fix #2 — Paso 5 (modo_tiempo): defaults de Oficiales/Ayudantes y jornales:**
  - Nueva función `get_config_jornales()` en `routes/presupuesto.py` (mismo patrón que `get_config_pct()`), lee `jornal_oficial_dia`/`jornal_ayudante_dia` de la tabla `config` (defaults 80.000/40.000, igual que `routes/admin.py`).
  - En `modo_tiempo()` GET: se agregó `p.setdefault('n_oficiales', 1)` (antes 2) y `p.setdefault('n_ayudantes', 1)`, y si `jornal_oficial`/`jornal_ayudante` no están cargados (0 o ausentes) se completan con los valores de `get_config_jornales()` en vez de mostrar 0,0.
  - POST de `modo_tiempo()`: default de `n_oficiales` cambiado de 2 a 1 (fallback si el form no lo manda).
  - `templates/presupuesto/paso5_modo_tiempo.html`: fallback Jinja de `n_oficiales` cambiado de 2 a 1 (los campos de jornal ya toman el valor real desde `p`, no hace falta tocar su fallback).
- **Pendiente:** commitear `routes/presupuesto.py`, `templates/presupuesto/paso2_rubros.html`, `templates/presupuesto/paso5_modo_tiempo.html` y este `PROYECTO.md`. Probar en un presupuesto nuevo: paso 2 con botones visibles al hacer scroll, y paso 5 mostrando 1 Oficial/1 Ayudante + jornales precargados (no 0,0) al entrar por primera vez.

### Sesión 05/07/2026 (cont. 9) — Costo/m² igualado al presupuesto real + panel admin de usuarios
- Daniel pidió (1) verificar si Costo/m² calcula igual que el presupuesto (ya verificado/validado contra Excel), y (2) un panel admin con listado de usuarios + cantidad de presupuestos + consultas de Costo/m² + filtros por localidad/provincia/país.
- **Verificación de Costo/m² — CONFIRMADO que NO calculaba igual (bug real):**
  - Materiales: `routes/costo_m2.py` hacía `SELECT ... FROM analisis_sub WHERE item_nombre=?` directo, sin la normalización de nombres (`normalize_nombre`/`ANALISIS_NAME_MAP`), sin la expansión recursiva de ítems compuestos (`_resolver_material`, usada por ej. en "Ho.Ado. pavimento 15cm" → Hormigón colado/Armadura/Encofrado se expanden a sus materiales reales) y sin la conversión kg→bolsas. Probado en sandbox: para "Ho.Ado. pavimento 15cm" el cálculo viejo hubiera dado ~$53.442 en materiales tomando "Hormigón colado"/"Armadura colocada" como si fueran materiales sueltos; el cálculo correcto (expandido) da $80.781.
  - MO: usaba el jornal editable en pantalla (`hof×jornal_hora + hay×jornal_hora`) en vez del costo ya congelado en `items_obra.precio_mo_ars` (el que realmente se cobra en un presupuesto real — cambiar el jornal en paso 5 del asistente NO cambia lo que se termina cobrando).
  - GG/Impuestos: 10%/5% fijos en el código, aplicados solo sobre MO. El presupuesto usa los % configurables de Admin (hoy 20%/7%) aplicados sobre MO+Materiales.
  - **Decisión de Daniel: igualar 100%.** Fix aplicado en `routes/costo_m2.py`: materiales ahora se calculan llamando a `_calcular_materiales_desde_rubros()` (la MISMA función del presupuesto real, importada de `routes/presupuesto.py`) con un "presupuesto sintético" de 1 solo ítem y cantidad=factor de conversión m³→m²; MO usa `item['precio_mo_ars']` (mismo costo congelado); GG/Impuestos usa `get_config_pct()` (mismos % configurables) aplicados sobre MO+Materiales. Verificado con un test standalone (fuera del mount, en `/tmp`, por el problema de mojibake de `database.py` en este entorno) que reproduce exactamente los números ya validados contra Excel (MO = $35.250 para "Mamp. ladrillo comun 30cm", igual al valor de referencia documentado arriba en este archivo).
  - `templates/costo_m2/resultado.html`: los inputs de jornal editables se reemplazaron por una línea informativa de solo lectura ("Jornales de referencia: los mismos del presupuesto"); el JS se reescribió (`recalcAll()`) para recalcular GG/Impuestos sobre MO(fijo)+Materiales cuando se edita el % o el precio de un material (el precio unitario de cada material sigue editable, para simular variaciones — eso no formaba parte del bug).
- **Panel admin de usuarios (`/admin/usuarios`) ampliado:**
  - `routes/admin.py::usuarios()`: agrega 3 columnas por usuario vía subqueries: presupuestos con `status='completo'`, presupuestos con `status='borrador'`, y consultas a `costo_m2_consultas`. Filtros por `f_ciudad` (LIKE), `f_provincia` (LIKE, con datalist de provincias ya cargadas) y `f_pais` (select con `PAISES` de `utils/calculations.py`), todos vía querystring GET.
  - Nueva tabla `costo_m2_consultas` (`database.py`): se inserta una fila cada vez que un usuario ve un resultado en `routes/costo_m2.py::resultado()` — no había ningún tracking de esto antes, así que el conteo arranca en cero desde el próximo deploy (no hay historial previo).
  - `templates/admin/usuarios.html`: form de filtros arriba de la tabla + 3 columnas nuevas (Presup. / Borr. / Costo/m²).
- **Nota de entorno (importante, no es un bug real):** durante la verificación de `database.py` en este chat, confirmé de forma concluyente el mojibake ya documentado más arriba — una copia (`cp database.py database_check.py`) hecha desde bash en este entorno mostró un `SyntaxError` real por un literal de string sin cerrar cerca de "Zócalo" (corrupción de acentos al leer el archivo a través del mount). Esto solo afecta la verificación en ESTE chat, no el archivo real ni Railway. **Quedó un archivo `database_check.py` en la carpeta del proyecto que no pude borrar desde acá (permiso denegado) — Daniel: por favor borralo manualmente, es una copia de prueba sin uso, no hace falta commitearlo.**
- **Otra nota de entorno:** confirmé que `PRAGMA journal_mode=WAL` funciona sin problema en una copia de la base en un filesystem normal, pero falla con "disk I/O error" al ejecutarse directamente sobre el archivo dentro de la carpeta montada de este chat. Es muy probablemente una limitación del mount de ESTE entorno (no del volumen real de Railway, que es un filesystem normal), pero de todas formas **conviene verificar con cuidado en Railway después del deploy** que WAL funciona bien ahí (por las dudas, si tirara "disk I/O error" en producción, el fix es volver `journal_mode` a `DELETE` en `database.py`).
- **Archivos tocados:** `routes/costo_m2.py` (reescrito), `templates/costo_m2/resultado.html`, `database.py` (tabla `costo_m2_consultas`), `routes/admin.py` (filtros + conteos en `usuarios()`), `templates/admin/usuarios.html`.
- **Pendiente:** commitear y deployar; probar en producción: (1) Costo/m² de un ítem compuesto (ej. cualquier "Ho.Ado...") y confirmar que el desglose de materiales coincide con lo que muestra el paso 6 de un presupuesto con ese mismo ítem; (2) `/admin/usuarios` con los filtros de localidad/provincia/país; (3) confirmar que WAL no da error en Railway (ver nota arriba); (4) borrar manualmente `database_check.py` de la carpeta del proyecto.

### Sesión 05/07/2026 (cont. 8) — Manual del Usuario como página web dentro de la app
- Daniel preguntó si el Manual quedó dentro de la app o solo como PDF (quedó solo como PDF suelto). Preguntó si se puede armar como página web igual que la landing. Decisión: sí, página web (mejor que PDF: siempre actualizada, se ve bien en el celular, URL fija) + link en el menú principal junto a Sugerencias.
- **Implementado:**
  - `routes/manual.py` (nuevo blueprint): ruta `/manual`, `@login_required`, renderiza `templates/manual.html`.
  - `templates/manual.html` (nuevo): mismo contenido del PDF pero en HTML con el estilo Bootstrap de la app (cards `card-header-blue`, acordeón para los 8 pasos del wizard y para el FAQ, índice lateral sticky con anchors en desktop).
  - `templates/base.html`: nuevo link "Manual de uso" en el menú principal, junto a "Sugerencias".
  - `app.py`: registrado `manual.bp`.
  - Verificado con Read (`app.py`, `base.html`) y con un parseo real de Jinja2 (`env.get_template('manual.html')`) que el template no tiene errores de sintaxis.
- **El PDF (`Manual_Usuario_PresupuestoPRO.pdf`) se mantiene** como archivo descargable aparte (por si Daniel lo quiere compartir por fuera de la app), pero la referencia "oficial" para los usuarios pasa a ser la página `/manual`.
- **Archivos nuevos:** `routes/manual.py`, `templates/manual.html`.
- **Archivos tocados:** `app.py`, `templates/base.html`.
- **Pendiente:** commitear (sumar a la tanda pendiente) y deployar; probar `/manual` logueado, confirmar que el acordeón de los 8 pasos y el FAQ abren/cierran bien y que el índice lateral funciona.

### Sesión 05/07/2026 (cont. 7) — Fix portada del Manual, tildes, WAL, mail de notificaciones
- Daniel reportó que en la página 1 del Manual el título y subtítulo estaban superpuestos, y que `presupuestopro.com.ar` parecía salir dos veces cortado en la misma línea. Pidió también restaurar tildes/caracteres especiales (el manual anterior los había evitado por precaución, quedando sin acentos) y preguntó por el mail que recibe las notificaciones de la app, y pidió pasar a WAL.
- **Causa real de la portada:** la línea de dominios tenía `stopro.com.ar · presupuestopro.com.ar` — `stopro.com.ar` comparte el sufijo `pro.com.ar` con `presupuestopro.com.ar`, así que a simple vista parecía el mismo dominio duplicado y cortado. Además, `stopro.com.ar` NO es un dominio oficial verificado en el proyecto (solo aparece mencionado una vez en un reporte de bug de Daniel) — se sacó de la portada, quedando solo `presupuestopro.com.ar`. El título/subtítulo se separaron con `Spacer` explícitos (antes dependían de `spaceAfter` insuficiente para una fuente de 28pt) — ya no se superponen.
- **Tildes:** el manual se reescribió completo con acentos y caracteres especiales correctos (á é í ó ú ñ ¿ ¡ ² ³) — el font base Helvetica de reportlab los soporta sin problema (no había motivo real para haberlos evitado la primera vez).
- **Nota de infraestructura:** el script de generación (`build_manual.py`, fuera del repo) volvió a mostrar el mismo síntoma de bash con contenido stale tras 2-3 ediciones seguidas en la misma sesión (`SyntaxError` falso en una línea que Read confirmó completa). Se resolvió escribiendo el contenido final en un archivo con nombre nuevo (`manual_final.py`, nunca antes tocado en la sesión) y ejecutando ese — bash lo leyó bien al no tener caché previa de ese nombre. Puede ser un atajo útil la próxima vez que esto pase con cualquier archivo.
- **Mail de notificaciones (respondido):** todo el código (`routes/landing.py`, `routes/dashboard.py`, `routes/pagos.py`, `routes/sugerencias.py`) usa `os.environ.get('ADMIN_EMAIL', 'danve61@gmail.com')` — o sea, si la variable `ADMIN_EMAIL` no está seteada en Railway, todas las notificaciones (contacto, leads, sugerencias, activaciones) van a **danve61@gmail.com** por defecto. La tabla de variables de entorno más arriba ya marcaba esto como "⚠️ Verificar" — recomendado confirmar en Railway → Variables si `ADMIN_EMAIL` está explícitamente seteada (y a qué dirección) o si depende del default.
- **WAL aplicado:** `database.py::get_db()` — `PRAGMA journal_mode=DELETE` → `PRAGMA journal_mode=WAL`. Permite lecturas concurrentes mientras hay una escritura en curso (antes cada escritura bloqueaba el archivo entero por un instante). Decisión de Daniel: aplicarlo ya de cara al lanzamiento.
- **Logo agregado a la portada del Manual:** `IMAGENES/LOGO SOLO limpio v3.png` (confirmado visualmente que es el logo correcto), insertado centrado arriba del título en la portada.
- **Aclarado (sin cambios de código):** pasar a WAL es un cambio puramente de almacenamiento/concurrencia de SQLite — no toca ninguna fórmula de cálculo (precios, MO, materiales, totales, márgenes siguen exactamente igual).
- **Archivos tocados:** `database.py` (WAL), `Manual_Usuario_PresupuestoPRO.pdf` (regenerado, con logo).
- **Pendiente:** commitear TODO lo acumulado sin commitear de esta sesión y de sesiones anteriores (ver lista completa de `git status` de esta sesión) y deployar; después del deploy, SQLite va a crear automáticamente los archivos `presupuestopro.db-wal` y `presupuestopro.db-shm` junto al `.db` en el volumen de Railway — es comportamiento normal de WAL, no un error.

### Sesión 05/07/2026 (cont. 6) — Capacidad de usuarios, sección Sugerencias, Manual del Usuario
- Daniel preguntó por capacidad de usuarios simultáneos/totales de cara al lanzamiento, y pidió un Manual del Usuario (PDF) y una sección de Sugerencias.
- **Capacidad (respondido, sin cambios de código):** stack actual = gunicorn 2 workers sync + SQLite con `journal_mode=DELETE` (no WAL) — cada escritura bloquea el archivo entero brevemente; hay `timeout=20` en la conexión así que reintenta en vez de tirar error. Estimado con esta arquitectura: cómodo ~20-30 usuarios simultáneos activos, funcional con algo de latencia hasta ~50-80; usuarios totales registrados (no simultáneos) sin problema hasta varios miles, dado el patrón de uso espaciado. Recomendación de bajo costo antes del lanzamiento si se espera un pico de tráfico: pasar `journal_mode` a `WAL` y subir a 3-4 workers; si crece sostenido, evaluar migrar a Postgres (addon de Railway). **Pendiente de decisión de Daniel:** si aplicar el cambio a WAL antes del lanzamiento o dejarlo para después.
- **Nueva sección "Sugerencias" implementada** (decisión de Daniel: formulario + panel admin + email automático):
  - `database.py`: nueva tabla `sugerencias` (`id, user_id, mensaje, leido, respondida, created_at`), creada vía `CREATE TABLE IF NOT EXISTS` en `migrate_db()`.
  - `routes/sugerencias.py` (nuevo blueprint): `/sugerencias` GET/POST, `@login_required`. POST guarda el mensaje y dispara email al admin (mismo patrón que `routes/landing.py::contacto()`, usando `RESEND_API_KEY`/`ADMIN_EMAIL`). GET muestra el formulario + lista de sugerencias propias del usuario con estado "Enviada"/"Respondida".
  - `templates/sugerencias.html` (nuevo): formulario simple + historial propio.
  - `routes/admin.py`: nueva vista `/admin/sugerencias` (mismo patrón visual que `/admin/contactos`) con botón "Marcar respondida"; nuevo stat `sugerencias_nuevas` en el dashboard admin.
  - `templates/admin/dashboard.html`: nuevo botón de acceso rápido "💡 Sugerencias de usuarios" con badge de nuevas.
  - `templates/base.html`: nuevo link "Sugerencias" en el menú principal (usuarios logueados).
  - `app.py`: registrado `sugerencias.bp`.
  - **Verificado con Read/Grep (no bash)** que las 3 funciones nuevas (`_redir_next`, `_actualizar_descripcion_con_faltantes`, tabla `sugerencias`) y los edits de `app.py`/`routes/admin.py` quedaron completos — `py_compile` vía bash volvió a mostrar un falso `SyntaxError` en `app.py` (paréntesis "sin cerrar" que sí está cerrado al leerlo con Read). **Se amplía la regla de infraestructura: agregar `app.py` a la lista de archivos que no hay que verificar con bash dentro de esta misma sesión de chat** (además de `database.py`, `routes/presupuesto.py`, `utils/pdf_generator.py`).
  - **Pendiente:** commitear y deployar; probar en producción: cargar una sugerencia como usuario normal, confirmar que llega el email al admin y que aparece en `/admin/sugerencias`; marcarla "Respondida" y confirmar que el usuario la ve así en su propia lista.
- **Manual del Usuario (PDF) creado:** `Manual_Usuario_PresupuestoPRO.pdf` (6 páginas), generado con reportlab a partir de una exploración real del código (templates de los 8 pasos del wizard, dashboard, perfil, costo/m2, sugerencias) — no es contenido genérico. Cubre: alta/suscripción, login/recuperar contraseña, Dashboard, los 8 pasos del asistente en detalle, navegación entre pasos y borradores, Ver/Editar/PDF Propietario/PDF Constructor, Costo/m², Mi Empresa, Sugerencias, y FAQ. Guardado en la carpeta del proyecto.
- **Archivos nuevos:** `routes/sugerencias.py`, `templates/sugerencias.html`, `Manual_Usuario_PresupuestoPRO.pdf`.
- **Archivos tocados:** `database.py` (tabla `sugerencias`), `routes/admin.py` (vista + stat), `templates/admin/dashboard.html`, `templates/base.html`, `app.py` (registro de blueprint).

### Sesión 05/07/2026 (cont. 5) — Fix navegación wizard, descripción no sumaba subcontratos, "Accesorios" genérico
- Daniel reportó 3 bugs nuevos después de probar:
- **(1) Navegación entre pasos por ícono saltaba al paso equivocado** (ej. de 2 a 7 iba al 3; de 5 a 2 iba al 6, y reintentando iba al 7). **Causa real:** el JS `wizardGoto(this.href)` en `_wizard_steps.html` pasaba `this.href`, que en el DOM devuelve la URL ABSOLUTA (con dominio, ej. `https://stopro.com.ar/presupuesto/forma_pago`) en vez de la ruta relativa que generaba `url_for()`. Como `_redir_next()` (routes/presupuesto.py) solo acepta destinos que empiecen con `/presupuesto/`, esa URL absoluta nunca pasaba el filtro y SIEMPRE caía al `default_url` (el paso siguiente por defecto) — por eso cualquier ícono clickeado terminaba llevando a "paso actual + 1", sin importar cuál se hubiera tocado. **Fix:** `_wizard_steps.html` ahora usa `this.getAttribute('href')` (ruta relativa, tal cual la generó `url_for()`); además `_redir_next()` se endureció usando `urlparse(destino).path` para funcionar igual aunque llegue una URL absoluta.
- **(2) Al editar un presupuesto ya guardado y agregar un subcontrato nuevo, no se sumaba a la Descripción de trabajos.** Causa: `_generar_descripcion_trabajos()` solo se ejecutaba si la descripción estaba TOTALMENTE vacía (para no pisar texto ya editado a mano) — pero eso significaba que editar y agregar algo nuevo nunca lo sumaba. **Fix:** nueva función `_actualizar_descripcion_con_faltantes()` que, si la descripción ya tiene texto, detecta qué nombres de ítems/subcontratos ("SC {nombre}") todavía NO aparecen como texto en ella y los inserta antes de "Limpieza de obra." (o al final si esa frase no está) — sin tocar el resto del texto ya escrito.
- **(3) "Accesorios" seguía apareciendo genérico en vez de "Accesorios Desagües"/"Accesorios TF"/"Accesorios Gas" (nombres de la lista V3).** Causa real encontrada en `database.py`: la migración `2n` (04/07/2026, resincronización contra `PRESUPUESTO COCHERA.xlsx`) reinsertó estos 3 materiales con el nombre genérico "Accesorios" para 'Instalacion Desague'/'Instalacion Agua F/C'/'Instalacion Gas', perdiendo la distinción que sí tiene la fuente canónica (`utils/analisis_data.py`: Desague→"Accesorios Desagues", Agua F/C→"Accesorios TF", Gas→"Accesorios Gas"). Efecto secundario no menor: la migración `2q` (que sí trae los precios reales de la lista V3, buscando por `sub_nombre` EXACTO) nunca encontraba esos 3 nombres específicos desde entonces, así que tampoco les actualizaba el precio real. **Fix:** (a) corregidos los 3 nombres en la lista fuente `SUBS_2N`; (b) nueva migración `2s` (guardia `2s_done`, corre en el próximo deploy) que renombra los registros YA guardados en la base de producción (`sub_nombre='Accesorios'` → nombre específico) y les aplica el precio real de la V3 en el mismo paso.
- **Archivos tocados:** `templates/presupuesto/_wizard_steps.html`, `routes/presupuesto.py` (`_redir_next` con urlparse, `_actualizar_descripcion_con_faltantes`, call site en `resumen()`), `database.py` (migración `2s`, fix nombres en `SUBS_2N`).
- **Pendiente:** commitear y deployar; probar: (1) saltar entre varios pasos con los íconos verdes en cualquier orden y confirmar que siempre lleva al paso clickeado; (2) editar un presupuesto ya guardado, agregar un subcontrato nuevo, y confirmar que aparece "SC {nombre}" en la descripción de paso 8 sin borrar el resto del texto; (3) crear un presupuesto con Instalación Desagüe/Agua/Gas y confirmar que en paso 6/PDF figuran como "Accesorios Desagües"/"Accesorios TF"/"Accesorios Gas" con el precio de la V3 (8500/3000/3500), no "Accesorios" genérico.

### Sesión 05/07/2026 (cont. 4) — Subcontratos en descripción de trabajos y en tabla de items del PDF
- Daniel pidió que la oración autogenerada y la tabla "Items de obra a realizar" del PDF también incluyan los subcontratos (antes solo tomaban ítems de rubros).
- **Implementado:**
  - `_generar_descripcion_trabajos(rubros, subcontratos=None)`: ahora agrega, antes de "Limpieza de obra.", un token `SC {nombre}` por cada subcontrato cargado (ej. "SC Electricidad", "SC Plomería"), sin duplicados.
  - `resumen()` (paso 8): pasa `p.get('subcontratos', [])` a la función de arriba.
  - Subcontratos ahora tienen `cantidad`/`unidad` (antes no existía el concepto): `subcontratos()` POST (`routes/presupuesto.py`) captura `subc_{id}_cant`/`subc_{id}_unidad` (sugeridos) y `custom_{n}_cant`/`custom_{n}_unidad` (personalizados), default `1`/`Global`, con try/except para evitar un 500 si se ingresa un valor no numérico en cantidad.
  - `templates/presupuesto/paso3_subcontratos.html`: agregados inputs de Cantidad/Unidad (editables) junto a MO/Materiales, tanto para subcontratos sugeridos como para los personalizados (`agregarSubc()`/`agregarSubcPrellenado()`); el pre-fill (`SUBC_PREV`) ahora también completa estos 2 campos al reeditar un presupuesto.
  - `utils/pdf_generator.py` → `generar_pdf_propietario()`: la tabla "Items de obra a realizar" ahora agrega, después de los ítems de rubros, una fila por cada subcontrato con nombre (prefijo "SC"), cantidad y unidad.
- **Archivos tocados:** `routes/presupuesto.py`, `templates/presupuesto/paso3_subcontratos.html`, `utils/pdf_generator.py`.
- **Pendiente:** commitear y deployar; probar: cargar un presupuesto con subcontratos (con cantidad/unidad editada, ej. "2 Global" o "1 Cuadra"), confirmar que en paso 8 la descripción incluye "SC {nombre}" antes de "Limpieza de obra", y que el PDF a propietario lista esos subcontratos en la tabla de items con su cantidad/unidad.

### Sesión 05/07/2026 (cont. 3) — Descripción de trabajos autogenerada en paso 8
- Charla sobre dónde conviene armar la "Descripción de trabajos": Daniel decidió sacarla de paso 1 (ahí todavía no existen los ítems, se cargan recién en paso 2) y autogenerarla en paso 8 como una oración simple, SIN cantidades (las cantidades ya están en la tabla "Items de obra a realizar" del PDF, agregada antes en esta misma sesión — poner cantidades de nuevo acá hubiera sido redundante).
- **Implementado:**
  - `templates/presupuesto/paso1_obra.html`: sacado el textarea "Descripción de trabajos".
  - `routes/presupuesto.py` → `nuevo()` POST: ya NO pisa `descripcion_trabajos` con `''` (antes lo hacía porque el campo del form ya no existe — se sacó esa clave del `p.update()` para no perder la descripción al reeditar un presupuesto que ya la tenía).
  - Nueva función `_generar_descripcion_trabajos(rubros)`: arma "Se realizarán los siguientes trabajos: {item1}, {item2}, ..., Limpieza de obra." a partir de los nombres de ítems con cantidad > 0 (sin duplicados, sin cantidades).
  - `resumen()` (paso 8): si `descripcion_trabajos` está vacía, se autogenera con la función de arriba — pero solo si está vacía, para no pisar una ya guardada o editada a mano. Sigue siendo 100% editable en el textarea de paso 8 antes de guardar (el constructor puede "adornarla" como quiera).
- **Archivos tocados:** `routes/presupuesto.py`, `templates/presupuesto/paso1_obra.html`.
- **Pendiente:** commitear y deployar; probar: crear un presupuesto nuevo, cargar ítems en paso 2, y confirmar que en paso 8 el campo "Descripción de trabajos" ya viene con la oración generada (editable).

### ⚠️ Regla ampliada — bash muestra copias viejas/truncadas de archivos muy editados en una sesión
Ya estaba documentado para `database.py` ("nunca commitear desde bash, tiene mojibake"). Esta sesión (05/07/2026) se confirmó que el MISMO síntoma afecta a cualquier archivo con muchas ediciones seguidas en un mismo chat — pasó también con `utils/pdf_generator.py` y `routes/presupuesto.py`: bash (`py_compile`, `cat`, `grep` de contenido puntual) mostraba el archivo cortado a la mitad de una función, con errores de sintaxis que NO existen en el archivo real (confirmado comparando con el resultado de la herramienta Read, que es la fuente de verdad). **Regla general: para verificar sintaxis/contenido de archivos editados varias veces en la misma sesión, confiar en Read/Edit, no en bash.** No afecta el archivo real ni Railway (que clona el repo real desde git) — es una limitación de este entorno de chat para probar en vivo.

### Sesión 05/07/2026 (cont. 2) — Bug "Olvidé mi contraseña" (Error Interno del Servidor)
- Daniel reportó Error Interno del Servidor al entrar por "Olvidé mi contraseña" en stopro.com.ar.
- **Causa:** `routes/auth.py` (`recuperar()` y `restablecer()`) usa la tabla `password_reset_tokens` desde siempre, pero esa tabla **nunca se creó** — ni en `init_db()` ni en `migrate_db()`. En producción, el `INSERT INTO password_reset_tokens` tira `no such table` → 500.
- **Fix:** agregada `CREATE TABLE IF NOT EXISTS password_reset_tokens (id, user_id, token, expires_at, used, created_at)` en `migrate_db()` (para la DB ya existente en Railway) y en `init_db()` (para instalaciones nuevas). `RESEND_API_KEY` ya está configurada en Railway, así que una vez creada la tabla el email de recuperación debería enviarse normalmente.
- **Archivo tocado:** `database.py`.
- **Pendiente:** commitear y deployar; probar "Olvidé mi contraseña" en stopro.com.ar con un email real registrado.

### Sesión 05/07/2026 (cont.) — Fix definitivo navegación, Total Final, PDF materiales y salto de página
- Daniel probó lo anterior y reportó 3 problemas nuevos: (1) la frecuencia de pago TODAVÍA se pierde al ir a paso 2/5 y volver a 7 (a veces con el TOTAL mostrando $0 momentáneamente), (2) el Total Final de paso 5 ($14.059.296) no coincidía con el del PDF guardado ($13.788.722), (3) el PDF no mostraba materiales en modo MO+Materiales y desperdiciaba una hoja casi vacía (solo membrete y firma).
- **Causa real de (1):** no era el botón "Anterior" de paso 7 (ya arreglado la vez anterior) — era la navegación NUEVA por íconos verdes de `_wizard_steps.html`, que son links `<a href>` planos: saltar de paso 7 a 5 con el ícono (en vez del botón Anterior) descartaba la frecuencia igual, por la misma razón (nunca pasa por el servidor a guardar). Además había un segundo punto de riesgo real en `rubros()` GET (paso 2): un fallback que reemplazaba `session['presup']` ENTERO por un snapshot viejo de la DB sin mergear con la sesión actual — podía pisar cualquier cosa recién guardada (frecuencia incluida) y por eso a veces el total volvía a $0 momentáneamente.
  - **Fix general (no solo parche puntual):** nueva función `_redir_next()` en `routes/presupuesto.py` + JS global `wizardGoto()` (en `base.html`). Todos los botones "Anterior" de los 8 pasos ahora son `<button type="submit">` con `name="_next" value="<url destino>"` (guardan antes de navegar). Los íconos de `_wizard_steps.html` ahora llaman a `wizardGoto()`: si la página tiene un `<form data-wizard-form>`, lo guarda (agregando `_next` como campo oculto) ANTES de saltar de paso. Cada handler POST del wizard revisa `_next` y redirige ahí en vez de al paso siguiente por defecto. Se excluyó a propósito paso 8 (resumen) de este mecanismo — su POST finaliza el presupuesto (genera nro, borra la sesión), así que convertir su "Anterior" en un submit hubiera finalizado presupuestos sin querer.
  - También se corrigió el fallback riesgoso de `rubros()` GET para que mergee (`{**p_db, **p}`) en vez de reemplazar la sesión entera.
- **Causa real de (2):** `modo_tiempo()` GET armaba el contexto para paso 5 con una fórmula manual duplicada (`cd_rubros = total_mo_analisis + mat_total`) en vez de usar `_calcular_totales_finales()` (la misma función del guardado final) — quedaba levemente distinta. Fix: paso 5 GET ahora llama a `_calcular_totales_finales()` igual que el guardado. Además, `resumen()` (paso 8) ahora recalcula `p['totales']` fresco tanto en GET como en POST (antes solo lo hacía en POST, justo antes de guardar), para que la pantalla de resumen SIEMPRE coincida con lo que se termina guardando y con el PDF.
- **Causa real de (3a) — materiales ausentes en modo MO+Materiales:** la sección nueva de materiales del PDF (agregada la vez anterior) se había restringido a `modo=='solo_mo'` únicamente. Se sacó esa restricción: ahora se muestra siempre que haya `p['materiales']`, con título distinto según el modo ("a comprar" en solo_mo vs "detalle informativo, ya incluido en el TOTAL" en mo_mat) — igual que ya se mostraba en pantalla en el resumen interno (paso 8).
- **Causa real de (3b) — hoja casi vacía:** es una combinación de (a) el bloque final "Forma de pago + firma" podía partirse entre 2 páginas de forma fea (ej. 2 de 3 filas en una hoja, el resto + firma en la siguiente), y (b) algunos espacios en blanco evitables (filas de Telefono/Email vacías siempre impresas, saltos de línea un poco generosos). Fix: se calcula la altura aproximada de todo el bloque "Forma de pago"+firma y si no entra en el resto de la página actual, se fuerza un salto de página ANTES de empezar (con `pdf.add_page()`), así el bloque queda siempre completo y prolijo en una sola hoja (nunca partido). Se sacaron las filas de Teléfono/Email cuando están vacías y se recortaron un poco los `pdf.ln()` entre secciones. Esto reduce cuánto se usa la 2da hoja pero no lo elimina del todo — presupuestos con muchos ítems/materiales van a seguir ocupando 2 páginas, ahora de forma prolija (nunca partiendo una tabla a la mitad).
- **Hallazgo nuevo de infraestructura:** durante la verificación de estos cambios, `utils/pdf_generator.py` mostró el MISMO síntoma que ya está documentado para `database.py` — bash ve una copia vieja/truncada del archivo que no refleja los últimos cambios guardados (se comprobó comparando tamaño/mtime del archivo entre bash y las herramientas de archivo). **Agregar a la regla existente: para `utils/pdf_generator.py` tampoco confiar en bash para verificar contenido — usar Read/Edit.** No afecta el archivo real ni el deploy (Railway clona el repo real desde git, no desde este entorno de verificación) — es solo una limitación del entorno de este chat para probar cambios en vivo.
- **Archivos tocados en esta sub-sesión:** `routes/presupuesto.py` (`_redir_next()`, fix rubros() GET, paso5 GET con `_calcular_totales_finales`, resumen() recálculo fresco en GET), `templates/base.html` (JS `wizardGoto()`), `templates/presupuesto/_wizard_steps.html` (íconos usan wizardGoto), `templates/presupuesto/paso1_obra.html` `paso2_rubros.html` `paso3_subcontratos.html` `paso4_indirectos.html` `paso5_modo_tiempo.html` `paso6_materiales.html` `paso7_pago.html` (botones "Anterior" → submit con `_next`, `data-wizard-form`), `utils/pdf_generator.py` (materiales siempre visibles, salto de página prolijo, filas vacías omitidas).
- **Pendiente:** commitear y deployar; probar en la app real (no se pudo re-verificar visualmente el último ajuste del PDF por el problema de sync de bash explicado arriba, aunque se revisó el código a mano con cuidado): (1) elegir "semanal" en paso 7, saltar a paso 2 con el ícono verde, volver a paso 7 con el ícono → debe seguir "semanal"; (2) confirmar que el TOTAL FINAL de paso 5 coincide con el del PDF; (3) generar PDF de un presupuesto MO+Materiales y confirmar que aparece la lista de materiales; (4) generar PDF de un presupuesto con varios ítems y confirmar que si ocupa 2 hojas, la sección "Forma de pago" no queda partida a la mitad.

### Sesión 05/07/2026 — Navegación del wizard, bug frecuencia de pago, PDF propietario
- **Botones/pasos del wizard en todas las ventanas:** `paso2_rubros.html` era la única de las 8 pantallas sin el include de `_wizard_steps.html` — agregado.
- **Etiquetas cortas debajo de cada paso:** INICIO, COMPUTO, SUBCONT, INDIR, MODO, MATER, F PAGO, RESUMEN (`_wizard_steps.html` + `.step-label` en `static/css/style.css`).
- **Navegación libre adelante/atrás entre pasos ya visitados** (pedido: "si estoy en 2, poder ir al 6"): antes solo funcionaba al editar un presupuesto YA completo (`_editando_nro`→max_step=8). Para un borrador en progreso no había forma de saltar adelante porque el template usaba `p.get('wizard_step', ...)`, una clave que en la práctica nunca estaba en el dict de sesión. Fix: nueva clave `_max_step` (en `_guardar_borrador()`, `routes/presupuesto.py`) que guarda el paso más avanzado alcanzado por ese borrador — a diferencia de la columna DB `wizard_step` (que se pisa con el paso actual y puede bajar si volvés atrás), `_max_step` solo crece. `_wizard_steps.html` la usa para habilitar el link "verde" de cualquier paso ≤ `_max_step`.
- **Bug corregido — frecuencia de pago (paso 7) no persistía:** Daniel reportó que si elegía "semanal", iba al paso 5 y volvía al 7, veía "mensual" de nuevo. Causa real: el botón "Anterior" de paso 7 era un `<a href>` (no un submit), así que la elección hecha en el `<select>` nunca se guardaba en el servidor antes de navegar — al volver, se re-renderiza con el último valor SÍ guardado (mensual, de antes). Fix: los 2 botones "Anterior" de `paso7_pago.html` ahora son `<button type="submit" form="formPago" name="ir_atras" value="1">` — se guarda todo (incluida la frecuencia) y recién después `forma_pago()` (routes/presupuesto.py) redirige hacia atrás en vez de a resumen.
- **PDF propietario — banner más claro:** nuevo parámetro `banner_claro` en la clase `PDF` (`utils/pdf_generator.py`); el PDF propietario usa `AZUL_M` (más claro) en vez de `AZUL` para el rectángulo del banner. El PDF constructor no cambia.
- **PDF propietario — logo placeholder con iniciales:** si la empresa no cargó logo, se dibuja un cuadro con las iniciales del nombre de la empresa (ej. "Vega Construcciones" → "VC"), función `_iniciales_empresa()`. Nombre de la empresa en el banner: de 11pt a 14pt.
- **PDF propietario — "Resumen económico" dinámico:** el texto fijo "Incluye mano de obra, materiales, subcontratos, gastos generales e impuestos" ahora se arma según lo realmente presupuestado: sin "materiales" si `modo == 'solo_mo'`, sin "subcontratos" si no hay ninguno cargado, sin "gastos generales"/"impuestos" si esos % son 0. Función `_conectar_ultima()` arma la lista con gramática correcta (coma + "y"/"e").
- **PDF propietario — nueva sección "Items de obra a realizar":** tabla por ítem (no por rubro como en el resumen interno), con cantidad y unidad presupuestada, SIN detalle de costo (ese detalle es solo para el PDF constructor).
- **PDF propietario — lista de materiales cuando es "Solo mano de obra":** en ese modo el wizard salta el paso 6 (materiales), así que `p['materiales']` quedaba vacío. `routes/pdf_routes.py::cargar_presupuesto()` ahora calcula la lista en vivo con `_calcular_materiales_desde_rubros()` (la misma función que usa el paso 6) cuando `modo=='solo_mo'` y no hay materiales guardados. El PDF muestra la tabla completa (material/cantidad/unidad/precio/subtotal) con el total a comprar, solo en este modo (en "Mano de obra + materiales" ya está incluido en el TOTAL).
- **No se tocó ninguna fórmula de cálculo** — pedido explícito de Daniel ("no modifiques nada de la forma de calcular eso ya está bien").
- **Pendiente:** commitear `routes/presupuesto.py`, `routes/pdf_routes.py`, `utils/pdf_generator.py`, `templates/presupuesto/_wizard_steps.html`, `templates/presupuesto/paso2_rubros.html`, `templates/presupuesto/paso7_pago.html`, `static/css/style.css`, `PROYECTO.md`. Probar: (1) crear un borrador nuevo, avanzar hasta paso 6, volver al 2 y confirmar que aparece el link verde al 6; (2) elegir "semanal" en paso 7, ir a paso 5, volver a paso 7, confirmar que sigue "semanal"; (3) generar PDF propietario de un presupuesto "Solo mano de obra" y confirmar que aparece la lista de materiales a comprar; (4) generar PDF propietario de cualquier presupuesto y revisar banner/logo/nombre/resumen económico/items.

### Sesión 04/07/2026 (tarde) — Precios reales V3 + bug de `_migrar_precios_v1` nunca ejecutado
- Pedido: listado de materiales con Unidad/Precio Comercial vs Unidad/Precio de Cálculo. El primer intento se armó contra un `presupuestopro.db` local **desactualizado** (sin ninguno de los flags `2j_done`...`2p_done`, sin tabla `suscripciones`) → descartado.
- Daniel señaló `D:\ESCRITORIO\CLAUDE\02_CONSTRUCCION\PRESUPUESTOS\LISTA_MATERIALES_V3_formulafix.xlsx` (Corralón El Cruce, Lista 169, 04/06/2026) como la planilla de referencia real. Es una planilla de TRABAJO (no la lee la app): columna F = precio comercial que carga Daniel, columna G = F÷cant.presentación (autocalculada, "va a la app"), columna H = precio de lista viejo (jun-2026, como referencia).
- **Hallazgo clave:** existe `_migrar_precios_v1(db)` en `database.py` (agregada en commit `5882585`, ANTES de que existieran las migraciones 2h-2p) con precios ya sacados de esta misma V3. Pero solo se llama desde `init_db()`, nunca desde `migrate_db()` → en una base que ya existe (como producción) nunca corrió de forma útil. Es código "muerto" en la práctica.
- **Fix:** migración nueva `2q` en `database.py` (después de 2p), que actualiza `analisis_sub.precio_ars` de 88 materiales con los valores de la V3: para los 6 materiales que ya están en unidad comercial (Cemento portland, Cemento Albañilería, Cal aérea Milagro, Klaukol, Salpicrete, Super Iggam) usa la columna F (precio de la bolsa); para el resto usa la columna G (precio por unidad de cálculo cruda). Guardada con flag `2q_done`, corre sola en el próximo arranque de la app.
- **Decisiones de Daniel (04/07/2026) sobre los casos ambiguos:**
  - ✅ Adoptados y agregados a 2q: Baldosa cerámica azotea (V3: "Baldosa cerámica Alberdi", $33.000/m2), Zócalo de madera (V3: "Zócalo de pino", $3.500/ml), Viga Vipret 4m. (V3: "Vigueta 4,00 m", $3.862,50/u), Ladrillo hueco 18X18X33cm (V3 celda B22 corregida por Daniel de "25cm" a "33cm", $1.160/u).
  - ⛔ Hormigón colado / Hormigon elaborado colado / Hormigón elaborado colado: **NO se tocan en 2q, a propósito.** Son 2 materiales distintos usados como insumo interno en las recetas de `analisis_sub`: "Hormigón colado" = mezclado en obra, usado en ítems `Ho.Ado.*` a $233.860/m3 (COCHERA, migración 2n); "Hormigón elaborado colado" = camión mixer, usado en ítems `H.Elab.*` a $215.000/m3 ("Hormigon elaborado colado" sin tilde es el mismo material, con inconsistencia de tilde en los datos). Estos cálculos internos se mantienen tal como los trae el Excel. El valor de la V3 ($190.000/m3, "Hormigón elaborado pto.obra") se usa **solo como referencia de "costo de hormigón puesto en obra"** en el Excel de precios comerciales — no reemplaza los 2 insumos internos.
  - "Revear/DeckAr" y "Contenedor/volquete" de la V3 no tienen fila propia en `analisis_sub` hoy (no son materiales usados actualmente por ningún ítem). Los renglones "Jornal Oficial/Ayudante" de la V3 ($80.000/$40.000 por día) no tocan `analisis_sub` — van por la tabla `config` (`jornal_oficial_dia`/`jornal_ayudante_dia`), coinciden con los defaults actuales de `routes/admin.py`.
- **Entregable actualizado:** `EXPORTS/Materiales_App_Lista_Comercial_v2.xlsx` — regenerado con los valores finales confirmados (88 actualizados + fila de referencia "Hormigón colado" $190.000/m3 + nota de los 2 insumos internos que no cambian). El archivo `Materiales_App_Lista_Comercial.xlsx` (sin `_v2`) quedó abierto en Excel y no se pudo sobrescribir — reemplazar manualmente cuando se cierre.
- **Pendiente:** commitear `database.py` (migración 2q) + `PROYECTO.md` vía Git Bash (comandos pasados a Daniel en el chat) — sigue la regla crítica de este archivo. Después del commit+push+deploy, revisar `/admin/precios` en producción para confirmar que los 88 valores quedaron aplicados.

### Sesión 04/07/2026 — Verificación vs Excel real (PRESUPUESTO COCHERA.xlsx)
- Comparados los 15 ítems cargados en la cochera de Ezequiel Petrini contra el Excel: HOF/HAY de ítems normales coincide 100% con la app.
- **Bug encontrado y corregido:** HOF/HAY de las 4 instalaciones estaban cruzadas (la migración 2h las había tomado de la columna de referencia del Excel, que está desalineada respecto al desglose real de Oficial/Ayudante por instalación). Corregido con migración `2m` en `database.py`:
  - Instalación Desagües: 5,7/5,7 → **24,5/24,5**
  - Instalación Agua F/C: 5,7/5,7 → **31,67/31,67**
  - Instalación Gas: 5,7/5,7 → **27/27**
  - Instalación Eléctrica: 31,67/31,67 → **5,7/5,7**
- **Resync completo hecho:** al comparar programáticamente los 93 ítems en común entre `analisis_sub` (migración 2h) y la hoja "Análisis" del Excel, 79 tenían al menos una diferencia de cantidad o precio de material (varios directamente les faltaba un material, ej. Hidrófugo en "Cemento: capa aisladora s/muros"). Se armó un parser automático de la hoja Análisis (bloques por ítem, separando materiales de mano de obra) y se generó la migración `2n` en `database.py`: reemplaza los materiales de 117 ítems (358 filas) tomando el Excel como fuente de verdad, preservando sin tocar los 9 ítems que no están en ese Excel (variantes propias de la app: Piso/Rvto/Zocalo Cerámico "2"/"3", etc).
- ⚠️ **Ojo:** este resync es un reemplazo masivo automático. Si en el pasado se hizo alguna corrección manual deliberada que contradice el Excel (ej. el comentario "Mamp. ladrillo comun 30cm: mismas proporciones que 15cm, corrección del Excel" en `database.py` línea ~1145), esa corrección pudo haber quedado pisada por 2n. Revisar si aparece algo raro en presupuestos nuevos.
- **Bug encontrado por Daniel en "Relleno y Compactación"** (probando la cochera): la app traía "Máquina excavadora" de más (el Excel no la tiene para este ítem) y menos Tierra Colorada de la real. Causa: `database.py` tiene una lista `_renombres` (línea ~777) que renombra `items_obra.nombre` DESPUÉS de poblar `analisis_sub` — ej. "Relleno y Compactacion" → "Relleno y Compactacion C/15cm". La migración 2n comparó contra el Excel usando el nombre viejo (pre-renombre) y no tocó estos ítems. Afectaba a 7 ítems en total (Relleno y Compactación + Piso/Zocalo/Rvto Cerámico y Porcellanato con Klaukol a precio viejo $720 en vez de $600). Corregido con migración **2o**.
- **Bug encontrado al preparar el export de materiales:** las migraciones 2n/2o insertan los datos del Excel tal cual (kg/L crudos), pero 2j/2k/2l ya habían convertido 6 materiales a unidad comercial (bolsa) antes de que 2n/2o corrieran. El DELETE+INSERT de 2n/2o pisó esa conversión, reintroduciendo — del lado de los datos — el mismo bug de doble-conversión que ya se había arreglado en el código (`_calcular_materiales_desde_rubros` y `admin.py`). Afecta a: Cemento portland bolsas, Cemento Albañilería, Cal aérea Milagro, Klaukol (factor 25), Salpicrete y Super Iggam (factor 30). Corregido con migración **2p** (reaplica los mismos factores que dejó 2l). Validado con una simulación completa de la cadena 2h→2j→2k→2l→2m→2n→2o→2p: 358 filas finales consistentes, 127 ítems, unidades comerciales correctas.
- **Entregable generado:** `EXPORTS/Materiales_App_Referencia.xlsx` — lista de materiales que usa la app como referencia de cálculo (358 filas, 127 ítems, agrupado por ítem + hoja de precios únicos + notas), generado desde el estado final post-migración 2p.

### Sesión 03/07/2026 — Integración Mercado Pago
- `requirements.txt`: agregado `mercadopago==2.3.0`
- `config.py`: variables MP_ACCESS_TOKEN, MP_PUBLIC_KEY, MP_APP_ID, MP_PRECIO_ARS, MP_PLAN_NOMBRE, APP_BASE_URL
- `database.py`: tabla `suscripciones` + migración `users.mp_preapproval_id`
- `routes/pagos.py`: blueprint nuevo con 5 rutas (planes, crear-suscripcion, retorno, webhook, estado)
- `app.py`: registrado blueprint `pagos`
- **Deploy:** ✅ Deployment successful en Railway · Página `/pagos/planes` verificada y funcional

### Sesión anterior
- `admin.py`: lista de precios con JORNALES como primer grupo, typo CORRELON→CORRALÓN corregido, sub_nombres actualizados
- `templates/admin/precios.html`: botón Volver, tarjeta JORNALES con jornal_oficial/ayudante editables y cálculo $/hr en tiempo real

## Sistema de contexto entre chats (configurado 30/06/2026)
- `CLAUDE.md` creado en la raíz del proyecto — Claude lo lee automáticamente al empezar cada chat
- Al mensaje 20, Claude actualiza PROYECTO.md automáticamente antes de sugerir nuevo chat
- **Para empezar un chat nuevo no hace falta pegar nada** — CLAUDE.md lo maneja solo

---

## Migraciones en database.py (historial)
- `2a-2e`: columnas usuarios, items_obra, config, analisis_sub, HOF/HAY correcciones
- `2f`: precios hormigón y losa cerámica
- `2g`: columna `m2_factor` en items_obra + set de valores + renombres de ítems
- `2h`: corrección masiva hof/hay + populate analisis_sub con materiales hardcodeados desde Excel
- `2i`: ajustes adicionales de analisis_sub
- `2j`: factores de unidad comercial (primera pasada)
- `2k`: factores de unidad comercial (segunda pasada)
- `2l`: ⚠️ **ESCRITA PERO NO COMMITEADA** — corrige 11 factores comerciales erróneos de 2j/2k:
  - Cemento portland: 50→25 (bolsa 25kg)
  - Klaukol: 30→25 (bolsa 25kg)
  - Hidrófugo: 5→10 (balde 10kg)
  - Super Iggam: 20→30 (bolsa 30kg)
  - Salpicrete: 20→30 (bolsa 30kg)
  - Fondo Base: 20→25 (balde 25kg)
  - Enduido sintético: 30→4 (lata 4kg)
  - Pintura látex cielos: 20→10 (balde 10L)
  - Pintura especial 1/2: 20→4 (lata 4L)
  - Pintura satinol: 20→4 (lata 4L)
  - Pintura cal hidráulica: 25→1 (revertir)
- `2m`: corrige HOF/HAY cruzadas de las 4 instalaciones (Desagües/Agua F-C/Gas/Eléctrica)
- `2n`: resync completo de materiales (358 filas, 117 ítems) contra PRESUPUESTO COCHERA.xlsx
- `2o`: corrige 7 ítems que 2n no tocó por el mecanismo de `_renombres` (Relleno y Compactación, Piso/Zocalo/Rvto Cerámico/Porcellanato)
- `2p`: reaplica factores de unidad comercial (25/30) a 6 materiales que 2n/2o habían revertido a Kg crudo
- `2q`: actualiza precio_ars de 88 materiales con los valores reales de `LISTA_MATERIALES_V3_formulafix.xlsx` (Corralón El Cruce, Lista 169, 04/06/2026). Ver sesión 04/07/2026 (tarde) para detalle y hallazgo del bug de `_migrar_precios_v1`.
- `2r`: recalcula `items_obra.precio_mo_ars` de las 4 instalaciones (Desagües/Agua F-C/Gas/Eléctrica) — quedó desactualizado tras 2m. Ver sesión 04/07/2026 (noche).
