/* ═══════════════════════════════════════════════════════════════
   PRESUPUESTOPRO · Tour interactivo de onboarding (spotlight)
   Pedido de Daniel 02/08/2026 — estrategia de conversión: de 140
   usuarios registrados, 45 vencieron la prueba gratis sin pagar
   nunca (0 conversiones). El tour acompaña a un usuario nuevo por
   el asistente real hasta guardar su primer presupuesto, con un
   desvío destacado hacia Costo/m² (la feature que genera el
   "aha moment" más rápido).

   Librería: Driver.js (~5kb, sin dependencias) — cargada vía CDN
   en templates/base.html, junto a este archivo.

   Cómo funciona (recorrido real de 5 páginas, no un modal único):
   - Cada paso del tour vive en una página distinta (Dashboard tiene
     2 pasos, el resto 1 cada uno). Como una carga de página normal
     destruye cualquier instancia de Driver.js, el patrón es el
     recomendado por la propia documentación de Driver.js para tours
     multi-página: guardar en qué paso quedó (localStorage) antes de
     navegar, y retomarlo en la carga de página siguiente.
   - Cada plantilla que participa declara su "etapa" con
     data-tour-stage="..." en el <body> (ver templates/base.html,
     bloque Jinja {% block tour_stage %}). Este script solo actúa si
     la etapa de la página actual coincide con el paso que corresponde
     mostrar.
   - Al cerrar el popover (botón "×") en cualquier paso, o al terminar
     el último paso (Guardar, paso 8), se marca el tour como
     completado — en ambos casos no vuelve a aparecer (POST a
     /tour/completar, ver routes/dashboard.py).
   ═══════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  var STORAGE_KEY = 'pp_tour_step';
  var MARCAR_URL = '/tour/completar';

  // Recorrido sugerido por Daniel: 1) Nuevo presupuesto, 2) Costo/m² (desvío
  // destacado — "aha moment" rápido), 3) cómputo/rubros, 4) subcontratos,
  // 5) resumen y PDF. Los índices de este array son el "número de paso"
  // que se persiste en localStorage entre páginas.
  var STEPS = [
    {
      stage: 'dashboard',
      element: '#tour-nuevo-presupuesto',
      popover: {
        title: '¡Bienvenido a PresupuestoPRO! 👋',
        description: 'Te mostramos en 1 minuto cómo armar tu primer presupuesto. Arrancá acá cuando quieras — te vamos a acompañar paso a paso.'
      }
    },
    {
      stage: 'dashboard',
      element: '#tour-costo-m2',
      popover: {
        title: '¿Necesitás algo más rápido?',
        description: '¿Necesitás una respuesta rápida sin armar todo el presupuesto? Probá esto: calculá el costo de un solo ítem por m² o m³ en segundos, con los mismos precios de referencia.'
      }
    },
    {
      stage: 'paso2',
      element: '#accordionRubros',
      popover: {
        title: 'Cargá el cómputo',
        description: 'Tocá un rubro para desplegarlo y cargá la cantidad de cada ítem (m², m³, unidades...). El costo directo se calcula solo, en vivo, abajo de todo.'
      }
    },
    {
      stage: 'paso3',
      element: '#tour-subcontratos',
      popover: {
        title: 'Subcontratos (si aplica)',
        description: 'Si parte de la obra la hace un subcontratista (electricidad, plomería, etc.), marcalo acá y cargá mano de obra y/o materiales. Si no subcontratás nada, tocá "Siguiente" y listo.'
      }
    },
    {
      stage: 'paso8',
      element: '#tour-guardar',
      popover: {
        title: 'Resumen y PDF',
        description: 'Revisá los totales y la forma de pago, y tocá "Guardar". Después vas a poder descargar el PDF para tu cliente y el PDF con el detalle interno para vos. ¡Con esto ya armaste tu primer presupuesto!'
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

  function avanzar(driverObj) {
    var activeIndex = driverObj.getActiveIndex();
    var siguiente = STEPS[activeIndex + 1];
    if (!siguiente) { // no debería pasar (el último paso usa onDoneClick)
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
        terminarTour(driverObj);
      },
      onDoneClick: function () {
        terminarTour(driverObj);
      },
      onNextClick: function () {
        avanzar(driverObj);
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

  // Botón "Recorrido virtual" del Dashboard (pedido de Daniel 02/08/2026):
  // arranca el tour a demanda, sin importar si ya estaba marcado como
  // completado — sirve tanto para que un usuario lo vuelva a ver como
  // para que el propio Admin lo revise. Solo tiene sentido en el
  // Dashboard (ahí vive el paso 0); en cualquier otra página no hace nada.
  window.ppIniciarTour = function () {
    if (document.body.dataset.tourStage !== 'dashboard') return;
    if (!window.driver || !window.driver.js || !window.driver.js.driver) return;
    _tourEnding = false;
    guardarStorage(0);
    var driverObj = crearDriverTour();
    driverObj.drive(0);
  };
})();
