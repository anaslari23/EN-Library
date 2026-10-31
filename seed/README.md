# The EN seed: rebuild EN from memory

You are in a room with an IDE and nothing else: no internet, no `pip`, no `en.pyz`. This folder is the way back.
`en.py` (about 3.7 KB, 47 lines) and `en.js` (1.4 KB) are the whole **EN core language** as a *phrasebook*:
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

1. Type the 47 lines of `en.py` (or the 20 of `en.js`). The phrasebook `P` is the part that matters; the rest is a 20-line engine.
2. Test it with the programs in this README. If the output matches, you have EN.
3. Everything beyond the core (classes, the 90 recipes, `import`-from-comments, Java) lives in the full package: `pip install en`
   or the single file `python3 scripts/build_zipapp.py`. The seed is the way to get *started*, not a replacement.

## How we know it is right

`seed/fuzz.py` writes random programs and compares the full EN tool with the seed's Python, JavaScript and C. 300 programs
(900 comparisons) found 0 differences after two bugs were fixed: empty blocks need `pass` in Python, and C numbers must be 64-bit
(`100000 times 100000`). `tests/test_seed.py` repeats it on every test run.

## Limits (be honest with yourself)

- Only the core: `set`, `show`, lists, `for each`, `if`/`otherwise`, whole numbers, text. No division, classes, input or recipes.
- Whole numbers: unlimited in Python, exact to about 9 × 10¹⁵ in JavaScript, about 9 × 10¹⁸ in C.
- The seed is lenient: it does not check that a name was set before use (the full tool does).
- `plus` on text works in Python and JavaScript, not C.
