# PresupuestoPRO — Contexto del Proyecto

## Cómo usar este archivo
- **Al empezar un chat nuevo:** pegá → `Leé PROYECTO.md y continuá desde donde quedamos`
- **Al terminar un chat:** pedí → `Actualizá PROYECTO.md con lo que hicimos hoy`

---

_Última actualización: 04/07/2026 — 11:25 ART_

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
