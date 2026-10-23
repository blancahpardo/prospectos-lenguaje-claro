"""Análisis del experimento 1: ¿detectan las métricas los errores críticos mínimos?

1. Caída media de cada métrica respecto de la copia idéntica (pares por pasaje).
2. AUROC de cada métrica para separar la sustitución benigna (LEX) de cada error
   crítico: 1 = la métrica siempre puntúa mejor la benigna; 0,5 = no distingue.
   IC 95 % por remuestreo (bootstrap) de pasajes.
3. Sensibilidad de los detectores lingüísticos a su categoría y tasa de falsas
   alarmas sobre LEX.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

RAIZ = Path(__file__).resolve().parents[1]
df = pd.read_csv(RAIZ / "resultados" / "perturbaciones_metricas.csv")
METRICAS = ["bertscore_f1", "nli_cobertura", "nli_soporte", "nli_cobertura_min"]
CRITICAS = ["POL", "MOD-D", "MOD-E", "NUM", "FREC", "OMI"]
BANDERA = {"POL": "flag_POL", "MOD-D": "flag_MOD_D", "MOD-E": "flag_MOD_E",
           "NUM": "flag_NUM", "FREC": "flag_FREC", "OMI": "flag_COND"}
rng = np.random.default_rng(2027)

# 1. Caídas respecto de la identidad
ident = df[df.tipo == "IDENT"].set_index("id")[METRICAS]
filas = []
for tipo in CRITICAS + ["LEX"]:
    sub = df[df.tipo == tipo].set_index("id")[METRICAS]
    delta = sub - ident.loc[sub.index]
    fila = {"tipo": tipo, "n": len(sub)}
    for m in METRICAS:
        fila[f"{m}_media"] = sub[m].mean()
        fila[f"{m}_delta"] = delta[m].mean()
    filas.append(fila)
t1 = pd.DataFrame(filas)
print(t1.round(3).to_string(index=False))


# 2. AUROC benigna frente a crítica
def auroc(benigna, critica):
    y = np.r_[np.ones(len(benigna)), np.zeros(len(critica))]
    return roc_auc_score(y, np.r_[benigna, critica])


filas = []
lex = df[df.tipo == "LEX"]
for tipo in CRITICAS:
    cri = df[df.tipo == tipo]
    fila = {"tipo": tipo}
    for m in METRICAS:
        a = auroc(lex[m].values, cri[m].values)
        boots = []
        for _ in range(1000):
            b = lex[m].values[rng.integers(0, len(lex), len(lex))]
            c = cri[m].values[rng.integers(0, len(cri), len(cri))]
            boots.append(auroc(b, c))
        fila[m] = f"{a:.2f} [{np.percentile(boots, 2.5):.2f}–{np.percentile(boots, 97.5):.2f}]"
    filas.append(fila)
t2 = pd.DataFrame(filas)
print("\nAUROC (LEX frente a error crítico)")
print(t2.to_string(index=False))

# 3. Detectores
filas = []
for tipo in CRITICAS:
    col = BANDERA[tipo]
    filas.append({"tipo": tipo, "detector": col,
                  "sensibilidad": df[df.tipo == tipo][col].mean(),
                  "falsas_alarmas_LEX": df[df.tipo == "LEX"][col].mean(),
                  "falsas_alarmas_IDENT": df[df.tipo == "IDENT"][col].mean()})
t3 = pd.DataFrame(filas)
print("\nDetectores")
print(t3.round(3).to_string(index=False))

with pd.ExcelWriter(RAIZ / "resultados" / "experimento1.xlsx") as w:
    t1.to_excel(w, sheet_name="caidas", index=False)
    t2.to_excel(w, sheet_name="auroc", index=False)
    t3.to_excel(w, sheet_name="detectores", index=False)
