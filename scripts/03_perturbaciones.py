"""Experimento 1: sensibilidad de las métricas automáticas a errores críticos mínimos.

Para cada pasaje se crean pares mínimos con UNA sola alteración controlada:
  críticas:  POL (se suprime una negación de prohibición), MOD-D (debe → puede),
             MOD-E (puede + infinitivo → presente de indicativo), NUM (se duplica una cifra),
             FREC (se cambia la categoría o la cifra de frecuencia), OMI (se omite un
             elemento de lista que empieza por «Si …»)
  benigna:   LEX (sustitución de tecnicismos por equivalentes de uso común)
Todas las perturbaciones son deterministas y se aplican solo donde el patrón existe.
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASAJES = RAIZ / "corpus" / "pasajes.jsonl"
SALIDA = RAIZ / "resultados" / "perturbaciones.jsonl"

# Verbos que aparecen tras «puede(n)» en prospectos y cuyo presente es irregular
IRREGULARES = {"tener": ("tiene", "tienen"), "sentir": ("siente", "sienten"),
               "aparecer": ("aparece", "aparecen"), "producir": ("produce", "producen"),
               "reducir": ("reduce", "reducen"), "disminuir": ("disminuye", "disminuyen"),
               "aumentar": ("aumenta", "aumentan"), "hacer": ("hace", "hacen"),
               "ser": ("es", "son"), "haber": ("hay", "hay"), "estar": ("está", "están"),
               "sufrir": ("sufre", "sufren"), "empeorar": ("empeora", "empeoran"),
               "influir": ("influye", "influyen"), "contribuir": ("contribuye", "contribuyen"),
               "volver": ("vuelve", "vuelven"), "querer": ("quiere", "quieren"),
               "poder": ("puede", "pueden"), "ocurrir": ("ocurre", "ocurren"),
               "provocar": ("provoca", "provocan"), "notar": ("nota", "notan"),
               "experimentar": ("experimenta", "experimentan"), "afectar": ("afecta", "afectan"),
               "interferir": ("interfiere", "interfieren"), "requerir": ("requiere", "requieren"),
               "conducir": ("conduce", "conducen")}

# Verbos de acontecimiento: con ellos «puede(n)» es epistémico, no de permiso
VERBOS_EFECTO = ["producir", "causar", "provocar", "aparecer", "afectar", "ocurrir", "aumentar",
                 "reducir", "disminuir", "interferir", "empeorar", "ocasionar", "alterar",
                 "originar", "desencadenar", "ser", "sufrir", "experimentar"]

# Tecnicismo → equivalente de uso común (sustituciones benignas)
LEXICO = {"cefalea": "dolor de cabeza", "náuseas": "ganas de vomitar", "prurito": "picor",
          "erupción cutánea": "sarpullido", "hipersensibilidad": "alergia",
          "insuficiencia renal": "problemas de riñón", "insuficiencia hepática": "problemas de hígado",
          "somnolencia": "sueño", "vértigo": "mareo con sensación de que todo da vueltas",
          "hipotensión": "tensión baja", "hipertensión": "tensión alta", "astenia": "cansancio",
          "diarrea": "diarrea (heces líquidas)", "estreñimiento": "estreñimiento (dificultad para hacer de vientre)",
          "dispepsia": "digestión pesada", "edema": "hinchazón", "mialgia": "dolor muscular",
          "artralgia": "dolor de las articulaciones", "insomnio": "dificultad para dormir",
          "taquicardia": "latidos rápidos del corazón", "disnea": "dificultad para respirar",
          "ingerir": "tragar", "administrar": "dar", "comprimido": "pastilla",
          "comprimidos": "pastillas", "facultativo": "médico", "posología": "dosis",
          "concomitante": "a la vez", "contraindicado": "prohibido", "hepático": "del hígado",
          "renal": "del riñón", "gástrico": "del estómago", "pediátrica": "en niños",
          "lactancia": "lactancia (dar el pecho)", "anticoagulantes": "anticoagulantes (medicamentos para que la sangre no coagule)"}


def presente(infinitivo, plural):
    if infinitivo in IRREGULARES:
        return IRREGULARES[infinitivo][1 if plural else 0]
    base, fin = infinitivo[:-2], infinitivo[-2:]
    if fin == "ar":
        return base + ("an" if plural else "a")
    return base + ("en" if plural else "e")


def pert_POL(t):
    m = re.search(r"\b([Nn])o (tome|use|utilice|debe|administre|conduzca|beba|aplique|deje|interrumpa|"
                  r"se recomienda|combine|exceda|supere|aumente|duplique)\b", t)
    if not m:
        return None
    verbo = m.group(2)
    nuevo = verbo[0].upper() + verbo[1:] if m.group(1) == "N" else verbo
    return t[:m.start()] + nuevo + t[m.end():]


def pert_MOD_D(t):
    # obligación → permiso: «debe(n) + infinitivo» → «puede(n) + infinitivo»
    m = re.search(r"\b([Dd])ebe(n?)(?= [a-záéíóú]+(?:ar|er|ir)(?:se|le|lo|la)?\b)", t)
    if not m:
        return None
    return t[:m.start()] + ("P" if m.group(1) == "D" else "p") + "uede" + m.group(2) + t[m.end():]


def pert_MOD_E(t):
    m = re.search(r"\b([Pp])uede(n?) (" + "|".join(VERBOS_EFECTO) + r")\b", t)
    if not m:
        return None
    verbo = presente(m.group(3), bool(m.group(2)))
    if m.group(1) == "P":
        verbo = verbo[0].upper() + verbo[1:]
    return t[:m.start()] + verbo + t[m.end():]


def pert_NUM(t):
    for m in re.finditer(r"(?<![\d.,])(\d+)(?![\d.,])", t):
        contexto = t[max(0, m.start() - 12):m.start()].lower()
        if "sección" in contexto or "cada" in contexto or "apartado" in contexto:
            continue  # no tocar remisiones internas ni cifras de frecuencia (van en FREC)
        n = int(m.group(1))
        if n == 0:
            continue
        return t[:m.start()] + str(n * 2) + t[m.end():]
    return None


CAMBIO_FREC = [("poco frecuentes", "frecuentes"), ("Poco frecuentes", "Frecuentes"),
               ("muy raros", "frecuentes"), ("Muy raros", "Frecuentes"),
               ("raros", "frecuentes"), ("Raros", "Frecuentes"),
               ("1 de cada 1.000", "1 de cada 10"), ("1 de cada 10.000", "1 de cada 100"),
               ("1 de cada 100", "1 de cada 10")]


def pert_FREC(t):
    for a, b in CAMBIO_FREC:
        m = re.search(rf"(?<![\w.]){re.escape(a)}(?![\w.])", t)
        if m:
            return t[:m.start()] + b + t[m.end():]
    return None


def pert_COND(t):
    lineas = t.split("\n")
    for i, l in enumerate(lineas):
        if re.match(r"- (Si|si) ", l) and sum(x.startswith("- ") for x in lineas) >= 2:
            return "\n".join(lineas[:i] + lineas[i + 1:])
    return None


def pert_LEX(t):
    nuevo, cambios = t, 0
    for tec, comun in sorted(LEXICO.items(), key=lambda x: -len(x[0])):
        patron = re.compile(rf"\b{re.escape(tec)}\b", re.I)
        if patron.search(nuevo) and cambios < 3:
            nuevo = patron.sub(comun, nuevo, count=1)
            cambios += 1
    return nuevo if cambios else None


PERTURBACIONES = {"POL": pert_POL, "MOD-D": pert_MOD_D, "MOD-E": pert_MOD_E, "NUM": pert_NUM,
                  "FREC": pert_FREC, "OMI": pert_COND, "LEX": pert_LEX}


def main():
    pasajes = [json.loads(l) for l in PASAJES.read_text(encoding="utf-8").splitlines()]
    SALIDA.parent.mkdir(exist_ok=True)
    n = {k: 0 for k in PERTURBACIONES}
    with open(SALIDA, "w", encoding="utf-8") as f:
        for p in pasajes:
            f.write(json.dumps({"id": p["id"], "tipo": "IDENT", "original": p["texto"],
                                "salida": p["texto"]}, ensure_ascii=False) + "\n")
            for tipo, fn in PERTURBACIONES.items():
                s = fn(p["texto"])
                if s and s != p["texto"]:
                    n[tipo] += 1
                    f.write(json.dumps({"id": p["id"], "tipo": tipo, "original": p["texto"],
                                        "salida": s}, ensure_ascii=False) + "\n")
    print(n)


if __name__ == "__main__":
    main()
