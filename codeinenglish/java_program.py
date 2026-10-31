"""Java backend for whole instruction programs.

Values are dynamic (`Object`) and the `En` runtime class reproduces Python's behaviour (typing, errors, printing),
the same approach as the JavaScript backend. EN classes become Java classes; every user method is `m_NAME` so it
can never collide with a Java keyword or an `Object` method. Run with `java File.java` (JDK 11+).
"""
import json

from .errors import CodeInEnglishError
from .ir import (
    Append, Assign, Attribute, Binary, ClassDef, Compare, Contains, CreateDictionary, CreateInstance,
    CreateList, Display, ForEach, If, Index, Literal, MethodCall, Name, Program, ReadInput, Return,
    SetAttribute, SetItem,
)

_IMPORTS = "import java.io.*;\nimport java.lang.reflect.*;\nimport java.util.*;\n"
_RUNTIME = r'''
class EnObject {
  final Map<String, Object> f = new HashMap<>();
}

final class En {
  static boolean T = true; // not a constant, so `return` never makes later code "unreachable" to javac
  static final BufferedReader IN = new BufferedReader(new InputStreamReader(System.in));
  static RuntimeException err(String message) { return new RuntimeException(message); }
  static String input(String prompt) {
    System.out.print(prompt);
    System.out.flush();
    try {
      String line = IN.readLine();
      if (line == null) throw err("EOF when reading a line");
      return line;
    } catch (IOException e) { throw err(e.getMessage()); }
  }
  static boolean num(Object o) { return o instanceof Long || o instanceof Double; }
  static double d(Object o) { return ((Number) o).doubleValue(); }
  static Object add(Object a, Object b) {
    if (a instanceof Long && b instanceof Long) return (Long) a + (Long) b;
    if (num(a) && num(b)) return d(a) + d(b);
    if (a instanceof String && b instanceof String) return (String) a + (String) b;
    if (a instanceof List && b instanceof List) { List<Object> r = new ArrayList<>((List<?>) a); r.addAll((List<?>) b); return r; }
    throw err("unsupported operand types for +");
  }
  static Object sub(Object a, Object b) {
    if (a instanceof Long && b instanceof Long) return (Long) a - (Long) b;
    if (num(a) && num(b)) return d(a) - d(b);
    throw err("unsupported operand types for -");
  }
  static Object mul(Object a, Object b) {
    if (a instanceof Long && b instanceof Long) return (Long) a * (Long) b;
    if (num(a) && num(b)) return d(a) * d(b);
    if (a instanceof String && b instanceof Long) return ((String) a).repeat((int) Math.max((Long) b, 0));
    throw err("unsupported operand types for *");
  }
  static Object div(Object a, Object b) {
    if (!num(a) || !num(b)) throw err("unsupported operand types for /");
    if (d(b) == 0) throw err("division by zero");
    return d(a) / d(b);
  }
  static boolean eq(Object a, Object b) {
    if (num(a) && num(b)) return d(a) == d(b);
    return Objects.equals(a, b);
  }
  @SuppressWarnings("unchecked")
  static int cmp(Object a, Object b, String op) {
    if (num(a) && num(b)) return Double.compare(d(a), d(b));
    if (a instanceof String && b instanceof String) return ((String) a).compareTo((String) b);
    throw err("'" + op + "' not supported between these types");
  }
  static boolean lt(Object a, Object b) { return cmp(a, b, "<") < 0; }
  static boolean gt(Object a, Object b) { return cmp(a, b, ">") > 0; }
  static boolean test(Object o) {
    if (o instanceof Boolean) return (Boolean) o;
    throw err("a condition must be true or false");
  }
  static int at(Object c, Object i) {
    if (!(i instanceof Long)) throw err("indices must be whole numbers");
    int size = c instanceof List ? ((List<?>) c).size() : ((String) c).length();
    long at = (Long) i < 0 ? size + (Long) i : (Long) i;
    if (at < 0 || at >= size) throw err("index out of range");
    return (int) at;
  }
  static Object get(Object c, Object i) {
    if (c instanceof Map) { Map<?, ?> m = (Map<?, ?>) c; if (!m.containsKey(i)) throw err("key not found: " + repr(i)); return m.get(i); }
    if (c instanceof List) return ((List<?>) c).get(at(c, i));
    if (c instanceof String) return String.valueOf(((String) c).charAt(at(c, i)));
    throw err("value is not indexable");
  }
  @SuppressWarnings("unchecked")
  static void set(Object c, Object i, Object v) {
    if (c instanceof Map) { ((Map<Object, Object>) c).put(i, v); return; }
    if (c instanceof List) { ((List<Object>) c).set(at(c, i), v); return; }
    throw err("value does not support item assignment");
  }
  @SuppressWarnings("unchecked")
  static void append(Object c, Object v) { ((List<Object>) c).add(v); }
  static boolean in(Object item, Object c) {
    if (c instanceof Map) return ((Map<?, ?>) c).containsKey(item);
    if (c instanceof String) return ((String) c).contains((String) item);
    for (Object x : (List<?>) c) if (eq(x, item)) return true;
    return false;
  }
  static Iterable<Object> iter(Object c) {
    if (c instanceof List) { @SuppressWarnings("unchecked") List<Object> l = (List<Object>) c; return l; }
    throw err("value is not a list");
  }
  static Object field(Object o, String name) {
    if (!(o instanceof EnObject) || !((EnObject) o).f.containsKey(name)) throw err("no field " + name);
    return ((EnObject) o).f.get(name);
  }
  static void setField(Object o, String name, Object v) {
    if (!(o instanceof EnObject)) throw err("cannot set a field on this value");
    ((EnObject) o).f.put(name, v);
  }
  static Method method(Object o, String name, int count) {
    if (o == null) throw err("cannot call a method on None");
    Method found = null;
    for (Method m : o.getClass().getMethods()) {
      if (m.getName().equals("m_" + name)) {
        if (m.getParameterCount() == count) return m;
        found = m;
      }
    }
    if (found != null) throw err((name.equals("__init__") ? "the constructor" : "'" + name + "'") + " takes " + found.getParameterCount() + " value(s) but got " + count);
    return null;
  }
  static Object call(Object o, String name, Object... args) {
    Method m = method(o, name, args.length);
    if (m == null) throw err("no method '" + name + "'");
    try { m.setAccessible(true); return m.invoke(o, args); }
    catch (InvocationTargetException e) { throw e.getCause() instanceof RuntimeException ? (RuntimeException) e.getCause() : err(String.valueOf(e.getCause())); }
    catch (IllegalAccessException e) { throw err(e.getMessage()); }
  }
  static Object neu(Object o, Object... args) {
    Method init = method(o, "__init__", args.length);
    if (init != null) call(o, "__init__", args);
    else if (args.length > 0) throw err("'" + o.getClass().getSimpleName().replaceFirst("^En_", "") + "' has no constructor, so it takes no values");
    return o;
  }
  static String repr(Object o) {
    if (o instanceof String) return "'" + ((String) o).replace("\\", "\\\\").replace("'", "\\'") + "'";
    return str(o);
  }
  static String str(Object o) {
    if (o == null) return "None";
    if (o instanceof Boolean) return (Boolean) o ? "True" : "False";
    if (o instanceof Double) {
      double x = (Double) o;
      return x == Math.rint(x) && Math.abs(x) < 1e16 ? String.valueOf((long) x) + ".0" : String.valueOf(x);
    }
    if (o instanceof List) {
      StringJoiner s = new StringJoiner(", ", "[", "]");
      for (Object x : (List<?>) o) s.add(repr(x));
      return s.toString();
    }
    if (o instanceof Map) {
      StringJoiner s = new StringJoiner(", ", "{", "}");
      for (Map.Entry<?, ?> e : ((Map<?, ?>) o).entrySet()) s.add(repr(e.getKey()) + ": " + repr(e.getValue()));
      return s.toString();
    }
    if (o instanceof EnObject) return "<" + o.getClass().getSimpleName().replaceFirst("^En_", "") + " object>";
    return String.valueOf(o);
  }
}
'''


def _fail(filename, message):
    raise CodeInEnglishError(filename, 1, message, kind="unsupported")


class _Generator:
    def __init__(self, filename):
        self.filename = filename

    def expr(self, node):
        if isinstance(node, Literal):
            value = node.value
            if isinstance(value, float) or (type(value) is int and abs(value) > 2**53 - 1):
                _fail(self.filename, "Java currently supports only exact integer, text, boolean, and null literals")
            if value is None:
                return "null"
            if isinstance(value, bool):
                return "Boolean.TRUE" if value else "Boolean.FALSE"
            if isinstance(value, int):
                return f"Long.valueOf({value}L)"
            return json.dumps(value, ensure_ascii=True)
        if isinstance(node, Name):
            return "this" if node.identifier == "self" else f"en_{node.identifier}"
        if isinstance(node, Binary):
            helper = {"+": "add", "-": "sub", "*": "mul", "/": "div"}[node.operator]
            return f"En.{helper}({self.expr(node.left)}, {self.expr(node.right)})"
        if isinstance(node, Compare):
            return f"((Object) {self.condition(node)})"
        if isinstance(node, Index):
            return f"En.get({self.expr(node.collection)}, {self.expr(node.index)})"
        if isinstance(node, Contains):
            return f"((Object) {self.condition(node)})"
        if isinstance(node, Attribute):
            return f"En.field({self.expr(node.value)}, {json.dumps(node.name)})"
        if isinstance(node, MethodCall):
            arguments = ", ".join(self.expr(argument) for argument in node.arguments)
            if node.value == Name("super"):
                return f"super.m_{'__init__' if node.name == 'init' else node.name}({arguments})"
            extra = f", {arguments}" if arguments else ""
            return f"En.call({self.expr(node.value)}, {json.dumps(node.name)}{extra})"
        _fail(self.filename, f"Java does not yet support {type(node).__name__} expressions")

    def condition(self, node):
        """A Java boolean for an if/compare/contains expression."""
        if isinstance(node, Compare):
            left, right = self.expr(node.left), self.expr(node.right)
            return {"==": f"En.eq({left}, {right})", "!=": f"!En.eq({left}, {right})",
                    ">": f"En.gt({left}, {right})", "<": f"En.lt({left}, {right})"}[node.operator]
        if isinstance(node, Contains):
            return f"En.in({self.expr(node.item)}, {self.expr(node.collection)})"
        return f"En.test({self.expr(node)})"

    def declared(self, statements):
        names = set()
        for node in statements:
            if isinstance(node, (Assign, ReadInput, CreateList, CreateDictionary, CreateInstance)):
                names.add(node.name)
            elif isinstance(node, ForEach):
                names.add(node.name)
                names |= self.declared(node.body)
            elif isinstance(node, If):
                names |= self.declared(node.body) | self.declared(node.otherwise or [])
        return names

    def block(self, statements, indent):
        pad, lines = "  " * indent, []
        for node in statements:
            if isinstance(node, Assign):
                lines.append(f"{pad}en_{node.name} = {self.expr(node.value)};")
            elif isinstance(node, ReadInput):
                lines.append(f"{pad}en_{node.name} = En.input({json.dumps(f'Your {node.prompt}: ')});")
            elif isinstance(node, Display):
                if not node.values:
                    _fail(self.filename, "Java display needs a value")
                lines.append(f"{pad}System.out.println({' + '.join(f'En.str({self.expr(value)})' for value in node.values)});")
            elif isinstance(node, If):
                lines.append(f"{pad}if ({self.condition(node.condition)}) {{")
                lines += self.block(node.body, indent + 1)
                if node.otherwise is not None:
                    lines.append(f"{pad}}} else {{")
                    lines += self.block(node.otherwise, indent + 1)
                lines.append(f"{pad}}}")
            elif isinstance(node, CreateList):
                lines.append(f"{pad}en_{node.name} = new ArrayList<Object>();")
            elif isinstance(node, CreateDictionary):
                lines.append(f"{pad}en_{node.name} = new LinkedHashMap<Object, Object>();")
            elif isinstance(node, Append):
                lines.append(f"{pad}En.append(en_{node.collection}, {self.expr(node.value)});")
            elif isinstance(node, SetItem):
                lines.append(f"{pad}En.set(en_{node.collection}, {self.expr(node.index)}, {self.expr(node.value)});")
            elif isinstance(node, ForEach):
                lines.append(f"{pad}for (Object en__item : En.iter({self.expr(node.collection)})) {{")
                lines.append(f"{pad}  en_{node.name} = en__item;")
                lines += self.block(node.body, indent + 1)
                lines.append(f"{pad}}}")
            elif isinstance(node, ClassDef):
                continue  # emitted as a top-level Java class
            elif isinstance(node, CreateInstance):
                arguments = "".join(f", {self.expr(argument)}" for argument in node.arguments)
                lines.append(f"{pad}en_{node.name} = En.neu(new En_{node.class_name}(){arguments});")
            elif isinstance(node, SetAttribute):
                lines.append(f"{pad}En.setField({self.expr(node.value)}, {json.dumps(node.name)}, {self.expr(node.expression)});")
            elif isinstance(node, Return):
                lines.append(f"{pad}if (En.T) return {self.expr(node.value)};")
            elif isinstance(node, MethodCall):
                lines.append(f"{pad}{self.expr(node)};")
            else:
                _fail(self.filename, f"Java does not yet support {type(node).__name__} instructions")
        return lines

    def class_def(self, node):
        parent = f"En_{node.parent}" if node.parent else "EnObject"
        lines = [f"class En_{node.name} extends {parent} {{"]
        for method in node.methods:
            parameters = ", ".join(f"Object en_{parameter}" for parameter in method.parameters)
            lines.append(f"  public Object m_{method.name}({parameters}) {{")
            local = sorted(self.declared(method.body) - set(method.parameters))
            lines += [f"    Object en_{name} = null;" for name in local]
            lines += self.block(method.body, 2)
            lines.append("    return null;")
            lines.append("  }")
        lines.append("}")
        return lines


def program_java(program: Program, filename: str) -> str:
    generator = _Generator(filename)
    names = sorted(generator.declared(program.statements))
    body = generator.block(program.statements, 2)
    main = ["final class EnProgram {  // first class: `java File.java` runs it",
            "  public static void main(String[] args) {",
            "    try {",
            "      run();",
            "    } catch (RuntimeException error) {",
            "      System.out.flush();",
            "      System.err.println(error.getMessage());",
            "      System.exit(1);",
            "    }",
            "  }",
            "  static void run() {",
            *[f"    Object en_{name} = null;" for name in names],
            *body,
            "  }",
            "}"]
    classes = [line for node in program.statements if isinstance(node, ClassDef) for line in generator.class_def(node)]
    return "\n".join([_IMPORTS, *main, *classes, _RUNTIME, ""])
