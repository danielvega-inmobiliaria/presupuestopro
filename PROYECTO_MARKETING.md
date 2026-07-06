# PresupuestoPRO — DIFUSIÓN EN REDES — Contexto del proyecto

## Cómo usar este archivo
- **Al empezar un chat nuevo:** pegá → `Leé PROYECTO_MARKETING.md y continuá desde donde quedamos`
- **Al terminar un chat:** pedí → `Actualizá PROYECTO_MARKETING.md con lo que hicimos hoy`

---

_Última actualización: 02/07/2026 — 16:26 ART_

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
- `IMAGENES/LOGO SOLO.png` — logo original, 1408×768 px, con fondo de falsa transparencia (cuadriculado horneado en los píxeles, alfa 100% opaca). **Ya no usar como base de trabajo directo** — ver limpieza abajo.
- **`IMAGENES/LOGO SOLO limpio v3.png`** — ✅ **versión final del ícono**, fondo transparente real, 1000×1000px, bordes limpios, grúa con el mismo estilo calado (triángulos transparentes) en torre y brazo. Esta es la que hay que usar de acá en adelante para cualquier pieza nueva.
- `IMAGENES/LOGO SOLO limpio.png` y `v2.png`/`v2-2.png` — versiones intermedias del proceso de limpieza, **no usar**, quedaron por historial.
- **`IMAGENES/Portada_Facebook_1640x856_v3.png`** — ✅ portada de Facebook final (logo limpio v3 + tagline "De los metros a los pesos, en minutos." en Poppins Bold, más grande y clara). **Ya subida a Facebook por Daniel.**
- `IMAGENES/Portada_Facebook_1640x856.png` y `_v2.png` — versiones previas de la portada, no usar.

---

## Pendientes

### 🔴 CRÍTICO
- [ ] **Conectar WhatsApp a la página de Facebook — bloqueado.** Daniel consiguió un número nuevo (3417542009) pero Facebook dice "Este número no está asociado a una cuenta de WhatsApp o WhatsApp Business". **Falta:** instalar WhatsApp o WhatsApp Business en un teléfono con esa línea, completar el alta normal de WhatsApp (verificación por SMS de WhatsApp, no de Facebook), y recién después volver a Configuración → Cuentas vinculadas → WhatsApp en la página para conectar ese número ya activo.
- [ ] Crear la cuenta de Instagram profesional (Negocio) — Daniel ya creó el Gmail dedicado `presupuestopro.app@gmail.com` para esto. Falta crear la cuenta de Instagram en sí (mejor desde el celular), pasarla a cuenta profesional/Empresa, y vincularla a la página de Facebook "Presupuestopro".
- [ ] Confirmar precio definitivo post-lanzamiento (hoy: $12.500 ARS/mes en evaluación, pero **decisión tomada: lanzamiento 100% gratis sin plazo definido**)
- [ ] Llevar `LANDING_UNIFICADA_PRESUPUESTOPRO.md` a implementación real en presupuestopro.com.ar (hoy es solo un documento de copy, no está aplicado al sitio vivo)
- [ ] Publicar el **POST 0 (historia de Daniel)** como primera publicación de la página, ahora que el perfil/portada/nombre ya están OK.

### 🟡 IMPORTANTE
- [ ] Tomar screenshots reales de la app para reemplazar mockups en piezas del Agente 3
- [ ] Definir tipografías de marca definitivas en Canva (Poppins Bold confirmado y usado ya en portada de Facebook)
- [ ] Publicar el calendario de 4 semanas del Agente 4 y activar Make.com
- [ ] Publicar el carrusel de 5 slides + video demo en grupos de Facebook (plan: Albañiles Rosario lunes, Constructores y Contratistas martes, Albañiles zona sur miércoles, grupos de corralones jueves, Albañiles Buenos Aires viernes)
- [ ] Revisar/limpiar archivos de logo intermedios en `IMAGENES/` (`LOGO SOLO-2.png`, `LOGO SOLO MEJORADO.psd`, `LOGO SOLO limpio.png`, `v2.png`, `v2-2.png`) — quedaron de las pruebas de esta sesión, solo `LOGO SOLO limpio v3.png` es la definitiva.

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

## Notas técnicas del proceso de limpieza del logo (por si hace falta repetirlo)
1. Nunca editar copias/documentos de Photoshop de sesiones anteriores sin verificar la resolución real (Imagen → Tamaño de imagen) — ahí se detectó el problema de la copia reducida.
2. Mejor partir siempre del archivo original en la carpeta `IMAGENES/`.
3. Para fondos de falsa transparencia (cuadriculado horneado en los píxeles): en vez de Varita mágica + Suprimir, conviene chroma key por "colorfulness" (diferencia entre canal máximo y mínimo de RGB) vía script — separa bien el gris neutro del fondo de los colores de marca (naranja/azul), y con umbral suave conserva el anti-aliasing original.
4. Elementos muy finos (como la grilla de la grúa) pueden perder su transparencia interior por el mismo motivo que el fondo grande — si un patrón se ve "relleno" en vez de "calado", comparar contra zonas equivalentes del diseño (en este caso la torre) para detectar la inconsistencia.

## Estado de la página de Facebook (al cierre de esta sesión)
- Nombre: **Presupuestopro** (corregido) · Foto de perfil y portada: **actualizadas** (logo v3)
- Bio: "Presupuestá obras en minutos. Materiales, mano de obra y cuotas calculados solos, con precios actualizados. PDF con tu logo listo para el cliente. Probala gratis: presupuestopro.com.ar"
- Categoría: Software · Botón de acción: **Registrarte → presupuestopro.com.ar** (confirmado)
- Teléfono de contacto del perfil personal de Daniel (no de la página): 0341 301-7371
- **WhatsApp de la página: pendiente**, número nuevo 3417542009 sin activar en WhatsApp todavía (ver Pendientes 🔴)
- Emails asociados a la cuenta personal de Daniel (por si hace falta recuperar algo): danve61@gmail.com y danyrocentral@yahoo.com.ar
- Email dedicado a la marca (nuevo, para Instagram y otras cuentas): **presupuestopro.app@gmail.com**

## Landing page unificada — resumen
Se comparó `presupuestopro.com.ar` (producción, base elegida) con la versión vieja de Railway (aportó badge de audiencia y grilla de 4 íconos). Resultado en `LANDING_UNIFICADA_PRESUPUESTOPRO.md`: CTA unificado a "PROBALA GRATIS", "Ganancia Real" agregada como feature en 3 lugares, footer actualizado. Es un documento de copy, todavía **no aplicado al sitio real**.

## Notas / Decisiones de sesiones anteriores
- Red principal de lanzamiento: grupos de Facebook de albañiles/constructores + página propia "Presupuestopro" para credibilidad/ads a futuro
- Frase ancla de marca: **"De los metros a los pesos, en minutos."**
- El sistema de 4 agentes es reutilizable pegando este archivo + `SISTEMA_AGENTES_PRESUPUESTOPRO.md` en un chat nuevo

---

## Para el próximo chat

Este chat llegó al límite de 20 mensajes. Contexto exacto a trasladar, pegar esto en un chat nuevo:

> Leé PROYECTO_MARKETING.md y continuá desde donde quedamos. Frentes abiertos:
> 1. Conectar WhatsApp a la página de Facebook — Daniel tiene que instalar WhatsApp/WhatsApp Business en el número nuevo (3417542009) primero, recién después se puede vincular desde Configuración → Cuentas vinculadas → WhatsApp en la página.
> 2. Crear la cuenta de Instagram Negocio con el Gmail ya creado (presupuestopro.app@gmail.com), pasarla a profesional y vincularla a la página de Facebook.
> 3. Publicar el POST 0 (historia de Daniel) como primera publicación de la página — ya está redactado en posts_lanzamiento_presupuestopro.md.
> 4. Pendiente de más largo plazo: llevar LANDING_UNIFICADA_PRESUPUESTOPRO.md a implementación real en el sitio.

Recordá: no hay Chrome automatizado disponible en esta máquina — todo lo de navegador se guía por chat, paso a paso, con Daniel manejando el mouse y pegando capturas. El logo definitivo para cualquier pieza nueva es `IMAGENES/LOGO SOLO limpio v3.png`.
