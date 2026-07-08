# Campaña "Gratis por Canje" — WhatsApp → Facebook/Instagram
_Creado: 06/07/2026 — hilo Difusión en Redes_

## La mecánica (nuevo modelo, reemplaza al "gratis sin condición")

Ya no se ofrece la app gratis sin más. Se ofrece **gratis a cambio de 3 acciones** ("canje", no sorteo ni concurso — esto importa para no chocar con las reglas de Meta sobre concursos, que exigen bases legales, ver Nota abajo):

1. Seguir la página de Facebook **Presupuestopro**
2. Seguir @presupuesto_pro en Instagram
3. Dar **like** al posteo ancla (fijado en ambas cuentas) **y** etiquetar en los comentarios a **3 colegas** (albañiles, contratistas, corralones)

A cambio: acceso gratis a la app + a los 15-20 días de uso, Daniel les pide feedback real (2-3 preguntas cortas). Esto además resuelve de paso el pendiente del precio: no hay que definir un número todavía, porque el "precio" hoy es el canje, no pesos.

**Verificación (sin desarrollo, arranca ya):** no hay forma automática de chequear follows/likes sin integrarse a la API de Meta (que además no es trivial para esto). Por ahora el control es manual: la persona manda una captura de las 3 acciones por WhatsApp al número personal de Daniel (0341 301-7371, **ya activo**, no hace falta esperar al número nuevo 3417542009) o al mail presupuestopro.app@gmail.com. Daniel confirma y le pasa el acceso. Cuando haya volumen, esto se automatiza con Make.com (webhook de WhatsApp + planilla de control).

**Importante — no depende del pendiente crítico de WhatsApp de la página.** Ese bloqueo es solo para el botón oficial de WhatsApp *en la página de Facebook*. Para esta campaña alcanza con el WhatsApp personal de Daniel, que ya funciona. Se puede lanzar hoy mismo.

---

## 1) Mensaje de WhatsApp (para reenviar a grupos y contactos, y subir como estado)

> 🏗️ *PresupuestoPRO* — De los metros a los pesos, en minutos.
>
> Armá el presupuesto completo de tu obra (materiales + mano de obra + cuadro de pagos + PDF con tu logo) en minutos, no en horas de Excel.
>
> Te la regalamos a cambio de una ayuda:
> 1️⃣ Seguí Presupuestopro en Facebook
> 2️⃣ Seguí @presupuesto_pro en Instagram
> 3️⃣ Le das like al posteo fijado y etiquetás a 3 colegas
>
> Mandame la captura por acá y te activo el acceso gratis. Así de simple.
>
> 👉 presupuestopro.com.ar

_Variante corta para estados de WhatsApp:_
> Presupuestá tu obra en minutos, no en horas de Excel. La app es gratis si seguís nuestras redes y etiquetás a 3 colegas. Posteo fijado en Facebook/Instagram de Presupuestopro. 🏗️

---

## 2) Posteo ancla — Facebook (fijar en la página)

> **¿Cansado de que el presupuesto siempre te quede corto?**
>
> PresupuestoPRO calcula materiales, mano de obra y cuotas de tu obra en minutos — con precios actualizados todos los meses contra corralones de primera línea. Nada de Excel armado a mano, nada de números viejos.
>
> **¿La querés gratis?** Así de fácil:
> ✅ Like a este posteo
> ✅ Etiquetá a 3 colegas (albañiles, contratistas, quien la necesite)
> ✅ Ya seguís esta página, ¿no? Si no, apretá Seguir
>
> Mandanos captura por WhatsApp y te activamos el acceso. De obra a obra.
>
> 👉 presupuestopro.com.ar
>
> #Construccion #Albañiles #Contratistas #PresupuestoPRO

## 3) Variante Instagram (mismo posteo, caption adaptado)

> Che, colega 👷 ¿Seguís presupuestando a ojo o en Excel armado a mano?
>
> PresupuestoPRO te arma el presupuesto completo — materiales, mano de obra, cuotas y PDF con tu logo — en minutos. Precios actualizados cada mes, nunca te quedás corto.
>
> 🎁 ¿La querés gratis? Seguí esta cuenta + like a este posteo + etiquetá a 3 colegas en los comentarios. Nos mandás la captura por WhatsApp y te activamos el acceso.
>
> De los metros a los pesos, en minutos.
>
> .
> #presupuestopro #construccion #albañiles #contratistas #obra #maestromayordeobras #argentina #corralon #materialesdeconstruccion #manodeobra #excel #presupuestodeobra #construccionargentina #albañilargentino #rosario #buenosaires #zonasur #obraencurso #reformas #ampliaciones #refacciones #costosdeobra #calculodemateriales #appdeconstruccion #saasargentina #proptech #tecnologiaparaobra #precioscorralones #contratistaindependiente #obrasenargentina #presupuestogratis

---

## 4) Banner para la landing (copy — implementación técnica es tarea del hilo de desarrollo de la app)

Texto sugerido para un bloque nuevo en `templates/landing.html`, arriba del CTA principal o como banner destacado:

> **¿Querés probarla gratis?**
> Seguí a Presupuestopro en Facebook e Instagram, le das like al posteo fijado y etiquetás a 3 colegas. Nos escribís por WhatsApp y te activamos el acceso.
> [Botón: Ir a Facebook] [Botón: Ir a Instagram] [Botón: Escribir por WhatsApp]

**Handoff:** esto requiere tocar `templates/landing.html` (agregar el bloque + 3 botones con links). Es cambio de código — corresponde al hilo de desarrollo de la app (`PROYECTO.md`), no a este hilo de marketing. Llevar este copy para allá.

---

## Nota — riesgo con las reglas de Meta

Pedir "like + etiquetar" como condición para algo de valor roza las políticas de "engagement bait" de Meta (Facebook puede bajar el alcance orgánico de posteos que piden explícitamente like/comentario como acción obligatoria) y las reglas de promociones (que exigen bases legales si se llama "sorteo" o "concurso"). Para minimizar riesgo:
- No usar la palabra "sorteo" ni "concurso" en ningún lado — es un **canje directo**, no un juego de azar (no aplican bases legales).
- Si Facebook empieza a limitar el alcance del posteo, es una señal para bajar el énfasis en "like" y dejar el foco en "etiquetá a 3 colegas" (esto sí es una práctica común y más tolerada).
- No es necesario resolverlo antes de lanzar — es un riesgo menor (alcance, no baneo de cuenta) y monitoreable.

## Próximos pasos sugeridos
1. Daniel publica el posteo ancla en Facebook e Instagram y lo fija.
2. Daniel reenvía el mensaje de WhatsApp a sus contactos/grupos y lo sube como estado.
3. Cuando lleguen capturas, confirmar manualmente y activar acceso.
4. Llevar el copy del banner de landing al hilo de desarrollo de la app.
5. Publicar el POST 0 (historia de Daniel) — sigue pendiente, es la primera publicación de la página.
