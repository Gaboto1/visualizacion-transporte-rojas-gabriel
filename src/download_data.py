"""Descarga los recursos originales desde datos.gob.cl hacia data/raw/.

Uso (desde la raíz del proyecto):
    python src/download_data.py            # descarga lo que falte
    python src/download_data.py --force    # vuelve a descargar todo
    python src/download_data.py --check    # sólo verifica hashes SHA-256

Los archivos de data/raw/ no se editan nunca: cualquier transformación se
realiza por código y se escribe en data/processed/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "manifest.json"

BASE = "https://datos.gob.cl/dataset"
OPS = f"{BASE}/d5fac3ed-01c7-43f0-9dc4-8970566bc059/resource"
DIM = f"{BASE}/7085b6e0-482a-403a-a569-6f6df4f30f82/resource"

RESOURCES = {
    "bitacora-vuelos.parquet": f"{OPS}/5bc8842e-d95a-4f8f-8ec6-acfbe700258a/download/bitacora-vuelos.parquet",
    "operaciones-aeropuertos.csv": f"{OPS}/2b7f3fbd-8be8-45e6-8ef5-64eea097528b/download/operaciones-aeropuertos.csv",
    "dim_aeropuerto.csv": f"{DIM}/0663a4e0-c224-4ca9-98de-dfa7ec57bdbd/download/dim_aeropuerto.csv",
    "dim_aerolinea.csv": f"{DIM}/4d3c30d3-a7e1-40ef-9ec3-1af6a7b5164c/download/dim.aerolinea.csv",
    "dim_actividad_dgac.csv": f"{DIM}/ca67dae0-8b11-49a5-b2d4-8cca5bc2ca4b/download/dim.actividad_dgac.csv",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as resp, tmp.open("wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    tmp.replace(dest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text("utf-8")) if MANIFEST.exists() else {}

    for name, url in RESOURCES.items():
        dest = RAW / name
        if not args.check and (args.force or not dest.exists()):
            print(f"Descargando {name} ...")
            download(url, dest)
        if not dest.exists():
            print(f"[FALTA] {name}")
            continue
        digest = sha256(dest)
        expected = manifest.get(name, {}).get("sha256")
        if expected and expected != digest:
            # La fuente se actualiza mensualmente: un hash distinto indica
            # una versión nueva, no necesariamente un error.
            print(f"[DISTINTO] {name}: versión diferente a la del manifiesto")
        else:
            print(f"[OK] {name} ({dest.stat().st_size:,} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
