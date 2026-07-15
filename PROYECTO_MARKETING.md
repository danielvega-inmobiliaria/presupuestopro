# PresupuestoPRO — DIFUSIÓN EN REDES — Contexto del proyecto

## Cómo usar este archivo
- **Al empezar un chat nuevo:** pegá → `Leé PROYECTO_MARKETING.md y continuá desde donde quedamos`
- **Al terminar un chat:** pedí → `Actualizá PROYECTO_MARKETING.md con lo que hicimos hoy`

---

_Última actualización: 06/07/2026 — 16:28 ART_

## Qué es este proyecto
Proyecto de difusión en redes sociales de PresupuestoPRO. Corre un sistema de 4 agentes IA en cadena (Analista de mercado → Estratega creativo → Diseñador senior → Social media manager) que genera, a partir de los datos reales de la marca, todo el contenido de lanzamiento: análisis de competencia, ideas de contenido, piezas visuales listas para Canva y calendario de publicación con automatización. También incluye la ejecución operativa: creación de página de Facebook, cuenta de Instagram, y unificación de la landing page.

**Nota:** esta carpeta también tiene un `PROYECTO.md` propio, pero es el log del proyecto de **desarrollo de la app** (Flask, Railway, DB). Este archivo (`PROYECTO_MARKETING.md`) es exclusivamente para el hilo de **marketing/difusión**. No confundir ni mezclar los dos.

## Stack / Herramientas
- No es un proyecto de código — es de estrategia, contenido y ejecución operativa (Facebook, Instagram, Photoshop, landing)
- Fuente de datos de marca: `RESUMEN_MARKETING.md` (esta misma carpeta)
- Prompt maestro del sistema de agentes: `SISTEMA_AGENTES_PRESUPUESTOPRO.md` (raíz de `D:\ESCRITORIO\CLAUDE`)
- **Limitación técnica:** no hay extensión "Claude in Chrome" conectada en esta máquina. El acceso a Chrome vía computer-use es **solo lectura** (Claude puede ver capturas que Daniel comparte, pero no puede clickear ni tipear en el navegador). Todo lo de Facebook/Instagram se hace **guiando a Daniel paso a paso por chat**, con capturas de pantalla que él pega. Photoshop **sí** se pudo controlar directamente vía computer-use (app nativa, no navegador) — aunque terminó siendo mejor trabajar con Python/PIL en sandbox para el recorte de precisión (ver abajo).

## Archivos importantes
- `SISTEMA_AGENTES_PRESUPUESTOPRO.md` (raíz de CLAUDE) — plantilla completa de los 4 agentes con todos los datos de marca ya reemplazados.
- `RESUMEN_MARKETING.md` (esta carpeta) — resumen de producto, target, precio, paleta y assets ya creados. Fuente de verdad para completar cualquier dato de marca.
- `CONTEXTO_MARKETING.md` (esta carpeta) — brief desactualizado de un chat anterior. Mantener solo como referencia histórica.
- `POST_FACEBOOK_ALBANILES.md`, `posts_lanzamiento_presupuestopro.md`, `slides_facebook.html` — copy y piezas ya redactadas. `posts_lanzamiento_presupuestopro.md` ahora incluye el **POST 0 (historia de lanzamiento)** al principio, antes del resto del calendario.
- **`LANDING_UNIFICADA_PRESUPUESTOPRO.md`** (esta carpeta) — copy unificada de landing page. "Ganancia Real" confirmada como **feature** (no pilar de contenido nuevo) — ver Decisiones.
- **`CAMPANA_CANJE_REDES.md`** (esta carpeta) — nueva campaña "gratis por canje" (seguir FB+IG, like al posteo ancla, etiquetar 3 colegas). Copy de WhatsApp, posteo ancla FB/IG y banner de landing (para pasar al hilo de desarrollo).
- **`CARRUSEL_FUNCIONES_CANVA.md`** (esta carpeta) — carrusel de 7 slides listo para Canva con las 6 funciones reales de la app (materiales, precios actualizados, PDF, cuotas, ganancia real, multi-dispositivo) + cierre con CTA de prueba gratis.
- **`CARRUSEL_CRONICA_ALBANILES.md`** (esta carpeta) — nuevo carrusel de 8 slides, tono crónica/urgencia ("SE BUSCAN ALBAÑILES"), inspirado en el formato storytime de @ganga.home. Gancho de alarma → historia del problema → giro hacia la app → funciones → oferta de canje → CTA final. Listo para Canva, reutiliza los íconos de `IMAGENES/ICONOS_CARRUSEL/`.
- **`HISTORIA_ORIGEN_PRESUPUESTOPRO.md`** (esta carpeta) — ⚠️ **nuevo relato de origen de marca, reemplaza al POST 0.** Historia narrativa/emotiva (nombres ilustrativos, no personas reales verificables): dos arquitectos recién recibidos + un amigo programador + el abuelo de uno de ellos, Maestro Mayor de Obras con 40 años de oficio, que los guio los domingos hasta darle forma a la app. Incluye versión larga (post ancla/landing), versión corta (caption) y notas de adaptación. **Pendiente crítico:** editar/borrar el POST 0 real antes de publicar esta, para no dejar dos orígenes de marca contradictorios online al mismo tiempo.
- **`IMAGENES/post_mundial_gol_media_cancha.png`** — pieza única 1080×1080, gancho futbolero ("Hacé un gol de media cancha, empezá a presupuestar con PresupuestoPRO") aprovechando el clima del Mundial 2026, sin usar logos ni marcas oficiales de FIFA. Caption FB/IG con hashtags en el cuerpo de este archivo.
- **`IMAGENES/CARRUSEL_CRONICA/`** — ✅ carrusel final: **10 slides** (`slide_01...` a `slide_10...`), rediseño v2 estilo placa de Crónica TV a pedido de Daniel (gancho "SE BUSCAN ALBAÑILES" solo, banner URGENTE con triángulos de alarma dibujados a mano, textos con palabras clave resaltadas, cierre con botón de solo URL). PNG 1080×1080 (Python/PIL, Poppins Bold + Lato, paleta de marca), listas para subir directo. Los 8 PNG viejos (`slide_1...` a `slide_8...`) de la v1 siguen en la misma carpeta sin poder borrarse (falta autorización) — ignorarlos.
- **`IMAGENES/ICONOS_CARRUSEL/`** — 6 íconos PNG (400×400, círculo naranja/dorado, línea blanca) generados con Python/PIL para el carrusel de arriba: materiales, precios, PDF, pagos, ganancia, dispositivos. Listos para importar directo a Canva.
- `IMAGENES/LOGO SOLO.png` — logo original, 1408×768 px, con fondo de falsa transparencia (cuadriculado horneado en los píxeles, alfa 100% opaca). **Ya no usar como base de trabajo directo** — ver limpieza abajo.
- **`IMAGENES/LOGO SOLO limpio v3.png`** — ✅ **versión final del ícono**, fondo transparente real, 1000×1000px, bordes limpios, grúa con el mismo estilo calado (triángulos transparentes) en torre y brazo. Esta es la que hay que usar de acá en adelante para cualquier pieza nueva.
- `IMAGENES/LOGO SOLO limpio.png` y `v2.png`/`v2-2.png` — versiones intermedias del proceso de limpieza, **no usar**, quedaron por historial.
- **`IMAGENES/Portada_Facebook_1640x856_v3.png`** — ✅ portada de Facebook final (logo limpio v3 + tagline "De los metros a los pesos, en minutos." en Poppins Bold, más grande y clara). **Ya subida a Facebook por Daniel.**
- `IMAGENES/Portada_Facebook_1640x856.png` y `_v2.png` — versiones previas de la portada, no usar.

---

## Pendientes

### 🔴 CRÍTICO
- [ ] **Editar o eliminar el POST 0 real** (historia personal de Daniel) en Facebook e Instagram, publicado el 06/07 — quedó reemplazado por el nuevo relato de origen en `HISTORIA_ORIGEN_PRESUPUESTOPRO.md` (dos arquitectos + programador + abuelo). No dejar ambas historias visibles a la vez.
- [ ] Publicar el nuevo relato de origen (`HISTORIA_ORIGEN_PRESUPUESTOPRO.md`) como posteo ancla en Facebook e Instagram, una vez resuelto el punto anterior.
- [x] ~~Investigar "UnclaimedBusinessUser FromPool" en el portfolio comercial PresupuestoPRO~~ → **Resuelto (06/07, 22:02 ART)**: se le sacó a la entidad placeholder el toggle de "Acceso total: Todo → Administrar" (quedó solo con el acceso básico automático). Además se confirmó que **Daniel Vega ya estaba asignado directamente a @presupuesto_pro** con permisos de Contenido, Actividad de la comunidad, Anuncios y Estadísticas — no hizo falta re-asignar nada. Daniel queda como administrador real de ambas cuentas (Facebook + Instagram) bajo su propio usuario.
- [x] ~~Conectar WhatsApp a la página de Facebook — bloqueado~~ → **Parcialmente resuelto (06/07 16:54 ART): el número 3417542009 ya tiene WhatsApp activo**, según confirma Daniel. Falta el último paso: ir a Configuración → Cuentas vinculadas → WhatsApp en la página de Facebook y conectar ese número.
- [x] ~~Confirmar precio definitivo post-lanzamiento~~ → **Cambio de modelo (06/07, 16:28 ART): ya no es gratis sin condición. Pasa a ser "gratis por canje": seguir FB + seguir IG + like al posteo ancla + etiquetar 3 colegas, verificado a mano por captura enviada por WhatsApp.** Ver `CAMPANA_CANJE_REDES.md` (esta carpeta).
- [ ] Publicar el posteo ancla (FB + IG) y fijarlo, con la mecánica de canje — copy listo en `CAMPANA_CANJE_REDES.md`
- [ ] Reenviar el mensaje de WhatsApp de la campaña (usa el WhatsApp personal de Daniel, 0341 301-7371, ya activo — no depende del pendiente del número nuevo)
- [ ] Llevar al hilo de desarrollo de la app el copy del banner de landing ("¿Querés probarla gratis? Seguí + like + etiquetá 3 colegas") para agregarlo a `templates/landing.html` con botones a Facebook/Instagram/WhatsApp
- [x] ~~Publicar el **POST 0 (historia de Daniel)**~~ → **Publicado el 06/07 en Instagram** (~19:55 ART) **y en Facebook** (~20:26 ART), con la mecánica de canje integrada en el mismo texto (historia + "PROBALA GRATIS → seguí + like + etiquetá 3 + WhatsApp 341 754-2009"). IG arrancó con 5 seguidores/5 seguidos; FB con 0 seguidores (esperable, página recién creada — para eso es la campaña de canje).
- [x] ~~Confirmar que el deploy en Railway de `templates/landing.html` (commit `6c33b1a`, iniciales de logo) ya tomó~~ → **Confirmado 06/07 16:31 ART**: Daniel compartió captura de Railway, deploy ACTIVE con el commit de iniciales ya incluido (aparece como deploy anterior, superado por uno más nuevo que lo contiene). Además esa captura muestra que ya se hizo, commiteó y deployó el fix de Reply-To **y** el borrado del código muerto de la landing vieja — ambos eran pendientes del hilo de desarrollo de la app, quedaron resueltos también (falta que Daniel confirme que los probó en vivo).

### 🟡 IMPORTANTE
- [ ] **Corregir el email de contacto de la página de Facebook**: hoy muestra `danve61@gmail.com` (personal). Cambiarlo a `presupuestopro.app@gmail.com` (el mail dedicado a la marca, creado justamente para no mezclar) desde Detalles → Información de contacto.
- [ ] Opcional: ocultar del timeline de Facebook los posteos automáticos de cambio de foto de perfil/portada (Facebook los generó solos al actualizar esas fotos) para que el POST 0 quede como lo primero que ve alguien nuevo — se ocultan sin borrar desde "Administrar publicaciones".
- [ ] Tomar screenshots reales de la app para reemplazar mockups en piezas del Agente 3
- [ ] Definir tipografías de marca definitivas en Canva (Poppins Bold confirmado y usado ya en portada de Facebook)
- [ ] Publicar el calendario de 4 semanas del Agente 4 y activar Make.com
- [ ] Publicar el carrusel "SE BUSCAN ALBAÑILES" en grupos de Facebook siguiendo `PLAN_PUBLICACION_GRUPOS_FB.md` (Albañiles Rosario lunes, Constructores y Contratistas martes, Albañiles zona sur miércoles, grupos de corralones jueves, Albañiles Buenos Aires viernes) — verificar antes las reglas de autopromoción de cada grupo
- [ ] Revisar/limpiar archivos de logo intermedios en `IMAGENES/` (`LOGO SOLO-2.png`, `LOGO SOLO MEJORADO.psd`, `LOGO SOLO limpio.png`, `v2.png`, `v2-2.png`) — quedaron de las pruebas de esta sesión, solo `LOGO SOLO limpio v3.png` es la definitiva.
- [ ] Si se quiere administración completa de Instagram (no solo publicar), subir a Daniel de "acceso parcial" a "acceso total" en Configuración de la empresa → Cuentas de Instagram → @presupuesto_pro → Administrar.
- [x] ~~**(Hilo de desarrollo de la app, no acá)** Commitear + pushear + probar el fix de Reply-To en notificaciones de email~~ → deployado en Railway según captura del 06/07 16:31 ART (confirmar prueba en vivo en el hilo de desarrollo).
- [x] ~~**(Hilo de desarrollo de la app, no acá)** Borrar el código muerto de la landing vieja~~ → deployado en Railway según captura del 06/07 16:31 ART, en el mismo deploy que el fix de Reply-To.

### 🟢 IDEAS FUTURAS
- [ ] Desarrollar el Segmento B (particulares) como público secundario, con canal LinkedIn
- [ ] Sumar testimonios reales de usuarios activos (pieza #12 del Agente 4)
- [ ] Probar el circuito de cobro (Mercado Pago) en privado, con Daniel o 2-3 usuarios de confianza, sin exponerlo en el lanzamiento público gratis

---

## ✅ Completado en la sesión del 02/07/2026

- **Logo limpio de verdad.** El primer intento (editar dentro de un documento de Photoshop de sesiones previas) partía de una copia reducida a ~136×154px sin que se supiera — por eso salía pixelado por más ajustes que se hicieran. Se resolvió trabajando directo sobre `LOGO SOLO.png` original (1408×768px) con recorte por color (chroma key sobre el fondo cuadriculado gris) vía Python/PIL en vez de Varita mágica de Photoshop, preservando el anti-aliasing real del archivo. Resultado: `LOGO SOLO limpio v3.png`.
- **Corrección puntual de la grúa**, a pedido de Daniel: el brazo horizontal tenía una fila de triangulitos rellenos de celeste pálido (en vez de calados como la torre). Se identificó la banda exacta de píxeles y se forzó la transparencia ahí, quedando el mismo estilo "se ve el fondo a través" en toda la grúa.
- **Portada de Facebook actualizada** (`Portada_Facebook_1640x856_v3.png`): logo reemplazado por la versión limpia, tagline "De los metros a los pesos, en minutos." rehecha en Poppins Bold más grande y en celeste claro (antes era chica y de bajo contraste). Subida por Daniel a la página.
- **Foto de perfil de Facebook** reemplazada por el logo limpio — confirmado subido.
- **Nombre de la página corregido**: tenía un typo ("Preupuestopro", sin la primera "s") — se corrigió a "Presupuestopro". Requirió que Daniel reseteara su contraseña de Facebook personal (no la recordaba); quedó resuelto.
- **Botón de llamada a la acción de Facebook**: se verificó que "Registrarte" → `https://presupuestopro.com.ar/` ya estaba correctamente configurado y validado (no hacía falta tocar nada, solo estaba mal ubicado visualmente y parecía faltante).
- **Gmail dedicado a la marca creado**: `presupuestopro.app@gmail.com`, cuenta personal estándar (no Workspace), para usar en Instagram y otras herramientas sin mezclar con el mail personal de Daniel.
- **"Ganancia Real" resuelto**: queda como **feature** dentro del pilar "autoridad/confianza" de la landing, no como pilar de contenido nuevo. Actualizado en `LANDING_UNIFICADA_PRESUPUESTOPRO.md`.
- **POST 0 — historia de lanzamiento** redactado y guardado en `posts_lanzamiento_presupuestopro.md`: texto personal de Daniel (45 años de trayectoria como Maestro Mayor de Obras, la app como regalo a colegas y albañiles), pulido para ser directo y conciso manteniendo la profundidad emocional, cerrado con la frase ancla de marca y el CTA "PROBALA GRATIS".
- **Guía de conexión de WhatsApp a la página** entregada (Configuración → Cuentas vinculadas → WhatsApp → Conecta otro número), con fuente oficial de Meta. Quedó bloqueada porque el número nuevo todavía no tiene WhatsApp instalado (ver Pendientes 🔴).

## ✅ Completado en la sesión del 06/07/2026

- **Bloqueo de Meta Business Suite resuelto.** Daniel había aceptado por error un cartel para unirse al portfolio de otro negocio suyo (la inmobiliaria) mientras configuraba el celular dedicado a PresupuestoPRO. Se confirmó por Configuración de la empresa (escritorio) que **PresupuestoPRO tiene su propio portfolio comercial**, separado de "Daniel Guillermo Vega" (inmobiliaria), "Italia Automotores" y "vegaconstrucciones" — no hubo mezcla real de datos.
- **Página de Facebook "Presupuestopro"**: confirmada correctamente asignada al portfolio PresupuestoPRO, con Daniel Vega como única persona con acceso total.
- **Instagram @presupuesto_pro ya existe y está armado**: foto de perfil, categoría "Software", bio completa y link a presupuestopro.com.ar. Daniel tiene acceso parcial (contenido, actividad de la comunidad, anuncios, estadísticas) — suficiente para publicar. Ya tiene 2 publicaciones. El pendiente de "crear cuenta de Instagram" queda resuelto (ya no hace falta crearla).
- **Post "3 minutos" (oferta) publicado** por Daniel en Instagram — pendiente tachado.
- **Iniciales de logo en `landing.html`**: confirmado que el código (función `getIniciales`, recuadro "Subí tu logo" mostrando iniciales tipo placeholder) ya estaba en el archivo local. Se commiteó (`6c33b1a8`) y se hizo `git push` a `origin/main` — confirmado que el commit llegó a GitHub. Quedó pendiente confirmar si Railway ya redeployó (al último chequeo el sitio en vivo aún mostraba la versión vieja).
- **Aclarado qué es cada URL**: la landing definitiva y la app son el **mismo dominio**, `presupuestopro.com.ar` (ruta `/` sirve `templates/landing.html` sin sesión, y redirige al dashboard con sesión iniciada). La URL `web-production-0c9c1.up.railway.app/landing` es una landing vieja y no usada (`routes/landing.py`, variable `LANDING_HTML`), con un formulario de pago directo por Mercado Pago obsoleto — pendiente de borrar, sin tocar la función `contacto()` del mismo archivo que sigue viva.
- **Detectados 4 archivos sin commitear ajenos a esta sesión** (`PROYECTO.md`, `routes/dashboard.py`, `routes/landing.py`, `routes/sugerencias.py`) — son el fix de Reply-To en notificaciones de email de la sesión de desarrollo del 05/07. Por pedido de Daniel, se dejaron sin tocar acá; se le entregó un texto para llevar al hilo de desarrollo de la app con las instrucciones exactas (commitear/pushear/probar el fix, y por separado borrar el código muerto de la landing vieja).

## Notas técnicas del proceso de limpieza del logo (por si hace falta repetirlo)
1. Nunca editar copias/documentos de Photoshop de sesiones anteriores sin verificar la resolución real (Imagen → Tamaño de imagen) — ahí se detectó el problema de la copia reducida.
2. Mejor partir siempre del archivo original en la carpeta `IMAGENES/`.
3. Para fondos de falsa transparencia (cuadriculado horneado en los píxeles): en vez de Varita mágica + Suprimir, conviene chroma key por "colorfulness" (diferencia entre canal máximo y mínimo de RGB) vía script — separa bien el gris neutro del fondo de los colores de marca (naranja/azul), y con umbral suave conserva el anti-aliasing original.
4. Elementos muy finos (como la grilla de la grúa) pueden perder su transparencia interior por el mismo motivo que el fondo grande — si un patrón se ve "relleno" en vez de "calado", comparar contra zonas equivalentes del diseño (en este caso la torre) para detectar la inconsistencia.

## Estado de la página de Facebook (al cierre de esta sesión)
- Nombre: **Presupuestopro** (corregido) · Foto de perfil y portada: **actualizadas** (logo v3)
- Bio: "Presupuestá obras en minutos. Materiales, mano de obra y cuotas calculados solos, con precios actualizados. PDF con tu logo listo para el cliente. Probala gratis: presupuestopro.com.ar"
- Categoría: Software · Botón de acción: **Registrarte → presupuestopro.com.ar** (confirmado)
- Teléfono de contacto de la página (Información de contacto): +54 341 754-2009 — **ya activo en WhatsApp**, falta el último paso de vincularlo (Configuración → Cuentas vinculadas → WhatsApp)
- Email de contacto de la página: hoy muestra `danve61@gmail.com` (personal) — **pendiente corregir a `presupuestopro.app@gmail.com`** (ver Pendientes 🟡)
- Emails asociados a la cuenta personal de Daniel (por si hace falta recuperar algo): danve61@gmail.com y danyrocentral@yahoo.com.ar
- Email dedicado a la marca (para Instagram y otras cuentas): **presupuestopro.app@gmail.com**
- POST 0 (historia de Daniel + mecánica de canje) **publicado en Facebook e Instagram** el 06/07
- Permisos del Business Manager revisados y corregidos el 06/07 (ver sección de abajo)

## Landing page unificada — resumen
Se comparó `presupuestopro.com.ar` (producción, base elegida) con la versión vieja de Railway (aportó badge de audiencia y grilla de 4 íconos). Resultado en `LANDING_UNIFICADA_PRESUPUESTOPRO.md`: CTA unificado a "PROBALA GRATIS", "Ganancia Real" agregada como feature en 3 lugares, footer actualizado. Es un documento de copy, todavía **no aplicado al sitio real**.

## Decisión — bio de Instagram (06/07, 20:03 ART)
Daniel preguntó si sacar el link de la app de la bio para forzar más follows/likes, y si poner ahí la consigna completa del canje. Recomendación dada: **no sacar el link** — una cuenta que pide "seguime + like + etiquetá" sin ningún sitio real detrás parece cuenta trucha, y el link de presupuestopro.com.ar es la prueba de que el producto es real. Tampoco duplicar la consigna completa en la bio (gasta los ~150 caracteres disponibles) porque ya está entera en el único posteo publicado, visible apenas se entra al perfil.

**Corrección (mismo día, tras ver captura real):** "+ Agregar banners" en Instagram **no es un botón de contacto/link-stack** — es un widget de plantillas personales (tipo "Obsesión actual", "Completá la frase") con límite de **20 caracteres**, pensado para contenido random/divertido, no para mensajes de marca. Se descartó esa idea: no usar banners para el canje, no aporta nada que la bio + el posteo fijado no cubran ya, y el formato no es el correcto para un mensaje comercial.

## Notas / Decisiones de sesiones anteriores
- Red principal de lanzamiento: grupos de Facebook de albañiles/constructores + página propia "Presupuestopro" para credibilidad/ads a futuro
- Frase ancla de marca: **"De los metros a los pesos, en minutos."**
- El sistema de 4 agentes es reutilizable pegando este archivo + `SISTEMA_AGENTES_PRESUPUESTOPRO.md` en un chat nuevo

---

## Resumen de la sesión del 06/07/2026 (segunda parte del día)

- **Cambio de modelo de oferta**: de "gratis sin condición" a **"gratis por canje"** — seguir FB + IG, like al posteo ancla, etiquetar 3 colegas, verificado a mano por WhatsApp. Ver `CAMPANA_CANJE_REDES.md` (copy de WhatsApp, posteo ancla, banner de landing).
- **Carrusel de funciones reales** para Canva armado en `CARRUSEL_FUNCIONES_CANVA.md` + 6 íconos PNG generados en `IMAGENES/ICONOS_CARRUSEL/`.
- **POST 0 (historia de Daniel) publicado** en Instagram y Facebook, con la mecánica de canje integrada en el mismo texto.
- **WhatsApp 3417542009 confirmado activo** — falta solo vincularlo en Configuración de la página.
- **Railway confirmado deployado** (commit de iniciales de logo, más el fix de Reply-To y el borrado de landing vieja — estos últimos dos son pendientes del hilo de desarrollo, no de este).
- **Permisos de Business Manager corregidos**: se detectó "UnclaimedBusinessUser FromPool" con acceso total (podía borrar el portfolio) — se le sacó ese nivel de acceso. Se confirmó que Daniel Vega ya está asignado directamente a @presupuesto_pro con permisos de contenido/comunidad/anuncios/estadísticas.
- Pendiente corregir: email de contacto de la página de Facebook (sacar `danve61@gmail.com`, poner `presupuestopro.app@gmail.com`).

## Para el próximo chat

Este chat llegó al límite de 20 mensajes. Sugerencia de nombre para el chat nuevo: **"PresupuestoPRO — Campaña canje redes y setup Meta"**.

Contexto exacto a trasladar, pegar esto en un chat nuevo:

> Leé PROYECTO_MARKETING.md y continuá desde donde quedamos. Frentes abiertos:
> 1. Publicar el posteo ancla de la campaña de canje en el feed (además del POST 0 que ya lo incluye) y reenviar el mensaje de WhatsApp de `CAMPANA_CANJE_REDES.md`.
> 2. Terminar de vincular el WhatsApp 3417542009 (ya activo) a la página de Facebook — Configuración → Cuentas vinculadas → WhatsApp.
> 3. Corregir el email de contacto de la página de Facebook: sacar danve61@gmail.com, poner presupuestopro.app@gmail.com.
> 4. Armar en Canva el carrusel de `CARRUSEL_FUNCIONES_CANVA.md` con los íconos de `IMAGENES/ICONOS_CARRUSEL/`.
> 5. Pendiente de más largo plazo: llevar LANDING_UNIFICADA_PRESUPUESTOPRO.md y el banner de canje a implementación real en el sitio (hilo de desarrollo de la app).

Recordá: no hay Chrome automatizado disponible en esta máquina — todo lo de navegador se guía por chat, paso a paso, con Daniel manejando el mouse y pegando capturas. El logo definitivo para cualquier pieza nueva es `IMAGENES/LOGO SOLO limpio v3.png`.
