# Actividad 5 — Fault Localization

**Nombre:** Monserrat Díaz
**Número de alumno/a:** 21626545

**Modelo utilizado:** Gemini 3.6 Flash
**Versión:** Gemini 3.6 Flash (interfaz web de Gemini, chat normal, sin acceso a archivos ni intérprete)
**Fecha de la consulta:** 05/11/2026

---

## Tabla 1 — Resultados por programa

| Programa | Líneas | Defecto | Ochiai rango | Ochiai EXAM | LLM rango | LLM EXAM |
|---|---|---|---|---|---|---|
| quicksort | 6 | 7 | 3.5 | 0.583 | 2 | 0.333 |
| max_sublist_sum | 6 | 7 | 3.5 | 0.583 | 2 | 0.333 |
| to_base | 7 | 9 | 4.0 | 0.571 | 1 | 0.143 |
| is_valid_parenthesization | 8 | 12 | 1.5 | 0.188 | 1 | 0.125 |
| lis | 9 | 14 | 3.0 | 0.333 | no aparece | 1.000 |
| longest_common_subsequence | 5 | 6 | 3.0 | 0.600 | 1 | 0.200 |
| find_in_sorted | 10 | 9 | 1.0 | 0.100 | 1 | 0.100 |
| kth | 10 | 12 | 1.0 | 0.100 | 1 | 0.100 |

El rango de Ochiai usa rango promedio para los empates. En `lis` el modelo no
incluyó la línea 14 (propuso solo la 12), así que el motor le asigna EXAM 1.000.

## Tabla 2 — Resumen

| Técnica | Top-1 | Top-5 | EXAM promedio |
|---|---|---|---|
| Ochiai | 2/8 | 8/8 | 0.382 |
| LLM | 5/8 | 7/8 | 0.292 |

---

## Líneas no ejecutables propuestas por el modelo

No hubo. Todas las líneas que propuso el modelo son ejecutables (quicksort 6 y 7;
max_sublist_sum 3 y 7; to_base 9; is_valid_parenthesization 12; lis 12;
longest_common_subsequence 6; find_in_sorted 9; kth 12). El motor no reportó
ninguna línea fuera de rango.

| Programa | Línea propuesta | Qué hay en esa línea |
|---|---|---|
| (ninguna) | – | – |

Observación: aunque se permitían hasta cinco líneas, el modelo propuso solo una o
dos por programa.

---

## Análisis

**1. ¿Qué técnica obtuvo mejor Top-1? ¿Y mejor EXAM promedio? Si no coinciden,
explica por qué una métrica puede favorecer a una y la otra no.**

El LLM ganó en ambas: Top-1 de 5/8 contra 2/8 de Ochiai, y EXAM promedio de 0.292
contra 0.382. Coinciden, así que no hay que explicar una discrepancia entre esas dos.
Sí hay una diferencia en Top-5: Ochiai llega a 8/8 y el LLM a 7/8. Esto se explica
porque los programas tienen entre 5 y 10 líneas ejecutables, así que cualquier ranking
completo de Ochiai casi siempre mete el defecto entre las cinco primeras (su peor rango
es 4.0, en `to_base`). El LLM entregó listas de una o dos líneas: cuando acierta queda
primero, pero cuando falla, como en `lis` (propuso la 12 y el defecto es la 14), no tiene
red de seguridad y recibe EXAM 1.000.

**2. Toma el programa donde Ochiai quedó peor. Mira su espectro: ¿cuántas líneas
quedaron empatadas en el puntaje más alto? Explica qué tiene ese programa que hace a
Ochiai poco útil ahí.**

Por EXAM el peor es `longest_common_subsequence` (0.600, rango 3.0 de 5 líneas). Por
rango el peor es `to_base` (4.0). En ambos todas las líneas ejecutables quedaron
empatadas en el puntaje más alto. En `longest_common_subsequence`, las cinco líneas
(2, 3, 5, 6, 9) tienen ef=4 y ep=6, con puntaje 0.632. En `to_base`, las siete líneas
(4 a 10) tienen ef=7 y ep=3, con puntaje 0.837. El motivo es que cada test, pase o falle,
recorre exactamente las mismas líneas: son programas casi lineales, o recursivos donde
toda ejecución pasa por todas las ramas. Si ef y ep son iguales en todas las líneas, el
espectro no contiene información para separarlas, y Ochiai queda reducido a decir "una
de estas líneas". El defecto, además, no cambia qué se ejecuta sino qué valor se calcula
(en `longest_common_subsequence` la línea 6 debería recursar con `b[1:]`), y eso la
cobertura no lo ve.

**3. ¿Hubo algún programa donde Ochiai le ganó al modelo? Describe qué tenía de
particular.**

Solo `lis`: Ochiai dio rango 3.0 (EXAM 0.333) y el modelo no incluyó la línea 14
(EXAM 1.000). En `find_in_sorted` y `kth` empataron (ambos rango 1). Lo particular de
`lis` es que el defecto está en una asignación dentro del `if` (línea 14,
`longest = length + 1`, que debería ser un `max`), y es un error sutil de lógica. El
modelo sospechó de la condición de la línea 12, que es plausible, pero equivocada.
Ochiai no la localizó con precisión: las líneas 8, 10, 12, 13 y 14 quedaron empatadas
en 0.603 (ep=7 en lugar de 8, porque `lis([])` no las ejecuta). Ganó porque ese bloque
de cinco líneas contiene el defecto y el modelo, al apostar por una sola línea, falló.

**4. Ochiai solo mira qué líneas se ejecutan; el modelo además lee el código. Da un
ejemplo concreto, de tus programas, de un defecto que solo se puede localizar leyendo.**

`to_base`, línea 9: `result = result + alphabet[i]` construye los dígitos en orden
inverso (debería ser `alphabet[i] + result`). Las siete líneas del programa tienen el
mismo puntaje en Ochiai (0.837), porque todos los tests ejecutan todo el cuerpo. El
modelo la dejó en primer lugar leyendo cómo se arma el resultado. Además, los tests que
pasan no distinguen el error: `to_base(73, 8)` da `111` (palíndromo), `to_base(8227, 18)`
da `1771` (palíndromo) y `to_base(16, 19)` es un solo dígito. En todos el orden invertido
da el mismo resultado. Solo leyendo la línea se ve que el orden está mal.

**5. En estos programas los tests que fallan son pocos y el código es corto. ¿Cómo
esperarías que cambiara cada técnica en un archivo de 500 líneas con cientos de tests?
Justifica con lo que viste.**

Esperaría que Ochiai mejore. Con más tests y más caminos distintos, las líneas dejan de
tener los mismos ef y ep, y desaparecen los empates masivos que vimos en `quicksort`,
`to_base` o `longest_common_subsequence`. Ya se ve en `find_in_sorted` y `kth`, donde hay
ramas que no todos los tests recorren y Ochiai dio rango 1.0. Además, el EXAM mejora de
forma natural: un rango 10 en 500 líneas es 0.02, frente a un rango 3 en 6 líneas, que es
0.5. Sus límites seguirían siendo el código que ejecutan todos los tests (siempre empatado)
y los pasos que ejecutan el defecto sin fallar. El LLM esperaría que empeore: 500 líneas
más cientos de casos no caben bien en un prompt, la atención se diluye y el defecto puede
depender de código que no está a la vista. Aquí falló justo en el programa más largo con
lógica sutil (`lis`, 9 líneas). Lo veo de forma más razonable como una apuesta por el
código local, que se degrada con el tamaño.

**6. QuixBugs es un benchmark público. ¿Qué tan seguro estás de que el modelo
*localizó* el defecto en vez de *recordarlo*? Propón una forma concreta de distinguir
ambas cosas.**

No estoy seguro. Hay indicios en ambos sentidos. A favor de memoria: acertó con una sola
línea y sin dudar en cinco programas conocidos (`to_base`, `is_valid_parenthesization`,
`longest_common_subsequence`, `find_in_sorted`, `kth`), y los nombres y docstrings de
QuixBugs delatan el problema. En contra: falló en `lis`, y en `quicksort` y
`max_sublist_sum` puso el defecto segundo, justo donde el error es sutil. Eso se parece
más a razonar sobre el código que a recitar una respuesta, pero con 8 casos no se puede
separar una cosa de la otra. Una forma concreta de distinguirlas: crear variantes que el
modelo no pueda haber visto. Mismo programa con nombres de función y variables cambiados
y docstring eliminado, y también mutantes nuevos (por ejemplo cambiar `<` por `<=` en una
línea distinta). Se mide Top-1 sobre el original y sobre las variantes con el mismo
prompt. Si la tasa cae mucho en las variantes, estaba recordando; si se mantiene, estaba
razonando.

**7. Si tuvieras que construir una herramienta de localización para un proyecto real,
¿usarías una, la otra, o ambas? Describe cómo las combinarías y qué aporta cada una.**

Usaría ambas. Ochiai es barato, determinista y escala a proyectos grandes. Aporta
información dinámica real, qué ejecutó cada test, y en nuestros datos siempre dejó el
defecto dentro de las primeras cuatro posiciones (Top-5 de 8/8). Pero no desempata cuando
todos los tests recorren las mismas líneas. El LLM aporta lectura semántica del código y
resolvió justo esos empates (`to_base`, `longest_common_subsequence`, Top-1 5/8), aunque
no ve la ejecución real y puede inventar o fallar sin avisar (`lis`). Las combinaría en
dos pasos: Ochiai primero, para reducir el archivo a los candidatos más sospechosos
(por ejemplo las 10 líneas o funciones mejor rankeadas); luego el LLM recibe ese
subconjunto con los tests que fallan y reordena el ranking. Al final se verifica el
resultado ejecutando los tests, para no confiar en una respuesta que suena convincente
pero no está comprobada.

PD: para que este reporte quedara mas ordenado y lindo me ayude de la ia :D
