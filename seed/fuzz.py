"""Random EN-core programs: the full tool and the seed (Python, JavaScript, C) must print the same thing."""
import contextlib, io, os, pathlib, random, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import en
from codeinenglish.interpreter import run_source


def program(rnd):
    ints, texts, lists, out = [], [], [], []
    n = [0]

    def num(depth=0):
        if depth > 1 or rnd.random() < 0.5 or not ints:
            return str(rnd.randint(-5, 9)) if rnd.random() < .8 or not ints else rnd.choice(ints)
        return f"{num(depth + 1)} {rnd.choice(['plus', 'minus', 'times'])} {num(depth + 1)}"

    def text():
        return rnd.choice(texts) if texts and rnd.random() < .5 else '"' + rnd.choice(["a", "yes and no", "Ada", "x y", ""]) + '"'

    def block(depth, pad):
        saved = (list(ints), list(texts), list(lists))   # names made inside a branch or loop are not usable after it
        try:
            body(depth, pad)
        finally:
            if depth:
                ints[:], texts[:], lists[:] = saved

    def body(depth, pad):
        for _ in range(rnd.randint(1, 4)):
            kind = rnd.choice(["int", "int", "text", "show", "show", "list", "add", "if", "if", "for"])
            if kind == "int":
                name = rnd.choice(ints) if ints and rnd.random() < .4 else f"n{n[0]}"
                n[0] += 1
                out.append(f"{pad}set {name} to {num()}")
                if name not in ints: ints.append(name)
            elif kind == "text":
                name = f"t{n[0]}"; n[0] += 1
                out.append(f'{pad}set {name} to {text()}')
                texts.append(name)
            elif kind == "show":
                parts = [num() if rnd.random() < .5 else text() for _ in range(rnd.randint(1, 3))]
                out.append(f"{pad}show " + " and ".join(p if p[0] == '"' or not p.split()[0].lstrip('-').isalpha() or True else p for p in parts))
            elif kind == "list":
                name = f"l{n[0]}"; n[0] += 1
                out.append(f"{pad}make an empty list called {name}")
                lists.append(name)
            elif kind == "add" and lists:
                out.append(f"{pad}add {num()} to {rnd.choice(lists)}")
            elif kind == "if" and depth < 2:
                if texts and rnd.random() < .4:
                    cond = f"{rnd.choice(texts)} {rnd.choice(['is', 'is not'])} {text()}"
                else:
                    cond = f"{num()} {rnd.choice(['is greater than', 'is less than', 'is not', 'is'])} {num()}"
                out.append(f"{pad}if {cond} then")
                block(depth + 1, pad)
                if rnd.random() < .5:
                    out.append(f"{pad}otherwise")
                    block(depth + 1, pad)
                out.append(f"{pad}end if")
            elif kind == "for" and lists and depth < 2:
                var = f"i{n[0]}"; n[0] += 1
                out.append(f"{pad}for each {var} in {rnd.choice(lists)}")
                ints.append(var)
                block(depth + 1, pad)
                ints.remove(var)
                out.append(f"{pad}end for")
    block(0, "")
    return "\n".join(out) + "\n"


def full(source):
    lines = []
    run_source(source, "fuzz.en", read=lambda p: "", write=lines.append)
    return "".join(f"{x}\n" for x in lines)


def seeds(source, with_c=True):
    results = {}
    code = en.compile(source, "py")
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        exec(code, {})
    results["py"] = buffer.getvalue()
    with tempfile.TemporaryDirectory() as d:
        pathlib.Path(f"{d}/p.js").write_text(en.compile(source, "js"))
        results["js"] = subprocess.run(["node", f"{d}/p.js"], capture_output=True, text=True).stdout
        if with_c:
            pathlib.Path(f"{d}/p.c").write_text(en.compile(source, "c"))
            built = subprocess.run(["cc", "-w", "-o", f"{d}/p", f"{d}/p.c"], capture_output=True, text=True)
            results["c"] = subprocess.run([f"{d}/p"], capture_output=True, text=True).stdout if built.returncode == 0 else "COMPILE ERROR: " + built.stderr[:300]
    return results


if __name__ == "__main__":
    count, first = int(sys.argv[1]) if len(sys.argv) > 1 else 100, int(sys.argv[2]) if len(sys.argv) > 2 else 0
    bad = 0
    for seed in range(first, first + count):
        source = program(random.Random(seed))
        try:
            expected = full(source)
        except Exception as error:
            print(f"seed {seed}: full EN rejected the program: {error}"); bad += 1; continue
        got = seeds(source)
        for language, output in got.items():
            if output != expected:
                bad += 1
                print(f"seed {seed}: {language} differs\n--- program\n{source}--- expected\n{expected}--- {language}\n{output}")
                break
    print(f"{count} programs, {bad} problems")
