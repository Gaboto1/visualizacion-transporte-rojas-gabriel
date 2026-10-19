"""Carga, limpieza y variables derivadas de la bitácora de operaciones (JAC/DGAC).

Todas las funciones reciben y devuelven DataFrames nuevos: data/raw/ nunca se
modifica. El notebook documenta la evidencia de cada decisión; aquí sólo vive
la implementación reutilizable.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

BITACORA = RAW / "bitacora-vuelos.parquet"
RESUMEN = RAW / "operaciones-aeropuertos.csv"
DIM_AEROPUERTO = RAW / "dim_aeropuerto.csv"
DIM_ACTIVIDAD = RAW / "dim_actividad_dgac.csv"

TEXT_COLS = [
    "aeropuerto_oaci", "tipo_operacion", "aeropuerto_dgac_orig_dest",
    "aerolinea_dgac", "numero_vuelo", "actividad_cod", "matricula",
    "modelo_avion", "modelo_avion_desc",
]

# Agrupación de los 28 códigos DGAC en familias interpretables. Se basa en la
# descripción oficial de dim_actividad_dgac.csv, no en el volumen observado.
GRUPO_ACTIVIDAD = {
    "U": "Pasajeros",
    "T": "Carga",
    "O": "Instrucción",
    "P": "Privada/deportiva", "R": "Privada/deportiva", "V": "Privada/deportiva",
    "N": "Trabajo aéreo", "F": "Trabajo aéreo", "D": "Trabajo aéreo",
    "A": "Trabajo aéreo", "B": "Trabajo aéreo", "C": "Trabajo aéreo",
    "E": "Trabajo aéreo", "G": "Trabajo aéreo", "H": "Trabajo aéreo",
    "I": "Trabajo aéreo", "J": "Trabajo aéreo", "K": "Trabajo aéreo",
    "L": "Trabajo aéreo", "M": "Trabajo aéreo", "Y": "Trabajo aéreo",
    "X": "Traslado/ferry", "Z": "Traslado/ferry",
    "W": "Sobrevuelo",
    "Q": "Otros", "1": "Otros", "S": "Otros", "2": "Otros",
}

# Categorías de estela turbulenta OACI según PMD (toneladas):
# Ligera <= 7 t, Media 7-136 t, Pesada > 136 t.
ESTELA_BINS = [0, 7, 136, np.inf]
ESTELA_LABELS = ["Ligera (≤7 t)", "Media (7–136 t)", "Pesada (>136 t)"]

# Mayor PMD de una aeronave real que opera/operó en Chile (An-225, 640 t).
PMD_MAX_FISICO = 650.0
# Factor de tolerancia respecto de la mediana del modelo (ver notebook §6).
PMD_FACTOR = 3.0
PMD_MIN_REGISTROS_MODELO = 20


def cargar_bitacora(path: Path = BITACORA, columns: list[str] | None = None) -> pd.DataFrame:
    """Lee el parquet con las columnas de texto como categóricas (≈ 6x menos RAM)."""
    cols = columns or pq.ParquetFile(path).schema_arrow.names
    table = pq.read_table(path, columns=cols,
                          read_dictionary=[c for c in TEXT_COLS if c in cols])
    df = table.to_pandas()
    if "pmd" in df:
        df["pmd"] = df["pmd"].astype("float64")
    return df


def cargar_dim_aeropuerto() -> pd.DataFrame:
    return pd.read_csv(DIM_AEROPUERTO)


def cargar_dim_actividad() -> pd.DataFrame:
    return pd.read_csv(DIM_ACTIVIDAD, dtype={"codigo": "string"})


def _normalizar_texto(s: pd.Series, upper: bool = True) -> pd.Series:
    """strip + mayúsculas sobre las categorías; cadenas vacías pasan a NA."""
    cats = s.cat.categories.str.strip()
    if upper:
        cats = cats.str.upper()
    mapping = dict(zip(s.cat.categories, cats))
    out = s.map(mapping).astype("string")
    return out.mask(out == "").astype("category")


def limpiar(df: pd.DataFrame, log: list[dict] | None = None) -> pd.DataFrame:
    """Aplica las decisiones de calidad documentadas en el informe.

    Si se entrega `log`, se agrega una fila por transformación con el número
    de registros afectados (sirve como evidencia en el notebook).
    """
    log = log if log is not None else []
    out = df.copy()

    def registrar(paso: str, n: int) -> None:
        log.append({"paso": paso, "registros_afectados": int(n)})

    # 1. Microsegundos espurios: los segundos siempre son 0, la resolución
    #    real del registro es el minuto.
    micro = out["dt_operacion"].dt.microsecond > 0
    # Se trunca en UTC: en hora local los cambios de horario de verano
    # producen instantes ambiguos.
    tz_orig = out["dt_operacion"].dt.tz
    out["dt_operacion"] = (out["dt_operacion"].dt.tz_convert("UTC")
                           .dt.floor("min").dt.tz_convert(tz_orig))
    registrar("dt_operacion: truncar a minuto (microsegundos espurios)", micro.sum())

    # 2. Normalización de cadenas (espacios y minúsculas).
    for col in ["aerolinea_dgac", "modelo_avion", "matricula", "tipo_operacion"]:
        antes = out[col].astype("string")
        out[col] = _normalizar_texto(out[col])
        registrar(f"{col}: strip + mayúsculas", (antes != out[col].astype("string")).sum())
    antes_desc = out["modelo_avion_desc"].isna().sum()
    out["modelo_avion_desc"] = _normalizar_texto(out["modelo_avion_desc"], upper=False)
    registrar("modelo_avion_desc: vacío -> NA", out["modelo_avion_desc"].isna().sum() - antes_desc)

    # 3. numero_vuelo: '', ' ' y '0' son marcadores de "sin número".
    antes_nv = out["numero_vuelo"].isna().sum()
    nv = _normalizar_texto(out["numero_vuelo"])
    out["numero_vuelo"] = nv.mask(nv == "0")
    registrar("numero_vuelo: '', ' ' y '0' -> NA", out["numero_vuelo"].isna().sum() - antes_nv)

    # 4. tipo_operacion fuera del dominio {A, D, W}: no se puede asignar sin
    #    inventar el dato, se excluye.
    invalido = ~out["tipo_operacion"].isin(["A", "D", "W"])
    registrar("tipo_operacion fuera de {A,D,W}: excluir", invalido.sum())
    out = out[~invalido]

    # 5. Duplicados exactos: misma aeronave, mismo minuto, mismo aeródromo y
    #    misma operación es físicamente imposible -> registro repetido.
    dup = out.duplicated()
    registrar("duplicados exactos: eliminar (se conserva el primero)", dup.sum())
    out = out[~dup]

    # 6. PMD implausible -> NA (se conserva el valor original en pmd_original).
    out["pmd_original"] = out["pmd"]
    pmd = out["pmd"].where(out["pmd"] > 0)
    registrar("pmd = 0 -> NA", (out["pmd"] == 0).sum())
    ref = pmd.groupby(out["modelo_avion"], observed=True).agg(["median", "count"])
    med = out["modelo_avion"].map(ref["median"]).astype("float64")
    cnt = out["modelo_avion"].map(ref["count"]).astype("float64")
    con_ref = cnt >= PMD_MIN_REGISTROS_MODELO
    incoherente = con_ref & ((pmd > med * PMD_FACTOR) | (pmd < med / PMD_FACTOR))
    fuera_rango = pmd > PMD_MAX_FISICO
    registrar(f"pmd incoherente con su modelo (×{PMD_FACTOR:g} mediana) -> NA", incoherente.sum())
    registrar(f"pmd > {PMD_MAX_FISICO:g} t (imposible) -> NA", (fuera_rango & ~incoherente).sum())
    out["pmd"] = pmd.mask(incoherente | fuera_rango)

    return out.reset_index(drop=True)


def agregar_variables(df: pd.DataFrame, dim_aeropuerto: pd.DataFrame,
                      dim_actividad: pd.DataFrame) -> pd.DataFrame:
    """Variables derivadas. La fecha local usa la zona horaria de cada aeropuerto,
    igual que el resumen oficial (operaciones-aeropuertos.csv)."""
    out = df.copy()
    aer = dim_aeropuerto.set_index("oaci")

    # Fecha/hora local del aeródromo que informa (Santiago, Punta Arenas, Isla de Pascua).
    tz = out["aeropuerto_oaci"].map(aer["zona_horaria"]).astype("string")
    utc = out["dt_operacion"].dt.tz_convert("UTC")
    local = pd.Series(pd.NaT, index=out.index, dtype="datetime64[us]")
    for zona in tz.dropna().unique():
        m = tz == zona
        local[m] = utc[m].dt.tz_convert(zona).dt.tz_localize(None)
    out["fecha_local"] = local
    out["anio"] = local.dt.year.astype("int16")
    out["mes"] = local.dt.month.astype("int8")
    out["periodo"] = local.dt.to_period("M")
    out["mes_id"] = (out["anio"].astype("int32") * 100 + out["mes"]).astype("int32")
    out["hora_local"] = local.dt.hour.astype("int8")
    out["dia_semana"] = local.dt.dayofweek.astype("int8")  # 0 = lunes

    out["ambito"] = pd.Categorical(
        np.where(out["es_internacional"], "Internacional", "Doméstico"),
        categories=["Doméstico", "Internacional"])

    act = dim_actividad.set_index("codigo")
    out["actividad_desc"] = out["actividad_cod"].map(act["descripcion"]).astype("category")
    out["grupo_actividad"] = out["actividad_cod"].map(GRUPO_ACTIVIDAD).astype("category")

    out["categoria_estela"] = pd.cut(out["pmd"], bins=ESTELA_BINS, labels=ESTELA_LABELS)

    # Operación local: origen/destino igual al aeródromo que informa
    # (circuitos de instrucción, vuelos panorámicos, trabajos aéreos).
    out["es_vuelo_local"] = (out["aeropuerto_dgac_orig_dest"].astype("string")
                             == out["aeropuerto_oaci"].astype("string"))

    out["aeropuerto_nombre"] = out["aeropuerto_oaci"].map(aer["nombre_corto"]).astype("category")
    out["region_iso"] = out["aeropuerto_oaci"].map(aer["region_iso"]).astype("category")
    out["categoria_aeropuerto"] = out["aeropuerto_oaci"].map(aer["categoria"]).astype("category")
    return out
