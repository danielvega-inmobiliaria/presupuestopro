/* ═══════════════════════════════════════════════════════════════
   PRESUPUESTOPRO · Tour interactivo de onboarding (spotlight, modo demo)
   Pedido de Daniel 02/08/2026 — estrategia de conversión: de 140
   usuarios registrados, 45 vencieron la prueba gratis sin pagar
   nunca (0 conversiones).

   Fix 02/08/2026 (2da vuelta, importante): la primera versión era un
   tour "real" — le pedía al usuario escribir su propio cliente/obra
   para poder avanzar. Daniel lo probó y no daba pie con bola ("me
   quedo esperando el tour, no se sabe qué hay que completar"). Ahora
   es un recorrido DEMO: al arrancar (botón "＋ Nuevo presupuesto" o
   "Recorrido virtual" del Dashboard, mientras el tour está activo) se
   precarga en el servidor un presupuesto 100% ficticio (ver
   routes/presupuesto.py::demo()) — cliente, ítems de 3 rubros,
   2 subcontratos, indirectos — y el usuario SOLO va tocando
   "Siguiente" mientras el popover le explica cada pantalla ya
   completada. Nada de tipeo, nada de decisiones.

   Librería: Driver.js (~5kb, sin dependencias) — cargada vía CDN
   en templates/base.html, junto a este archivo.

   Cómo funciona (recorrido real de 8 páginas, no un modal único):
   - Cada paso del tour vive en una página distinta. Como una carga de
     página normal destruye cualquier instancia de Driver.js, se usa
     el patrón recomendado por la propia documentación de Driver.js
     para tours multi-página: guardar en qué paso quedó (localStorage)
     antes de navegar, y retomarlo en la carga de página siguiente.
   - Cada plantilla que participa declara su "etapa" con
     data-tour-stage="..." en el <body> (ver templates/base.html,
     bloque Jinja {% block tour_stage %}). Este script solo actúa si
     la etapa de la página actual coincide con el paso que corresponde
     mostrar.
   - El botón "×" (cerrar) de cada paso NO cancela el recorrido entero
     — solo cierra ese popover puntual y avanza al próximo paso, igual
     que tocar "Siguiente" (si alguien cierra pensando "listo,
     entendido", el recorrido sigue disponible en la próxima pantalla
     en vez de apagarse para siempre).
   - El único lugar donde se marca `tour_completado=1` (no se vuelve a
     mostrar más) es: (a) al cerrar/terminar el último paso (los PDF,
     al final), o (b) tocando el link chico "Saltar todo el recorrido"
     que tiene cada popover (POST a /tour/completar, ver
     routes/dashboard.py).
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var STORAGE_KEY = 'pp_tour_step';
  var MARCAR_URL = '/tour/completar';
  var DEMO_URL = '/presupuesto/demo';

  // Recorrido: 1) Nuevo presupuesto, 2) Costo/m² (desvío destacado — "aha
  // moment" rápido), 3) datos de obra (ya completados), 4) cómputo/rubros
  // (ítems ya elegidos), 5) subcontratos (ya marcados), 6) indirectos (ya
  // completados), 7) resumen y Guardar, 8) los 2 PDF. Los índices de este
  // array son el "número de paso" que se persiste en localStorage entre
  // páginas.
  var STEPS = [
    {
      stage: 'dashboard',
      element: '#tour-nuevo-presupuesto',
      popover: {
        title: '¡Bienvenido a PresupuestoPRO! 👋',
        description: 'Te mostramos en 1 minuto cómo se arma un presupuesto de punta a punta, con un ejemplo ya completado — no hace falta que escribas nada, con ir tocando "Siguiente" alcanza.'
      }
    },
    {
      stage: 'dashboard',
      element: '#tour-costo-m2',
      popover: {
        title: '¿Necesitás algo más rápido?',
        description: '¿Necesitás una respuesta rápida sin armar todo el presupuesto? Probá esto: calculá el costo de un solo ítem por m² o m³ en segundos. (Esto es aparte del recorrido — seguimos con "Siguiente".)'
      }
    },
    {
      stage: 'paso1',
      element: '#tour-datos-obra',
      popover: {
        title: 'Datos del cliente y la obra',
        description: 'Ya completamos un cliente y una obra de ejemplo (todo ficticio) para que veas cómo queda. En un presupuesto real, estos datos van a ser los de tu cliente.'
      }
    },
    {
      stage: 'paso2',
      element: '#accordionRubros',
      popover: {
        title: 'Cómputo de la obra',
        description: 'Ya elegimos algunos ítems de ejemplo, de distintos rubros (mampostería, contrapisos, techos). El costo directo se calcula solo, en vivo, abajo de todo. En un presupuesto real acá cargás las cantidades reales de tu obra.'
      }
    },
    {
      stage: 'paso3',
      element: '#tour-subcontratos',
      popover: {
        title: 'Subcontratos',
        description: 'Ya marcamos Electricidad y Plomería como ejemplo, con mano de obra y materiales cargados. Si un presupuesto real no lleva subcontratos, simplemente no marcás ninguno.'
      }
    },
    {
      stage: 'paso4',
      element: '#tour-indirectos',
      popover: {
        title: 'Costos indirectos',
        description: 'Movilidad, alquiler de andamios y de herramientas — ya completados como ejemplo. Estos son gastos de la obra que no son ni mano de obra ni materiales.'
      }
    },
    {
      stage: 'paso8',
      element: '#tour-guardar',
      popover: {
        title: 'Resumen y Guardar',
        description: 'Acá se ve el resumen final: totales, forma de pago y la descripción de trabajos (autogenerada, editable). Tocá "Guardar" para ver cómo queda el presupuesto ya guardado y sus dos PDF.'
      }
    },
    {
      stage: 'ver',
      element: '#tour-pdfs',
      popover: {
        title: '¡Listo! Los 2 PDF',
        description: 'Con esto ya armaste tu primer presupuesto. "PDF Propietario" es para mandarle al cliente (sin desglose de costos internos); "PDF Constructor" tiene el detalle completo, para vos. Los dos salen con el nombre y el logo de tu empresa (los configurás en el menú de usuario → "Mi empresa").'
      }
    }
  ];

  var _tourEnding = false;

  function leerStorage() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }
  function guardarStorage(v) {
    try { localStorage.setItem(STORAGE_KEY, String(v)); } catch (e) { /* Safari privado, etc. — no es crítico */ }
  }
  function limpiarStorage() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* no crítico */ }
  }

  // Mientras el tour está activo en el Dashboard, el botón real "＋ Nuevo
  // presupuesto" apunta al presupuesto DEMO precargado (routes/presupuesto.py
  // ::demo()) en vez de al asistente vacío — así el usuario no tiene que
  // escribir nada para ver el resto del recorrido. Fuera del tour, el botón
  // sigue siendo el de siempre (no se toca el HTML, solo se pisa el href acá).
  function apuntarBotonAlDemo() {
    var btn = document.getElementById('tour-nuevo-presupuesto');
    if (btn) btn.setAttribute('href', DEMO_URL);
  }

  function marcarCompletadoBackend() {
    // best-effort: si falla la red no bloquea nada, el tour ya se ocultó
    // en esta sesión igual (dataset.tourDone) y no se vuelve a intentar
    // arrancar en esta carga de página.
    try {
      fetch(MARCAR_URL, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } }).catch(function () {});
    } catch (e) { /* no crítico */ }
  }

  function terminarTour(driverObj) {
    if (_tourEnding) return;
    _tourEnding = true;
    limpiarStorage();
    document.body.dataset.tourDone = '1';
    try { driverObj.destroy(); } catch (e) {}
    marcarCompletadoBackend();
  }

  // Usada tanto por "Siguiente" como por la X (cerrar) — cerrar un popover
  // puntual no apaga el recorrido entero, solo avanza al próximo paso (misma
  // página u otra) y recién marca completado si no queda ningún paso más.
  function avanzarOTerminar(driverObj) {
    var activeIndex = driverObj.getActiveIndex();
    var siguiente = STEPS[activeIndex + 1];
    if (!siguiente) {
      // No queda ningún paso más (se cerró/terminó el último, los PDF).
      terminarTour(driverObj);
      return;
    }
    if (siguiente.stage === document.body.dataset.tourStage) {
      // El siguiente paso vive en la misma página — solo avanzar.
      driverObj.moveNext();
    } else {
      // El siguiente paso vive en otra página del asistente: guardamos en
      // qué paso retomar y dejamos que la navegación normal del usuario
      // (botón "Siguiente" del wizard, o el link que se está destacando)
      // lo lleve ahí. No forzamos ninguna navegación nosotros.
      guardarStorage(activeIndex + 1);
      try { driverObj.destroy(); } catch (e) {}
    }
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
      steps: STEPS.map(function (s) {
        return { element: s.element, popover: s.popover };
      }),
      onCloseClick: function () {
        avanzarOTerminar(driverObj);
      },
      onDoneClick: function () {
        terminarTour(driverObj);
      },
      onNextClick: function () {
        avanzarOTerminar(driverObj);
      },
      // Link chico "Saltar todo el recorrido" en el pie del popover — la
      // única forma de saltear el tour completo antes de llegar al final
      // (pedido original de Daniel: "una sola vez, o hasta que lo
      // salteen"). Separado a propósito del botón "×", que solo avanza al
      // próximo paso (ver avanzarOTerminar).
      onPopoverRender: function (popover) {
        var link = document.createElement('button');
        link.type = 'button';
        link.className = 'pp-tour-skip';
        link.textContent = 'Saltar todo el recorrido';
        link.addEventListener('click', function () {
          terminarTour(driverObj);
        });
        // Se agrega al wrapper del popover (no a footerButtons) para que
        // quede en su propia línea, debajo de todo, sin pelear con el
        // layout flex de los botones Anterior/Siguiente.
        popover.wrapper.appendChild(link);
      }
    });
    return driverObj;
  }

  function init() {
    if (!window.driver || !window.driver.js || !window.driver.js.driver) return; // CDN no cargó — no rompemos nada
    var stage = document.body.dataset.tourStage;
    if (!stage) return; // esta página no participa del tour
    if (document.body.dataset.tourDone === '1') return; // ya lo completó o lo salteó

    var guardado = leerStorage();
    var indiceInicial = null;

    if (guardado !== null && STEPS[parseInt(guardado, 10)]) {
      indiceInicial = parseInt(guardado, 10);
    } else if (guardado === null && stage === 'dashboard') {
      // Primera vez que se le muestra a este usuario: siempre arranca en
      // Dashboard (paso 0), nunca en medio del asistente.
      indiceInicial = 0;
    }

    if (indiceInicial === null) return;
    if (STEPS[indiceInicial].stage !== stage) return; // el paso pendiente es de otra página

    if (stage === 'dashboard') apuntarBotonAlDemo();

    // Pequeño delay para no competir con el resto del contenido de la
    // página (carteles de bienvenida/trial, render del acordeón, etc.).
    setTimeout(function () {
      // Verificación tardía: el elemento puede no existir si algo cambió
      // en el DOM (defensivo, no debería pasar en uso normal).
      if (!document.querySelector(STEPS[indiceInicial].element)) return;
      var driverObj = crearDriverTour();
      driverObj.drive(indiceInicial);
    }, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Botón "Recorrido virtual" del Dashboard: arranca el tour a demanda, sin
  // importar si ya estaba marcado como completado — sirve tanto para que un
  // usuario lo vuelva a ver como para que el propio Admin lo revise. Solo
  // tiene sentido en el Dashboard (ahí vive el paso 0); en cualquier otra
  // página no hace nada.
  window.ppIniciarTour = function () {
    if (document.body.dataset.tourStage !== 'dashboard') return;
    if (!window.driver || !window.driver.js || !window.driver.js.driver) return;
    _tourEnding = false;
    apuntarBotonAlDemo();
    guardarStorage(0);
    var driverObj = crearDriverTour();
    driverObj.drive(0);
  };
})();
