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

  // Cada paso vive en una pantalla concreta (`stage`) y apunta a un
  // elemento real de esa pantalla. `leaveAction` (solo en el ÚLTIMO paso
  // de cada pantalla) define cómo se avanza a la siguiente: "navigate"
  // pega un salto directo a otra URL, "submit" dispara el submit real del
  // formulario de esa pantalla (con todos sus datos ya precargados). Los
  // pasos sin `leaveAction` simplemente avanzan dentro de la misma pantalla.
  var STEPS = [
    // ── 1) Mi Empresa ──────────────────────────────────────────────
    {
      stage: 'dashboard', element: '#tour-mi-empresa',
      popover: {
        title: '¡Bienvenido a PresupuestoPRO! 👋',
        description: 'Antes de armar tu primer presupuesto, configuremos los datos de tu empresa — así van a aparecer en los PDFs que le mandás a tus clientes. Con tocar "Siguiente" alcanza, no hace falta que hagas clic en nada de la pantalla real.'
      },
      leaveAction: { type: 'navigate', url: URL_PERFIL }
    },
    {
      stage: 'perfil', element: '#tour-perfil-logo',
      popover: { title: 'Tu logo', description: 'Así se ve tu logo en los PDF. Por ahora, sin logo cargado, usamos las iniciales de tu empresa — podés subir el tuyo cuando quieras, acá mismo.' }
    },
    {
      stage: 'perfil', element: '#tour-perfil-datos',
      popover: { title: 'Datos de tu empresa', description: 'Acá completás el resto: podés poner un Slogan que te diferencie ("Calidad y confianza en cada obra", por ejemplo), tu nombre de contacto, teléfono y email — todo esto sale en tus PDFs. Esto es tu perfil real, no lo vamos a modificar en el recorrido.' },
      leaveAction: { type: 'navigate', url: URL_DASHBOARD }
    },
    // ── 2) Costo/m² (aha moment rápido) ────────────────────────────
    {
      stage: 'dashboard', element: '#tour-costo-m2',
      popover: { title: '¿Necesitás algo más rápido?', description: '¿Necesitás una respuesta rápida sin armar todo el presupuesto? Con "Costo/m²" calculás el costo de un solo ítem en segundos. Te muestro cómo.' },
      leaveAction: { type: 'navigate', url: URL_COSTO_M2 }
    },
    {
      stage: 'costo_m2', element: '#tour-costo-m2-item1',
      popover: { title: '¿Necesitás algo más rápido?', description: 'Elegís un ítem — por ejemplo este — y calculás en segundos su costo por m² o m³, sin tener que armar todo el presupuesto.' }
    },
    {
      stage: 'costo_m2', element: '#tour-costo-m2-item2',
      popover: {
        title: 'Cualquier ítem, de cualquier rubro',
        description: 'Podés probar con este otro, por ejemplo. El resultado te da la mano de obra y el detalle de materiales con su costo, actualizado mes a mes — pero totalmente editable: podés ajustarlo según los precios de tu zona, igual que lo que le pagás a tu oficial y a tu ayudante.'
      },
      leaveAction: { type: 'navigate', url: URL_DEMO }
    },
    // ── 3) Presupuesto — Paso 1: Datos de obra ─────────────────────
    {
      stage: 'paso1', element: '#tour-cliente',
      popover: { title: 'Ahora sí, el presupuesto', description: 'Ya completamos un cliente de ejemplo (ficticio) — así se ve. Vos vas a cargar acá los datos reales de tu cliente.' }
    },
    {
      stage: 'paso1', element: '#tour-obra',
      popover: { title: 'Datos de la obra', description: 'Descripción, dirección y tipo de obra — también de ejemplo. Nada de esto hace falta tocarlo ahora, seguimos con "Siguiente".' },
      leaveAction: { type: 'submit', formId: 'formObra' }
    },
    // ── Paso 2: Cómputo ─────────────────────────────────────────────
    {
      stage: 'paso2', element: '#accordionRubros',
      popover: { title: 'Cómputo de la obra', description: 'Elegimos 2-3 ítems de ejemplo, de distintos rubros. Acá cargás las cantidades reales de tu obra y el costo se calcula solo, en vivo.' },
      leaveAction: { type: 'submit', formId: 'formComputo' }
    },
    // ── Paso 3: Subcontratos ──────────────────────────────────────
    {
      stage: 'paso3', element: '#tour-subcontratos',
      popover: { title: 'Subcontratos', description: 'Si tenés subcontratos (electricidad, plomería...) los marcás acá, con su mano de obra y materiales. Ya dejamos 2 de ejemplo cargados.' },
      leaveAction: { type: 'submit', formId: 'formSubc' }
    },
    // ── Paso 4: Indirectos ──────────────────────────────────────────
    {
      stage: 'paso4', element: '#tour-indirectos',
      popover: { title: 'Costos indirectos', description: 'Movilidad, alquiler de andamios y de herramientas — gastos de la obra que no son ni mano de obra ni materiales. Ya completados como ejemplo.' },
      leaveAction: { type: 'submit', formId: 'formInd' }
    },
    // ── Paso 5: Modo y tiempo ────────────────────────────────────────
    {
      stage: 'paso5', element: '#tour-paso5-config',
      popover: {
        title: 'Tu equipo y tus márgenes',
        description: 'Acá podés ajustar cuántos oficiales y ayudantes usás, cuánto les pagás por día, y el % de gastos generales y de impuestos/seguros. Si tu presupuesto no incluye materiales (los pone el cliente), arriba de todo podés elegir "Solo mano de obra".'
      }
    },
    {
      stage: 'paso5', element: '#tour-paso5-cuadro',
      popover: { title: 'Costo Directo, Total Final y Ganancia Real', description: 'Con esos datos se arma este cuadro: el Costo Directo, el Total Final (lo que le cobrás al cliente) y — lo más importante — tu Ganancia Real.' },
      leaveAction: { type: 'submit', formId: 'formModo' }
    },
    // ── Paso 6: Materiales ────────────────────────────────────────
    {
      stage: 'paso6', element: '#tour-materiales-precio',
      popover: { title: 'Precio unitario editable', description: 'Los materiales se calculan solos a partir de tus ítems. Podés editar el precio unitario de cada uno según lo que cuesta en tu zona — al cambiarlo, se actualiza el subtotal de esa fila.' }
    },
    {
      stage: 'paso6', element: '#tour-materiales-total',
      popover: { title: 'Total de materiales', description: 'Y acá te queda el total de materiales de todo el presupuesto.' },
      leaveAction: { type: 'submit', formId: 'formMateriales' }
    },
    // ── Paso 7: Forma de pago ────────────────────────────────────────
    {
      stage: 'paso7', element: '#tour-paso7-config',
      popover: { title: 'Forma de pago', description: 'El % de anticipo y de saldo final son editables, y elegís la frecuencia de las cuotas intermedias. Para este ejemplo elegimos cuotas semanales.' }
    },
    {
      stage: 'paso7', element: '#tour-paso7-cuadro',
      popover: { title: 'Cuadro de pago estimado', description: 'Con eso se arma el cuadro de pago: anticipo al inicio, cuotas intermedias y saldo final al terminar la obra.' },
      leaveAction: { type: 'submit', formId: 'formPago' }
    },
    // ── Paso 8: Resumen y Guardar ─────────────────────────────────
    {
      stage: 'paso8', element: '#tour-p8-cliente-obra',
      popover: { title: 'Resumen final', description: 'Arriba de todo, un resumen de cliente y obra.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-totales',
      popover: { title: 'Totales', description: 'Acá los totales del presupuesto: costo directo, subcontratos, indirectos, GG e impuestos, y el TOTAL final.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-pago',
      popover: { title: 'Forma de pago', description: 'La forma de pago que elegiste en el paso anterior, ya calculada.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-materiales',
      popover: { title: 'Materiales a comprar', description: 'La lista completa de materiales a comprar para esta obra, con cantidades y precios.' }
    },
    {
      stage: 'paso8', element: '#tour-p8-descripcion',
      popover: { title: 'Descripción de trabajos', description: 'Este texto se arma solo, a partir de los ítems que presupuestaste — y es editable antes de guardar. Sale en los 2 PDF.' }
    },
    {
      stage: 'paso8', element: '#tour-guardar',
      popover: { title: 'Guardar', description: 'Tocás "Guardar" y listo: se genera el presupuesto final, con sus 2 PDF.' },
      leaveAction: { type: 'submit', formId: 'formResumen' }
    },
    // ── Presupuesto guardado: materiales + botones + cierre ─────────
    {
      stage: 'ver', element: '#tour-ver-materiales',
      popover: { title: 'Presupuesto guardado ✓', description: 'Este es tu presupuesto ya armado. Bajamos hasta el final para ver el detalle completo de materiales.' }
    },
    {
      stage: 'ver', element: '#tour-ver-botones',
      popover: { title: 'Tus 4 accesos', description: '"Volver" te lleva al Dashboard, "Editar" te deja modificar el presupuesto, y los 2 PDF: "Propietario" (para mandarle a tu cliente) y "Constructor" (con el detalle completo, para vos).' }
    },
    {
      stage: 'ver', element: '#tour-fin-recorrido',
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

  // Ajustes previos a iluminar un elemento puntual (el panel final del tour
  // arranca oculto — display:none — hasta que se llega a este paso; el link
  // "Mi empresa" arranca dentro de un dropdown cerrado).
  function prepararElemento(step) {
    if (!step) return;
    if (step.element === '#tour-fin-recorrido') {
      var panel = document.querySelector('#tour-fin-recorrido');
      if (panel) panel.style.display = '';
    }
    if (step.element === '#tour-mi-empresa') {
      abrirMenuUsuario();
    }
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
      prepararElemento(siguiente);
      driverObj.moveNext();
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
      onCloseClick: function () { avanzarOTerminar(driverObj); },
      onDoneClick: function () { terminarTour(driverObj); },
      onNextClick: function () { avanzarOTerminar(driverObj); },
      // Link chico "Saltar todo el recorrido" — única forma real de
      // saltear el tour completo antes del final (separado a propósito de
      // la X, que solo avanza un paso).
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
      prepararElemento(STEPS[indiceInicial]);
      if (!document.querySelector(STEPS[indiceInicial].element)) return; // defensivo
      var driverObj = crearDriverTour();
      driverObj.drive(indiceInicial);
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
