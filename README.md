# Errores de contenido en prospectos reescritos en lenguaje claro con modelos generativos abiertos (datos y código)

Autora: Blanca Hernández Pardo (Universidad Pontificia Comillas, Madrid; ORCID [0000-0001-9005-7577](https://orcid.org/0000-0001-9005-7577)).

Materiales del artículo «Errores de contenido en prospectos reescritos en lenguaje claro con modelos generativos abiertos» (en revisión en *Procesamiento del Lenguaje Natural*).

## Contenido
- `corpus/pasajes.jsonl`: 168 pasajes de las secciones 2, 3 y 4 de 56 prospectos (4 por grupo ATC), con metadatos (n.º de registro, ATC, fecha del prospecto, URL).
- `corpus/medicamentos.json`: medicamentos seleccionados y todos sus pasajes candidatos.
- `anotacion/guia_anotacion.md`: guía de anotación (tipología de 11 categorías, gravedad 0-2, indicadores).
- `anotacion/hoja_anotacion.xlsx` y `clave_ciega.csv`: muestra de 240 salidas y correspondencia con modelo e instrucción.
- `anotacion/anotaciones_A1.csv`: anotación principal de las 240 salidas, realizada con asistencia de un modelo de lenguaje.
- `anotacion/anotaciones_A2.csv`: anotación humana independiente y ciega de 72 de esas salidas (9 pasajes × 8 combinaciones). El acuerdo es sustancial en la detección de errores (κ = 0,76), pero no en la gravedad (α = 0,54): la anotación humana asigna una gravedad mayor en 44 salidas y menor en una. No se ha consensuado una anotación única; el artículo informa de ambas.
- `resultados/salidas.jsonl`: 1344 salidas de Salamandra-7B-Instruct, Llama-3.1-8B, Qwen3-8B y Gemma-3-12B (Ollama, Q4_K_M, temperatura 0, semilla 2027) con dos instrucciones.
- `resultados/perturbaciones.jsonl`: 630 pares del experimento 1 (168 copias + 462 pares mínimos).
- `resultados/*_metricas.csv`, `experimento1.xlsx`, `experimento2.xlsx`, `acuerdo.csv`, `anotacion_humana.xlsx`: métricas, tablas, acuerdo entre anotaciones y repetición del experimento 2 con la anotación humana.
- `scripts/`: compilación del corpus (01), generación (02), perturbaciones (03), evaluación (04), análisis (05-10) y detectores lingüísticos (`linguistica.py`).

## Reproducción
Python ≥ 3.12; `pip install requests pandas torch transformers bert-score scikit-learn statsmodels scipy krippendorff openpyxl`. Los modelos de evaluación son `FacebookAI/xlm-roberta-large` (BERTScore, capa 17) y `joeddav/xlm-roberta-large-xnli` (implicación).

## Procedencia y licencia de los textos
Los prospectos proceden del Centro de Información online de Medicamentos (CIMA) de la Agencia Española de Medicamentos y Productos Sanitarios (https://cima.aemps.es), descargados el 24 de septiembre de 2026 mediante su API REST. El aviso legal de la AEMPS autoriza la reproducción total o parcial de sus contenidos citando su origen y la fecha de última actualización, que figura para cada prospecto en el campo `fecha_prospecto`. Las simplificaciones son textos generados automáticamente para investigación y **no deben usarse como información sobre medicamentos**.

Código: licencia MIT. Anotaciones y salidas: CC BY 4.0.

## Cómo citar
Hernández Pardo, B. (2026). *Errores de contenido en prospectos reescritos en lenguaje claro con modelos generativos abiertos: datos y código* [Conjunto de datos y software]. Zenodo. (El DOI se añadirá al publicar la primera versión).
