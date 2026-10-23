"""Construye el corpus de pasajes de prospectos a partir de la API REST de CIMA (AEMPS).

Muestreo estratificado por grupo anatómico ATC (nivel 1): N_POR_GRUPO medicamentos
por grupo, uno por principio activo (vtm), excluidos los de uso hospitalario.
De cada prospecto se toman las secciones 2 (antes de tomar), 3 (cómo tomar)
y 4 (efectos adversos), segmentadas en pasajes por subepígrafes.

Condiciones de reutilización (aviso legal AEMPS): se autoriza la reproducción
citando el origen y la fecha de última actualización; ambas se guardan en los metadatos.
"""
import html
import json
import random
import re
import time
from pathlib import Path

import requests

BASE = "https://cima.aemps.es/cima/rest"
SEMILLA = 2027
N_POR_GRUPO = 4
SECCIONES = ["2", "3", "4"]
MIN_PAL, MAX_PAL = 60, 320
GRUPOS_ATC = list("ABCDGHJLMNPRSV")
# Texto normalizado de la plantilla QRD, idéntico en todos los prospectos
PLANTILLA = re.compile(r"comunicación de efectos adversos|farmacovigilancia|apéndice v|"
                       r"si tiene cualquier otra duda sobre el uso", re.I)

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "corpus"
CACHE = SALIDA / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

sesion = requests.Session()
sesion.headers["User-Agent"] = "investigacion-academica-simplificacion (uso no comercial)"


def get_json(ruta, params=None, cache_id=None):
    if cache_id:
        f = CACHE / f"{cache_id}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    for intento in range(4):
        try:
            r = sesion.get(f"{BASE}/{ruta}", params=params,
                           headers={"Accept": "application/json"}, timeout=30)
            r.raise_for_status()
            datos = r.json()
            break
        except (requests.RequestException, ValueError):
            time.sleep(2 * (intento + 1))
    else:
        raise RuntimeError(f"Fallo al consultar {ruta} {params}")
    time.sleep(0.3)
    if cache_id:
        f.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return datos


def listado_completo():
    todos, pagina = [], 1
    while True:
        d = get_json("medicamentos", {"comerc": 1, "autorizados": 1, "pagina": pagina},
                     cache_id=f"listado_p{pagina:03d}")
        todos.extend(d["resultados"])
        if pagina * d["tamanioPagina"] >= d["totalFilas"]:
            return todos
        pagina += 1


def html_a_bloques(fragmento):
    """Devuelve una lista de (es_titulo, texto) conservando párrafos y viñetas."""
    bloques = []
    for m in re.finditer(r"<(p|li|h\d)\b[^>]*>(.*?)</\1>", fragmento, flags=re.S | re.I):
        etiqueta, interior = m.group(1).lower(), m.group(2)
        texto = html.unescape(re.sub(r"<[^>]+>", "", interior))
        texto = re.sub(r"\s+", " ", texto).strip()
        if not texto:
            continue
        negrita = " ".join(re.findall(r"<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>", interior, flags=re.S))
        negrita = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", negrita))).strip()
        es_titulo = etiqueta.startswith("h") or (
            etiqueta == "p" and negrita == texto and len(texto.split()) <= 15)
        prefijo = "- " if etiqueta == "li" else ""
        bloques.append((es_titulo, prefijo + texto))
    return bloques


def pasajes_de_seccion(bloques):
    """Agrupa bloques en pasajes que empiezan en un subepígrafe."""
    grupos, actual = [], []
    for es_titulo, texto in bloques:
        if es_titulo and actual:
            grupos.append(actual)
            actual = []
        actual.append(texto)
    if actual:
        grupos.append(actual)
    pasajes = []
    for g in grupos:
        # Trocea grupos demasiado largos por límites de bloque
        trozo, n = [], 0
        for t in g:
            k = len(t.split())
            if n + k > MAX_PAL and n >= MIN_PAL:
                pasajes.append("\n".join(trozo))
                trozo, n = [], 0
            trozo.append(t)
            n += k
        if trozo:
            pasajes.append("\n".join(trozo))
    return [p for p in pasajes
            if MIN_PAL <= len(p.split()) <= MAX_PAL and not PLANTILLA.search(p)]


def main():
    rng = random.Random(SEMILLA)
    lista = listado_completo()
    print(f"Medicamentos comercializados y autorizados: {len(lista)}")
    candidatos = [m for m in lista
                  if "hospitalario" not in (m.get("cpresc") or "").lower()
                  and any(d["tipo"] == 2 and d.get("secc") for d in m.get("docs", []))
                  and m.get("vtm")]
    print(f"Con prospecto segmentado y sin uso hospitalario: {len(candidatos)}")
    rng.shuffle(candidatos)

    elegidos = {g: [] for g in GRUPOS_ATC}
    vtm_vistos = set()
    for m in candidatos:
        if all(len(v) >= N_POR_GRUPO for v in elegidos.values()):
            break
        if m["vtm"]["id"] in vtm_vistos:
            continue
        det = get_json("medicamento", {"nregistro": m["nregistro"]},
                       cache_id=f"med_{m['nregistro']}")
        atcs = [a["codigo"] for a in det.get("atcs") or []]
        if not atcs:
            continue
        grupo = atcs[0][0]
        forma = ((det.get("formaFarmaceutica") or {}).get("nombre") or "").upper()
        if "PERFUSI" in forma:  # administración exclusivamente profesional
            continue
        if grupo not in elegidos or len(elegidos[grupo]) >= N_POR_GRUPO:
            continue
        secs = get_json("docSegmentado/contenido/2", {"nregistro": m["nregistro"]},
                        cache_id=f"prosp_{m['nregistro']}")
        por_sec = {s["seccion"]: s for s in secs}
        pasajes = {s: pasajes_de_seccion(html_a_bloques(por_sec[s]["contenido"]))
                   for s in SECCIONES if s in por_sec}
        if any(not pasajes.get(s) for s in SECCIONES):
            continue
        fecha = next((d.get("fecha") for d in det["docs"] if d["tipo"] == 2), None)
        elegidos[grupo].append({
            "nregistro": m["nregistro"], "nombre": det["nombre"],
            "vtm": det["vtm"]["nombre"], "atc": atcs[-1], "grupo_atc": grupo,
            "receta": det.get("receta"), "generico": det.get("generico"),
            "forma": (det.get("formaFarmaceuticaSimplificada") or {}).get("nombre"),
            "fecha_prospecto": time.strftime("%Y-%m-%d", time.gmtime(fecha / 1000)) if fecha else None,
            "url": f"https://cima.aemps.es/cima/dochtml/p/{m['nregistro']}/P_{m['nregistro']}.html",
            "pasajes": pasajes,
        })
        vtm_vistos.add(m["vtm"]["id"])
        print(f"  {grupo}: {det['nombre'][:70]}")

    # Un pasaje por sección y medicamento, elegido al azar
    registros = []
    for grupo, meds in elegidos.items():
        for med in meds:
            for s in SECCIONES:
                texto = rng.choice(med["pasajes"][s])
                registros.append({
                    "id": f"{med['nregistro']}_s{s}", "seccion": s,
                    "texto": texto, "n_palabras": len(texto.split()),
                    **{k: v for k, v in med.items() if k != "pasajes"},
                })
    (SALIDA / "medicamentos.json").write_text(
        json.dumps(elegidos, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(SALIDA / "pasajes.jsonl", "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Medicamentos: {sum(len(v) for v in elegidos.values())} | pasajes: {len(registros)}")


if __name__ == "__main__":
    main()
