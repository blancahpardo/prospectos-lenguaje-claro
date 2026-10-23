"""Medidas de legibilidad y detectores de riesgo lingüístico para prospectos en español.

Los detectores comparan el original con la salida y señalan posibles pérdidas en
las categorías de la guía de anotación (NUM, FREC, POL, MOD-D, MOD-E, DIR, ENT).
Son deliberadamente superficiales: su precisión y cobertura se miden después
contra la anotación manual.
"""
import re
import unicodedata

# ---------------------------------------------------------------- tokenización

PAL = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:-[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*")
FIN_ORACION = re.compile(r"(?<=[.!?])\s+(?=[¿¡(«\"A-ZÁÉÍÓÚÑ0-9])|\n+")
ABREVIATURAS = re.compile(r"\b(p\. ej|aprox|etc|Dr|Dra|Sr|Sra|n\.º|núm|pág|vol|approx|i\.e|e\.g)\.", re.I)


def palabras(texto):
    return PAL.findall(texto)


def oraciones(texto):
    """Oraciones y elementos de lista; no corta tras abreviaturas habituales."""
    protegido = ABREVIATURAS.sub(lambda m: m.group(0).replace(".", "\x00"), texto)
    trozos = [t.replace("\x00", ".").strip(" -•\t") for t in FIN_ORACION.split(protegido)]
    return [t for t in trozos if palabras(t)]


def limpiar_salida(texto):
    """Normaliza el formato de las salidas sin tocar su contenido verbal.

    Elimina las comillas triples que algunos modelos copian de la instrucción, las marcas
    de Markdown (negritas, cursivas, encabezados) y unifica las viñetas en «- ».
    """
    t = texto.replace('"""', "")
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t, flags=re.S)
    t = re.sub(r"(?m)^\s*#{1,6}\s*", "", t)
    t = re.sub(r"(?m)^\s*[*•·]\s+", "- ", t)
    t = re.sub(r"(?m)^\s*\d+\.\s+(?=[A-ZÁÉÍÓÚÑ¿¡])", "- ", t)
    t = re.sub(r"(?<!\*)\*(?!\s)([^*\n]+?)\*(?!\*)", r"\1", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


# ---------------------------------------------------------------- sílabas

FUERTES, DEBILES, DEBILES_TILDE = set("aeoáéó"), set("iuü"), set("íú")


def silabas(palabra):
    """Cuenta núcleos silábicos con las reglas ortográficas de diptongo e hiato."""
    p = palabra.lower().replace("qu", "q").replace("gue", "ge").replace("gui", "gi")
    p = re.sub(r"y$", "i", p)
    n, previa = 0, None
    for c in p:
        if c in FUERTES or c in DEBILES or c in DEBILES_TILDE:
            if previa is None:
                n += 1
            else:
                # diptongo: débil átona con cualquier vocal; hiato: fuerte+fuerte o débil tónica
                if (previa in FUERTES and c in FUERTES) or c in DEBILES_TILDE or previa in DEBILES_TILDE:
                    n += 1
            previa = c
        else:
            previa = None
    return max(n, 1)


def legibilidad(texto):
    pals = palabras(texto)
    ors = oraciones(texto)
    if not pals or not ors:
        return {}
    n_p, n_o = len(pals), len(ors)
    n_s = sum(silabas(p) for p in pals)
    return {
        "palabras": n_p,
        "oraciones": n_o,
        "palabras_por_oracion": n_p / n_o,
        "silabas_por_palabra": n_s / n_p,
        # Fernández Huerta (1959) con la corrección que propone Law (2011): el último
        # término es la longitud media de la oración, no el número de oraciones por 100 palabras
        "fernandez_huerta": 206.84 - 0.60 * (100 * n_s / n_p) - 1.02 * (n_p / n_o),
        # Perspicuidad de Szigriszt Pazos (1993) en la formulación de Barrio-Cantalejo
        # et al. (2008), con 206,835 en lugar del 207 original; se interpreta con INFLESZ
        "szigriszt": 206.835 - 62.3 * (n_s / n_p) - (n_p / n_o),
        "prop_palabras_largas": sum(silabas(p) >= 4 for p in pals) / n_p,
    }


def inflesz(valor):
    if valor <= 40:
        return "muy difícil"
    if valor <= 55:
        return "algo difícil"
    if valor <= 65:
        return "normal"
    if valor <= 80:
        return "bastante fácil"
    return "muy fácil"


# ---------------------------------------------------------------- normalización

NUMERALES = {"un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
             "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
             "doce": 12, "catorce": 14, "quince": 15, "veinte": 20, "veinticuatro": 24,
             "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "cien": 100,
             "mil": 1000, "media": 0.5, "medio": 0.5}


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def norm(t):
    return sin_tildes(t.lower())


def cantidades(texto):
    """Multiconjunto de valores numéricos (cifras y numerales en letra)."""
    t = norm(texto)
    valores = []
    for m in re.finditer(r"\d+(?:[.,]\d+)*", t):
        s = m.group()
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):   # 6.000
            valores.append(float(s.replace(".", "")))
        elif re.fullmatch(r"\d+([.,]\d+)?", s):     # 2,5
            valores.append(float(s.replace(",", ".")))
        else:                                          # 2.5.7: numeración, se toma cada parte
            valores.extend(float(x) for x in re.split(r"[.,]", s) if x)
    for w in re.findall(r"[a-z]+", t):
        if w in NUMERALES and w not in {"un", "una", "uno"}:  # «un» suele ser artículo
            valores.append(float(NUMERALES[w]))
    return valores


# ---------------------------------------------------------------- inventarios

NEGACION = re.compile(r"\b(no|nunca|jamas|tampoco|ningun[oa]?s?|nada|ni)\b")
PROHIBICION = re.compile(r"\bno\s+(se\s+)?(debe|deberia|tome|tomar|use|usar|utilice|utilizar|"
                         r"administre|conduzca|beba|aplique|deje|interrumpa|se\s+recomienda|"
                         r"combine|mezcle|exceda|supere|aumente|duplique)")
DEONTICA_FUERTE = re.compile(r"\b(debe|deben|debera|deberan|tiene que|tienen que|es necesario|"
                             r"es imprescindible|es obligatorio|obligatoriamente|siempre)\b")
DEONTICA_DEBIL = re.compile(r"\b(se recomienda|es recomendable|es aconsejable|se aconseja|conviene|"
                            r"es mejor|seria mejor|intente|procure|es preferible|debería|deberia)\b")
EPISTEMICA = re.compile(r"\b(puede[n]?|podria[n]?|es posible|posiblemente|a veces|en algunos casos|"
                        r"en ocasiones|ocasionalmente|probablemente|raramente|quizas?|tal vez)\b")
CONDICION = re.compile(r"\b(si|en caso de|cuando|salvo|excepto|a menos que|siempre que|"
                       r"mayores de|menores de|antes de|despues de)\b")
DIRECTIVA = re.compile(r"\b(consulte|consultar|informe|informar|comunique|acuda|acudir|llame|llamar|"
                       r"contacte|contactar|avise|hable con|hablar con|pida ayuda|busque ayuda|"
                       r"deje de|dejar de|interrumpa|interrumpir|suspenda|vaya al)\b")
FRECUENCIAS = {
    "muy_frecuentes": re.compile(r"\bmuy frecuentes?\b|mas de 1 de cada 10\b"),
    "frecuentes": re.compile(r"(?<!muy )(?<!poco )\bfrecuentes?\b|hasta 1 de cada 10\b"),
    "poco_frecuentes": re.compile(r"\bpoco frecuentes?\b|hasta 1 de cada 100\b"),
    "raros": re.compile(r"(?<!muy )\braros?\b|\braras?\b|hasta 1 de cada 1\.?000\b"),
    "muy_raros": re.compile(r"\bmuy raros?\b|hasta 1 de cada 10\.?000\b"),
    "no_conocida": re.compile(r"frecuencia no conocida|no puede estimarse"),
}
CIFRA_FRECUENCIA = re.compile(r"\b1 de cada [\d.]+\b")


def cuenta(regex, texto):
    return len(regex.findall(norm(texto)))


# ---------------------------------------------------------------- comparación

def detectores(original, salida, nombre_medicamento="", principio_activo=""):
    """Devuelve banderas por categoría (True = posible pérdida) y los recuentos."""
    o, s = norm(original), norm(salida)
    res = {}

    # NUM: cantidades del original que no aparecen en la salida (multiconjunto)
    q_o, q_s = cantidades(original), cantidades(salida)
    restantes = list(q_s)
    perdidas = []
    for v in q_o:
        if v in restantes:
            restantes.remove(v)
        else:
            perdidas.append(v)
    res["num_original"], res["num_perdidas"], res["num_nuevas"] = len(q_o), len(perdidas), len(restantes)
    res["flag_NUM"] = bool(perdidas) or bool(restantes)

    # FREC: cambia el número de menciones de alguna categoría de frecuencia o de sus cifras
    cambios = sum(len(r.findall(o)) != len(r.findall(s)) for r in FRECUENCIAS.values())
    res["frec_categorias_alteradas"] = cambios
    res["frec_cifras_perdidas"] = max(0, len(CIFRA_FRECUENCIA.findall(o)) - len(CIFRA_FRECUENCIA.findall(s)))
    res["flag_FREC"] = cambios > 0 or res["frec_cifras_perdidas"] > 0

    # POL: pérdida de prohibiciones o de negaciones
    for nombre, regex in [("neg", NEGACION), ("proh", PROHIBICION)]:
        res[f"{nombre}_original"], res[f"{nombre}_salida"] = cuenta(regex, original), cuenta(regex, salida)
    res["flag_POL"] = res["proh_salida"] < res["proh_original"] or res["neg_salida"] < res["neg_original"]

    # MOD-D: menos marcas deónticas fuertes o más atenuadas
    res["deon_fuerte_original"], res["deon_fuerte_salida"] = cuenta(DEONTICA_FUERTE, original), cuenta(DEONTICA_FUERTE, salida)
    res["deon_debil_original"], res["deon_debil_salida"] = cuenta(DEONTICA_DEBIL, original), cuenta(DEONTICA_DEBIL, salida)
    res["flag_MOD_D"] = (res["deon_fuerte_salida"] < res["deon_fuerte_original"]
                         or res["deon_debil_salida"] > res["deon_debil_original"])

    # MOD-E: pérdida de marcas de posibilidad
    res["epis_original"], res["epis_salida"] = cuenta(EPISTEMICA, original), cuenta(EPISTEMICA, salida)
    res["flag_MOD_E"] = res["epis_salida"] < res["epis_original"]

    # COND: pérdida de marcas condicionales o de alcance
    res["cond_original"], res["cond_salida"] = cuenta(CONDICION, original), cuenta(CONDICION, salida)
    res["flag_COND"] = res["cond_salida"] < res["cond_original"]

    # DIR: pérdida de instrucciones de actuación
    res["dir_original"], res["dir_salida"] = cuenta(DIRECTIVA, original), cuenta(DIRECTIVA, salida)
    res["flag_DIR"] = res["dir_salida"] < res["dir_original"]

    # ENT: el principio activo aparece en el original y no en la salida
    pa = norm(principio_activo).split(",")[0].strip()
    res["flag_ENT"] = bool(pa) and pa in o and pa not in s
    return res
