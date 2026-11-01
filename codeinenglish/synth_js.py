"""JavaScript forms of the synthesized operations (see synth.py). Each mirrors the Python form exactly.

Differences are deliberate and documented: integers must stay inside JavaScript's exact range (a larger
intermediate or final value raises an error instead of silently losing digits), and text operations assume
ordinary Unicode text (case rules follow JavaScript)."""

from __future__ import annotations

from .errors import CodeInEnglishError
from .synth import Program, nullable

TOO_BIG = "throw new Error('number too large for this operation')"
JS_HELPERS = {
    "enSafe": "function enSafe(v) { if (typeof v === 'number' && (!Number.isFinite(v) || (Number.isInteger(v) && !Number.isSafeInteger(v)))) throw new Error('value exceeds the exact integer range'); if (Array.isArray(v)) v.forEach(enSafe); return v; }",
    "enWords": "function enWords(v) { return v.split(/\\s+/).filter((w) => w !== ''); }",
    "enProduct": "function enProduct(v) { let r = 1; for (const x of v) r *= x; return r; }",
    "enMedian": "function enMedian(v) { if (!v.length) return null; const s = enSorted(v); const m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }",
    "enMode": "function enMode(v) { if (!v.length) return null; const c = new Map(); for (const x of v) c.set(x, (c.get(x) || 0) + 1); const best = Math.max(...c.values()); return Math.min(...[...c].filter(([, n]) => n === best).map(([x]) => x)); }",
    "enRunning": "function enRunning(v) { let t = 0; return v.map((x) => (t += x)); }",
    "enSecond": "function enSecond(v, largest) { const d = enSorted(Array.from(new Set(v))); return d.length >= 2 ? (largest ? d[d.length - 2] : d[1]) : null; }",
    "enSwapcase": "function enSwapcase(v) { return Array.from(v).map((c) => (c === c.toUpperCase() ? c.toLowerCase() : c.toUpperCase())).join(''); }",
    "enTitle": "function enTitle(v) { return v.replace(/\\p{L}+/gu, (w) => w[0].toUpperCase() + w.slice(1).toLowerCase()); }",
    "enBinary": "function enBinary(n) { return n >= 0 ? n.toString(2) : '-' + (-n).toString(2); }",
    "enIsPrime": f"function enIsPrime(n) {{ if (n > 1e12) {TOO_BIG}; if (n < 2) return false; for (let d = 2; d * d <= n; d++) if (n % d === 0) return false; return true; }}",
    "enDivisors": f"function enDivisors(n) {{ if (Math.abs(n) > 1e5) {TOO_BIG}; const r = []; if (n === 0) return r; for (let d = 1; d <= Math.abs(n); d++) if (enMod(n, d) === 0) r.push(d); return r; }}",
    "enFactorial": f"function enFactorial(n) {{ if (n > 5000) {TOO_BIG}; if (n < 0) return null; let r = 1; for (let v = 2; v <= n; v++) r = enSafe(r * v); return r; }}",
    "enFib": f"function enFib(n) {{ if (n > 100000) {TOO_BIG}; if (n < 0) return null; let a = 0, b = 1; for (let i = 0; i < n; i++) {{ [a, b] = [b, a + b]; enSafe(a); }} return a; }}",
    "enFibList": f"function enFibList(n) {{ if (n > 100000) {TOO_BIG}; const r = []; let a = 0, b = 1; for (let i = 0; i < Math.max(n, 0); i++) {{ r.push(a); [a, b] = [b, a + b]; if (i < n - 1) enSafe(a); }} return r; }}",
    "enCollatz": f"function enCollatz(n) {{ if (n > 1e18) {TOO_BIG}; if (n < 1) return null; let s = 0; while (n !== 1) {{ n = n % 2 === 0 ? n / 2 : enSafe(3 * n + 1); s++; }} return s; }}",
    "enIsSquare": "function enIsSquare(n) { if (n < 0) return false; let r = Math.floor(Math.sqrt(n)); while (r * r > n) r--; while ((r + 1) * (r + 1) <= n) r++; return r * r === n; }",
    "enLeap": "function enLeap(y) { return (enMod(y, 4) === 0 && enMod(y, 100) !== 0) || enMod(y, 400) === 0; }",
    "enArmstrong": "function enArmstrong(n) { if (n < 0) return false; const d = String(n); let t = 0; for (const c of d) t += Number(c) ** d.length; return t === n; }",
    "enPerfect": f"function enPerfect(n) {{ if (n > 1e5) {TOO_BIG}; if (n <= 1) return false; let t = 0; for (let d = 1; d < n; d++) if (n % d === 0) t += d; return t === n; }}",
    "enPalindrome": "function enPalindrome(v) { const c = Array.from(v.toLowerCase()).filter((x) => /^[\\p{L}\\p{N}]$/u.test(x)); return c.join('') === [...c].reverse().join(''); }",
    "enPangram": "function enPangram(v) { const s = new Set(v.toLowerCase()); return [...'abcdefghijklmnopqrstuvwxyz'].every((c) => s.has(c)); }",
    "enConsonants": "function enConsonants(v) { return Array.from(v.toLowerCase()).filter((c) => /^\\p{L}$/u.test(c) && !'aeiou'.includes(c)).length; }",
    "enPrimesUpTo": f"function enPrimesUpTo(n) {{ if (n > 1e5) {TOO_BIG}; if (n < 2) return []; const f = new Array(n + 1).fill(true); f[0] = f[1] = false; for (let p = 2; p * p <= n; p++) if (f[p]) for (let m = p * p; m <= n; m += p) f[m] = false; const r = []; f.forEach((ok, i) => ok && r.push(i)); return r; }}",
    "enRange1": f"function enRange1(n) {{ if (Math.abs(n) > 1e5) {TOO_BIG}; const r = []; for (let i = 1; i <= n; i++) r.push(i); return r; }}",
    "enPow2": "function enPow2(n) { if (n < 1) return false; while (n % 2 === 0) n /= 2; return n === 1; }",
}
JS_DEPS = {"enFactorial": ("enSafe",), "enFib": ("enSafe",), "enFibList": ("enSafe",), "enCollatz": ("enSafe",), "enDivisors": ("enMod",), "enLeap": ("enMod",), "enMedian": ("enSorted",), "enSecond": ("enSorted",)}
_V = "Array.from({x}).filter((c) => "
JS_EXPR = {
    "keep_even": ("{x}.filter((v) => enMod(v, 2) === 0)", ()), "keep_odd": ("{x}.filter((v) => enMod(v, 2) !== 0)", ()),
    "keep_positive": ("{x}.filter((v) => v > 0)", ()), "keep_negative": ("{x}.filter((v) => v < 0)", ()),
    "keep_nonzero": ("{x}.filter((v) => v !== 0)", ()), "keep_prime": ("{x}.filter((v) => enIsPrime(v))", ("enIsPrime",)),
    "keep_greater": ("{x}.filter((v) => v > {n})", ()), "keep_less": ("{x}.filter((v) => v < {n})", ()),
    "keep_at_least": ("{x}.filter((v) => v >= {n})", ()), "keep_at_most": ("{x}.filter((v) => v <= {n})", ()),
    "keep_divisible": ("{x}.filter((v) => enMod(v, {n}) === 0)", ()),
    "square_each": ("{x}.map((v) => v * v)", ()), "cube_each": ("{x}.map((v) => v * v * v)", ()),
    "double_each": ("{x}.map((v) => v * 2)", ()), "negate_each": ("{x}.map((v) => -v)", ()), "absolute_each": ("{x}.map((v) => Math.abs(v))", ()),
    "sort_ascending": ("enSorted({x})", ()), "sort_descending": ("enSorted({x}).reverse()", ()), "reverse_list": ("[...{x}].reverse()", ()),
    "remove_duplicates": ("Array.from(new Set({x}))", ()), "running_total": ("enRunning({x})", ("enRunning",)),
    "first_n": ("{x}.slice(0, {n})", ()), "last_n": ("{x}.slice(Math.max({x}.length - {n}, 0))", ()),
    "differences": ("{x}.slice(1).map((b, i) => b - {x}[i])", ()),
    "total": ("enSum({x})", ()), "product": ("enProduct({x})", ("enProduct",)), "count_items": ("{x}.length", ()),
    "maximum": ("({x}.length ? enMax({x}) : null)", ()), "minimum": ("({x}.length ? enMin({x}) : null)", ()),
    "average": ("({x}.length ? enSum({x}) / {x}.length : null)", ()), "median": ("enMedian({x})", ("enMedian",)), "mode": ("enMode({x})", ("enMode",)),
    "spread": ("({x}.length ? enMax({x}) - enMin({x}) : null)", ()),
    "second_largest": ("enSecond({x}, true)", ("enSecond",)), "second_smallest": ("enSecond({x}, false)", ("enSecond",)),
    "has_duplicates": ("(new Set({x}).size !== {x}.length)", ()), "join_commas": ("{x}.join(', ')", ()),
    "to_uppercase": ("{x}.toUpperCase()", ()), "to_lowercase": ("{x}.toLowerCase()", ()), "swap_case": ("enSwapcase({x})", ("enSwapcase",)),
    "title_case": ("enTitle({x})", ("enTitle",)), "remove_spaces": ("enWords({x}).join('')", ("enWords",)),
    "remove_vowels": (_V + "!'aeiou'.includes(c.toLowerCase())).join('')", ()),
    "remove_digits": (_V + "!/^[0-9]$/.test(c)).join('')", ()),
    "remove_punctuation": (_V + "/^[\\p{L}\\p{N}]$/u.test(c) || /^\\s$/.test(c)).join('')", ()),
    "reverse_text": ("Array.from({x}).reverse().join('')", ()), "reverse_word_order": ("enWords({x}).reverse().join(' ')", ("enWords",)),
    "sort_letters": ("enSorted(Array.from({x})).join('')", ()), "remove_repeated_characters": ("Array.from(new Set(Array.from({x}))).join('')", ()),
    "to_binary": ("enBinary({x})", ("enBinary",)),
    "length": ("Array.from({x}).length", ()), "count_vowels": (_V + "'aeiou'.includes(c.toLowerCase())).length", ()),
    "count_consonants": ("enConsonants({x})", ("enConsonants",)), "count_words": ("enWords({x}).length", ("enWords",)),
    "count_uppercase": (_V + "/^\\p{Lu}$/u.test(c)).length", ()), "count_lowercase": (_V + "/^\\p{Ll}$/u.test(c)).length", ()),
    "count_digit_characters": (_V + "/^[0-9]$/.test(c)).length", ()), "count_unique_characters": ("new Set(Array.from({x})).size", ()),
    "is_palindrome_text": ("enPalindrome({x})", ("enPalindrome",)), "is_pangram": ("enPangram({x})", ("enPangram",)),
    "split_words": ("enWords({x})", ("enWords",)), "split_characters": ("Array.from({x})", ()),
    "keep_longer": ("{x}.filter((w) => Array.from(w).length > {n})", ()), "keep_shorter": ("{x}.filter((w) => Array.from(w).length < {n})", ()),
    "sort_alphabetically": ("enSorted({x})", ()), "unique_words": ("Array.from(new Set({x}))", ()), "count_entries": ("{x}.length", ()),
    "longest_entry": ("({x}.length ? {x}.reduce((a, b) => (b.length > a.length ? b : a)) : '')", ()),
    "shortest_entry": ("({x}.length ? {x}.reduce((a, b) => (b.length < a.length ? b : a)) : '')", ()),
    "is_prime_number": ("enIsPrime({x})", ("enIsPrime",)), "is_even_number": ("(enMod({x}, 2) === 0)", ()), "is_odd_number": ("(enMod({x}, 2) !== 0)", ()),
    "is_perfect_square": ("enIsSquare({x})", ("enIsSquare",)), "is_power_of_two": ("enPow2({x})", ("enPow2",)),
    "is_leap_year": ("enLeap({x})", ("enLeap",)), "is_armstrong": ("enArmstrong({x})", ("enArmstrong",)),
    "is_perfect_number": ("enPerfect({x})", ("enPerfect",)), "is_palindrome_number": ("(String({x}) === Array.from(String({x})).reverse().join(''))", ()),
    "factorial": ("enFactorial({x})", ("enFactorial",)), "fibonacci_term": ("enFib({x})", ("enFib",)), "collatz_steps": ("enCollatz({x})", ("enCollatz",)),
    "square_number": ("({x} * {x})", ()), "absolute_number": ("Math.abs({x})", ()),
    "reverse_digits": ("((({x}) < 0 ? -1 : 1) * Number(Array.from(String(Math.abs({x}))).reverse().join('')))", ()),
    "digits": ("Array.from(String(Math.abs({x})), Number)", ()), "divisors": ("enDivisors({x})", ("enDivisors",)),
    "primes_up_to": ("enPrimesUpTo({x})", ("enPrimesUpTo",)), "primes_below": ("enPrimesUpTo({x} - 1)", ("enPrimesUpTo",)),
    "natural_numbers": ("enRange1({x})", ("enRange1",)), "fibonacci_list": ("enFibList({x})", ("enFibList",)),
}
BRIDGE_JS = {"{x}.split()": ("enWords({x})", ("enWords",)), "' '.join({x})": ("{x}.join(' ')", ())}


def js_step(op, n, bridge_expr):
    """(JavaScript expression over {x}, helper names) for a chain step, or None when it has no JavaScript form."""
    if op is None:
        return BRIDGE_JS.get(bridge_expr)
    found = JS_EXPR.get(op.name)
    return None if found is None else (found[0].replace("{n}", str(n)), found[1])


def helper_closure(names):
    ordered = []

    def add(name):
        for dep in JS_DEPS.get(name, ()):
            add(dep)
        if name not in ordered and name in JS_HELPERS:
            ordered.append(name)

    for name in names:
        add(name)
    return ordered


def chain_function_js(program: Program, filename: str = "<synth>"):
    """(helper source, function name, function source) for a synthesized chain."""
    lines, helpers = [], []
    for index, (op, n, expr, says) in enumerate(program.chain):
        step = js_step(op, n, expr)
        if step is None:
            raise CodeInEnglishError(filename, 1, f"JavaScript: '{op.says}' has no JavaScript form yet; use target python", kind="unsupported")
        body, needed = step
        helpers += list(needed)
        lines.append(f"  value = enSafe({body.replace('{x}', 'value')});")
        if nullable(op) and index < len(program.chain) - 1:
            lines.append("  if (value === null) return null;")
    helpers.append("enSafe")
    names = helper_closure(helpers)
    parameter = program.parameter[0]
    function = "\n".join([f"function {program.function_name}(en_{parameter}) {{", f"  let value = en_{parameter};", *lines, "  return value;", "}"])
    return "\n".join(JS_HELPERS[name] for name in names), program.function_name, function
