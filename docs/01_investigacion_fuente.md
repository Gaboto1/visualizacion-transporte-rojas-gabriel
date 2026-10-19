# Parte I y II — Investigación de la fuente y formulación del problema

## Actividad 1. Localización

| Campo | Detalle |
|---|---|
| **Nombre** | Operaciones de Aeronaves |
| **Institución responsable** | Junta de Aeronáutica Civil (JAC), Ministerio de Transportes y Telecomunicaciones. Autor declarado: *Unidad de Datos JAC*. Los datos los recolecta la Dirección General de Aeronáutica Civil (DGAC). |
| **Enlace** | https://datos.gob.cl/dataset/operaciones-aeronaves (grupo [Transporte](https://datos.gob.cl/group/transporte)) |
| **Documentación técnica** | https://jac-mtt.github.io/jac-docs/docs/series/operaciones_aeroportuarias |
| **Descripción** | Dos series obtenidas de las bitácoras de los aeropuertos de Chile: (1) un subconjunto de la bitácora a nivel de operación y (2) un resumen mensual de operaciones por aeropuerto. |
| **Licencia** | Creative Commons CCZero (dominio público) |
| **Frecuencia de actualización** | Mensual (≈ día 10 de cada mes, con datos del mes anterior). Versión utilizada: publicada el 2026-10-13, descargada el 2026-10-19. |
| **Periodo cubierto** | No se declara en los metadatos del portal. Se determina a partir de los datos: 2000-01-01 00:00 UTC a 2026-09-30 23:58 UTC. |

### Archivos disponibles

| Recurso | Formato | Tamaño | Contenido |
|---|---|---|---|
| `bitacora-vuelos.parquet` | Parquet (zstd, nivel máximo) | 138,2 MB | 11.163.791 registros × 12 columnas, una fila por aterrizaje (A), despegue (D) o sobrevuelo (W). |
| `operaciones-aeropuertos.csv` | CSV UTF-8, coma, con cabecera | 285 KB | 16.172 filas × 4 columnas: mes, aeródromo, ámbito (I/D), número de operaciones. Excluye sobrevuelos. |

Se usaron además tres tablas del conjunto **Dimensiones Aeronáuticas** (misma institución, https://datos.gob.cl/dataset/dimensiones-aeronauticas) para dar contexto a los códigos:
`dim_aeropuerto.csv` (nombre, ciudad, región, coordenadas, categoría y **zona horaria** de cada aeródromo), `dim_actividad_dgac.csv` (descripción de los 28 códigos de actividad) y `dim_aerolinea.csv` (151 aerolíneas con código OACI).

### Metadatos relevantes (de la documentación oficial)

- `dt_operacion`: fecha y hora del hito de despegue o aterrizaje.
- `aeropuerto_oaci`: aeródromo que informa la operación.
- `tipo_operacion`: A (aterrizaje), D (despegue), W (sobrevuelo).
- `aeropuerto_dgac_orig_dest`: origen si es aterrizaje, destino si es despegue. Puede ser OACI o un código interno DGAC.
- `aerolinea_dgac`, `numero_vuelo`, `actividad_cod`, `matricula`, `modelo_avion`, `modelo_avion_desc`, `es_internacional`, `pmd` (peso máximo de despegue).

### Condiciones y limitaciones identificadas

1. **Cobertura parcial**: se excluyen operaciones militares y policiales y las de aeródromos no administrados por la DGAC (la propia documentación lo advierte). Sólo 69 aeródromos informan.
2. **Registros del último día de t-2 pueden ser corregidos** en versiones posteriores.
3. **Discrepancias documentación ↔ datos** (detectadas en este proyecto):
   - La columna del CSV se llama `cnt_operaciones`, no `n_operaciones`.
   - `dt_operacion` está almacenada con zona `America/Santiago`, no en UTC como dice la documentación (el instante es correcto; sólo cambia la representación).
   - La documentación indica que se incluye el primer día del mes siguiente; esta versión termina el 30-09-2026 a las 23:58 UTC.
4. **Unidad de PMD no declarada**. Por los valores (B767 = 187, A320 = 77) corresponde a toneladas.
5. El Parquet (138 MB) excede el límite de 100 MB por archivo de GitHub, por lo que se descarga mediante script y no se versiona.

## Actividad 2. Análisis preliminar

**¿Qué fenómeno representa?** El movimiento de aeronaves (aterrizajes, despegues y sobrevuelos) en los aeródromos chilenos administrados por la DGAC, desde el año 2000.

**¿Quién produce los datos?** El personal aeronáutico de cada aeródromo los registra en las bitácoras de la DGAC; la JAC los consolida y publica.

**¿Unidad de observación?** En la bitácora: **una operación** (un aterrizaje, despegue o sobrevuelo de una aeronave en un aeródromo en un minuto determinado). En el resumen: un **mes × aeródromo × ámbito**.

**¿Qué permite analizar?** Volumen de operaciones en el tiempo (hasta el minuto), por aeródromo, por tipo de actividad (pasajeros, carga, instrucción, privada, trabajos aéreos…), doméstico vs. internacional, rutas (aeródromo ↔ origen/destino), tamaño de aeronaves (PMD) y flota (matrícula, modelo).

**¿Qué no proporciona?** Pasajeros transportados, carga en toneladas, ocupación, retrasos, cancelaciones, tarifas, ni operaciones militares/policiales. Una operación de un A321 con 200 pasajeros pesa igual que la de un Cessna en un circuito de instrucción. Tampoco se sabe qué operaciones de despegue y aterrizaje corresponden al mismo vuelo (no hay identificador de vuelo único).

**Dimensiones preliminares.** Tiempo (año → mes → día → hora), aeródromo (región → ciudad → aeródromo, vía dimensión), ámbito, tipo de operación, actividad (tipo → código), aerolínea, modelo de aeronave. **Medidas:** conteo de operaciones (implícita: cada fila vale 1) y PMD.

**Utilidad para una organización.** Planificación de capacidad aeroportuaria (horas punta, estacionalidad), seguimiento de la recuperación post-pandemia, análisis de concentración del sistema (dependencia de Santiago), dimensionamiento de servicios de escuelas de vuelo y aviación general, apoyo a políticas públicas de conectividad regional.

## Parte II. Formulación del problema

**Pregunta principal.** ¿Cómo se distribuye y cómo ha evolucionado entre 2000 y 2026 la actividad de aterrizajes y despegues informada por la DGAC, según aeródromo, ámbito (doméstico / internacional) y tipo de actividad, y qué diferencias revela el shock de 2020?

- **P1:** ¿Qué aeródromos concentran las operaciones en 2025 (último año completo) y qué proporción corresponde a tráfico internacional?
- **P2:** ¿Cómo evolucionó el volumen mensual de operaciones entre 2000 y 2026, y existe un patrón estacional estable?
- **P3:** ¿En qué se diferencian los tipos de actividad (pasajeros, instrucción, privada, carga…) en el tamaño de aeronave (PMD) y en su horario de operación?

**H1 (exploratoria):** Tras la caída de 2020, el tráfico internacional se recuperó más lentamente que el doméstico: tardó más años en volver al nivel de 2019.

> La hipótesis orienta la exploración; no es una conclusión. Se contrasta en §9.5 y §12 del notebook.
