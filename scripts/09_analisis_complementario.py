"""Análisis complementarios del experimento 2.

1. ¿Mide BERTScore fidelidad o solo cantidad de cambio? Se compara su AUROC con la de la
   similitud de caracteres (difflib) y se calcula su correlación parcial con los errores
   controlando esa similitud.
2. Salidas útiles: ganancia de legibilidad ≥ 5 puntos Szigriszt y sin errores de gravedad ≥ 1.
"""
import difflib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

RAIZ = Path(__file__).resolve().parents[1]
ps = pd.read_excel(RAIZ / "resultados" / "experimento2.xlsx", sheet_name="por_salida")
h = pd.read_excel(RAIZ / "anotacion" / "hoja_anotacion.xlsx")
clave = pd.read_csv(RAIZ / "anotacion" / "clave_ciega.csv")
m = pd.read_csv(RAIZ / "resultados" / "salidas_metricas.csv")
h = h.merge(clave, on="id_salida")
h["similitud"] = [difflib.SequenceMatcher(None, o, s).ratio() for o, s in zip(h.original, h.salida)]
d = h.merge(m, left_on=["id_pasaje", "modelo", "condicion"], right_on=["id", "modelo", "condicion"])
d = d.merge(ps[["id_salida", "n_rel", "algun_relevante", "grave", "NOSIMP", "modelo_c"]], on="id_salida")
d["delta"] = d.sal_szigriszt - d.orig_szigriszt

for nombre, sub in [("todas", d), ("sin copias", d[~d.NOSIMP])]:
    y = (~sub.algun_relevante).astype(int)
    print(nombre, "AUROC similitud caracteres:", round(roc_auc_score(y, sub.similitud), 3),
          "| BERTScore:", round(roc_auc_score(y, sub.bertscore_f1), 3),
          "| rho(BERTScore, similitud):", round(spearmanr(sub.bertscore_f1, sub.similitud)[0], 3))
    # correlación parcial de Spearman (rangos, residuos lineales)
    r = sub[["bertscore_f1", "similitud", "n_rel", "nli_cobertura_min"]].rank()
    def resid(a, b):
        X = np.c_[np.ones(len(b)), b]
        return a - X @ np.linalg.lstsq(X, a, rcond=None)[0]
    for met in ["bertscore_f1", "nli_cobertura_min"]:
        pr = np.corrcoef(resid(r[met].values, r.similitud.values), resid(r.n_rel.values, r.similitud.values))[0, 1]
        print(f"   parcial({met}, errores | similitud) = {pr:.3f}")

d["util"] = (d.delta >= 5) & (~d.algun_relevante)
t = d.groupby(["modelo_c", "condicion"]).util.mean().unstack().round(3)
print("\nSalidas útiles (Δ Szigriszt ≥ 5 y sin errores de gravedad ≥ 1)")
print(t)
print("Global:", d.groupby("condicion").util.mean().round(3).to_dict())
t.to_csv(RAIZ / "resultados" / "salidas_utiles.csv")
