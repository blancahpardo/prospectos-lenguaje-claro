# Guía de anotación de errores de fidelidad en la simplificación de prospectos

Versión 0.2 — 16/10/2026 (0.1: 24/09/2026; la 0.2 añade los indicadores REG y DEG)

## 1. Objeto

Se anota cada par (pasaje original del prospecto, versión simplificada por un modelo). La pregunta que guía la anotación es: **¿podría una persona que solo lea la versión simplificada tomar una decisión sobre su medicación distinta de la que tomaría con el original?**

No se evalúa si el original es claro ni si la versión simplificada está bien escrita en general. Solo se anotan las **desviaciones de contenido** respecto del original y, aparte, dos indicadores de simplificación fallida (§5).

## 2. Unidad y procedimiento

1. Leer el pasaje original entero y localizar las **unidades de información críticas**: dosis, intervalos, duraciones, edades y otros umbrales; contraindicaciones; advertencias; instrucciones ("consulte a su médico", "deje de tomar"); interacciones; efectos adversos y su frecuencia.
2. Leer la versión simplificada y alinear cada unidad crítica con su expresión en la salida (o con su ausencia).
3. Anotar cada desviación como un **error** con: categoría (§3), fragmento del original, fragmento de la salida (vacío si es una omisión) y gravedad (§4).
4. Un mismo fragmento puede tener más de una etiqueta si hay más de un fenómeno (p. ej., omisión de la condición y cambio de fuerza modal en la misma oración).

## 3. Tipología

La tipología combina el eje de operación de Devaraj et al. (2022) —omisión, adición y sustitución— con categorías lingüísticas propias del género prospecto. Cada error lleva **una categoría lingüística**, y la operación se deduce de ella o se marca aparte.

| Código | Categoría | Definición | Ejemplo (original → salida) |
|---|---|---|---|
| **POL** | Polaridad | Se pierde, se añade o se invierte una negación, o una prohibición pasa a ser permiso. | *No tome X si está embarazada* → *Tome X si está embarazada* |
| **MOD-D** | Fuerza deóntica | Cambia la fuerza de una obligación o prohibición: se debilita (*debe → puede, es recomendable*) o se refuerza. | *No debe conducir* → *Es mejor que no conduzca* |
| **MOD-E** | Modalidad epistémica | Cambia el grado de certeza: una posibilidad pasa a ser un hecho o al revés, o se pierde un atenuador. | *Puede producir somnolencia* → *Produce somnolencia* |
| **COND** | Condición y alcance | Se omite, se añade o se altera una condición o su alcance (a quién se aplica, en qué circunstancia), o cambia un cuantificador. | *Si tiene más de 65 años, …* → (omitido); *algunos pacientes* → *los pacientes* |
| **NUM** | Cantidades | Cambia o se omite una dosis, unidad, intervalo, duración, número de tomas, umbral de edad o de peso. | *cada 8 horas* → *3 veces al día, con las comidas* (el *con las comidas* es añadido) |
| **FREC** | Frecuencia de efectos adversos | Se altera, se omite o se reasigna una categoría de frecuencia (muy frecuentes, frecuentes, poco frecuentes, raros, muy raros, frecuencia no conocida) o su cifra (*1 de cada 10*). | Mover un efecto de *raros* a *frecuentes*; suprimir las cifras |
| **TERM** | Terminología | Un término se sustituye por uno no equivalente: hiperónimo que borra una distinción relevante, falso sinónimo o explicación errónea. | *anticoagulantes orales* → *medicamentos*; *hipotensión* → *mareo* |
| **ENT** | Entidades | Se confunde, se omite o se añade un medicamento, principio activo, grupo farmacológico, órgano o profesional. | Omitir uno de los fármacos de una lista de interacciones |
| **DIR** | Instrucción de actuación | Se omite o se altera una instrucción dirigida al paciente (consultar, acudir a urgencias, suspender, informar). | *Deje de tomarlo y acuda al médico* → *Consulte a su médico* |
| **ADD** | Adición no sustentada | Información que no está en el original (alucinación extrínseca) y que no entra en otra categoría. | Añadir una recomendación dietética |
| **OMI** | Omisión de otra información | Omisión de contenido del original que no entra en las categorías anteriores. | Suprimir la explicación de para qué sirve un componente |

**Precedencia:** si un error encaja en una categoría específica (POL a DIR), se usa esa y no ADD u OMI.

## 4. Gravedad

| Nivel | Criterio |
|---|---|
| **0 — Sin repercusión** | La desviación no cambia ninguna decisión posible del paciente (p. ej., se omite una redundancia). |
| **1 — Menor** | Se pierde o altera información útil, pero sin riesgo previsible para la seguridad. |
| **2 — Relevante para la seguridad** | Podría llevar a un uso incorrecto del medicamento: dosis o frecuencia erróneas, ignorar una contraindicación, no buscar ayuda ante un efecto grave o tomarlo cuando no se debe. |

En caso de duda entre 1 y 2, se anota **2** y se añade un comentario.

## 5. Indicadores de simplificación fallida (no son errores de fidelidad)

- **TEC**: se conserva un tecnicismo sin explicar cuando el original tampoco lo explica (fallo de simplificación, no de fidelidad).
- **NOSIMP**: la salida es prácticamente igual al original o más compleja.
- **REG**: la salida cambia el tratamiento de *usted* por el tuteo, total o parcialmente (añadido durante la anotación, 16/10/2026).
- **DEG**: la salida degenera en repeticiones o texto sin relación con el original (además de anotar los errores que contenga).

## 6. Salida no válida

Si la salida no es una simplificación (respuesta en otra lengua, texto truncado, comentario del modelo sobre la tarea, rechazo), se marca como **INVÁLIDA** y no se anota más.

## 7. Formato de anotación

Una fila por error en `anotaciones.csv`:

`id_salida, categoria, operacion (OMI/ADD/SUS), fragmento_original, fragmento_salida, gravedad, comentario`

Las salidas sin errores se registran con una fila con `categoria = NINGUNO`.

## 8. Acuerdo entre anotadores

- Las salidas de 9 de los 30 pasajes de la muestra (3 por sección; 72 de 240 salidas, un 30 %) se anotan de forma independiente por una segunda persona. La anotación es ciega: la hoja no muestra el modelo ni la instrucción.
- Se calcula el acuerdo a dos niveles: (a) presencia o ausencia de cada categoría por salida (κ de Cohen por categoría), y (b) gravedad máxima por salida (α de Krippendorff ordinal).
- Los desacuerdos se discuten y se resuelven para la versión final; la guía se actualiza con los casos límite.

## Casos límite (se ampliarán durante el piloto)

- Cambiar *médico o farmacéutico* por *médico*: **ENT**, gravedad 1.
- Reformular *muy frecuentes (pueden afectar a más de 1 de cada 10 personas)* como *muy frecuentes*: **FREC** (omisión de la cifra), gravedad 1. Si se suprime la categoría entera y los efectos pasan a una lista sin frecuencia: gravedad 2 cuando la lista mezcla efectos graves y leves.
- Convertir *no se recomienda* en *no debe*: **MOD-D** (refuerzo), gravedad 0 o 1.
