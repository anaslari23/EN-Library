// EN seed for a browser console or node.   en(`set x to 2\nshow "x is " and x times 3`)   ->   prints, and returns the JavaScript
function en(src, run = true) {
  const W = {plus: '+', minus: '-', times: '*', 'is greater than': '>', 'is less than': '<', 'is not': '!==', is: '==='};
  const x = e => e.replace(/"[^"]*"|\w+/g, m => W[m] || (/^["0-9]/.test(m) ? m : 'e_' + m));
  const P = [   // the phrasebook: English line -> JavaScript.  $1 $2 $3 are its parts
    [/^set (\w+) to (.+)$/, 'var $1 = $2;'], [/^make an empty list called (\w+)$/, 'var $1 = [];'],
    [/^add (.+) to (\w+)$/, '$2.push($1);'], [/^for each (\w+) in (\w+)$/, 'for (var $1 of $2) {'],
    [/^if (.+?) (is greater than|is less than|is not|is) (.+) then$/, 'if ($1 $2 $3) {'],
    [/^otherwise$/, '} else {'], [/^end (if|for)$/, '}'],
  ];
  const code = src.split('\n').map(l => l.trim()).filter(l => l && l[0] !== '#' && !l.startsWith('target')).map(l => {
    let m = l.match(/^show (.+)$/);
    if (m) return 'console.log(' + m[1].split(/ and (?=(?:[^"]*"[^"]*")*[^"]*$)/).map(a => 'String(' + x(a) + ')').join('+') + ');';
    for (const [r, t] of P) if ((m = l.match(r))) return t.replace(/\$(\d)/g, (_, i) => (W[m[i]] || x(m[i])));
    throw new Error('I do not understand: ' + l);
  }).join('\n');
  if (run) new Function(code)();
  return code;
}
if (typeof module !== 'undefined') module.exports = en;
