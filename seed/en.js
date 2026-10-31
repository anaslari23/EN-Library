// EN seed for a browser console or node.   en(`set x to 2\nshow "x is " and x times 3`)   ->   prints, and returns the JavaScript
function en(src, run = true) {
  const W = {plus: '+', minus: '-', times: '*', 'is greater than': '>', 'greater than': '>', 'is less than': '<', 'less than': '<', 'is not': '!==', is: '==='};
  const AND = / and (?=(?:[^"]*"[^"]*")*[^"]*$)/;
  const args = s => s ? s.split(AND).map(x).join(', ') : '';
  const x = e => {
    let m = e.match(/^call (\w+)\.(\w+)(?: with (.+))?$/);      // a call: object.method(arguments), or super's
    if (m) return (m[1] == 'super' ? 'super.' + (m[2] == 'init' ? 'init' : 'e_' + m[2]) : x(m[1]) + '.e_' + m[2]) + '(' + args(m[3]) + ')';
    return e.replace(/"[^"]*"|\w+(?:\.\w+)*/g, w => {
      if (W[w]) return W[w];
      if (/^["0-9]/.test(w)) return w;
      const [h, ...t] = w.split('.');
      return [h == 'self' ? 'this' : 'e_' + h, ...t.map(a => 'e_' + a)].join('.');
    });
  };
  const P = [   // the phrasebook: English line -> JavaScript.  $0 $1 $2 are its parts; (?<l>..) is a list "a and b"
    [/^set (\w+) to (.+)$/, 'var $0 = $1;'], [/^set (\w+\.\w+) to (.+)$/, '$0 = $1;'],
    [/^make an empty list called (\w+)$/, 'var $0 = [];'], [/^add (.+) to (\w+)$/, '$1.push($0);'],
    [/^for each (\w+) in (\w+)$/, 'for (var $0 of $1) {'],
    [/^if (.+?) (is greater than|is less than|greater than|less than|is not|is) (.+) then$/, 'if ($0 $1 $2) {'], [/^otherwise$/, '} else {'],
    [/^define a class called (\w+) that extends (\w+)$/, 'class $0 extends $1 {'], [/^define a class called (\w+)$/, 'class $0 {'],
    [/^define a constructor(?: with parameters? (?<l>.+))?$/, 'init($0) {'],
    [/^define a method called (\w+)(?: with parameters? (?<l>.+))?$/, '$0($1) {'], [/^return (.+)$/, 'return $0;'],
    [/^make an? (\w+) called (\w+)(?: with (?<l>.+))?$/, 'var $1 = mk($0, $2);'], [/^(call .+)$/, '$0;'],
    [/^end (?:if|for|class|method|constructor)$/, '}'],
  ];
  const code = (/define a class/.test(src) ? 'function mk(C, ...a) { const o = new C(); if (o.init) o.init(...a); return o; }\n' : '') +
    src.split('\n').map(l => l.trim()).filter(l => l && l[0] !== '#' && !l.startsWith('target')).map(l => {
    let m = l.match(/^show (.+)$/);
    if (m) return 'console.log(' + m[1].split(AND).map(a => 'String(' + x(a) + ')').join('+') + ');';
    for (const [r, t] of P) if ((m = l.match(r))) {
      const g = m.slice(1).map(a => a === undefined ? '' : W[a] || x(a));
      if (m.groups) g[m.slice(1).indexOf(m.groups.l)] = args(m.groups.l);
      return t.replace(/\$(\d)/g, (_, i) => g[i]);
    }
    throw new Error('I do not understand: ' + l);
  }).join('\n');
  if (run) new Function(code)();
  return code;
}
if (typeof module !== 'undefined') module.exports = en;
