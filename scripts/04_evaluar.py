"""Calcula legibilidad, detectores lingüísticos, BERTScore y NLI para pares original–salida.

Uso:
    python scripts/04_evaluar.py resultados/perturbaciones.jsonl
    python scripts/04_evaluar.py resultados/salidas.jsonl        # salidas de los modelos
Escribe un CSV con el mismo nombre y sufijo _metricas.csv.
"""
import json
import sys
from pathlib import Path

import pandas as pd

import linguistica as L
import metricas_neuronales as N

RAIZ = Path(__file__).resolve().parents[1]


def main(ruta):
    ruta = Path(ruta)
    filas = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines()]
    pasajes = {json.loads(l)["id"]: json.loads(l)
               for l in (RAIZ / "corpus" / "pasajes.jsonl").read_text(encoding="utf-8").splitlines()}
    for f in filas:
        if "modelo" in f:  # salidas de los modelos: se normaliza el formato y se guarda el original
            f["salida_bruta"] = f["salida"]
            f["salida"] = L.limpiar_salida(f["salida"])
        f.setdefault("original", pasajes[f["id"]]["texto"])
        f["seccion"] = pasajes[f["id"]]["seccion"]

    originales = [f["original"] for f in filas]
    salidas = [f["salida"] if f["salida"].strip() else "." for f in filas]
    # Las métricas neuronales son lentas: se guardan en caché junto al fichero de entrada
    cache = ruta.with_name(ruta.stem + "_neuronales.json")
    if cache.exists():
        bs, nli = json.loads(cache.read_text(encoding="utf-8"))
    else:
        cache_bs = ruta.with_name(ruta.stem + "_bertscore.json")
        if cache_bs.exists():
            bs = json.loads(cache_bs.read_text(encoding="utf-8"))
        else:
            bs = N.bertscore(originales, salidas)
            cache_bs.write_text(json.dumps(bs), encoding="utf-8")
        print("BERTScore calculado", flush=True)
        nli = N.nli_lote(originales, salidas)
        print("NLI calculado", flush=True)
        cache.write_text(json.dumps([bs, nli]), encoding="utf-8")

    registros = []
    for i, f in enumerate(filas):
        pa = pasajes[f["id"]]
        r = {k: v for k, v in f.items() if k not in ("original", "salida", "salida_bruta", "opciones")}
        leg_o, leg_s = L.legibilidad(f["original"]), L.legibilidad(f["salida"])
        r.update({f"orig_{k}": v for k, v in leg_o.items()})
        r.update({f"sal_{k}": v for k, v in leg_s.items()})
        r["compresion"] = leg_s.get("palabras", 0) / max(leg_o.get("palabras", 1), 1)
        r.update(L.detectores(f["original"], f["salida"], pa["nombre"], pa["vtm"]))
        r["bertscore_f1"] = bs[i]
        r.update(nli[i])
        registros.append(r)
    df = pd.DataFrame(registros)
    destino = ruta.with_name(ruta.stem + "_metricas.csv")
    df.to_csv(destino, index=False)
    print(f"Escrito {destino} ({len(df)} filas)")


if __name__ == "__main__":
    main(sys.argv[1])
