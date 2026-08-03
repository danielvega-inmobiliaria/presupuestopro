/* ═══════════════════════════════════════════════════════════════
   PRESUPUESTOPRO · Tour interactivo de onboarding (spotlight, modo demo)
   Pedido de Daniel 02/08/2026 — estrategia de conversión: de 140
   usuarios registrados, 45 vencieron la prueba gratis sin pagar
   nunca (0 conversiones).

   Historial (para quien retome esto):
   - v1: tour "real" — el usuario tenía que escribir sus propios datos
     para poder avanzar. No funcionaba ("me quedo esperando, no sé qué
     hay que completar").
   - v2: demo auto-completado (rubros/subcontratos/indirectos
     precargados vía routes/presupuesto.py::demo()), pero el usuario
     todavía tenía que ir clickeando los controles reales de cada
     pantalla para avanzar.
   - v3 (esta versión, 02/08/2026 2da vuelta): recorrido MUCHO más
     granular — arranca mostrando cómo configurar la empresa (perfil),
     sigue con 2 ejemplos de Costo/m², y recién ahí entra al asistente
     de presupuesto (paso 1 a 8) y termina en la pantalla final con los
     2 PDF. En cada pantalla se van iluminando los bloques uno por uno
     con su propia explicación. El usuario SOLO toca "Siguiente" en el
     popover — nunca tiene que interactuar con el control real de la
     página (ni tocar un botón "Guardar", ni un link "Nuevo
     presupuesto"): este script dispara el submit del formulario real o
     la navegación por su cuenta cuando corresponde. Ver `leaveAction`
     en cada paso de STEPS más abajo.

   Librería: Driver.js (CDN, cargada en templates/base.html).

   Patrón multi-página: cada `{% block tour_stage %}...{% endblock %}`
   (ver templates/base.html) declara en qué pantalla está el usuario,
   vía `data-tour-stage` en <body>. Como cada carga de página destruye
   la instancia de Driver.js, el índice del paso actual se guarda en
   localStorage antes de navegar y se retoma en la página siguiente
   (patrón oficial de Driver.js para tours multi-página).
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var STORAGE_KEY = 'pp_tour_step';
  var MARCAR_URL = '/tour/completar';
  var URL_DASHBOARD = '/';
  var URL_PERFIL = '/perfil/';
  var URL_COSTO_M2 = '/costo-m2/';
  var URL_DEMO = '/presupuesto/demo';
  // Ítems de ejemplo para el recorrido de Costo/m² — bien distintos entre sí
  // (uno de hormigón, otro de mampostería) para mostrar que el cálculo
  // funciona igual con cualquier ítem. Fix 02/08/2026 (bug reportado por
  // Daniel): antes se armaba la URL con un item_id NUMÉRICO hardcodeado
  // (36, 40) — funcionaba en la base de prueba de esta sesión, pero en la
  // base real esos números son de OTROS ítems (el id autoincremental no es
  // estable entre bases). Ahora se resuelve por NOMBRE, vía
  // costo_m2.resultado_demo (routes/costo_m2.py) — el nombre del ítem sí es
  // estable, es el mismo catálogo fijo en cualquier base.
  var URL_RESULTADO_ZAPATA = '/costo-m2/resultado-demo?nombre=' + encodeURIComponent('Zapata Ho Pobre');
  var URL_RESULTADO_MAMPOSTERIA = '/costo-m2/resultado-demo?nombre=' + encodeURIComponent('Mamp. ladrillo comun 30cm');
  var URL_PASO1 = '/presupuesto/nuevo';
  var URL_PASO2 = '/presupuesto/rubros';
  var URL_PASO3 = '/presupuesto/subcontratos';
  var URL_PASO4 = '/presupuesto/indirectos';
  var URL_PASO5 = '/presupuesto/modo-tiempo';
  var URL_PASO6 = '/presupuesto/materiales';
  var URL_PASO7 = '/presupuesto/forma-pago';
  var URL_PASO8 = '/presupuesto/resumen';

  // Cada paso vive en una pantalla concreta (`stage`) y apunta a un
  // elemento real de esa pantalla. `pageUrl` es la URL para LLEGAR a esa
  // pantalla — se usa para el botón "Atrás" cuando el paso anterior queda
  // en otra página (ver `retroceder()`). `leaveAction` (solo en el ÚLTIMO
  // paso de cada pantalla) define cómo se avanza a la siguiente: "navigate"
  // pega un salto directo a otra URL, "submit" dispara el submit real del
  // formulario de esa pantalla (con todos sus datos ya precargados). Los
  // pasos sin `leaveAction` simplemente avanzan dentro de la misma pantalla.
  var STEPS = [
    // ── 1) Mi Empresa ──────────────────────────────────────────────
    {
      stage: 'dashboard', element: '#tour-mi-empresa', pageUrl: URL_DASHBOARD,
      popover: {
        title: '¡Bienvenido a PresupuestoPRO! 👋',
        description: 'Antes de armar tu primer presupuesto, configuremos los datos de tu empresa — así van a aparecer en los PDFs que le mandás a tus clientes. Con tocar "Siguiente" alcanza, no hace falta que hagas clic en nada de la pantalla real.'
      },
      leaveAction: { type: 'navigate', url: URL_PERFIL }
    },
    {
      stage: 'perfil', element: '#tour-perfil-logo', pageUrl: URL_PERFIL,
      popover: { title: 'Tu logo', description: 'Así se ve tu logo en los PDF. Por ahora, sin logo cargado, usamos las iniciales de tu empresa — podés subir el tuyo cuando quieras, acá mismo.' }
    },
    {
      stage: 'perfil', element: '#tour-perfil-datos-1', pageUrl: URL_PERFIL,
      popover: { title: 'Nombre y slogan', description: 'El nombre de tu empresa y, si querés, un Slogan que te diferencie — "Calidad y confianza en cada obra", por ejemplo. Todo esto sale en tus PDFs.' }
    },
    {
      stage: 'perfil', element: '#tour-perfil-datos-2', pageUrl: URL_PERFIL,
      popover: { title: 'Contacto', description: 'Y tu nombre de contacto, teléfono y email. Esto es tu perfil real, no lo vamos a modificar en el recorrido.' },
      leaveAction: { type: 'navigate', url: URL_DASHBOARD }
    },
    // ── 2) Costo/m² (aha moment rápido) ────────────────────────────
    {
      stage: 'dashboard', element: '#tour-costo-m2', pageUrl: URL_DASHBOARD,
      popover: { title: '¿Necesitás algo más rápido?', description: '¿Necesitás una respuesta rápida sin armar todo el presupuesto? Con "Costo/m²" calculás el costo de un solo ítem en segundos. Te muestro cómo.' },
      leaveAction: { type: 'navigate', url: URL_COSTO_M2 }
    },
    {
      stage: 'costo_m2', element: '#tour-costo-m2-item1', pageUrl: URL_COSTO_M2,
      popover: { title: '¿Necesitás algo más rápido?', description: 'Elegís un ítem — por ejemplo este, que se calcula por metro lineal — y calculás en segundos su costo por ml, m² o m³, sin tener que armar todo el presupuesto.' },
      leaveAction: { type: 'navigate', url: URL_RESULTADO_ZAPATA }
    },
    // Resultado de ejemplo #1: Zapata Ho Pobre — scrollea y va iluminando
    // Jornales, Adicionales y Desglose de materiales.
    {
      stage: 'resultado', element: '#tour-costo-jornales', pageUrl: URL_RESULTADO_ZAPATA,
      popover: { title: 'Así se ve el resultado', description: 'Por ejemplo, esta es "Zapata Hº Pobre". Acá, los Jornales — podés editarlos de acuerdo a lo que le pagás realmente a tu oficial y a tu ayudante.' }
    },
    {
      stage: 'resultado', element: '#tour-costo-adicionales', pageUrl: URL_RESULTADO_ZAPATA,
      popover: { title: 'Adicionales', description: 'También podés editar el % de Beneficio y de Seguro — se recalcula todo en vivo.' }
    },
    {
      stage: 'resultado', element: '#tour-costo-desglose', pageUrl: URL_RESULTADO_ZAPATA,
      popover: { title: 'Desglose de materiales', description: 'Y acá el desglose de materiales: podés editar el precio de lista de cada uno según los valores de tu zona.' },
      leaveAction: { type: 'navigate', url: URL_RESULTADO_MAMPOSTERIA }
    },
    // Resultado de ejemplo #2: Mamp. ladrillo comun 30cm — mismo recorrido,
    // para reforzar que funciona igual con cualquier ítem.
    {
      stage: 'resultado', element: '#tour-costo-jornales', pageUrl: URL_RESULTADO_MAMPOSTERIA,
      popover: { title: 'Lo mismo con cualquier ítem', description: 'Probemos con otro bien distinto: Mampostería de ladrillo común de 30cm. Los jornales, de nuevo, editables.' }
    },
    {
      stage: 'resultado', element: '#tour-costo-adicionales', pageUrl: URL_RESULTADO_MAMPOSTERIA,
      popover: { title: 'Adicionales', description: 'Beneficio y Seguro, siempre editables acá.' }
    },
    {
      stage: 'resultado', element: '#tour-costo-desglose', pageUrl: URL_RESULTADO_MAMPOSTERIA,
      popover: { title: 'Desglose de materiales', description: 'Y el desglose de materiales de este ítem, con precios también editables según tu zona.' },
      leaveAction: { type: 'navigate', url: URL_DEMO }
    },
    // ── 3) Presupuesto — Paso 1: Datos de obra ─────────────────────
    {
      stage: 'paso1', element: '#tour-cliente', pageUrl: URL_PASO1,
      popover: { title: 'Ahora sí, el presupuesto', description: 'Ya completamos un cliente de ejemplo (ficticio) — así se ve. Vos vas a cargar acá los datos reales de tu cliente.' }
    },
    {
      stage: 'paso1', element: '#tour-obra-desc', pageUrl: URL_PASO1,
      popover: { title: 'Datos de la obra', description: 'Descripción y dirección — también de ejemplo. Nada de esto hace falta tocarlo ahora.' }
    },
    {
      stage: 'paso1', element: '#tour-obra-tipo', pageUrl: URL_PASO1,
      popover: { title: 'Tipo, fecha y validez', description: 'Y el tipo de obra, la fecha y los días de validez del presupuesto. Seguimos con "Siguiente".' },
      leaveAction: { type: 'submit', formId: 'formObra' }
    },
    // ── Paso 2: Cómputo ─────────────────────────────────────────────
    // Fix 02/08/2026 (mismo bug que Costo/m²): antes apuntaba a #row-39 /
    // #row-54 — el id autoincremental del ítem, que no es estable entre
    // bases. Ahora usa un selector estable: "el ítem con cantidad cargada
    // dentro del rubro X" (.fila.activa ya se pinta server-side cuando
    // prev_cant > 0 — ver paso2_rubros.html), sin depender de qué id
    // numérico le tocó a ese ítem en cada base.
    {
      stage: 'paso2', element: '#rubro06 .fila.activa', pageUrl: URL_PASO2,
      popover: { title: 'Cómputo de la obra', description: 'Elegimos ejemplos de distintos rubros. Este es el ítem de ejemplo dentro de Mampostería, ya con una cantidad cargada. Acá cargás las cantidades reales de tu obra y el costo se calcula solo, en vivo.' }
    },
    {
      stage: 'paso2', element: '#rubro07 .fila.activa', pageUrl: URL_PASO2,
      popover: { title: 'Otro rubro, mismo criterio', description: 'Y este es el ítem de ejemplo dentro de Contrapisos — otro ítem ya cargado.' },
      leaveAction: { type: 'submit', formId: 'formComputo' }
    },
    // ── Paso 3: Subcontratos ──────────────────────────────────────
    {
      stage: 'paso3', element: '#tour-subcontratos', pageUrl: URL_PASO3,
      popover: { title: 'Subcontratos', description: 'Si tenés subcontratos (electricidad, plomería...) los marcás acá, con su mano de obra y materiales. Ya dejamos 2 de ejemplo cargados.' },
      leaveAction: { type: 'submit', formId: 'formSubc' }
    },
    // ── Paso 4: Indirectos ──────────────────────────────────────────
    {
      stage: 'paso4', element: '#tour-indirectos', pageUrl: URL_PASO4,
      popover: { title: 'Costos indirectos', description: 'Movilidad, alquiler de andamios y de herramientas — gastos de la obra que no son ni mano de obra ni materiales. Ya completados como ejemplo.' },
      leaveAction: { type: 'submit', formId: 'formInd' }
    },
    // ── Paso 5: Modo y tiempo ────────────────────────────────────────
    // Fix 02/08/2026 (bug reportado por Daniel, 5ta vuelta): el bloque
    // único #tour-paso5-config era muy alto — el % GG y % Impuestos
    // quedaban fuera de la pantalla visible junto con el popover. Se separó
    // en 2 pasos: Cuadrilla (#tour-paso5-modo) y Márgenes
    // (#tour-paso5-margenes).
    {
      stage: 'paso5', element: '#tour-paso5-modo', pageUrl: URL_PASO5,
      popover: {
        title: 'Tu cuadrilla',
        description: 'Acá ajustás cuántos oficiales y ayudantes usás y cuánto les pagás por día. Si tu presupuesto no incluye materiales (los pone el cliente), arriba de todo podés elegir "Solo mano de obra".'
      }
    },
    {
      stage: 'paso5', element: '#tour-paso5-margenes', pageUrl: URL_PASO5,
      popover: {
        title: 'Tus márgenes',
        description: 'Y acá el % de gastos generales/beneficio y el % de impuestos y seguros — con esto se arma el Costo Directo y el Total final.'
      }
    },
    {
      stage: 'paso5', element: '#tour-paso5-barra1', pageUrl: URL_PASO5,
      popover: { title: 'Costo Directo y Total base', description: 'Con esos datos se arma el Costo Directo (más subcontratos e indirectos) y el Total base.' }
    },
    {
      stage: 'paso5', element: '#tour-paso5-barra23', pageUrl: URL_PASO5,
      popover: { title: 'Total Final y Ganancia Real', description: 'Y acá, sumando GG/Beneficio e Impuestos: el Total Final (lo que le cobrás al cliente) y — lo más importante — tu Ganancia Real. Ojo: si vos mismo trabajás como uno de los oficiales, a esa Ganancia Real hay que sumarle también lo que cobrás por tu propio trabajo.' },
      leaveAction: { type: 'submit', formId: 'formModo' }
    },
    // ── Paso 6: Materiales ────────────────────────────────────────
    {
      stage: 'paso6', element: '#tour-materiales-precio', pageUrl: URL_PASO6,
      popover: { title: 'Precio unitario editable', description: 'Los materiales se calculan solos a partir de tus ítems. Podés editar el precio unitario de cada uno según lo que cuesta en tu zona — al cambiarlo, se actualiza el subtotal de esa fila.' }
    },
    {
      stage: 'paso6', element: '#tour-materiales-total', pageUrl: URL_PASO6,
      popover: { title: 'Total de materiales', description: 'Y acá te queda el total de materiales de todo el presupuesto.' },
      leaveAction: { type: 'submit', formId: 'formMateriales' }
    },
    // ── Paso 7: Forma de pago ────────────────────────────────────────
    {
      stage: 'paso7', element: '#tour-paso7-config', pageUrl: URL_PASO7,
      popover: { title: 'Forma de pago', description: 'El % de anticipo y de saldo final son editables, y elegís la frecuencia de las cuotas intermedias. Para este ejemplo elegimos cuotas semanales.' }
    },
    {
      stage: 'paso7', element: '#tour-paso7-cuadro', pageUrl: URL_PASO7,
      popover: { title: 'Cuadro de pago estimado', description: 'Con eso se arma el cuadro de pago: anticipo al inicio, cuotas intermedias y saldo final al terminar la obra.' },
      leaveAction: { type: 'submit', formId: 'formPago' }
    },
    // ── Paso 8: Resumen y Guardar ─────────────────────────────────
    {
      stage: 'paso8', element: '#tour-p8-cliente-obra', pageUrl: URL_PASO8,
      popover: { title: 'Resumen final', description: 'Arriba de todo, cliente y obra — con los mismos datos de ejemplo que cargamos antes.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-obra-datos', pageUrl: URL_PASO8,
      popover: { title: 'Ubicación y cuadrilla', description: 'Dirección, fecha y la cuadrilla de trabajo que definiste en el paso 5.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-totales', pageUrl: URL_PASO8,
      popover: { title: 'Totales', description: 'Acá los totales del presupuesto: costo directo, subcontratos, indirectos, GG e impuestos, y el TOTAL final.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-pago', pageUrl: URL_PASO8,
      popover: { title: 'Forma de pago', description: 'La forma de pago que elegiste en el paso anterior, ya calculada.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-materiales', pageUrl: URL_PASO8,
      popover: { title: 'Materiales a comprar', description: 'La lista completa de materiales a comprar para esta obra, con cantidades y precios.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-descripcion', pageUrl: URL_PASO8,
      popover: { title: 'Descripción de trabajos', description: 'Este texto se arma solo, a partir de los ítems que presupuestaste — y es editable antes de guardar. Sale en los 2 PDF.' }
    },
    {
      stage: 'paso8', element: '#tour-guardar', pageUrl: URL_PASO8,
      popover: { title: 'Guardar', description: 'Tocás "Guardar" y listo: se genera el presupuesto final, con sus 2 PDF.' },
      leaveAction: { type: 'submit', formId: 'formResumen' }
    },
    // ── Presupuesto guardado: materiales + botones + cierre ─────────
    // (pageUrl null: la URL real es /presupuesto/<id>, no se conoce de
    // antemano — "Atrás" desde el primer paso de acá no está soportado,
    // caso límite: ya se guardó, no tiene mucho sentido volver.)
    {
      stage: 'ver', element: '#tour-ver-materiales', pageUrl: null,
      popover: { title: 'Presupuesto guardado ✓', description: 'Este es tu presupuesto ya armado. Bajamos hasta el final para ver el detalle completo de materiales.' }
    },
    {
      stage: 'ver', element: '#tour-ver-botones', pageUrl: null,
      popover: { title: 'Tus 4 accesos', description: '"Volver" te lleva al Dashboard, "Editar" te deja modificar el presupuesto, y los 2 PDF: "Propietario" (para mandarle a tu cliente) y "Constructor" (con el detalle completo, para vos).' }
    },
    {
      stage: 'ver', element: '#tour-fin-recorrido', pageUrl: null,
      popover: { title: '¡Listo! 🎉', description: 'Mirá los 2 PDF ahora mismo, con el nombre y el logo de tu empresa, sin tener que descargarlos. Cuando quieras, tocá "Final del recorrido".' }
    }
  ];

  var _tourEnding = false;

  function leerStorage() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }
  function guardarStorage(v) {
    try { localStorage.setItem(STORAGE_KEY, String(v)); } catch (e) { /* Safari privado, etc. — no crítico */ }
  }
  function limpiarStorage() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* no crítico */ }
  }

  function marcarCompletadoBackend() {
    try {
      fetch(MARCAR_URL, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } }).catch(function () {});
    } catch (e) { /* no crítico */ }
  }

  function terminarTour(driverObj) {
    if (_tourEnding) return;
    _tourEnding = true;
    limpiarStorage();
    document.body.dataset.tourDone = '1';
    try { if (driverObj) driverObj.destroy(); } catch (e) {}
    marcarCompletadoBackend();
  }

  // El link "Mi empresa" vive dentro del dropdown del usuario (navbar), que
  // arranca cerrado. Lo abrimos por JS para poder iluminarlo sin pedirle al
  // usuario que lo abra él mismo.
  function abrirMenuUsuario() {
    var toggle = document.querySelector('.navbar-nav .dropdown-toggle');
    if (!toggle) return;
    var menu = toggle.parentElement ? toggle.parentElement.querySelector('.dropdown-menu') : null;
    if (menu && !menu.classList.contains('show')) {
      if (window.bootstrap && window.bootstrap.Dropdown) {
        try { window.bootstrap.Dropdown.getOrCreateInstance(toggle).show(); return; } catch (e) {}
      }
      menu.classList.add('show'); // fallback sin bootstrap.js
    }
  }

  // El acordeón de rubros (paso 2) arranca todo cerrado — antes de iluminar
  // un ítem puntual adentro de un rubro, hay que abrir ese rubro (mismo
  // mecanismo que el dropdown de "Mi empresa": Bootstrap Collapse por JS).
  // Fix 02/08/2026 (bug reportado por Daniel: el popover tapaba el ítem en
  // vez de mostrarlo, en los dos pasos de Cómputo): antes esto era
  // sincrónico y Driver.js iluminaba el ítem EN EL MISMO INSTANTE en que se
  // pedía abrir el rubro — pero la animación del collapse de Bootstrap tarda
  // ~350ms, así que Driver.js calculaba la posición del ítem ANTES de que
  // terminara de desplegarse (con una altura/posición todavía "a mitad de
  // camino"), y el popover quedaba mal ubicado. Ahora se espera el evento
  // `shown.bs.collapse` (o como mucho 400ms) antes de recién ahí iluminar.
  function abrirRubroYEsperar(rnum, callback) {
    var el = document.getElementById('rubro' + rnum);
    if (!el) { callback(); return; }
    if (el.classList.contains('show')) { callback(); return; } // ya estaba abierto
    var yaLlamado = false;
    var terminar = function () {
      if (yaLlamado) return;
      yaLlamado = true;
      callback();
    };
    el.addEventListener('shown.bs.collapse', terminar, { once: true });
    setTimeout(terminar, 400); // red de seguridad si el evento no llega
    if (window.bootstrap && window.bootstrap.Collapse) {
      try { window.bootstrap.Collapse.getOrCreateInstance(el, { toggle: false }).show(); return; } catch (e) {}
    }
    el.classList.add('show'); // fallback sin bootstrap.js — no hay animación, terminar() ya
  }

  // Ajustes previos a iluminar un elemento puntual (el panel final del tour
  // arranca oculto — display:none — hasta que se llega a este paso; el link
  // "Mi empresa" arranca dentro de un dropdown cerrado; los ítems de
  // Mampostería/Contrapisos arrancan dentro de un rubro colapsado). Recibe
  // un callback porque abrir un rubro es asíncrono (espera la animación).
  // Fix 02/08/2026 (bug reportado por Daniel, 4ta vuelta — el popover
  // SEGUÍA tapando contenido pese a dividir los bloques altos): se probó
  // primero `side:'top'` por paso (no alcanzaba), después la opción de
  // config `scrollIntoViewOptions: {block:'start'}` (Round 5→7 de esta
  // sesión) — comprobado ahora con una prueba real en un iframe de 390px
  // (ancho de celular) que ESA OPCIÓN NO HACE NADA: el elemento terminaba
  // scrolleado a una posición arbitraria (ni arriba, ni centrado), cortado
  // por el borde inferior de la pantalla. En vez de seguir confiando en esa
  // opción de Driver.js, ahora se hace el scroll A MANO acá, ANTES de
  // iluminar — mismo patrón que ya funcionó para el bug de la animación del
  // acordeón en paso 2 (esperar a que el layout se asiente antes de que
  // Driver.js calcule dónde poner el popover).
  // Fix 02/08/2026 (5ta vuelta): probado en vivo que 'center' no alcanza —
  // en pantallas donde el documento no tiene mucho margen para scrollear
  // (bloques cerca del principio o del final de una página corta), centrar
  // no deja lugar de sobra en ningún lado y Driver.js termina superponiendo
  // el popover sobre el propio elemento (esquina superior izquierda). Ahora
  // se scrollea el elemento SIEMPRE arriba de todo ("start") — así queda
  // garantizado que TODO el resto de la pantalla, hacia abajo, está libre —
  // y se fuerza side:'bottom'/align:'start' en cada paso (ver
  // crearDriverTour) para que Driver.js no tenga que "adivinar" un lado y
  // vuelva a caer en el fallback de superponer.
  //
  // Fix 02/08/2026 (6ta vuelta): CAUSA RAÍZ ENCONTRADA, con medición en vivo
  // sobre el sitio real (no simulado). El HTML del sitio tiene
  // `scroll-behavior: smooth` en `<html>` — no lo pusimos nosotros, es el
  // Reboot de Bootstrap 5 (`@media (prefers-reduced-motion: no-preference)
  // { :root { scroll-behavior: smooth } }`, activo salvo que el usuario
  // tenga "reducir movimiento" activado). `behavior:'auto'` en scrollTo NO
  // es "instantáneo": por spec, 'auto' significa "hacé lo que diga el CSS
  // del elemento" — como el CSS dice 'smooth', TODOS los scrolls de este
  // archivo (incluida `document.documentElement.scrollTop = x`, que
  // también sigue esa regla) quedaban animados, no instantáneos. El
  // `setTimeout(callback, 150)` de acá abajo asumía que a los 150ms el
  // scroll ya había terminado — probado en vivo que el scroll TODAVÍA
  // seguía animándose en ese momento (para distancias largas, la animación
  // tarda más). Resultado: Driver.js calculaba y congelaba la posición del
  // popover con el layout a MITAD de camino del scroll, y la página seguía
  // moviéndose después — de ahí el desfasaje/superposición en los 6 puntos
  // reportados, pese a los 5 intentos anteriores (ninguno tocaba esto,
  // todos asumían que el scroll ya era instantáneo). Confirmado con prueba
  // en vivo: `scrollTo({top, behavior:'auto'})` y hasta `scrollTop = x` NO
  // movían la página en 250ms; solo `behavior:'instant'` (que por spec
  // ignora el `scroll-behavior` del CSS y fuerza el salto real) funcionó.
  // Fix: forzar `behavior:'instant'` acá.
  //
  // Segunda causa encontrada en la MISMA prueba en vivo (independiente de la
  // del scroll): en Costo/m² (y probablemente en otras pantallas con su
  // propio sub-header, como el acordeón de rubros en paso 2) hay un DIV
  // `.sticky-top` propio de esa pantalla — con el título "Costo por M²",
  // "Volver" y el texto "Seleccioná un ítem..." — que mide 95px de alto.
  // `--nav-h` (fijado en base.html) solo mide `nav.navbar`, así que en esta
  // pantalla puntual `navH` quedaba con el fallback de 56px en vez de los
  // 95px reales — el ítem quedaba scrolleado a y:68, TAPADO por ese sticky
  // propio de la pantalla (que ocupa hasta y:95). Fix: en vez de asumir que
  // lo único pegado arriba es el navbar, se mide en vivo, en cada scroll,
  // cuál es el borde inferior más bajo entre TODOS los elementos realmente
  // pegados al techo de la pantalla en ese momento (navbar + cualquier
  // sub-header propio de la pantalla actual) — así sirve para cualquier
  // pantalla, sin tener que hardcodear una altura distinta por cada una.
  function alturaStickyTope() {
    var max = 0;
    var els = document.querySelectorAll('body *');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      var r = el.getBoundingClientRect();
      if (r.height <= 0) continue;
      if (cs.position === 'fixed') {
        // Un elemento fixed ya reporta su posición real relativa al viewport
        // en cualquier momento — sirve mirar su rect tal cual.
        if (r.top <= 5 && r.bottom > max) max = r.bottom;
      } else if (cs.position === 'sticky') {
        // OJO: un sticky recién cargado (scrollY:0, antes de scrollear más
        // allá de su posición natural en el documento) todavía NO está
        // "pegado" — su rect.top puede no ser 0 todavía (ver bug real
        // encontrado en Costo/m²: a scrollY:0 el sticky-top propio de esa
        // pantalla medía top:24, no top:0, porque recién se pega una vez
        // que se scrollea más allá de esos 24px). Por eso NO hay que mirar
        // el rect actual para decidir si cuenta, sino su `top` de CSS (a
        // qué altura se pega cuando se activa) — si ese valor es ~0, este
        // elemento SÍ va a tapar la parte de arriba de la pantalla en
        // cuanto se scrollee, así que cuenta su alto igual, esté ya pegado
        // o no en este momento.
        var cssTop = parseFloat(cs.top);
        if (!isNaN(cssTop) && cssTop <= 5) {
          var borde = cssTop + r.height;
          if (borde > max) max = borde;
        }
      }
    }
    return max;
  }
  function scrollearYEsperar(selector, callback) {
    var el = document.querySelector(selector);
    if (!el) { callback(); return; }
    var navH = alturaStickyTope();
    if (!navH) {
      // Red de seguridad si por lo que sea no se detectó nada pegado arriba.
      try {
        var v = getComputedStyle(document.documentElement).getPropertyValue('--nav-h');
        navH = (v && parseInt(v, 10)) || 56;
      } catch (e) { navH = 56; }
    }
    var destino = el.getBoundingClientRect().top + window.scrollY - navH - 12;
    window.scrollTo({ top: Math.max(destino, 0), behavior: 'instant' });
    setTimeout(callback, 150); // deja que el reflow se asiente (el scroll en sí ya es instantáneo)
  }

  function prepararElemento(step, callback) {
    callback = callback || function () {};
    if (!step) { callback(); return; }
    if (step.element === '#tour-fin-recorrido') {
      var panel = document.querySelector('#tour-fin-recorrido');
      if (panel) panel.style.display = '';
    }
    if (step.element === '#tour-mi-empresa') {
      abrirMenuUsuario();
    }
    if (step.element === '#rubro06 .fila.activa') {
      abrirRubroYEsperar('06', function () { scrollearYEsperar(step.element, callback); });
      return;
    }
    if (step.element === '#rubro07 .fila.activa') {
      abrirRubroYEsperar('07', function () { scrollearYEsperar(step.element, callback); });
      return;
    }
    scrollearYEsperar(step.element, callback);
  }

  // Usada tanto por "Siguiente" como por la X (cerrar) — cerrar un popover
  // puntual no apaga el recorrido entero, solo avanza al próximo paso.
  function avanzarOTerminar(driverObj) {
    var activeIndex = driverObj.getActiveIndex();
    var actual = STEPS[activeIndex];
    var siguiente = STEPS[activeIndex + 1];

    if (!siguiente) {
      terminarTour(driverObj);
      return;
    }

    // Mismo stage y sin acción especial de salida: solo avanzar en la
    // misma página (no hace falta guardar nada ni destruir la instancia).
    if (siguiente.stage === document.body.dataset.tourStage && !actual.leaveAction) {
      prepararElemento(siguiente, function () { driverObj.moveNext(); });
      return;
    }

    // Cambio de pantalla (o el paso actual tiene una acción explícita de
    // salida) — guardamos en qué paso retomar y ejecutamos la acción.
    guardarStorage(activeIndex + 1);
    try { driverObj.destroy(); } catch (e) {}

    if (actual.leaveAction) {
      if (actual.leaveAction.type === 'submit') {
        var form = document.getElementById(actual.leaveAction.formId);
        if (form) {
          if (form.requestSubmit) form.requestSubmit(); else form.submit();
          return;
        }
      } else if (actual.leaveAction.type === 'navigate') {
        window.location.href = actual.leaveAction.url;
        return;
      }
    }
    // Sin leaveAction pero con cambio de stage (no debería pasar con el
    // STEPS actual, pero por las dudas no rompemos nada): el usuario sigue
    // con la navegación normal de la app y el tour se retoma solo si vuelve
    // a coincidir data-tour-stage en la próxima carga de página.
  }

  // Fix 02/08/2026 (bug reportado por Daniel): "Atrás" no hacía nada cuando
  // el paso anterior quedaba en OTRA página — Driver.js por sí solo no sabe
  // navegar, solo puede resaltar elementos que ya están en el DOM actual.
  // Mismo patrón que avanzarOTerminar(), pero yendo para atrás: si el paso
  // anterior vive en la misma página, solo retrocede el índice; si vive en
  // otra, guarda el índice a retomar y navega ahí de verdad.
  function retroceder(driverObj) {
    var activeIndex = driverObj.getActiveIndex();
    if (activeIndex <= 0) return; // ya está en el primer paso, no hay "atrás"
    var anterior = STEPS[activeIndex - 1];
    var actual = STEPS[activeIndex];

    if (anterior.pageUrl === actual.pageUrl) {
      prepararElemento(anterior, function () { driverObj.movePrevious(); });
      return;
    }
    if (!anterior.pageUrl) return; // caso límite sin URL conocida (ver stage) — no navega

    guardarStorage(activeIndex - 1);
    try { driverObj.destroy(); } catch (e) {}
    window.location.href = anterior.pageUrl;
  }

  function crearDriverTour() {
    var driverObj = window.driver.js.driver({
      showProgress: true,
      animate: true,
      overlayOpacity: 0.55,
      popoverClass: 'pp-tour-popover',
      nextBtnText: 'Siguiente',
      prevBtnText: 'Atrás',
      doneBtnText: 'Entendido',
      // Fix 02/08/2026 (bug reportado por Daniel: "qué función cumple la X
      // y por qué está recuadrada en azul"): la X del popover confundía —
      // parecía "cerrar" pero en realidad avanzaba un paso (mismo criterio
      // que "Siguiente", para no terminar el tour entero sin querer). Ahora
      // se saca directamente: "Saltar todo el recorrido" ya cubre esa
      // necesidad, sin el elemento ambiguo de más.
      allowClose: false,
      // Fix 02/08/2026 (4ta vuelta): se sacó `scrollIntoViewOptions` de acá
      // — probado con una prueba real en viewport de celular (390px) que no
      // tiene ningún efecto (el elemento no quedaba ni arriba ni centrado,
      // sino cortado por el borde inferior). El scroll ahora se hace a mano
      // ANTES de iluminar, ver scrollearYEsperar()/prepararElemento() más
      // abajo — mismo patrón que ya funcionó para el bug del acordeón en
      // paso 2 (esperar a que el layout se asiente antes de que Driver.js
      // calcule la posición del popover).
      // Fix 02/08/2026 (5ta vuelta): antes se dejaba que Driver.js
      // calculara solo de qué lado poner el popover (side/align
      // automáticos). Combinado con el scroll manual de arriba (que deja
      // el elemento pegado arriba de todo, debajo del navbar), forzamos acá
      // side:'bottom'/align:'start' en TODOS los pasos — así el popover
      // siempre va DEBAJO del elemento iluminado, nunca superpuesto en su
      // esquina (que es lo que pasaba cuando Driver.js no encontraba lugar
      // claro de ningún lado).
      steps: STEPS.map(function (s) {
        var pop = {};
        for (var k in s.popover) { pop[k] = s.popover[k]; }
        if (!pop.side) pop.side = 'bottom';
        if (!pop.align) pop.align = 'start';
        return { element: s.element, popover: pop };
      }),
      onCloseClick: function () { avanzarOTerminar(driverObj); },
      onDoneClick: function () { terminarTour(driverObj); },
      onNextClick: function () { avanzarOTerminar(driverObj); },
      onPrevClick: function () { retroceder(driverObj); },
      // Link chico "Saltar todo el recorrido" — única forma real de
      // saltear el tour completo antes del final.
      onPopoverRender: function (popover) {
        var link = document.createElement('button');
        link.type = 'button';
        link.className = 'pp-tour-skip';
        link.textContent = 'Saltar todo el recorrido';
        link.addEventListener('click', function () { terminarTour(driverObj); });
        popover.wrapper.appendChild(link);
      }
    });
    return driverObj;
  }

  function init() {
    if (!window.driver || !window.driver.js || !window.driver.js.driver) return; // CDN no cargó
    var stage = document.body.dataset.tourStage;
    if (!stage) return; // esta página no participa del tour

    var guardado = leerStorage();
    var indiceInicial = null;

    // Fix 02/08/2026 (bug reportado por Daniel): "tourDone" (server-side,
    // user.tour_completado) solo debe frenar el arranque AUTOMÁTICO del
    // primer login. Si ya hay un paso guardado en localStorage (recorrido
    // en curso — arrancado a mano con "Recorrido virtual", o resumido
    // después de navegar de página), hay que RETOMARLO sin importar ese
    // flag — si no, el tour se cortaba en seco apenas se navegaba a la
    // segunda pantalla, porque la cuenta ya tenía tour_completado=1 de
    // pruebas anteriores y esta función cortaba antes de mirar el storage.
    if (guardado !== null && STEPS[parseInt(guardado, 10)]) {
      indiceInicial = parseInt(guardado, 10);
    } else if (guardado === null && stage === 'dashboard' && document.body.dataset.tourDone !== '1') {
      indiceInicial = 0; // primera vez de verdad: arranca en Dashboard, paso 0
    }

    if (indiceInicial === null) return;
    if (STEPS[indiceInicial].stage !== stage) return; // el paso pendiente es de otra página

    setTimeout(function () {
      prepararElemento(STEPS[indiceInicial], function () {
        if (!document.querySelector(STEPS[indiceInicial].element)) return; // defensivo
        var driverObj = crearDriverTour();
        driverObj.drive(indiceInicial);
      });
    }, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Botón "Recorrido virtual" del Dashboard: arranca el tour a demanda
  // (re-verlo, o revisión de Admin), sin importar si ya estaba completado.
  window.ppIniciarTour = function () {
    if (document.body.dataset.tourStage !== 'dashboard') return;
    if (!window.driver || !window.driver.js || !window.driver.js.driver) return;
    _tourEnding = false;
    guardarStorage(0);
    prepararElemento(STEPS[0]);
    var driverObj = crearDriverTour();
    driverObj.drive(0);
  };

  // Usado por el botón "Final del recorrido" del panel en ver.html: marca
  // el tour como completado en el backend y manda al Dashboard con el
  // cartel de felicitación (?tour_fin=1). Expuesto como función global
  // porque ver.html no tiene por qué saber nada de STEPS/localStorage.
  window.ppFinalizarRecorrido = function () {
    limpiarStorage();
    document.body.dataset.tourDone = '1';
    marcarCompletadoBackend();
    window.location.href = '/?tour_fin=1';
  };
})();
