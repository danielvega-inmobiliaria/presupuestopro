# PresupuestoPRO — Contexto del Proyecto

## Cómo usar este archivo
- **Al empezar un chat nuevo:** pegá → `Leé PROYECTO.md y continuá desde donde quedamos`
- **Al terminar un chat:** pedí → `Actualizá PROYECTO.md con lo que hicimos hoy`

---

_Última actualización: 05/07/2026 — 22:15 ART_

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

## Variables de entorno en Railway
| Variable | Estado |
|---|---|
| `RESEND_API_KEY` | ✅ Configurada |
| `MP_ACCESS_TOKEN` | ✅ Configurada (TEST-...) |
| `MP_PUBLIC_KEY` | ✅ Configurada (TEST-a4752ff6...) |
| `MP_APP_ID` | ✅ Configurada (3111479646589398) |
| `MP_PRECIO_ARS` | ✅ Configurada (12500) |
| `APP_BASE_URL` | ✅ Configurada |
| `SECRET_KEY` | ✅ Configurada |
| `ADMIN_EMAIL` | ⚠️ Verificar (default: `danve61@gmail.com`) |

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

## ⚠️ PROBLEMA CRÍTICO PENDIENTE — HH y materiales incorrectos

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

## Pendientes / Ideas

### 🔴 CRÍTICO
- [ ] **Configurar Webhook en MP Developers** → app PresupuestoPRO → Webhooks → URL: `https://web-production-0c9c1.up.railway.app/pagos/webhook` · Evento: `subscription_preapproval`
- [ ] **Test flujo completo MP**: crear cuenta prueba "comprador" en MP Developers → Cuentas de prueba → suscribirse desde `/pagos/planes` → verificar activación en DB
- [ ] **Pasar a producción MP**: cuando el test funcione, reemplazar `MP_ACCESS_TOKEN` y `MP_PUBLIC_KEY` por los de producción en Railway
- [ ] **Commitear database.py con migración 2l** — el archivo correcto (1993 líneas) está en disco pero NO está en git. Problema: git lock files bloquean el commit desde bash. Solución: usar **GitHub Desktop** o eliminar `.git/index.lock` desde Git Bash y correr:
  ```
  cd /d/ESCRITORIO/CLAUDE/APP_PRESUPUESTOPRO
  rm -f .git/index.lock
  git add database.py
  git commit -m "fix: migration 2l factores comerciales (11 materiales)"
  git push
  ```
- [x] **DNS Cloudflare** ✅ presupuestopro.com.ar funcionando (30/06/2026)

### 🟡 IMPORTANTE
- [ ] **Post Facebook de lanzamiento** — redactar post con screenshots del app para grupos de albañiles → landing page → MP. Pendiente de tomar screenshots: dashboard, costo/m2, ver presupuesto.
- [ ] Confirmar variable `APP_BASE_URL` en Railway
- [ ] Test completo flujo pago MP → activación → email
- [x] **Resincronizar cantidades de materiales en `analisis_sub`** ✅ hecho 04/07/2026 con migración 2n (ver abajo).

### 🟢 IDEAS FUTURAS
- [ ] Unificar landing_presupuestopro.md con posts para marketing
- [ ] **Permitir sesión simultánea celu + compu** — hoy `login_user()` en `utils/auth.py` invalida cualquier sesión anterior de la cuenta (sesión única). Decisión 04/07/2026: dejarlo como está por ahora, pero evaluar cambiarlo (guardar múltiples tokens por usuario en vez de uno solo) si vuelve a ser un problema.

## Cambios recientes comprometidos (HEAD actual en Railway)

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
