"""Selecciona la muestra estratificada de salidas para la anotación manual y prepara las hojas.

- 30 salidas por combinación modelo × instrucción (10 por sección), mismos pasajes para
  todas las combinaciones, de modo que las comparaciones sean pareadas.
- 9 de los 30 pasajes (3 por sección) se marcan para doble anotación: 72 de 240 salidas (30 %).
- Genera anotacion/hoja_anotacion.xlsx: una fila por salida, con el original y la salida
  en paralelo, en orden aleatorio y sin el nombre del modelo (anotación ciega).
"""
import json
import random
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from linguistica import limpiar_salida

RAIZ = Path(__file__).resolve().parents[1]
SEMILLA = 2027
POR_SECCION = 10

pasajes = {json.loads(l)["id"]: json.loads(l)
           for l in (RAIZ / "corpus" / "pasajes.jsonl").read_text(encoding="utf-8").splitlines()}
salidas = [json.loads(l) for l in (RAIZ / "resultados" / "salidas.jsonl").read_text(encoding="utf-8").splitlines()]

rng = random.Random(SEMILLA)
ids = []
for s in "234":
    candidatos = sorted(i for i, p in pasajes.items() if p["seccion"] == s)
    ids += rng.sample(candidatos, POR_SECCION)
dobles = set()
for s in "234":
    dobles |= set(rng.sample([i for i in ids if pasajes[i]["seccion"] == s], 3))

muestra = [d for d in salidas if d["id"] in ids]
rng.shuffle(muestra)
filas = []
for n, d in enumerate(muestra, 1):
    filas.append({"id_salida": f"S{n:03d}", "id_pasaje": d["id"], "seccion": pasajes[d["id"]]["seccion"],
                  "original": pasajes[d["id"]]["texto"], "salida": limpiar_salida(d["salida"]),
                  "doble_anotacion": d["id"] in dobles})
clave = pd.DataFrame([{"id_salida": f["id_salida"], "modelo": d["modelo"], "condicion": d["condicion"]}
                      for f, d in zip(filas, muestra)])
hoja = pd.DataFrame(filas)
with pd.ExcelWriter(RAIZ / "anotacion" / "hoja_anotacion.xlsx") as w:
    hoja.to_excel(w, sheet_name="salidas", index=False)
    pd.DataFrame(columns=["id_salida", "categoria", "operacion", "fragmento_original",
                          "fragmento_salida", "gravedad", "comentario"]).to_excel(w, sheet_name="anotaciones", index=False)
clave.to_csv(RAIZ / "anotacion" / "clave_ciega.csv", index=False)
print(f"{len(hoja)} salidas; {hoja.doble_anotacion.sum()} para doble anotación")
