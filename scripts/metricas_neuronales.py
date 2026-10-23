"""Métricas automáticas sin referencia: BERTScore original–salida e implicación textual (NLI).

- BERTScore (Zhang et al., 2020) con xlm-roberta-large, capa 17, sin reescalado.
- NLI con XLM-RoBERTa large ajustado en XNLI (Conneau et al., 2018, 2020):
    * cobertura: media, por oración del original, de la probabilidad de que la salida la implique;
    * soporte: media, por oración de la salida, de la probabilidad de que el original la implique.
  En ambos casos la premisa son las tres oraciones del otro texto con más solapamiento léxico.
"""
import os
from pathlib import Path

import torch
from bert_score import BERTScorer
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from linguistica import oraciones, palabras

DISPOSITIVO = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
# Copias locales (descargadas de Hugging Face); si no existen, se usa el identificador del Hub
LOCAL = Path(os.environ.get("SEPLN78_MODELOS", Path.home() / ".cache" / "sepln78_modelos"))
XLMR = str(LOCAL / "xlm-roberta-large") if (LOCAL / "xlm-roberta-large" / "model.safetensors").exists() else "xlm-roberta-large"
NLI_MODELO = os.environ.get("SEPLN78_NLI", str(LOCAL / "xlmr-xnli")
                            if (LOCAL / "xlmr-xnli" / "model.safetensors").exists()
                            else "joeddav/xlm-roberta-large-xnli")

_bs = None
_nli = None


def bertscore(originales, salidas):
    global _bs
    if _bs is None:
        _bs = BERTScorer(model_type=XLMR, num_layers=17, device=DISPOSITIVO)
    p, r, f = _bs.score(salidas, originales, batch_size=16)
    return f.tolist()


def _cargar_nli():
    global _nli
    if _nli is None:
        tok = AutoTokenizer.from_pretrained(NLI_MODELO)
        mod = AutoModelForSequenceClassification.from_pretrained(NLI_MODELO).to(DISPOSITIVO).eval()
        idx = {v.lower(): k for k, v in mod.config.id2label.items()}["entailment"]
        _nli = (tok, mod, idx)
    return _nli


@torch.no_grad()
def prob_implicacion(premisas, hipotesis, lote=32):
    """Probabilidad de implicación para cada par, en lotes ordenados por longitud."""
    tok, mod, idx = _cargar_nli()
    orden = sorted(range(len(premisas)), key=lambda i: len(premisas[i]) + len(hipotesis[i]))
    salida = [0.0] * len(premisas)
    for k in range(0, len(orden), lote):
        bloque = orden[k:k + lote]
        enc = tok([premisas[i] for i in bloque], [hipotesis[i] for i in bloque],
                  truncation="longest_first", max_length=512, padding=True,
                  return_tensors="pt").to(DISPOSITIVO)
        probs = torch.softmax(mod(**enc).logits.float(), dim=-1)[:, idx].tolist()
        for i, p in zip(bloque, probs):
            salida[i] = p
    return salida


K_PREMISA = 3


def _premisa(hipotesis, oraciones_fuente):
    """Las K oraciones de la fuente con más solapamiento léxico, en su orden original.

    Los modelos NLI se entrenan con premisas breves y rinden mal con un pasaje entero
    como premisa; se recupera primero el fragmento pertinente (cf. SummaC).
    """
    h = {w.lower() for w in palabras(hipotesis)}
    puntos = [(len(h & {w.lower() for w in palabras(o)}) / (len(h) or 1), i)
              for i, o in enumerate(oraciones_fuente)]
    elegidas = sorted(i for _, i in sorted(puntos, reverse=True)[:K_PREMISA])
    return " ".join(oraciones_fuente[i] for i in elegidas)


def nli_lote(originales, salidas):
    """Cobertura y soporte por par original–salida, con todas las oraciones en un solo lote."""
    prem, hip, clave = [], [], []
    for n, (o, s) in enumerate(zip(originales, salidas)):
        o_or, s_or = oraciones(o), oraciones(s)
        if not o_or or not s_or:
            continue
        for h in o_or:
            prem.append(_premisa(h, s_or)); hip.append(h); clave.append((n, "cob"))
        for h in s_or:
            prem.append(_premisa(h, o_or)); hip.append(h); clave.append((n, "sop"))
    probs = prob_implicacion(prem, hip)
    acum = [{"cob": [], "sop": []} for _ in originales]
    for (n, tipo), p in zip(clave, probs):
        acum[n][tipo].append(p)
    res = []
    for a in acum:
        if not a["cob"] or not a["sop"]:
            res.append({"nli_cobertura": None, "nli_soporte": None, "nli_cobertura_min": None})
        else:
            res.append({"nli_cobertura": sum(a["cob"]) / len(a["cob"]),
                        "nli_soporte": sum(a["sop"]) / len(a["sop"]),
                        "nli_cobertura_min": min(a["cob"])})
    return res
