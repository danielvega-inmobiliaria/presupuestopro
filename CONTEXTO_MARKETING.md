# Contexto para chat de Mockups y Promociones — PresupuestoPRO

## Qué es PresupuestoPRO

Aplicación web SaaS para **constructores, arquitectos y contratistas** que permite armar presupuestos de obra de manera rápida, profesional y precisa. Desarrollada en Flask (Python), actualmente en fase de testing local, próximamente en línea.

El creador y dueño es **Daniel** (danve61@gmail.com), Argentina.

---

## Problema que resuelve

Presupuestar una obra en Argentina es caótico: los precios cambian, los materiales tienen distintas unidades, el cálculo de mano de obra es complejo, y la presentación al cliente tiene que ser profesional. La mayoría usa Excel con fórmulas caseras o lo hace de memoria.

PresupuestoPRO automatiza todo eso en un wizard de 8 pasos.

---

## Flujo de la app (8 pasos del wizard)

1. **Datos generales** — cliente, obra, superficie, oficiales, jornales, tipo de cambio
2. **Rubros de obra** — el usuario ingresa cantidades por ítem (Preliminares, Fundaciones, Hormigón Armado, Hormigón Elaborado, Cemento, Mampostería, Contrapisos, Revoques, Revestimientos, Techos, Instalaciones, Cerámicos, Pintura)
3. **Subcontratos** — electricidad, plomería, gas, carpintería, herrería, pintura
4. **Gastos indirectos** — seguros, fletes, alquileres, imprevistos
5. **Resumen de costos** — costo directo, GG, impuestos, total final
6. **Lista de materiales** — generada automáticamente desde los rubros, agrupada por categoría
7. **Cuadro de pago** — anticipo + cuotas semanales/quincenales/mensuales + pago final
8. **PDF final** — genera dos versiones: para el propietario (con precios) y para el constructor (con cantidades de materiales)

---

## Características clave

- **Análisis de precios integrado**: cada ítem de obra tiene una hoja de análisis con submateriales (áridos, cemento, ladrillos, hierro, etc.) y sus cantidades por unidad
- **Lista de materiales automática**: al cargar rubros, calcula solos los materiales necesarios (en bolsas de cemento, m3 de arena, kg de hierro, etc.)
- **Soporte multi-moneda**: ARS, USD, cotización actualizable (Argentina, Chile, Uruguay, Brasil, Paraguay)
- **Modos de presupuesto**: MO+Materiales / Solo MO / Solo Materiales
- **Cuotas de pago**: calcula pagos intermedios reales según días de obra y frecuencia elegida
- **Multi-usuario**: sistema de login, suscripciones con fecha de vencimiento
- **Borradores**: el usuario puede guardar y retomar presupuestos incompletos

---

## Target

**Primario**: Constructores y contratistas independientes en Argentina (y LATAM) que hacen obras de vivienda y refacciones. Perfil: hombre 35-55 años, trabaja en campo, usa el celular tanto como la PC.

**Secundario**: Arquitectos jóvenes que arrancan y necesitan presupuestar con precisión.

**Dolor principal**: "Siempre me quedo corto en el presupuesto" / "No sé cuántos materiales pedir" / "Tardo horas en armar el presupuesto"

---

## Propuesta de valor (para comunicar)

- **"De los metros a los pesos, en minutos"**
- Ingresás las cantidades de obra → la app calcula materiales, mano de obra y total
- Precio de lanzamiento: modelo suscripción mensual (precio a definir, ~$10-15 USD/mes)
- Alternativa a: Excel manual, calculadoras genéricas, honorarios de estudio técnico

---

## Identidad visual (a definir / sugerida)

- **Nombre**: PresupuestoPRO
- **Paleta sugerida**: azul construcción (#1E3A5F) + naranja obras (#F97316) + blanco
- **Ícono**: casco + calculadora, o plano arquitectónico + signo $
- **Tono**: profesional pero directo, sin tecnicismos innecesarios. Para gente que trabaja con las manos y necesita resultados rápidos.
- **No es**: una app contable, no reemplaza al contador. Es una herramienta de campo.

---

## Lo que necesita el chat de mockups y redes

### Mockups (pantallas)
Crear imágenes de presentación de la app para redes y landing page. Opciones:
- Pantalla del wizard (paso 2 rubros, paso 6 materiales, paso 7 cuadro de pagos)
- Vista del PDF generado
- Dashboard de presupuestos guardados
- Vista móvil (responsive)

Estilo sugerido: mockup en dispositivo (laptop + celular), fondo oscuro o degradado azul/gris, texto en español, números argentinos ($).

### Contenido para redes sociales
- **Instagram/Facebook**: carruseles explicando el problema y la solución, stories con el before/after (Excel vs PresupuestoPRO), Reels mostrando los 8 pasos
- **LinkedIn**: post dirigido a arquitectos y estudios
- **WhatsApp/grupos de constructores**: mensaje corto de presentación

### Copy para lanzamiento
- Slogan
- Descripción corta (bio Instagram, 150 caracteres)
- Descripción larga (landing page, 3-4 párrafos)
- 3-5 posts de lanzamiento listos para publicar
- Posibles objeciones y respuestas

---

## Estado actual

- App funcional en localhost, próximamente en ngrok para demos
- Sin dominio ni hosting aún (próximo paso: Railway.app o Render.com)
- Sin diseño de marca definido (el chat de mockups puede proponer)
- Sin precio de suscripción definido aún

---

## Instrucción para el chat nuevo

Con este contexto, necesito:
1. Mockups de pantallas de la app para usar en redes (imágenes de presentación)
2. Copy y contenido para lanzamiento en Instagram, Facebook y grupos de WhatsApp de constructores
3. Propuesta de identidad visual (colores, logo, tipografía)
4. Al menos 5 posts listos para publicar

El tono tiene que ser directo, práctico, para alguien que trabaja en obra — no para un diseñador de interiores.
