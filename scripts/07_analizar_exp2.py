"""Análisis del experimento 2: simplificaciones de cuatro modelos con dos instrucciones.

A. Todas las salidas (1344): legibilidad, compresión, copia literal, métricas automáticas y tuteo.
B. Muestra anotada (240): errores por modelo, instrucción, sección, categoría y gravedad;
   efecto de la instrucción guiada (prueba de McNemar, pares por pasaje y modelo).
C. Métricas y detectores frente a la anotación: AUROC para salidas con error relevante,
   correlación de Spearman y precisión/cobertura de cada detector.
Escribe resultados/experimento2.xlsx y muestra las tablas en pantalla.
"""
import difflib
import re
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
rng = np.random.default_rng(2027)

# ---------------------------------------------------------------- A. todas las salidas
m = pd.read_csv(RAIZ / "resultados" / "salidas_metricas.csv")
m["modelo_c"] = m.modelo.map(NOMBRES)
pasajes = pd.read_json(RAIZ / "corpus" / "pasajes.jsonl", lines=True).set_index("id")
sal = pd.read_json(RAIZ / "resultados" / "salidas.jsonl", lines=True)
sal["limpia"] = sal.salida.map(L.limpiar_salida)
sal["original"] = sal.id.map(pasajes.texto)
sal["similitud"] = [difflib.SequenceMatcher(None, o, s).ratio() for o, s in zip(sal.original, sal.limpia)]
TUTEO = re.compile(r"\b(tú|tienes|debes|puedes|notas|tomas|sientes|consulta|habla|llama|tu|tus|te)\b", re.I)
sal["tuteo"] = sal.limpia.map(lambda t: len(TUTEO.findall(t)) >= 2)
m = m.merge(sal[["id", "modelo", "condicion", "similitud", "tuteo"]], on=["id", "modelo", "condicion"])
m["copia"] = m.similitud >= 0.95
m["delta_szigriszt"] = m.sal_szigriszt - m.orig_szigriszt

ta = (m.groupby(["modelo_c", "condicion"])
       .agg(n=("id", "size"), szigriszt=("sal_szigriszt", "mean"), delta=("delta_szigriszt", "mean"),
            palabras_oracion=("sal_palabras_por_oracion", "mean"), compresion=("compresion", "mean"),
            copia=("copia", "mean"), tuteo=("tuteo", "mean"), bertscore=("bertscore_f1", "mean"),
            cobertura=("nli_cobertura", "mean"), soporte=("nli_soporte", "mean"),
            segundos=("segundos", "mean"))
       .reset_index())
orig = pasajes.texto.map(L.legibilidad).apply(pd.Series)
print(f"Original: Szigriszt {orig.szigriszt.mean():.1f}; palabras/oración {orig.palabras_por_oracion.mean():.1f}")
print("\nA. Todas las salidas")
print(ta.round(3).to_string(index=False))

# ---------------------------------------------------------------- B. muestra anotada
h = pd.read_excel(RAIZ / "anotacion" / "hoja_anotacion.xlsx")
clave = pd.read_csv(RAIZ / "anotacion" / "clave_ciega.csv")
h = h.merge(clave, on="id_salida")
h["modelo_c"] = h.modelo.map(NOMBRES)
an = pd.read_csv(RAIZ / "anotacion" / "anotaciones_A1.csv", dtype=str)
an["gravedad"] = pd.to_numeric(an.gravedad, errors="coerce")
err = an[an.categoria.isin(ERRORES)].merge(h[["id_salida", "modelo_c", "condicion", "seccion"]], on="id_salida")

por_salida = h[["id_salida", "id_pasaje", "modelo_c", "condicion", "seccion"]].copy()
agg = err.groupby("id_salida").agg(n_err=("categoria", "size"), max_grav=("gravedad", "max"),
                                   n_rel=("gravedad", lambda g: (g >= 1).sum()))
por_salida = por_salida.merge(agg, on="id_salida", how="left").fillna({"n_err": 0, "max_grav": -1, "n_rel": 0})
for ind in ["NOSIMP", "REG", "DEG"]:
    ids = set(an.loc[an.categoria == ind, "id_salida"])
    por_salida[ind] = por_salida.id_salida.isin(ids)
por_salida["grave"] = por_salida.max_grav >= 2
por_salida["algun_relevante"] = por_salida.max_grav >= 1

tb = (por_salida.groupby(["modelo_c", "condicion"])
      .agg(n=("id_salida", "size"), errores_por_salida=("n_err", "mean"), relevantes=("n_rel", "mean"),
           con_error_grav1=("algun_relevante", "mean"), con_error_grav2=("grave", "mean"),
           copia=("NOSIMP", "mean"), tuteo=("REG", "mean"))
      .reset_index())
print("\nB1. Errores por modelo e instrucción (muestra anotada)")
print(tb.round(3).to_string(index=False))

tc = pd.crosstab(err.categoria, err.gravedad, margins=True)
print("\nB2. Errores por categoría y gravedad")
print(tc)
tcm = pd.crosstab(err.categoria, err.modelo_c)
print("\nB3. Errores por categoría y modelo")
print(tcm)
tsec = por_salida.groupby("seccion").agg(errores=("n_err", "mean"), grav2=("grave", "mean"))
print("\nB4. Por sección")
print(tsec.round(3))

# Efecto de la instrucción guiada: pares (pasaje, modelo)
pv = por_salida.pivot_table(index=["id_pasaje", "modelo_c"], columns="condicion",
                            values=["algun_relevante", "n_err", "NOSIMP"], aggfunc="first")
filas = []
for var in ["algun_relevante", "NOSIMP"]:
    b, g = pv[(var, "basica")].astype(bool), pv[(var, "guiada")].astype(bool)
    tabla = [[(b & g).sum(), (b & ~g).sum()], [(~b & g).sum(), (~b & ~g).sum()]]
    r = mcnemar(tabla, exact=True)
    filas.append({"variable": var, "basica": b.mean(), "guiada": g.mean(),
                  "solo_basica": tabla[0][1], "solo_guiada": tabla[1][0], "p_mcnemar": r.pvalue})
w = wilcoxon(pv[("n_err", "basica")], pv[("n_err", "guiada")], zero_method="wilcox")
filas.append({"variable": "n_err (Wilcoxon)", "basica": pv[("n_err", "basica")].mean(),
              "guiada": pv[("n_err", "guiada")].mean(), "p_mcnemar": w.pvalue})
td = pd.DataFrame(filas)
print("\nB5. Instrucción básica frente a guiada (120 pares)")
print(td.round(4).to_string(index=False))

# ---------------------------------------------------------------- C. métricas y detectores
mm = m.merge(h[["id_pasaje", "modelo", "condicion", "id_salida"]],
             left_on=["id", "modelo", "condicion"], right_on=["id_pasaje", "modelo", "condicion"])
mm = mm.merge(por_salida[["id_salida", "n_err", "n_rel", "grave", "algun_relevante", "NOSIMP"]], on="id_salida")
METRICAS = {"bertscore_f1": 1, "nli_cobertura": 1, "nli_soporte": 1, "nli_cobertura_min": 1,
            "sal_szigriszt": -1, "delta_szigriszt": -1}


def auroc_ic(y, x):
    a = roc_auc_score(y, x)
    bs = []
    idx = np.arange(len(y))
    for _ in range(1000):
        i = rng.choice(idx, len(idx))
        if y[i].min() != y[i].max():
            bs.append(roc_auc_score(y[i], x[i]))
    return a, np.percentile(bs, 2.5), np.percentile(bs, 97.5)


filas = []
for sub_nombre, sub in [("todas", mm), ("sin copias", mm[~mm.NOSIMP])]:
    for met, signo in METRICAS.items():
        x = signo * sub[met].fillna(sub[met].median()).values  # más alto = «más fiel» según la métrica
        for obj in ["algun_relevante", "grave"]:
            y = (~sub[obj]).astype(int).values  # 1 = salida sin error de ese nivel
            a, lo, hi = auroc_ic(y, x)
            filas.append({"subconjunto": sub_nombre, "metrica": met, "objetivo": f"sin {obj}",
                          "AUROC": a, "IC_inf": lo, "IC_sup": hi})
        rho, p = spearmanr(sub[met], sub.n_rel, nan_policy="omit")
        filas.append({"subconjunto": sub_nombre, "metrica": met, "objetivo": "Spearman con n.º errores ≥1",
                      "AUROC": rho, "IC_inf": p, "IC_sup": np.nan})
te = pd.DataFrame(filas)
print("\nC1. Métricas frente a la anotación")
print(te.round(3).to_string(index=False))

BANDERA = {"NUM": "flag_NUM", "FREC": "flag_FREC", "POL": "flag_POL", "MOD-D": "flag_MOD_D",
           "MOD-E": "flag_MOD_E", "COND": "flag_COND", "DIR": "flag_DIR", "ENT": "flag_ENT"}
filas = []
for cat, col in BANDERA.items():
    gold = mm.id_salida.isin(err.loc[(err.categoria == cat) & (err.gravedad >= 1), "id_salida"])
    pred = mm[col].astype(bool)
    tp, fp, fn = (gold & pred).sum(), (~gold & pred).sum(), (gold & ~pred).sum()
    filas.append({"categoria": cat, "casos_anotados": int(gold.sum()), "alarmas": int(pred.sum()),
                  "precision": tp / (tp + fp) if tp + fp else np.nan,
                  "cobertura": tp / (tp + fn) if tp + fn else np.nan})
cualquiera = mm[[c for c in BANDERA.values()]].any(axis=1)
gold = mm.algun_relevante
tp, fp, fn = (gold & cualquiera).sum(), (~gold & cualquiera).sum(), (gold & ~cualquiera).sum()
filas.append({"categoria": "cualquiera", "casos_anotados": int(gold.sum()), "alarmas": int(cualquiera.sum()),
              "precision": tp / (tp + fp), "cobertura": tp / (tp + fn)})
tf = pd.DataFrame(filas)
print("\nC2. Detectores frente a la anotación (errores de gravedad ≥ 1)")
print(tf.round(3).to_string(index=False))

with pd.ExcelWriter(RAIZ / "resultados" / "experimento2.xlsx") as wr:
    ta.to_excel(wr, sheet_name="A_todas", index=False)
    tb.to_excel(wr, sheet_name="B1_modelos", index=False)
    tc.to_excel(wr, sheet_name="B2_categorias")
    tcm.to_excel(wr, sheet_name="B3_cat_modelo")
    tsec.to_excel(wr, sheet_name="B4_seccion")
    td.to_excel(wr, sheet_name="B5_instruccion", index=False)
    te.to_excel(wr, sheet_name="C1_metricas", index=False)
    tf.to_excel(wr, sheet_name="C2_detectores", index=False)
    por_salida.to_excel(wr, sheet_name="por_salida", index=False)
