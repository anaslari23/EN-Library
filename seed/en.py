# EN seed.   python3 en.py FILE.en [run|py|js|c]
import re, sys
W = {'plus': '+', 'minus': '-', 'times': '*', 'is greater than': '>', 'is less than': '<', 'is not': '!=', 'is': '=='}
# The phrasebook: one English line -> Python, JavaScript, C.  @0 @1 @2 = the parts of the line.
# A line ending in : or { opens a block; a line starting with } closes one.
P = [
 (r'set (\w+) to (.+)',               '@0 = @1',        'var @0 = @1;',          '@0 = @1;'),
 (r'make an empty list called (\w+)', '@0 = []',         'var @0 = [];',          'n_@0 = 0;'),
 (r'add (.+) to (\w+)',               '@1.append(@0)',  '@1.push(@0);',          '@1[n_@1++] = @0;'),
 (r'for each (\w+) in (\w+)',         'for @0 in @1:',  'for (var @0 of @1) {',  'for (int k = 0; k < n_@1 && ((@0 = @1[k]) || 1); k++) {'),
 (r'if (.+?) (is greater than|is less than|is not|is) (.+) then', 'if @0 @1 @2:', 'if (@0 @1 @2) {', 'if (@0 @1 @2) {'),
 (r'otherwise',                       '}else:',         '} else {',              '} else {'),
 (r'end (?:if|for)',                  '}',              '}',                     '}'),
]
def x(e):                                  # English words -> operators, names get a prefix; the target language does the precedence
    return re.sub(r'"[^"]*"|\w+', lambda m: W.get(m[0], m[0] if m[0][0] in '"0123456789' else 'e_' + m[0]), e)
def compile(src, L):
    k, out, ind, v, decl = 'py js c'.split().index(L) + 1, [], 1, {}, []
    isText = lambda e: e[0] == '"' or v.get(e.split()[0]) == 's'
    lines = [l.strip() for l in src.splitlines() if l.strip() and l.strip()[0] != '#' and not l.startswith('target')]
    for l in lines:                        # C needs every variable declared first
        if m := re.fullmatch(r'set (\w+) to (.+)', l): v.setdefault(m[1], 's' if isText(m[2]) else 'i')
        if m := re.fullmatch(r'make an empty list called (\w+)', l): v[m[1]] = 'l'
        if m := re.fullmatch(r'for each (\w+) in \w+', l): v[m[1]] = 'i'
    for n, t in v.items(): decl.append(f'long long e_{n}[99]; int n_e_{n};' if t == 'l' else f'{"char *" if t == "s" else "long long "}e_{n};')
    for l in lines:
        if m := re.fullmatch(r'show (.+)', l):
            p = re.split(r' and (?=(?:[^"]*"[^"]*")*[^"]*$)', m[1])
            s = ('print(' + '+'.join(f'str({x(a)})' for a in p) + ')' if k == 1 else
                 'console.log(' + '+'.join(f'String({x(a)})' for a in p) + ');' if k == 2 else
                 'printf("' + ''.join('%s' if isText(a) else '%lld' for a in p) + '\\n", ' + ', '.join(x(a) for a in p) + ');')
        else:
            for r, *t in P:
                if m := re.fullmatch(r, l): break
            else: sys.exit('I do not understand: ' + l)
            g = [x(a) if a not in W else W[a] for a in m.groups()]
            if len(g) == 3 and L == 'c' and isText(m[1]): g = [f'strcmp({g[0]}, {g[2]})', g[1], '0']
            s = re.sub(r'@(\d)', lambda q: g[int(q[1])], t[k - 1])
        if L == 'c': s = re.sub(r'"[^"]*"|\b\d+\b', lambda q: q[0] if q[0][0] == '"' else q[0] + 'LL', s)   # whole numbers are 64-bit, as in EN
        if L == 'py' and s[:1] == '}' and out and out[-1][-1] == ':': out.append('    ' * ind + 'pass')   # an empty block
        if s[:1] == '}': ind -= 1
        if L == 'py' and s[:1] == '}': s = s[1:]
        if s: out.append('    ' * ind + s)
        if s[-1:] in (':', '{'): ind += 1
    body = '\n'.join(o[4:] for o in out) if L != 'c' else '\n'.join(o for o in out)
    return ('#include <stdio.h>\n#include <string.h>\nint main(void) {\n    ' + '\n    '.join(decl) + '\n' + body + '\n}') if L == 'c' else body
def run(src): exec(compile(src, 'py'))                 # import en; en.run('show "hi"')
if __name__ == '__main__':
    code = compile(open(sys.argv[1]).read(), 'py' if sys.argv[2:] in ([], ['run']) else sys.argv[2])
    exec(code) if sys.argv[2:] in ([], ['run']) else print(code)
