"""SymPy recomputation of numeric answer keys.

When a drafted question has a computed answer (a mean, a percentage, a ratio), the writer model also returns the arithmetic
("calculation": "(12 + 15 + 18) / 3"). SymPy evaluates it exactly and the key is refused when it disagrees with the stated
answer, or when a wrong option equals the computed value (two defensible answers). A language model gets arithmetic wrong far
more often than it gets a quote wrong; this catches the wrong key before a faculty member or an officer ever sees it.

The calculation is model output, so it is never handed to eval as-is: only digits, operators, brackets and a short list of
function names pass, exponents are capped, and the length is limited before SymPy parses it.
"""
from __future__ import annotations

import re

MAX_LEN = 200
_FUNCS = {"sqrt", "log", "ln", "exp", "abs"}
_ALLOWED = re.compile(r"^[0-9a-z+\-*/^().,%\s]*$")
_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?|-?\.\d+")


class CalcError(ValueError):
    pass


def evaluate(expr: str) -> float:
    """The value of a plain arithmetic expression, or CalcError."""
    s = (expr or "").strip().lower().replace("×", "*").replace("÷", "/").replace("−", "-")
    if not s or len(s) > MAX_LEN or not _ALLOWED.match(s):
        raise CalcError("only numbers, + - * / ^ ( ) and sqrt/log/exp/abs are allowed")
    bad = set(re.findall(r"[a-z]+", s)) - _FUNCS
    if bad:
        raise CalcError(f"unknown name(s): {', '.join(sorted(bad))}")
    s = re.sub(r"(\d),(\d{3})", r"\1\2", s)                     # thousands separators
    s = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", s)
    # exponents: a plain number of at most two digits, never chained (9^9^9) or bracketed (9^(9^9))
    if (re.search(r"(\^|\*\*)\s*(\(|-?\d{3,}|-?\d*\.)", s) or re.search(r"(\^|\*\*)\s*-?\d+\s*(\^|\*\*)", s)
            or len(re.findall(r"\^|\*\*", s)) > 3):
        raise CalcError("exponent too large")
    import sympy
    from sympy.parsing.sympy_parser import convert_xor, parse_expr, standard_transformations
    names = {"sqrt": sympy.sqrt, "log": sympy.log, "ln": sympy.log, "exp": sympy.exp, "abs": sympy.Abs}
    try:
        value = parse_expr(s, local_dict=names, global_dict={"__builtins__": {}, "Integer": sympy.Integer, "Float": sympy.Float,
                                                             "Rational": sympy.Rational},
                           transformations=standard_transformations + (convert_xor,), evaluate=True)
        out = complex(sympy.N(value, 15))
    except Exception as e:                                      # syntax error, division by zero, ...
        raise CalcError(f"could not evaluate ({type(e).__name__})") from e
    if out.imag or out.real != out.real or abs(out.real) == float("inf"):
        raise CalcError("not a real number")
    return out.real


def number_in(text: str) -> tuple[float, int, bool] | None:
    """(first number, decimals shown, is a percentage) in an answer such as "15.33", "Rs 1,200" or "12.5%"; None if none."""
    m = _NUMBER.search(text or "")
    if not m:
        return None
    raw = m.group(0).replace(",", "")
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    pct = (text[m.end():].lstrip()[:1] == "%") or "per cent" in text.lower() or "percent" in text.lower()
    return float(raw), decimals, pct


def matches(value: float, shown: tuple[float, int, bool]) -> bool:
    """Does the number as written equal `value`, allowing for rounding to the decimals shown (and x100 for a percentage)?"""
    num, decimals, pct = shown
    tol = max(0.5 * 10 ** -decimals, 1e-9 * max(1.0, abs(value)))
    candidates = [value, value * 100] if pct else [value]
    return any(abs(num - v) <= tol + 1e-12 for v in candidates)


def check(calculation: str, correct: str, wrong: list[str]) -> tuple[list[str], str]:
    """(problems, record). No calculation, or a non-numeric answer: nothing to check, ([], "")."""
    calc = (calculation or "").strip()
    shown = number_in(correct)
    if not calc or shown is None:
        return [], ""
    try:
        value = evaluate(calc)
    except CalcError as e:
        return [f'The calculation "{calc[:80]}" could not be checked: {e}. Write it with numbers and + - * / ( ) only.'], ""
    pretty = f"{value:.6g}"
    if not matches(value, shown):
        return [f'SymPy recomputed {calc} = {pretty}, but the correct answer says "{correct}". The key is wrong: fix the answer or the calculation.'], ""
    for w in wrong:
        n = number_in(w)
        if n is not None and matches(value, (n[0], shown[1], n[2])):    # judged at the key's precision: "15" is not "15.33"
            return [f'The wrong answer "{w}" also equals {pretty} ({calc}), so two options are correct.'], ""
    return [], f"SymPy: {calc} = {pretty}"


if __name__ == "__main__":                                       # self-check
    assert evaluate("(12 + 15 + 18) / 3") == 15 and abs(evaluate("sqrt(16) + 2^3") - 12) < 1e-12
    assert check("(12+15+18)/3", "15", ["12", "18", "45"]) == ([], "SymPy: (12+15+18)/3 = 15")
    assert check("(12+15+18)/3", "16", ["12", "18", "45"])[0]               # wrong key caught
    assert check("46/3", "15.33", ["15", "14.5", "16"])[1]                   # rounding to the decimals shown
    assert check("45/300", "15%", ["10%", "20%", "25%"])[1]                  # percentage
    assert check("10/2", "5", ["5.0", "4", "6"])[0]                          # a distractor equals the key
    for evil in ("__import__('os')", "a" * 300, "9^9^9^9", "x + 1", "2**99999"):
        try:
            evaluate(evil)
            raise AssertionError(evil)
        except CalcError:
            pass
    assert check("", "Rs 100", ["1"]) == ([], "") and check("2+2", "four", []) == ([], "")
    print("numcheck ok")
