# EN seed.   python3 en.py FILE.en [run|py|js|c]
import re, sys
W = {'plus': '+', 'minus': '-', 'times': '*', 'is greater than': '>', 'greater than': '>', 'is less than': '<', 'less than': '<', 'is not': '!=', 'is': '=='}
AND = r' and (?=(?:[^"]*"[^"]*")*[^"]*$)'  # " and " outside quotes
# The phrasebook: one English line -> Python, JavaScript, C (None = not in C).  @0 @1 @2 = the parts of the line.
# A line ending in : or { opens a block; a line starting with } closes one.  (?P<l>..) is a list: "a and b".
P = [
 (r'set (\w+) to (.+)',                 '@0 = @1',          'var @0 = @1;',            '@0 = @1;'),
 (r'set (\w+\.\w+) to (.+)',            '@0 = @1',          '@0 = @1;',                None),
 (r'make an empty list called (\w+)',   '@0 = []',          'var @0 = [];',            'n_@0 = 0;'),
 (r'add (.+) to (\w+)',                 '@1.append(@0)',    '@1.push(@0);',            '@1[n_@1++] = @0;'),
 (r'for each (\w+) in (\w+)',           'for @0 in @1:',    'for (var @0 of @1) {',    'for (int k = 0; k < n_@1 && ((@0 = @1[k]) || 1); k++) {'),
 (r'if (.+?) (is greater than|is less than|greater than|less than|is not|is) (.+) then', 'if @0 @1 @2:', 'if (@0 @1 @2) {', 'if (@0 @1 @2) {'),
 (r'otherwise',                         '}else:',           '} else {',                '} else {'),
 (r'define a class called (\w+) that extends (\w+)', 'class @0(@1):', 'class @0 extends @1 {', None),
 (r'define a class called (\w+)',       'class @0:',        'class @0 {',              None),
 (r'define a constructor(?: with parameters? (?P<l>.+))?', 'def __init__(self, @0):', 'init(@0) {', None),
 (r'define a method called (\w+)(?: with parameters? (?P<l>.+))?', 'def @0(self, @1):', '@0(@1) {', None),
 (r'return (.+)',                       'return @0',        'return @0;',              None),
 (r'make an? (\w+) called (\w+)(?: with (?P<l>.+))?', '@1 = @0(@2)', 'var @1 = mk(@0, @2);', None),
 (r'(call .+)',                         '@0',               '@0;',                     None),
 (r'end (?:if|for|class|method|constructor)', '}',          '}',                       '}'),
]
def args(s, L):                            # "a and b" -> "e_a, e_b"
    return ', '.join(x(a, L) for a in re.split(AND, s)) if s else ''
def x(e, L):                               # English words -> operators, names get a prefix; the target language does the precedence
    if m := re.fullmatch(r'call (\w+)\.(\w+)(?: with (.+))?', e):      # a call: object.method(arguments), or super's
        r, n, a = m[1], m[2], args(m[3], L)
        if r != 'super': return f'{x(r, L)}.e_{n}({a})'
        return ('super().' if L == 'py' else 'super.') + ({'py': '__init__', 'js': 'init'}[L] if n == 'init' else 'e_' + n) + f'({a})'
    def name(m):
        w = m[0]
        if w in W: return W[w]
        if w[0] in '"0123456789': return w
        h, *t = w.split('.')
        return '.'.join([{'self': 'self' if L == 'py' else 'this'}.get(h, 'e_' + h)] + ['e_' + a for a in t])
    return re.sub(r'"[^"]*"|\w+(?:\.\w+)*', name, e)
def compile(src, L):
    k, out, ind, v, decl = 'py js c'.split().index(L) + 1, [], 1, {}, []
    isText = lambda e: e[0] == '"' or v.get(e.split()[0]) == 's'
    lines = [l.strip() for l in src.splitlines() if l.strip() and l.strip()[0] != '#' and not l.startswith('target')]
    for l in lines:                        # C needs every variable declared first
        if m := re.fullmatch(r'set (\w+) to (.+)', l): v.setdefault(m[1], 's' if isText(m[2]) else 'i')
        if m := re.fullmatch(r'make an empty list called (\w+)', l): v[m[1]] = 'l'
        if m := re.fullmatch(r'for each (\w+) in \w+', l): v[m[1]] = 'i'
    for n, t in v.items(): decl.append(f'long long e_{n}[99]; int n_e_{n};' if t == 'l' else f'{"char *" if t == "s" else "long long "}e_{n};')
    if L == 'js' and 'define a class' in src: out.append('    function mk(C, ...a) { const o = new C(); if (o.init) o.init(...a); return o; }')
    for l in lines:
        if m := re.fullmatch(r'show (.+)', l):
            p = re.split(AND, m[1])
            s = ('print(' + '+'.join(f'str({x(a, L)})' for a in p) + ')' if k == 1 else
                 'console.log(' + '+'.join(f'String({x(a, L)})' for a in p) + ');' if k == 2 else
                 'printf("' + ''.join('%s' if isText(a) else '%lld' for a in p) + '\\n", ' + ', '.join(x(a, L) for a in p) + ');')
        else:
            for r, *t in P:
                if m := re.fullmatch(r, l): break
            else: sys.exit('I do not understand: ' + l)
            if not t[k - 1]: sys.exit(f'{L} does not have that: {l}')
            g = [W[a] if a in W else x(a, L) if a else '' for a in m.groups()]
            if m.re.groupindex.get('l'): g[m.re.groupindex['l'] - 1] = args(m['l'], L)
            if len(g) == 3 and L == 'c' and isText(m[1]): g = [f'strcmp({g[0]}, {g[2]})', g[1], '0']
            s = re.sub(r'@(\d)', lambda q: g[int(q[1])], t[k - 1])
        if L == 'c': s = re.sub(r'"[^"]*"|\b\d+\b', lambda q: q[0] if q[0][0] == '"' else q[0] + 'LL', s)   # whole numbers are 64-bit, as in EN
        if L == 'py' and s[:1] == '}' and out and out[-1][-1] == ':': out.append('    ' * ind + 'pass')   # an empty block
        if s[:1] == '}': ind -= 1
        if L == 'py' and s[:1] == '}': s = s[1:]
        if s: out.append('    ' * ind + s)
        if s[-1:] in (':', '{'): ind += 1
    body = '\n'.join(o[4:] for o in out)
    return ('#include <stdio.h>\n#include <string.h>\nint main(void) {\n    ' + '\n    '.join(decl) + '\n' + body + '\n}') if L == 'c' else body
def run(src): exec(compile(src, 'py'))                 # import en; en.run('show "hi"')
if __name__ == '__main__':
    code = compile(open(sys.argv[1]).read(), 'py' if sys.argv[2:] in ([], ['run']) else sys.argv[2])
    exec(code) if sys.argv[2:] in ([], ['run']) else print(code)
