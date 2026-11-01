"""Every synthesized operation, alone and in random chains, must agree between Python and JavaScript."""
import json
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from codeinenglish import synth
from codeinenglish.synth_js import JS_EXPR, JS_HELPERS, chain_function_js, helper_closure

LIMIT = 2 ** 53 - 1


def make_program(chain, kind):
    return synth.Program(kind, tuple(chain), "", "f")


def step_items(kind):
    return [(op, 3 if op.parametric else None) for op in synth.OPS if op.src == kind]


def random_chains(rng, count, depth):
    chains = []
    while len(chains) < count:
        kind = rng.choice(["ilist", "text", "int"])
        current, chain = kind, []
        for _ in range(rng.randint(1, depth)):
            options = step_items(current)
            bridge = [(None, None, b[1], b[0]) for (s, d), b in synth.COERCE.items() if s == current]
            if not options + bridge:
                break
            pick = rng.choice(options + bridge)
            if pick[0] is None:
                chain.append(pick)
                current = "tlist" if current == "text" else "text"
            else:
                chain.append((pick[0], pick[1], None, None))
                current = pick[0].dst
        if chain:
            chains.append((kind, chain))
    return chains


SPLIT = (None, None, "{x}.split()", "split into words")


def alone(op, n):
    """A one-operation program; word-list operations get the implicit split from a text first."""
    step = (op, n, None, None)
    return ("text", [SPLIT, step]) if op.src == "tlist" else (op.src, [step])


def contains_big(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return abs(value) > LIMIT
    if isinstance(value, list):
        return any(contains_big(v) for v in value)
    return False


def same(py, js):
    if isinstance(py, str) and py.startswith("ERR:"):
        return js == "ERR"
    if isinstance(py, bool) or isinstance(js, bool):
        return py is js
    if isinstance(py, (int, float)) and isinstance(js, (int, float)):
        return abs(py - js) < 1e-9 * max(1, abs(py))
    if isinstance(py, list) and isinstance(js, list):
        return len(py) == len(js) and all(same(a, b) for a, b in zip(py, js))
    return py == js


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class PythonAndJavaScriptAgree(unittest.TestCase):
    def run_node(self, jobs):
        helpers, functions, calls = set(), [], []
        for index, (kind, chain) in enumerate(jobs):
            source, _, function = chain_function_js(make_program(chain, kind))
            helpers.update(name for name in JS_HELPERS if f"function {name}(" in source)
            functions.append(function.replace("function f(", f"function f{index}(", 1))
            calls.append(f"{{ const r = []; for (const p of PROBES.{kind}) {{ try {{ r.push(f{index}(p)); }} catch (e) {{ r.push('ERR'); }} }} out.push(r); }}")
        prelude = Path(synth.__file__).with_name("transpile_js.py").read_text().split('_PRELUDE = """\\\n')[1].split('"""')[0]
        script = "\n".join([prelude, *[JS_HELPERS[n] for n in helper_closure(sorted(helpers))], *functions,
                            f"const PROBES = {json.dumps(synth.PROBES)};", "const out = [];", *calls, "console.log(JSON.stringify(out));"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "check.js"
            path.write_text(script, encoding="utf-8")
            done = subprocess.run(["node", str(path)], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr[:2000])
        return json.loads(done.stdout)

    def overflows(self, chain, value):
        try:
            for expr, n in synth._steps_of(chain):
                value = synth._function_of(expr, n)(value)
                if contains_big(value):
                    return True
        except Exception:
            return False
        return False

    def compare(self, jobs):
        failures = []
        for (kind, chain), outcome in zip(jobs, self.run_node(jobs)):
            names = " -> ".join(item[0].name if item[0] is not None else "bridge" for item in chain)
            for probe, js in zip(synth.PROBES[kind], outcome):
                py = synth._run(chain, probe)
                if js == "ERR" and not (isinstance(py, str) and py.startswith("ERR:")):
                    if not (contains_big(py) or self.overflows(chain, probe)):
                        failures.append(f"{names} on {probe!r}: JavaScript failed but Python gave {py!r}")
                elif not same(py, js):
                    failures.append(f"{names} on {probe!r}: Python {py!r} vs JavaScript {js!r}")
        self.assertEqual(failures[:15], [], f"{len(failures)} disagreements")

    def test_every_operation_has_a_javascript_form(self):
        self.assertEqual(sorted(op.name for op in synth.OPS if op.name not in JS_EXPR), [])

    def test_each_operation_alone(self):
        self.compare([alone(op, 3 if op.parametric else None) for op in synth.OPS])

    def test_parameters_other_than_three(self):
        self.compare([alone(op, n) for op in synth.OPS if op.parametric for n in (0, 1, 10, -2)
                      if not (op.name == "keep_divisible" and n == 0)])

    def test_random_chains(self):
        self.compare(random_chains(random.Random(7), 400, 4))


if __name__ == "__main__":
    unittest.main()
