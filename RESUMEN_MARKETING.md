# PresupuestoPRO — Resumen de Assets de Marketing
_Julio 2026 · Para chat de Marketing_

---

## El producto

**PresupuestoPRO** es una app web SaaS para constructores, albañiles y contratistas en Argentina. Permite armar presupuestos de obra completos en minutos.

**URL**: presupuestopro.com.ar  
**Dueño**: Daniel (danve61@gmail.com)  
**Estado**: Live — primeros usuarios con acceso gratuito

### Qué hace
El usuario ingresa los metros cuadrados de cada rubro (mampostería, hormigón, revoques, etc.) y la app calcula sola:
- Lista exacta de materiales (bolsas de cemento, m³ de arena, kg de hierro, ladrillos)
- Mano de obra (oficiales + ayudantes + días + jornales)
- Cuadro de pagos: anticipo, cuotas semanales/quincenales, saldo final
- PDF profesional con el logo, CUIT y datos del contratista

### Target
Hombre 35-55 años, trabaja en obra, usa el celu tanto como la PC. Constructor independiente o contratista que presupuesta a ojo o en Excel artesanal y siempre "queda corto".

### Propuesta de valor principal
**"De los metros a los pesos, en minutos."**  
Sin Excel. Sin fórmulas. Sin quedarse corto.

### Precio
~$12.500 ARS/mes (= 2 bolsas de cemento de 25kg).  
**Ahora en lanzamiento: GRATIS para los primeros usuarios.**

### Paleta de colores
- Azul oscuro: `#0d1e3c` / `#1E3A5F`
- Naranja: `#F97316`
- Dorado: `#eab308`

---

## Assets creados

### 1. Landing page
**Archivo**: `templates/landing.html`  
**URL**: presupuestopro.com.ar

Secciones:
- Hero con PDF preview (muestra el presupuesto con logo de empresa)
- "Así funciona en tu celular" — mockup del celu con 3 tabs: PDF, Mi marca, Precios
- **NUEVA**: "Tu logo. Tu marca." — demo interactiva donde el visitante escribe su nombre/CUIT/tel y ve el PDF actualizarse en tiempo real. También puede subir su logo.
- Antes/Después (Sin PresupuestoPRO vs Con PresupuestoPRO)
- 6 features (materiales, precios, PDF, cuotas, celu/PC, ARS+USD)
- Precio con comparación (2 bolsas de cemento)
- CTA final + modal de registro

---

### 2. Slides para Facebook/Instagram
**Archivo**: `slides_facebook.html`  
**Formato**: 5 slides de 1080×1080px, fondo azul oscuro, texto grande

| # | Título | Mensaje clave |
|---|--------|---------------|
| 1 | Hook | "¿Cuánto tardaste en el último presupuesto?" → "Con PresupuestoPRO: 3 minutos ⚡" |
| 2 | Proceso | "Ponés los metros. La app calcula todo." → 4 pasos numerados |
| 3 | Materiales | "Te dice exactamente qué comprar en el corralón" → lista: cemento, arena, ladrillos, granza |
| 4 | Precio | "¿Cuánto cuesta?" → 2 bolsas de cemento = $12.500/mes |
| 5 | CTA | "PresupuestoPRO — presupuestopro.com.ar" + 4 checks |

**Cómo capturar**: Abrir en Chrome → `Ctrl+-` al 67% → `Win+Shift+S` slide por slide.

---

### 3. Video demo
**Archivo**: `video_demo.html`  
**Duración**: ~45 segundos | **Formato sugerido de grabación**: MP4 fullscreen

Secuencia automática:
1. Intro: logo + slogan
2. Dashboard (presupuestos guardados)
3. Paso 1: datos del cliente
4. Paso 2: rubros con costo directo $8.979.668
5. Paso 6: lista de materiales automática
6. Paso 7: cuadro de pagos ($10.681.712 total)
7. Ver presupuesto final
8. Outro: logo + URL

Incluye música motivacional sintetizada (Web Audio API). Botón ▶ para iniciar.  
**Cómo grabar**: `F11` pantalla completa → `Win+G` → grabar → clic en ▶ → dejar correr.

---

### 4. Copy para redes

#### Post principal — grupos de Facebook de albañiles
**Archivo**: `POST_FACEBOOK_ALBANILES.md`

```
¿Cuántas veces terminaste una obra y te diste cuenta que te quedaste corto?

Pasa todo el tiempo. Los materiales subieron, no calculaste bien los jornales, te olvidaste un rubro… y al final laburaste para el cliente.

Para eso hice PresupuestoPRO 👷

Es una app en el celular y la PC. Ponés los metros de cada trabajo — mampostería, hormigón, revoques, lo que sea — y ella calcula sola:

✅ Cuántas bolsas de cemento necesitás
✅ Cuántos m³ de arena y piedra pedir al corralón
✅ La mano de obra por oficial y ayudante
✅ Los días de obra y los jornales
✅ El cuadro de cuotas y pagos para mostrarle al cliente
✅ El resumen completo con todos los rubros

Todo sale en un presupuesto prolijo para mostrarle al cliente. Nada de papelito escrito a mano.

¿Cuánto cuesta? Lo mismo que 2 bolsas de cemento de 25kg por mes.

Y los que entran ahora, GRATIS.

Si te sirvió o querés probarlo, escribime directo.
```
⚠️ El link `presupuestopro.com.ar` va en el **primer comentario**, no en el post.

---

#### Post corto — grupos grandes
```
El que presupuesta bien, cobra bien. 💡

PresupuestoPRO: ponés los metros de la obra y te calcula solo los materiales, los jornales, las cuotas y el total.

Sin Excel. Sin quedarte corto. Desde el celu.

🎯 Primeros usuarios: GRATIS → presupuestopro.com.ar
```

---

#### 8 posts adicionales listos
**Archivo**: `posts_lanzamiento_presupuestopro.md`

| Post | Canal | Tema |
|------|-------|------|
| 1 | Instagram/Facebook | Carrusel "antes/después" (Excel vs app) |
| 2 | Instagram | "Presupuestás obras de $10M. La herramienta cuesta 2 bolsas de cemento." |
| 3 | Instagram | Precios actualizados constantemente |
| 4 | Instagram | Carrusel "PDF con tu logo" |
| 5 | Reels | Guión 30-45 segundos |
| 6 | LinkedIn | Para arquitectos y estudios |
| 7 | WhatsApp/grupos | Mensaje directo para copiar y pegar |
| 8 | Stories | Secuencia de 4 stories (Story 1 con encuesta) |

---

#### Bio Instagram (150 caracteres)
```
Presupuestá obras en minutos 👷 | Precios actualizados + PDF con tu logo | Para constructores 🇦🇷 | Empezá gratis 👇
```

---

### 5. Respuestas a comentarios frecuentes
**Archivo**: `POST_FACEBOOK_ALBANILES.md` (sección "Respuestas a comentarios frecuentes")

Incluye respuestas listas para:
- "¿Sirve para albañiles o solo para arquitectos?"
- "¿Hay que descargar algo?"
- "¿Y si no sé los precios actuales?"
- "¿Se puede usar en obra sin internet?"
- "¿El presupuesto queda guardado?"

---

## Estrategia de publicación

### Orden recomendado en el grupo
1. Subir video + 5 slides juntos en un post
2. Texto del post principal arriba
3. Primer comentario: link presupuestopro.com.ar

### Horarios óptimos
- **Lunes a viernes 7-9am** (antes de arrancar la obra)
- **12-13hs** (descanso del mediodía)

### Grupos de Facebook a apuntar
- Albañiles Rosario y alrededores
- Albañiles zona sur
- Albañiles de Buenos Aires
- Albañilería de rosario y alrededor
- Constructores y Contratistas (Argentina)
- Grupos de corralones locales por provincia

### Hashtags
```
#presupuestodeobra #albanil #construccion #contratista #obranueva #refaccion #maestrodeobra #trabajo #jornales #materiales #argentina #constructores #albañileria
```

---

## Pendiente antes de escalar

- [ ] Tomar screenshots reales de la app desde el celu (para reemplazar los mockups)
- [ ] Subir logo propio en el demo interactivo de la landing
- [ ] Definir precio definitivo (¿$12.500 o diferente?)
- [ ] Test flujo completo: registro → pago MP → activación → email

---
_Archivos en `D:\ESCRITORIO\CLAUDE\APP_PRESUPUESTOPRO\`_
