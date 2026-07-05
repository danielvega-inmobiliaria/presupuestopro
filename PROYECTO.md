# PresupuestoPRO — Contexto del Proyecto

## Cómo usar este archivo
- **Al empezar un chat nuevo:** pegá → `Leé PROYECTO.md y continuá desde donde quedamos`
- **Al terminar un chat:** pedí → `Actualizá PROYECTO.md con lo que hicimos hoy`

---

_Última actualización: 04/07/2026 — 12:55 ART_

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
