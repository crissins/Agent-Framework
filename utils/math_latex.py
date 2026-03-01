"""
utils/math_latex.py
===================
Random math exercise generator that produces LaTeX-formatted problems
for injection into educational book chapters.

Usage example (in chapter_agent or curriculum_agent):

    from utils.math_latex import generate_exercises_block
    block = generate_exercises_block("fracciones", count=5, language="Spanish")
    # Returns a ready-to-use markdown string with LaTeX problems + solutions.
"""

from __future__ import annotations

import random
from math import gcd
from typing import Literal

# ──────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _lcm(a: int, b: int) -> int:
    return a * b // gcd(a, b)


def _simplify(num: int, den: int) -> tuple[int, int]:
    g = gcd(abs(num), abs(den))
    return num // g, den // g


def _frac(num: int, den: int, inline: bool = True) -> str:
    """Return a LaTeX fraction string.  den=1 → plain integer."""
    num, den = _simplify(num, den)
    if den == 1:
        return f"${num}$" if inline else f"$${num}$$"
    body = f"\\frac{{{num}}}{{{den}}}"
    return f"${body}$" if inline else f"$${body}$$"


# ──────────────────────────────────────────────────────────────────────────────
#  Arithmetic  (addition, subtraction, multiplication, division)
# ──────────────────────────────────────────────────────────────────────────────

def generate_arithmetic(
    count: int = 5,
    difficulty: Literal["easy", "medium", "hard"] = "medium",
    language: str = "Spanish",
) -> list[dict]:
    """
    Return *count* arithmetic problems as dicts:
        {"problem": LaTeX str, "solution": LaTeX str, "context": str}
    """
    ranges = {"easy": (2, 15), "medium": (10, 99), "hard": (50, 999)}
    lo, hi = ranges[difficulty]
    ops = ["+", "-", "\\times", "\\div"]

    MX_CONTEXTS = [
        "tamales en la canasta", "pesos en el mercado",
        "chiles en la milpa", "tortillas para la familia",
        "litros de agua en el tinaco", "metros de tela en el puesto",
        "kilos de jitomate", "personas en el salón",
    ]
    EN_CONTEXTS = [
        "items in the basket", "pesos at the market",
        "tortillas for the family", "liters in the tank",
    ]
    ctxs = MX_CONTEXTS if ("es" in language.lower() or "span" in language.lower()) else EN_CONTEXTS

    results = []
    for _ in range(count):
        op = random.choice(ops)
        a  = random.randint(lo, hi)
        b  = random.randint(lo, hi)

        if op == "\\div":
            # ensure clean division
            b   = random.randint(2, max(2, hi // 5))
            a   = b * random.randint(2, max(2, hi // b))
            ans = a // b
        elif op == "\\times":
            a   = random.randint(2, max(2, int(hi ** 0.5)))
            b   = random.randint(2, max(2, int(hi ** 0.5)))
            ans = a * b
        elif op == "+":
            ans = a + b
        else:  # -
            a, b = max(a, b), min(a, b)
            ans  = a - b

        ctx = random.choice(ctxs)
        results.append({
            "problem":  f"$${a} {op} {b} = ?$$",
            "solution": f"$${a} {op} {b} = {ans}$$",
            "context":  ctx,
        })
    return results


# ──────────────────────────────────────────────────────────────────────────────
#  Fractions
# ──────────────────────────────────────────────────────────────────────────────

def generate_fractions(
    count: int = 5,
    operation: Literal["add", "subtract", "compare", "simplify", "mixed"] = "mixed",
    language: str = "Spanish",
) -> list[dict]:
    """Return fraction exercises with step-by-step LaTeX solutions."""
    DENS = [2, 3, 4, 5, 6, 8, 10]
    results = []

    for _ in range(count):
        op = operation if operation != "mixed" else random.choice(["add", "subtract", "compare", "simplify"])
        d1 = random.choice(DENS)
        d2 = random.choice(DENS)
        n1 = random.randint(1, d1 - 1)
        n2 = random.randint(1, d2 - 1)

        if op in ("add", "subtract"):
            lcd   = _lcm(d1, d2)
            en1   = n1 * (lcd // d1)
            en2   = n2 * (lcd // d2)
            raw_n = en1 + en2 if op == "add" else en1 - en2
            rn, rd = _simplify(raw_n, lcd)
            op_sym = "+"  if op == "add" else "-"

            # Show conversion step only if denominators differ
            if d1 == d2:
                step = (f"$\\frac{{{n1}}}{{{d1}}} {op_sym} \\frac{{{n2}}}{{{d2}}} "
                        f"= \\frac{{{n1} {op_sym} {n2}}}{{{d1}}} "
                        f"= \\frac{{{raw_n}}}{{{d1}}}$")
            else:
                step = (f"$\\frac{{{n1}}}{{{d1}}} {op_sym} \\frac{{{n2}}}{{{d2}}} "
                        f"= \\frac{{{en1}}}{{{lcd}}} {op_sym} \\frac{{{en2}}}{{{lcd}}} "
                        f"= \\frac{{{raw_n}}}{{{lcd}}}$")

            answer = _frac(rn, rd)
            results.append({
                "problem":  f"$\\frac{{{n1}}}{{{d1}}} {op_sym} \\frac{{{n2}}}{{{d2}}} = ?$",
                "steps":    step,
                "solution": f"Resultado: {answer}",
            })

        elif op == "compare":
            lcd  = _lcm(d1, d2)
            en1  = n1 * (lcd // d1)
            en2  = n2 * (lcd // d2)
            sym  = ">" if en1 > en2 else ("<" if en1 < en2 else "=")
            results.append({
                "problem":  f"¿Cuál es mayor? $\\frac{{{n1}}}{{{d1}}}$ o $\\frac{{{n2}}}{{{d2}}}$",
                "steps":    (f"$\\frac{{{n1}}}{{{d1}}} = \\frac{{{en1}}}{{{lcd}}}$ "
                             f"y $\\frac{{{n2}}}{{{d2}}} = \\frac{{{en2}}}{{{lcd}}}$"),
                "solution": f"$\\frac{{{n1}}}{{{d1}}} {sym} \\frac{{{n2}}}{{{d2}}}$",
            })

        else:  # simplify
            factor   = random.randint(2, 5)
            big_n    = n1 * factor
            big_d    = d1 * factor
            sn, sd   = _simplify(big_n, big_d)
            results.append({
                "problem":  f"Simplifica: $\\frac{{{big_n}}}{{{big_d}}}$",
                "steps":    f"$\\frac{{{big_n}}}{{{big_d}}} \\div \\frac{{{factor}}}{{{factor}}} = \\frac{{{sn}}}{{{sd}}}$",
                "solution": f"$\\frac{{{sn}}}{{{sd}}}$",
            })

    return results


# ──────────────────────────────────────────────────────────────────────────────
#  Geometry
# ──────────────────────────────────────────────────────────────────────────────

def generate_geometry(
    count: int = 5,
    shapes: list[str] | None = None,
    language: str = "Spanish",
) -> list[dict]:
    """Return geometry problems (area / perimeter) with LaTeX solutions."""
    if shapes is None:
        shapes = ["rectangle", "square", "triangle", "circle"]

    MX_CTX = {
        "rectangle": ["parcela de maíz", "patio de la escuela", "cancha de básquetbol"],
        "square":    ["plaza del pueblo", "jardín comunitario", "habitación cuadrada"],
        "triangle":  ["techo de palapa", "bandera triangular", "trozo de tela"],
        "circle":    ["tortilla", "rueda de carreta", "olla talavera"],
    }
    EN_CTX = {
        "rectangle": ["garden plot", "school yard", "basketball court"],
        "square":    ["town square", "bedroom", "tile"],
        "triangle":  ["roof", "triangular flag", "piece of fabric"],
        "circle":    ["plate", "wheel", "pond"],
    }
    ctxs = MX_CTX if ("es" in language.lower() or "span" in language.lower()) else EN_CTX

    results = []
    for _ in range(count):
        shape = random.choice(shapes)
        ctx   = random.choice(ctxs.get(shape, ["figure"]))

        if shape == "rectangle":
            b, h  = random.randint(3, 20), random.randint(2, 15)
            area  = b * h
            perim = 2 * (b + h)
            if ("es" in language.lower() or "span" in language.lower()):
                q = f"Un {ctx} mide {b} m de base y {h} m de altura."
            else:
                q = f"A {ctx} is {b} m wide and {h} m tall."
            results.append({
                "problem":  q,
                "solution": (
                    f"Área: $A = b \\times h = {b} \\times {h} = {area}\\, \\text{{m}}^2$\n"
                    f"Perímetro: $P = 2(b + h) = 2({b} + {h}) = {perim}\\, \\text{{m}}$"
                ),
            })

        elif shape == "square":
            l     = random.randint(3, 18)
            area  = l * l
            perim = 4 * l
            if ("es" in language.lower() or "span" in language.lower()):
                q = f"Un {ctx} cuadrado tiene lado de {l} m."
            else:
                q = f"A square {ctx} has side {l} m."
            results.append({
                "problem":  q,
                "solution": (
                    f"Área: $A = l^2 = {l}^2 = {area}\\, \\text{{m}}^2$\n"
                    f"Perímetro: $P = 4l = 4 \\times {l} = {perim}\\, \\text{{m}}$"
                ),
            })

        elif shape == "triangle":
            b, h  = random.randint(4, 20), random.randint(3, 15)
            area2 = b * h          # twice the area (avoids fractions when odd)
            if area2 % 2 == 0:
                area_str = f"${area2 // 2}\\, \\text{{m}}^2$"
            else:
                area_str = f"$\\frac{{{area2}}}{{2}} = {area2 / 2:.1f}\\, \\text{{m}}^2$"
            if ("es" in language.lower() or "span" in language.lower()):
                q = f"Un {ctx} triangular tiene base {b} m y altura {h} m."
            else:
                q = f"A triangular {ctx} has base {b} m and height {h} m."
            results.append({
                "problem":  q,
                "solution": f"Área: $A = \\frac{{b \\times h}}{{2}} = \\frac{{{b} \\times {h}}}{{2}} = $ {area_str}",
            })

        else:  # circle
            r    = random.randint(2, 10)
            if ("es" in language.lower() or "span" in language.lower()):
                q = f"Un {ctx} circular tiene radio de {r} cm. Usa $\\pi \\approx 3.14$."
            else:
                q = f"A circular {ctx} has radius {r} cm. Use $\\pi \\approx 3.14$."
            area_val  = round(3.14159 * r * r, 2)
            circ_val  = round(2 * 3.14159 * r, 2)
            results.append({
                "problem":  q,
                "solution": (
                    f"Área: $A = \\pi r^2 = 3.14 \\times {r}^2 = 3.14 \\times {r*r} = {area_val}\\, \\text{{cm}}^2$\n"
                    f"Circunferencia: $C = 2\\pi r = 2 \\times 3.14 \\times {r} = {circ_val}\\, \\text{{cm}}$"
                ),
            })

    return results


# ──────────────────────────────────────────────────────────────────────────────
#  Basic algebra (one-step linear equations)
# ──────────────────────────────────────────────────────────────────────────────

def generate_algebra_basics(count: int = 5, language: str = "Spanish") -> list[dict]:
    """Return simple one-step equations like $x + 5 = 12$."""
    results = []
    for _ in range(count):
        x_val = random.randint(1, 20)
        op    = random.choice(["+", "-", "\\times"])

        if op == "+":
            b = random.randint(1, 15)
            c = x_val + b
            step  = f"$x + {b} = {c}  \\Rightarrow  x = {c} - {b} = {x_val}$"
            prob  = f"$x + {b} = {c}$"
        elif op == "-":
            b = random.randint(1, x_val)
            c = x_val - b
            step  = f"$x - {b} = {c}  \\Rightarrow  x = {c} + {b} = {x_val}$"
            prob  = f"$x - {b} = {c}$"
        else:
            b = random.randint(2, 10)
            c = x_val * b
            step  = f"$x \\times {b} = {c}  \\Rightarrow  x = {c} \\div {b} = {x_val}$"
            prob  = f"$x \\times {b} = {c}$"

        if ("es" in language.lower() or "span" in language.lower()):
            label = "Encuentra el valor de $x$:"
        else:
            label = "Find the value of $x$:"
        results.append({"problem": f"{label} {prob}", "solution": step})
    return results


# ──────────────────────────────────────────────────────────────────────────────
#  Public API — returns a ready-to-inject markdown block
# ──────────────────────────────────────────────────────────────────────────────

_EXERCISE_HEADERS = {
    "arithmetic": {
        "es": "### ✏️ Ejercicios de Operaciones",
        "en": "### ✏️ Arithmetic Exercises",
    },
    "fractions": {
        "es": "### ✏️ Ejercicios de Fracciones",
        "en": "### ✏️ Fraction Exercises",
    },
    "geometry": {
        "es": "### ✏️ Ejercicios de Geometría",
        "en": "### ✏️ Geometry Exercises",
    },
    "algebra": {
        "es": "### ✏️ Ejercicios de Álgebra",
        "en": "### ✏️ Algebra Exercises",
    },
}


def generate_exercises_block(
    topic: str,
    count: int = 5,
    difficulty: Literal["easy", "medium", "hard"] = "medium",
    language: str = "Spanish",
) -> str:
    """
    Generate a markdown/LaTeX exercise block ready to append to a chapter.

    *topic* is a keyword: 'arithmetic', 'fractions', 'geometry', 'algebra',
    or free text that is auto-detected.

    Returns a multi-line string with exercise problems and solutions.
    """
    lang = "es" if ("es" in language.lower() or "span" in language.lower()) else "en"
    t    = topic.lower()

    if any(k in t for k in ("fraccion", "fraction", "frac")):
        exercises = generate_fractions(count=count, language=language)
        header    = _EXERCISE_HEADERS["fractions"][lang]
        kind      = "fractions"
    elif any(k in t for k in ("geometr", "area", "perimetr", "circle", "rect")):
        exercises = generate_geometry(count=count, language=language)
        header    = _EXERCISE_HEADERS["geometry"][lang]
        kind      = "geometry"
    elif any(k in t for k in ("algebra", "ecuaci", "equation", "variable")):
        exercises = generate_algebra_basics(count=count, language=language)
        header    = _EXERCISE_HEADERS["algebra"][lang]
        kind      = "algebra"
    else:
        exercises = generate_arithmetic(count=count, difficulty=difficulty, language=language)
        header    = _EXERCISE_HEADERS["arithmetic"][lang]
        kind      = "arithmetic"

    lines = [header, ""]
    for i, ex in enumerate(exercises, 1):
        if lang == "es":
            lines.append(f"**Ejercicio {i}.** {ex['problem']}")
        else:
            lines.append(f"**Exercise {i}.** {ex['problem']}")

        if "context" in ex:
            ctx_label = "Contexto" if lang == "es" else "Context"
            lines.append(f"*{ctx_label}: {ex['context']}*")

        if "steps" in ex:
            step_label = "Paso a paso" if lang == "es" else "Step by step"
            lines.append(f"> {step_label}: {ex['steps']}")

        lines.append(f"> **{'Solución' if lang=='es' else 'Solution'}:** {ex['solution']}")
        lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
#  CLI  (python -m utils.math_latex fracciones --count 3)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    topic_arg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "arithmetic"
    print(generate_exercises_block(topic_arg, count=4, language="Spanish"))

