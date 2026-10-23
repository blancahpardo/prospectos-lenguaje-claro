"""Genera las simplificaciones con modelos abiertos servidos en local por Ollama.

Uso (Windows, PowerShell, desde la carpeta del proyecto):
    python scripts\\02_generar_simplificaciones.py
    python scripts\\02_generar_simplificaciones.py --prueba      # 3 pasajes por modelo

Es reanudable: si se interrumpe, al relanzarlo salta las salidas ya generadas.
Solo necesita el paquete `requests` (pip install requests).
"""
import argparse
import json
import time
from pathlib import Path

import requests

OLLAMA = "http://localhost:11434"
RAIZ = Path(__file__).resolve().parents[1]
PASAJES = RAIZ / "corpus" / "pasajes.jsonl"
SALIDAS = RAIZ / "resultados" / "salidas.jsonl"
CONFIG = RAIZ / "scripts" / "modelos.json"

OPCIONES = {"temperature": 0, "seed": 2027, "num_ctx": 4096, "num_predict": 1024}

INSTRUCCIONES = {
    "basica": (
        "Reescribe el siguiente fragmento de un prospecto de medicamento en lenguaje claro, "
        "para que lo pueda entender cualquier paciente sin conocimientos médicos.\n"
        "Escribe solo el texto reescrito, en español, sin comentarios."
    ),
    "guiada": (
        "Reescribe el siguiente fragmento de un prospecto de medicamento en lenguaje claro, "
        "para que lo pueda entender cualquier paciente sin conocimientos médicos.\n"
        "Sigue estas reglas:\n"
        "1. Conserva toda la información: dosis, cifras, unidades, plazos, edades, frecuencias "
        "de los efectos adversos, nombres de medicamentos y todas las advertencias.\n"
        "2. Mantén el sentido exacto de las prohibiciones, obligaciones y negaciones "
        "(no conviertas un «no debe» en un «es mejor que no»).\n"
        "3. Mantén las condiciones («si está embarazada», «en mayores de 65 años») y "
        "el grado de certeza («puede producir» no es lo mismo que «produce»).\n"
        "4. No añadas información que no esté en el texto.\n"
        "5. Usa frases cortas y palabras frecuentes, y explica entre paréntesis los términos "
        "médicos que no puedas sustituir.\n"
        "Escribe solo el texto reescrito, en español, sin comentarios."
    ),
}


def construir_prompt(condicion, texto):
    return f"{INSTRUCCIONES[condicion]}\n\nTexto:\n\"\"\"\n{texto}\n\"\"\""


def info_modelo(nombre):
    r = requests.post(f"{OLLAMA}/api/show", json={"model": nombre}, timeout=60)
    r.raise_for_status()
    d = r.json()
    etiquetas = {m["name"]: m for m in requests.get(f"{OLLAMA}/api/tags", timeout=60).json()["models"]}
    det = d.get("details", {})
    etiqueta = etiquetas.get(nombre) or etiquetas.get(f"{nombre}:latest") or {}
    return {"digest": etiqueta.get("digest"),
            "parametros": det.get("parameter_size"),
            "cuantizacion": det.get("quantization_level"),
            "familia": det.get("family")}


def generar(modelo, prompt, think=None):
    cuerpo = {"model": modelo, "stream": False, "options": OPCIONES,
              "messages": [{"role": "user", "content": prompt}]}
    if think is not None:
        cuerpo["think"] = think
    r = requests.post(f"{OLLAMA}/api/chat", json=cuerpo, timeout=1800)
    r.raise_for_status()
    return r.json()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba", action="store_true", help="solo 3 pasajes por modelo")
    args = ap.parse_args()

    modelos = json.loads(CONFIG.read_text(encoding="utf-8"))["modelos"]
    pasajes = [json.loads(l) for l in PASAJES.read_text(encoding="utf-8").splitlines()]
    if args.prueba:
        pasajes = pasajes[:3]
    SALIDAS.parent.mkdir(exist_ok=True)
    hechas = set()
    if SALIDAS.exists():
        for l in SALIDAS.read_text(encoding="utf-8").splitlines():
            d = json.loads(l)
            hechas.add((d["modelo"], d["condicion"], d["id"]))

    total = len(modelos) * len(INSTRUCCIONES) * len(pasajes)
    n = len(hechas)
    for m in modelos:
        modelo = m["nombre"]
        meta = info_modelo(modelo)
        print(f"== {modelo} {meta}")
        for condicion in INSTRUCCIONES:
            for p in pasajes:
                if (modelo, condicion, p["id"]) in hechas:
                    continue
                t0 = time.time()
                d = generar(modelo, construir_prompt(condicion, p["texto"]), m.get("think"))
                registro = {
                    "id": p["id"], "modelo": modelo, "condicion": condicion,
                    "salida": d["message"]["content"].strip(),
                    "tokens_prompt": d.get("prompt_eval_count"),
                    "tokens_salida": d.get("eval_count"),
                    "segundos": round(time.time() - t0, 2),
                    "opciones": OPCIONES, **{f"modelo_{k}": v for k, v in meta.items()},
                    "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                with open(SALIDAS, "a", encoding="utf-8") as f:
                    f.write(json.dumps(registro, ensure_ascii=False) + "\n")
                n += 1
                print(f"[{n}/{total}] {modelo} {condicion} {p['id']} {registro['segundos']} s")


if __name__ == "__main__":
    main()
