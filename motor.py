"""Motor de la Actividad 5 - Fault Localization.

Tres piezas:

  1. Espectro. Ejecuta cada caso de prueba trazando que lineas recorrio, y
     arma la matriz test x linea junto con el veredicto de cada test.

  2. Metricas. Top-1, Top-5 y EXAM score sobre un ranking de lineas
     sospechosas, venga de donde venga.

  3. Prompts y evaluacion de lo que responda el modelo.

NO MODIFICAR.
"""

import ast
import importlib.util
import inspect
import json
import math
import os
import re
import signal
import sys

PROGRAMAS = ["quicksort", "max_sublist_sum", "to_base",
             "is_valid_parenthesization", "lis",
             "longest_common_subsequence", "find_in_sorted", "kth"]

# Linea que contiene el defecto en cada programa, respecto del archivo tal como
# viene en programas/. Es la unica diferencia con la version correcta.
LINEA_DEFECTO = {
    "find_in_sorted": 9,
    "is_valid_parenthesization": 12,
    "kth": 12,
    "lis": 14,
    "longest_common_subsequence": 6,
    "max_sublist_sum": 7,
    "quicksort": 7,
    "to_base": 9,
}

TIMEOUT = 3
RESULTADOS = {}


# ==========================================================================
# 0. Carga
# ==========================================================================

def ruta_programa(nombre):
    return os.path.join("programas", nombre + ".py")


def fuente(nombre):
    return open(ruta_programa(nombre), encoding="utf-8").read()


def cargar(nombre):
    ruta = ruta_programa(nombre)
    alias = "prog_" + nombre
    if alias in sys.modules:
        del sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, nombre)


def lineas_ejecutables(nombre):
    """Lineas de la funcion que pueden ejecutarse. Excluye la firma, el
    docstring final de QuixBugs y las lineas en blanco."""
    texto = fuente(nombre)
    arbol = ast.parse(texto)
    objetivo = next((n for n in arbol.body
                     if isinstance(n, ast.FunctionDef) and n.name == nombre), None)
    if objetivo is None:
        return []
    salida = set()
    for n in ast.walk(objetivo):
        if isinstance(n, ast.stmt) and n is not objetivo:
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) \
                    and isinstance(n.value.value, str):
                continue
            salida.add(n.lineno)
    return sorted(salida)


def casos(nombre):
    salida = []
    with open(os.path.join("casos", nombre + ".json"), encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.strip()
            if not linea:
                continue
            try:
                caso = json.loads(linea)
            except Exception:
                continue
            if isinstance(caso, list) and len(caso) == 2:
                args, esperado = caso
                if not isinstance(args, list):
                    args = [args]
                salida.append((args, esperado))
    return salida


# ==========================================================================
# 1. Espectro
# ==========================================================================

class _Timeout(Exception):
    pass


def _alarma(s, f):
    raise _Timeout()


def _normalizar(x):
    if hasattr(x, "__next__"):
        return list(x)
    if isinstance(x, tuple):
        return list(x)
    return x


def espectro(nombre):
    """Devuelve dict con: lineas, tests (lista de dicts con 'pasa' y 'lineas'),
    y los conteos ef/ep por linea."""
    fn = cargar(nombre)
    ruta = os.path.abspath(ruta_programa(nombre))
    validas = set(lineas_ejecutables(nombre))
    tests = []

    usar_alarma = hasattr(signal, "SIGALRM")
    if usar_alarma:
        previo = signal.signal(signal.SIGALRM, _alarma)

    for args, esperado in casos(nombre):
        vistas = set()

        def traza(frame, evento, arg):
            if evento == "line" and frame.f_code.co_filename == ruta:
                if frame.f_lineno in validas:
                    vistas.add(frame.f_lineno)
            return traza

        copia = json.loads(json.dumps(args))
        anterior = sys.gettrace()
        if usar_alarma:
            signal.alarm(TIMEOUT)
        sys.settrace(traza)
        try:
            obtenido = _normalizar(fn(*copia))
            pasa = obtenido == _normalizar(esperado)
        except Exception:
            pasa = False
        finally:
            sys.settrace(anterior)
            if usar_alarma:
                signal.alarm(0)
        tests.append({"args": args, "pasa": pasa, "lineas": sorted(vistas)})

    if usar_alarma:
        signal.signal(signal.SIGALRM, previo)

    nf = sum(1 for t in tests if not t["pasa"])
    np_ = sum(1 for t in tests if t["pasa"])
    ef, ep = {}, {}
    for l in sorted(validas):
        ef[l] = sum(1 for t in tests if not t["pasa"] and l in t["lineas"])
        ep[l] = sum(1 for t in tests if t["pasa"] and l in t["lineas"])
    return {"programa": nombre, "lineas": sorted(validas), "tests": tests,
            "nf": nf, "np": np_, "ef": ef, "ep": ep}


def resumen_espectros(mostrar=True):
    datos = {}
    for n in PROGRAMAS:
        datos[n] = espectro(n)
    if mostrar:
        print("%-28s %7s %7s %8s %8s" % ("programa", "pasan", "fallan",
                                         "lineas", "defecto"))
        for n in PROGRAMAS:
            e = datos[n]
            print("%-28s %7d %7d %8d %8s"
                  % (n, e["np"], e["nf"], len(e["lineas"]),
                     LINEA_DEFECTO.get(n, "?")))
        malos = [n for n in PROGRAMAS if datos[n]["nf"] == 0 or datos[n]["np"] == 0]
        if malos:
            print("\n[ERROR] sin mezcla de tests que pasan y fallan: %s"
                  % ", ".join(malos))
        else:
            print("\n[OK] los 8 programas tienen tests que pasan y tests que fallan.")
    return datos


# ==========================================================================
# 2. Metricas
# ==========================================================================

def metricas(ranking, culpable, total_lineas, puntajes=None):
    """ranking: lista de lineas ordenada de mas a menos sospechosa.

    Si se entregan los puntajes, los empates se resuelven con el RANGO
    PROMEDIO. Es la convencion habitual y la justa: una formula que deja diez
    lineas empatadas en primer lugar no deberia contar como acierto de Top-1
    solo porque el defecto tiene el numero de linea mas bajo.

    Para un ranking que el modelo entrego ya ordenado no hay empates que
    resolver, y se usa la posicion tal cual."""
    if culpable not in ranking:
        return {"top1": False, "top5": False, "exam": 1.0, "rango": None}
    if puntajes:
        pos = rango_promedio(puntajes, culpable)
    else:
        pos = ranking.index(culpable) + 1
    return {"top1": pos <= 1, "top5": pos <= 5,
            "exam": round(pos / total_lineas, 3),
            "rango": pos if isinstance(pos, int) else round(pos, 1)}


def ranking_desde_puntajes(puntajes):
    """Ordena de mayor a menor puntaje. Los empates se desempatan por numero
    de linea, lo que es neutral: no favorece ni castiga al defecto."""
    return [l for l, _ in sorted(puntajes.items(), key=lambda kv: (-kv[1], kv[0]))]


def rango_promedio(puntajes, culpable):
    """Rango del culpable contando los empates como un bloque."""
    if culpable not in puntajes:
        return None
    s = puntajes[culpable]
    mejores = sum(1 for v in puntajes.values() if v > s)
    empatados = sum(1 for v in puntajes.values() if v == s)
    return mejores + (empatados + 1) / 2


# ==========================================================================
# 3. SBFL del alumno
# ==========================================================================

def evaluar_sbfl(mostrar=True):
    import sbfl
    importlib.reload(sbfl)
    try:
        sbfl.ochiai(espectro(PROGRAMAS[0]))
    except NotImplementedError:
        print("[PENDIENTE] ochiai() todavia no esta implementada en sbfl.py.")
        print("            Abre el archivo y completa la formula; Tarantula")
        print("            esta resuelta ahi como ejemplo del contrato.")
        return []
    except Exception as exc:
        print("[ERROR] ochiai() lanzo %s: %s" % (type(exc).__name__, exc))
        return []

    filas = []
    for n in PROGRAMAS:
        e = espectro(n)
        culpable = LINEA_DEFECTO[n]
        try:
            puntajes = sbfl.ochiai(e)
        except Exception as exc:
            filas.append({"programa": n,
                          "error": "ochiai() fallo con %s" % type(exc).__name__})
            continue
        if not isinstance(puntajes, dict) or not puntajes:
            filas.append({"programa": n, "error": "ochiai() no devolvio un dict"})
            continue
        rank = ranking_desde_puntajes(puntajes)
        m = metricas(rank, culpable, len(e["lineas"]), puntajes)
        m["programa"] = n
        m["lineas"] = len(e["lineas"])
        filas.append(m)
    RESULTADOS["sbfl"] = filas
    if mostrar:
        _imprimir_filas("SBFL (Ochiai)", filas)
    return filas


def _imprimir_filas(titulo, filas):
    print(titulo)
    print("-" * 70)
    print("  %-28s %6s %7s %7s %7s" % ("programa", "rango", "Top-1", "Top-5", "EXAM"))
    for f in filas:
        if "error" in f:
            print("  %-28s %s" % (f["programa"], f["error"]))
            continue
        print("  %-28s %6s %7s %7s %7.3f"
              % (f["programa"], f.get("rango", "-"),
                 "si" if f["top1"] else "no", "si" if f["top5"] else "no",
                 f["exam"]))
    buenos = [f for f in filas if "error" not in f]
    if buenos:
        print("-" * 70)
        print("  Top-1: %d/%d   Top-5: %d/%d   EXAM promedio: %.3f"
              % (sum(f["top1"] for f in buenos), len(buenos),
                 sum(f["top5"] for f in buenos), len(buenos),
                 sum(f["exam"] for f in buenos) / len(buenos)))


# ==========================================================================
# 4. Prompt y evaluacion del modelo
# ==========================================================================

INSTRUCCION = """You are debugging a program. Exactly ONE line contains a bug.

Below you get the source code with line numbers, the test cases that PASS and \
the test cases that FAIL.

Rank the lines by how likely they are to contain the bug, most likely first. \
Give at most 5 line numbers.

Answer with a JSON object and nothing else, mapping each program name to its \
ranked list of line numbers:

  {"nombre_programa": [12, 7, 9], ...}
"""


def _numerar(texto):
    lineas = texto.splitlines()
    ancho = len(str(len(lineas)))
    return "\n".join("%*d | %s" % (ancho, i, l) for i, l in enumerate(lineas, 1))


def mostrar_prompt():
    print("=" * 78)
    print("COPIA DESDE LA SIGUIENTE LINEA HASTA EL FINAL, EN UN CHAT NUEVO")
    print("=" * 78)
    print()
    print(INSTRUCCION)
    for n in PROGRAMAS:
        e = espectro(n)
        print("-" * 70)
        print("### %s" % n)
        print()
        print("```python")
        print(_numerar(fuente(n).rstrip()))
        print("```")
        print()
        pasan = [t for t in e["tests"] if t["pasa"]]
        fallan = [t for t in e["tests"] if not t["pasa"]]
        print("PASSING tests (%d):" % len(pasan))
        for t in pasan[:8]:
            print("  %s(%s)" % (n, ", ".join(json.dumps(a) for a in t["args"])))
        if len(pasan) > 8:
            print("  ... and %d more" % (len(pasan) - 8))
        print("FAILING tests (%d):" % len(fallan))
        for t in fallan[:8]:
            print("  %s(%s)" % (n, ", ".join(json.dumps(a) for a in t["args"])))
        if len(fallan) > 8:
            print("  ... and %d more" % (len(fallan) - 8))
        print()
    print("=" * 78)
    print("Guarda la respuesta cruda en prompts/llm.md y el JSON en")
    print("inputs/llm.json")
    print("=" * 78)


ENVOLTORIOS = ("respuesta", "answer", "result", "ranking", "lineas", "lines",
               "programas", "programs", "data")


def _leer_json(ruta):
    texto = open(ruta, encoding="utf-8").read().strip()
    if not texto:
        raise ValueError("%s esta vacio" % ruta)
    if texto.startswith("```"):
        texto = "\n".join(l for l in texto.splitlines()
                          if not l.strip().startswith("```"))
    texto = re.sub(r"^\s*(//|#).*$", "", texto, flags=re.M)
    texto = re.sub(r",(\s*[\]\}])", r"\1", texto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        try:
            datos = ast.literal_eval(texto)
        except (ValueError, SyntaxError):
            raise ValueError("%s no es JSON valido ni un dict de Python (%s)"
                             % (ruta, e))
        print("  [aviso] %s venia como dict de Python. Se leyo igual." % ruta)
        return datos


def _desenvolver(v):
    n = 0
    while isinstance(v, dict) and len(v) == 1 and n < 4:
        k = next(iter(v))
        if str(k).strip().lower() not in ENVOLTORIOS:
            break
        v = v[k]
        n += 1
    return v


def _entero(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if float(v).is_integer() else None
    if isinstance(v, str):
        m = re.search(r"-?\d+", v)
        return int(m.group(0)) if m else None
    return None


def evaluar_llm(mostrar=True):
    datos = _desenvolver(_leer_json("inputs/llm.json"))
    clave = {re.sub(r"[^a-z0-9]", "", p.lower()): p for p in PROGRAMAS}
    porprog, avisos, errores = {}, [], []
    if not isinstance(datos, dict):
        raise ValueError("se esperaba {programa: [lineas]}, llego %s"
                         % type(datos).__name__)
    for k, v in datos.items():
        real = clave.get(re.sub(r"[^a-z0-9]", "", str(k).lower()))
        if real is None:
            errores.append("no existe el programa %r" % k)
            continue
        if k != real:
            avisos.append("%r se interpreto como %s" % (k, real))
        v = _desenvolver(v)
        if isinstance(v, dict):
            v = list(v.values())
        if not isinstance(v, (list, tuple)):
            v = [v]
        rank, malos = [], []
        for x in v:
            if isinstance(x, dict):
                x = x.get("linea", x.get("line", next(iter(x.values()), None)))
            n = _entero(x)
            if n is None:
                malos.append(x)
            elif n not in rank:
                rank.append(n)
        if malos:
            errores.append("%s: valores que no son numero de linea: %r" % (real, malos))
        porprog[real] = rank

    for a in avisos:
        print("  [aviso] %s" % a)
    for e in errores:
        print("  [error] %s" % e)

    filas = []
    for n in PROGRAMAS:
        e = espectro(n)
        culpable = LINEA_DEFECTO[n]
        rank = porprog.get(n, [])
        m = metricas(rank, culpable, len(e["lineas"]))
        m["programa"] = n
        m["propuestas"] = len(rank)
        m["fuera_de_rango"] = [l for l in rank if l not in e["lineas"]]
        filas.append(m)
    RESULTADOS["llm"] = filas
    if mostrar:
        _imprimir_filas("LLM", filas)
        fuera = [(f["programa"], f["fuera_de_rango"]) for f in filas
                 if f["fuera_de_rango"]]
        if fuera:
            print("\n  Lineas propuestas que no son ejecutables:")
            for p, ls in fuera:
                print("    %-28s %s" % (p, ls))
    return filas


# ==========================================================================
# 5. Consolidacion
# ==========================================================================

def consolidar():
    sb = RESULTADOS.get("sbfl")
    ll = RESULTADOS.get("llm")
    if sb is None or ll is None:
        print("Faltan pasos: %s\n" % ", ".join(
            [k for k, v in [("evaluar_sbfl", sb), ("evaluar_llm", ll)] if v is None]))

    print("## Tabla 1 - Resultados por programa\n")
    print("| Programa | Lineas | Defecto | Ochiai rango | Ochiai EXAM | "
          "LLM rango | LLM EXAM |")
    print("|---|---|---|---|---|---|---|")
    sb = sb or []
    ll = ll or []
    for i, n in enumerate(PROGRAMAS):
        a = sb[i] if i < len(sb) else {}
        b = ll[i] if i < len(ll) else {}
        print("| %s | %s | %s | %s | %s | %s | %s |" % (
            n, a.get("lineas", "-"), LINEA_DEFECTO.get(n, "?"),
            a.get("rango", "-"),
            ("%.3f" % a["exam"]) if "exam" in a else "-",
            b.get("rango", "-"),
            ("%.3f" % b["exam"]) if "exam" in b else "-"))

    print("\n## Tabla 2 - Resumen\n")
    print("| Tecnica | Top-1 | Top-5 | EXAM promedio |")
    print("|---|---|---|---|")
    for etiqueta, filas in [("Ochiai", sb), ("LLM", ll)]:
        if not filas:
            print("| %s | - | - | - |" % etiqueta)
            continue
        b = [f for f in filas if "error" not in f]
        if not b:
            print("| %s | - | - | - |" % etiqueta)
            continue
        print("| %s | %d/%d | %d/%d | %.3f |" % (
            etiqueta, sum(f["top1"] for f in b), len(b),
            sum(f["top5"] for f in b), len(b),
            sum(f["exam"] for f in b) / len(b)))

    print("\n" + "-" * 70)
    print("EXAM mas bajo es mejor: es la fraccion de lineas que habria que")
    print("revisar siguiendo el ranking hasta dar con el defecto.")
    print("Copia las dos tablas a REPORTE.md.")
