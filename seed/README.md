# The EN seed: rebuild EN from memory

You are in a room with an IDE and nothing else: no internet, no `pip`, no `en.pyz`. This folder is the way back.
`en.py` (5.8 KB) and `en.js` (2.8 KB) are the whole **EN core language** as a *phrasebook*:
each English line becomes one line of Python, JavaScript or C. They need only what every machine already has:
Python 3.9+, or any browser console, or Node.

## What you actually have to remember

Not 90 recipes, not 100 KB of source. Just this table. It is the language itself, so learning it is learning EN:

| You write | Python | JavaScript | C |
|---|---|---|---|
| `set x to 5` | `x = 5` | `var x = 5;` | `x = 5;` |
| `make an empty list called xs` | `xs = []` | `var xs = [];` | `n_xs = 0;` |
| `add 3 to xs` | `xs.append(3)` | `xs.push(3);` | `xs[n_xs++] = 3;` |
| `for each i in xs` … `end for` | `for i in xs:` | `for (var i of xs) {` … `}` | a counted loop |
| `if x is greater than 3 then` … `otherwise` … `end if` | `if x > 3:` | `if (x > 3) {` | `if (x > 3) {` |
| `show "a" and x` | `print(str("a")+str(x))` | `console.log(…)` | `printf(…)` |
| `define a class called Dog that extends Animal` … `end class` | `class Dog(Animal):` | `class Dog extends Animal {` | not in C |
| `define a constructor with parameters a and b` | `def __init__(self, a, b):` | `init(a, b) {` | not in C |
| `define a method called speak with parameter p` | `def speak(self, p):` | `speak(p) {` | not in C |
| `return x` · `set self.f to x` | `return x` · `self.f = x` | `return x;` · `this.f = x;` | not in C |
| `make a Dog called rex with 1 and 2` | `rex = Dog(1, 2)` | `var rex = mk(Dog, 1, 2);` | not in C |
| `call rex.speak with 3` · `call super.init with a` | `rex.speak(3)` · `super().__init__(a)` | `rex.speak(3)` · `super.init(a)` | not in C |
| `plus` `minus` `times` | `+ - *` | `+ - *` | `+ - *` |

Operators map to words (`is greater than`, `is less than`, `is not`, `is`) and the target language applies its own precedence, so
`7 times 3 plus 2 minus 1` is `22` everywhere. That one decision is why the three outputs always agree.

## Use it

```sh
python3 en.py program.en            # run it
python3 en.py program.en py|js|c    # print the Python / JavaScript / C instead
```

```python
import en                            # save en.py next to your file
en.run('set x to 2\nshow "x is " and x times 3')
```

In a browser console (works offline): paste `en.js`, then `en('set x to 2\nshow x times 3')`.

## Rebuild it from nothing

1. Type `en.py` (about 65 lines) or `en.js` (about 40). The phrasebook `P` is the part that matters; the rest is a short engine. If that is too much, the first version of the seed (core language only, no classes) was 47 lines and 3.9 KB; type just the first nine phrases.
2. Test it with the programs in this README. If the output matches, you have EN.
3. Everything beyond the core (classes, the 90 recipes, `import`-from-comments, Java) lives in the full package: `pip install en`
   or the single file `python3 scripts/build_zipapp.py`. The seed is the way to get *started*, not a replacement.

## How we know it is right

`seed/fuzz.py` writes random programs and compares the full EN tool with the seed's Python, JavaScript and C. 300 programs
(900 comparisons) and 250 random class programs found 0 differences after two bugs were fixed: empty blocks need `pass` in Python, and C numbers must be 64-bit
(`100000 times 100000`). `tests/test_seed.py` repeats it on every test run.

## Limits (be honest with yourself)

- Only the core: `set`, `show`, lists, `for each`, `if`/`otherwise`, whole numbers, text, and (Python and JavaScript only) classes with constructors, methods, inheritance and `super`. No division, dictionaries, input, or recipes.
- Whole numbers: unlimited in Python, exact to about 9 × 10¹⁵ in JavaScript, about 9 × 10¹⁸ in C.
- The seed is lenient: it does not check that a name was set before use (the full tool does).
- `plus` on text works in Python and JavaScript, not C.
