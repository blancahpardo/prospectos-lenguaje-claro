"""Acuerdo entre la anotación principal (A1) y la de control (A2) sobre las 72 salidas dobles.

- κ de Cohen por categoría: presencia o ausencia de la categoría en cada salida.
- κ global para «alguna salida con error» (gravedad ≥ 0), «con error de gravedad ≥ 1» y «≥ 2».
- Dirección del desacuerdo en la gravedad máxima (cuántas salidas puntúa más alto cada anotación).
- α de Krippendorff ordinal para la gravedad máxima por salida (−1 = sin errores).
Cada κ se etiqueta con la escala de Landis y Koch (1977: 165), que los autores llaman arbitraria;
α se juzga con los umbrales de Krippendorff (2019: 356): ≥ 0,800 firme; 0,667–0,800 provisional.
Lee anotacion/anotaciones_A2.csv (anotación humana) y anotaciones_A1.csv.
"""
from pathlib import Path

import krippendorff
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

RAIZ = Path(__file__).resolve().parents[1]
ERRORES = ["POL", "MOD-D", "MOD-E", "COND", "NUM", "FREC", "TERM", "ENT", "DIR", "ADD", "OMI"]

a1 = pd.read_csv(RAIZ / "anotacion" / "anotaciones_A1.csv", dtype=str)
a2 = pd.read_csv(RAIZ / "anotacion" / "anotaciones_A2.csv", dtype=str)
a2 = a2.dropna(subset=["id_salida", "categoria"])
ids = sorted(set(a2.id_salida))
a1 = a1[a1.id_salida.isin(ids)]
for a in (a1, a2):
    a["gravedad"] = pd.to_numeric(a.gravedad, errors="coerce")


def presencia(a, cat):
    s = set(a.loc[a.categoria == cat, "id_salida"])
    return np.array([i in s for i in ids])


def grav_max(a):
    g = a[a.categoria.isin(ERRORES)].groupby("id_salida").gravedad.max()
    return np.array([g.get(i, -1) for i in ids])


def landis(k):
    """Etiqueta de Landis y Koch (1977, p. 165)."""
    if np.isnan(k):
        return ""
    for lim, et in ((0, "Poor"), (0.205, "Slight"), (0.405, "Fair"), (0.605, "Moderate"), (0.805, "Substantial")):
        if k < lim:
            return et
    return "Almost Perfect"


def krippendorff_juicio(a):
    """Umbrales de Krippendorff (2019, p. 356)."""
    return "fiable" if a >= 0.800 else "solo conclusiones provisionales" if a >= 0.667 else "no fiable"


filas = []
for cat in ERRORES + ["REG", "NOSIMP"]:
    x, y = presencia(a1, cat), presencia(a2, cat)
    k = cohen_kappa_score(x, y) if (x.any() or y.any()) and not (x.all() and y.all()) else np.nan
    filas.append({"categoria": cat, "A1": int(x.sum()), "A2": int(y.sum()), "kappa": k})
g1, g2 = grav_max(a1), grav_max(a2)
for umbral in (0, 1, 2):
    filas.append({"categoria": f"gravedad >= {umbral}", "A1": int((g1 >= umbral).sum()),
                  "A2": int((g2 >= umbral).sum()), "kappa": cohen_kappa_score(g1 >= umbral, g2 >= umbral)})
alpha = krippendorff.alpha(reliability_data=[g1, g2], level_of_measurement="ordinal")
t = pd.DataFrame(filas)
t["landis_koch"] = t.kappa.map(landis)
print(f"Salidas comparadas: {len(ids)}")
print(t.round(3).to_string(index=False))
print(f"α de Krippendorff (gravedad máxima, ordinal): {alpha:.3f} ({krippendorff_juicio(alpha)})")
print(f"Gravedad máxima: A2 > A1 en {(g2 > g1).sum()} salidas; A1 > A2 en {(g1 > g2).sum()}; iguales en {(g1 == g2).sum()}")
t.to_csv(RAIZ / "resultados" / "acuerdo.csv", index=False)
