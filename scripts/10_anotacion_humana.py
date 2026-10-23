"""Experimento 2 sobre las 72 salidas con doble anotación: anotación principal (A1, asistida por
un modelo de lenguaje) frente a la anotación humana independiente (A2).

Repite sobre el mismo subconjunto los cálculos de 07_analizar_exp2.py (proporciones de salidas con
errores por modelo e instrucción, sección y categoría; efecto de la instrucción guiada; AUROC de las
métricas; precisión y cobertura de los detectores) para comprobar qué conclusiones se mantienen
con la anotación humana. Escribe resultados/anotacion_humana.xlsx.
"""
import difflib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon
from sklearn.metrics import roc_auc_score
from statsmodels.stats.contingency_tables import mcnemar

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import linguistica as L  # noqa: E402

NOMBRES = {"hdnh2006/salamandra-7b-instruct": "Salamandra-7B", "llama3.1:8b": "Llama-3.1-8B",
           "qwen3:8b": "Qwen3-8B", "gemma3:12b": "Gemma-3-12B"}
ERRORES = ["POL", "MOD-D", "MOD-E", "COND", "NUM", "FREC", "TERM", "ENT", "DIR", "ADD", "OMI"]
BANDERA = {"NUM": "flag_NUM", "FREC": "flag_FREC", "POL": "flag_POL", "MOD-D": "flag_MOD_D",
           "MOD-E": "flag_MOD_E", "COND": "flag_COND", "DIR": "flag_DIR", "ENT": "flag_ENT"}
rng = np.random.default_rng(2027)

h = pd.read_excel(RAIZ / "anotacion" / "hoja_anotacion.xlsx").merge(
    pd.read_csv(RAIZ / "anotacion" / "clave_ciega.csv"), on="id_salida")
h["modelo_c"] = h.modelo.map(NOMBRES)
a2 = pd.read_csv(RAIZ / "anotacion" / "anotaciones_A2.csv", dtype=str)
a2 = a2.dropna(subset=["id_salida", "categoria"])
IDS = sorted(set(a2.id_salida))
a1 = pd.read_csv(RAIZ / "anotacion" / "anotaciones_A1.csv", dtype=str)
a1 = a1[a1.id_salida.isin(IDS)]
h = h[h.id_salida.isin(IDS)]

m = pd.read_csv(RAIZ / "resultados" / "salidas_metricas.csv")
pasajes = pd.read_json(RAIZ / "corpus" / "pasajes.jsonl", lines=True).set_index("id")
sal = pd.read_json(RAIZ / "resultados" / "salidas.jsonl", lines=True)
sal["sim"] = [difflib.SequenceMatcher(None, pasajes.texto[i], L.limpiar_salida(s)).ratio()
              for i, s in zip(sal.id, sal.salida)]
m = m.merge(sal[["id", "modelo", "condicion", "sim"]], on=["id", "modelo", "condicion"])
m["delta_szigriszt"] = m.sal_szigriszt - m.orig_szigriszt
mm = m.merge(h[["id_pasaje", "modelo", "condicion", "id_salida"]],
             left_on=["id", "modelo", "condicion"], right_on=["id_pasaje", "modelo", "condicion"])


def por_salida(an):
    an = an.copy()
    an["gravedad"] = pd.to_numeric(an.gravedad, errors="coerce")
    err = an[an.categoria.isin(ERRORES)]
    ps = h[["id_salida", "id_pasaje", "modelo_c", "condicion", "seccion"]].copy()
    agg = err.groupby("id_salida").agg(n_err=("categoria", "size"), max_grav=("gravedad", "max"))
    ps = ps.merge(agg, on="id_salida", how="left").fillna({"n_err": 0, "max_grav": -1})
    ps["NOSIMP"] = ps.id_salida.isin(set(an.loc[an.categoria == "NOSIMP", "id_salida"]))
    ps["con_error"] = ps.max_grav >= 0
    ps["grav1"] = ps.max_grav >= 1
    ps["grave"] = ps.max_grav >= 2
    return ps, err


def auroc_ic(y, x):
    a = roc_auc_score(y, x)
    bs = [roc_auc_score(y[i], x[i]) for i in (rng.choice(len(y), len(y)) for _ in range(1000))
          if y[i].min() != y[i].max()]
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


hojas = {}
resumen = []
for nombre, an in (("A1", a1), ("A2", a2)):
    ps, err = por_salida(an)
    tb = (ps.groupby(["modelo_c", "condicion"])
          .agg(n=("id_salida", "size"), err_salida=("n_err", "mean"), con_error=("con_error", "mean"),
               grav1=("grav1", "mean"), grave=("grave", "mean")).reset_index())
    tsec = ps.groupby("seccion").agg(n=("id_salida", "size"), grav1=("grav1", "mean"), grave=("grave", "mean"))
    tcat = pd.crosstab(err.categoria, err.gravedad, margins=True)
    pv = ps.pivot_table(index=["id_pasaje", "modelo_c"], columns="condicion",
                        values=["grav1", "grave", "n_err"], aggfunc="first")
    filas = []
    for var in ("grav1", "grave"):
        b, g = pv[(var, "basica")].astype(bool), pv[(var, "guiada")].astype(bool)
        t = [[(b & g).sum(), (b & ~g).sum()], [(~b & g).sum(), (~b & ~g).sum()]]
        filas.append({"variable": var, "basica": b.mean(), "guiada": g.mean(), "mejoran": t[0][1],
                      "empeoran": t[1][0], "p": mcnemar(t, exact=True).pvalue})
    w = wilcoxon(pv[("n_err", "basica")], pv[("n_err", "guiada")])
    filas.append({"variable": "n_err (Wilcoxon)", "basica": pv[("n_err", "basica")].mean(),
                  "guiada": pv[("n_err", "guiada")].mean(), "p": w.pvalue})
    tinst = pd.DataFrame(filas)
    x = mm.merge(ps[["id_salida", "grav1", "grave", "NOSIMP", "n_err"]], on="id_salida")
    filas = []
    for sub_n, sub in (("todas", x), ("sin copias", x[~x.NOSIMP])):
        for met, signo in (("bertscore_f1", 1), ("nli_cobertura", 1), ("nli_cobertura_min", 1),
                           ("sal_szigriszt", -1)):
            for obj in ("grav1", "grave"):
                y = (~sub[obj]).astype(int).values
                if y.min() == y.max():
                    continue
                a, lo, hi = auroc_ic(y, signo * sub[met].fillna(sub[met].median()).values)
                filas.append({"subconjunto": sub_n, "metrica": met, "objetivo": f"sin {obj}",
                              "n": len(sub), "AUROC": a, "IC_inf": lo, "IC_sup": hi})
    tmet = pd.DataFrame(filas)
    filas = []
    for cat, col in BANDERA.items():
        gold = x.id_salida.isin(err.loc[(err.categoria == cat) & (err.gravedad >= 1), "id_salida"])
        pred = x[col].astype(bool)
        tp, fp, fn = (gold & pred).sum(), (~gold & pred).sum(), (gold & ~pred).sum()
        filas.append({"categoria": cat, "anotadas": int(gold.sum()), "alarmas": int(pred.sum()),
                      "precision": tp / (tp + fp) if tp + fp else np.nan,
                      "cobertura": tp / (tp + fn) if tp + fn else np.nan})
    cual = x[list(BANDERA.values())].any(axis=1)
    gold = x.grav1
    tp, fp, fn = (gold & cual).sum(), (~gold & cual).sum(), (gold & ~cual).sum()
    filas.append({"categoria": "cualquiera", "anotadas": int(gold.sum()), "alarmas": int(cual.sum()),
                  "precision": tp / (tp + fp), "cobertura": tp / (tp + fn)})
    tdet = pd.DataFrame(filas)
    for k, v in (("modelos", tb), ("seccion", tsec), ("categorias", tcat), ("instruccion", tinst),
                 ("metricas", tmet), ("detectores", tdet)):
        hojas[f"{nombre}_{k}"] = v
    print(f"\n================ {nombre}")
    print(f"errores: {len(err)}; salidas con error: {ps.con_error.sum()}; grav>=1: {ps.grav1.sum()}; "
          f"grav2: {ps.grave.sum()} de {len(ps)}")
    print(tb.round(3).to_string(index=False)); print(tsec.round(3)); print(tcat)
    print(tinst.round(4).to_string(index=False)); print(tmet.round(3).to_string(index=False))
    print(tdet.round(3).to_string(index=False))

with pd.ExcelWriter(RAIZ / "resultados" / "anotacion_humana.xlsx") as wr:
    for k, v in hojas.items():
        v.to_excel(wr, sheet_name=k[:31], index=k.endswith(("seccion", "categorias")))
