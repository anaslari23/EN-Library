"""Random class programs (constructors, fields, methods, inheritance, super): the seed must match the full tool."""
import os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
import fuzz


def program(rnd):
    out, classes, n = [], [], [0]

    def num(names, depth=0):
        if depth > 1 or rnd.random() < .5:
            return rnd.choice(names) if names and rnd.random() < .6 else str(rnd.randint(-4, 9))
        return f"{num(names, depth + 1)} {rnd.choice(['plus', 'minus', 'times'])} {num(names, depth + 1)}"

    for index in range(rnd.randint(1, 3)):
        parent = rnd.choice(classes) if classes and rnd.random() < .6 else None
        name = f"C{index}"
        fields = [f"f{n[0] + j}" for j in range(rnd.randint(1, 2))]
        n[0] += 2
        out.append(f"define a class called {name}" + (f" that extends {parent['name']}" if parent else ""))
        params = (list(parent["params"]) if parent and rnd.random() < .7 else []) + [f"p{index}{j}" for j in range(len(fields))]
        out.append("define a constructor with parameters " + " and ".join(params) if params else "define a constructor")
        if parent:
            given = [p if p in params else str(rnd.randint(-3, 9)) for p in parent["params"]]
            out.append(("call super.init with " + " and ".join(given)) if given else "call super.init")
        for field, param in zip(fields, params[len(params) - len(fields):]):
            out.append(f"set self.{field} to {param}")
        out.append("end constructor")
        own = list(fields) + (parent["fields"] if parent else [])
        methods = []
        for j in range(rnd.randint(1, 2)):
            method = rnd.choice(parent["methods"])[0] if parent and parent["methods"] and rnd.random() < .5 else f"m{index}{j}"
            if any(m[0] == method for m in methods):
                continue
            arity = next((m[1] for m in (parent["methods"] if parent else []) if m[0] == method), rnd.randint(0, 1))
            plist = [f"z{index}{j}"] * arity
            out.append(f"define a method called {method}" + (f" with parameter {plist[0]}" if arity else ""))
            expression = num([f"self.{f}" for f in own] + plist)
            inherited = parent and any(m[0] == method for m in parent["methods"])
            if inherited and rnd.random() < .7:
                out.append("set base to call super." + method + (f" with {plist[0]}" if arity else ""))
                out.append(f"return base plus {expression}")
            else:
                out.append(f"return {expression}")
            out.append("end method")
            methods.append((method, arity))
        out.append("end class")
        classes.append({"name": name, "params": params, "fields": own, "methods": methods + [m for m in (parent["methods"] if parent else []) if m[0] not in [x[0] for x in methods]]})
    for number in range(rnd.randint(1, 3)):
        cls = rnd.choice(classes)
        out.append(f"make a {cls['name']} called o{number}" + (" with " + " and ".join(num([], 1) for _ in cls["params"]) if cls["params"] else ""))
        for method, arity in rnd.sample(cls["methods"], min(len(cls["methods"]), 2)):
            out.append(f"set r{number}{method} to call o{number}.{method}" + (f" with {num([])}" if arity else ""))
            out.append(f"show r{number}{method}")
        out.append(f"show o{number}.{rnd.choice(cls['fields'])}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    count, first = int(sys.argv[1]) if len(sys.argv) > 1 else 100, int(sys.argv[2]) if len(sys.argv) > 2 else 0
    bad = 0
    for seed in range(first, first + count):
        source = program(random.Random(seed))
        try:
            expected = fuzz.full(source)
        except Exception as error:
            print(f"seed {seed}: full EN rejected the program: {error}\n{source}"); bad += 1; continue
        got = {k: v for k, v in fuzz.seeds(source, with_c=False).items()}
        for language, output in got.items():
            if output != expected:
                bad += 1
                print(f"seed {seed}: {language} differs\n--- program\n{source}--- expected\n{expected}--- {language}\n{output}")
                break
    print(f"{count} class programs, {bad} problems")
