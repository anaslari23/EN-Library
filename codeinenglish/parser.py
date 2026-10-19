import keyword
import re

from .errors import CodeInEnglishError
from .expressions import parse_expression
from .ir import (
    Append,
    Attribute,
    Assign,
    Binary,
    Compare,
    Contains,
    ClassDef,
    CreateInstance,
    CreateDictionary,
    CreateList,
    Display,
    Expr,
    ForEach,
    If,
    Index,
    Name,
    MethodCall,
    MethodDef,
    Program,
    ReadInput,
    Return,
    SetAttribute,
    SetItem,
    Statement,
)


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_RESERVED_NAMES = {"input", "print", "str"}


def _split_display(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
    quoted: str | None = None
    escaped = False
    depth = 0
    index = 0
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif quoted and char == "\\":
            escaped = True
        elif quoted and char == quoted:
            quoted = None
        elif not quoted and char in ('"', "'"):
            quoted = char
        elif not quoted and char == "(":
            depth += 1
        elif not quoted and char == ")":
            depth -= 1
        elif not quoted and depth == 0 and text.startswith(" and ", index):
            parts.append(text[start:index].strip())
            index += 4
            start = index
            continue
        index += 1
    parts.append(text[start:].strip())
    return parts


def _validate_expression(expression: Expr, names: set[str], filename: str, line: int) -> None:
    if isinstance(expression, Name):
        if expression.identifier not in names:
            raise CodeInEnglishError(
                filename, line, f"unknown name {expression.identifier!r}", kind="unknown_name"
            )
        return
    if isinstance(expression, Compare):
        _validate_expression(expression.left, names, filename, line)
        if isinstance(expression.right, Name) and expression.right.identifier not in names:
            raise CodeInEnglishError(
                filename,
                line,
                f"{expression.right.identifier!r} could be a missing variable or text; quote the text or define the variable",
                kind="ambiguous",
            )
        _validate_expression(expression.right, names, filename, line)
        return
    if isinstance(expression, Contains):
        _validate_expression(expression.item, names, filename, line)
        _validate_expression(expression.collection, names, filename, line)
        return
    if isinstance(expression, Attribute):
        _validate_expression(expression.value, names, filename, line)
        return
    if isinstance(expression, MethodCall):
        _validate_expression(expression.value, names, filename, line)
        for argument in expression.arguments:
            _validate_expression(argument, names, filename, line)
        return
    if isinstance(expression, Index):
        _validate_expression(expression.collection, names, filename, line)
        _validate_expression(expression.index, names, filename, line)
        return
    if isinstance(expression, Binary):
        _validate_expression(expression.left, names, filename, line)
        _validate_expression(expression.right, names, filename, line)


def _check_name(name: str, filename: str, line: int) -> None:
    if not _IDENTIFIER.fullmatch(name) or keyword.iskeyword(name):
        raise CodeInEnglishError(filename, line, f"{name!r} is not a valid Python variable name")
    if name in _RESERVED_NAMES:
        raise CodeInEnglishError(filename, line, f"{name!r} is reserved by the translator")


def parse_program(source: str, filename: str = "<string>") -> Program:
    """Parse supported English statements into a source-located program IR."""
    statements: list[Statement] = []
    names: set[str] = set()
    collection_kinds: dict[str, str] = {}
    classes: set[str] = set()
    loop_scopes: list[set[str]] = []
    blocks: list[dict] = []

    def visible_names() -> set[str]:
        result = set(names)
        for scope in loop_scopes:
            result.update(scope)
        return result

    def define_name(name: str) -> None:
        if loop_scopes:
            loop_scopes[-1].add(name)
        else:
            names.add(name)

    def append(statement: Statement) -> None:
        if not blocks:
            statements.append(statement)
            return
        frame = blocks[-1]
        if frame["kind"] == "if" and frame["branch"] == "otherwise":
            frame["otherwise"].append(statement)
        elif frame["kind"] == "class":
            raise CodeInEnglishError(filename, frame["line"], "classes may contain method definitions only")
        elif frame["kind"] == "method" and len(blocks) == 2:
            frame["body"].append(statement)
        else:
            frame["body"].append(statement)

    def close_block(expected_kind: str, line_number: int) -> None:
        if not blocks:
            raise CodeInEnglishError(filename, line_number, f"end {expected_kind} without a matching block")
        frame = blocks[-1]
        if frame["kind"] != expected_kind:
            raise CodeInEnglishError(
                filename,
                line_number,
                f"end {expected_kind} cannot close the open {frame['kind']} block",
            )
        blocks.pop()
        if expected_kind == "if":
            statement = If(frame["condition"], frame["body"], frame["otherwise"])
        elif expected_kind == "for":
            loop_scopes.pop()
            statement = ForEach(frame["name"], frame["collection"], frame["body"])
        elif expected_kind == "method":
            if len(blocks) != 1 or blocks[-1]["kind"] != "class":
                raise CodeInEnglishError(filename, line_number, "method must be directly inside a class")
            loop_scopes.pop()
            blocks[-1]["methods"].append(MethodDef(frame["name"], frame["parameters"], frame["body"]))
            return
        else:
            statement = ClassDef(frame["name"], frame["methods"])
        append(statement)

    for line_number, original in enumerate(source.splitlines(), start=1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if original != original.lstrip():
            raise CodeInEnglishError(filename, line_number, "unexpected indentation; use matching end markers to close blocks")

        if line.startswith("if "):
            match = re.fullmatch(r"if\s+(.+)\s+then", line)
            if not match:
                raise CodeInEnglishError(filename, line_number, "use: if condition then")
            condition = parse_expression(match.group(1), filename=filename, line=line_number)
            if not isinstance(condition, (Compare, Contains)):
                raise CodeInEnglishError(filename, line_number, "an if condition must compare values or check membership")
            _validate_expression(condition, visible_names(), filename, line_number)
            blocks.append({
                "kind": "if", "condition": condition, "line": line_number,
                "body": [], "otherwise": None, "branch": "body",
            })
            continue

        class_match = re.fullmatch(r"define a class called ([A-Za-z_][A-Za-z0-9_]*)", line)
        if class_match:
            if blocks:
                raise CodeInEnglishError(filename, line_number, "class definitions must be top-level")
            name = class_match.group(1)
            _check_name(name, filename, line_number)
            if name in classes or name in visible_names():
                raise CodeInEnglishError(filename, line_number, f"{name!r} is already defined")
            classes.add(name)
            blocks.append({"kind": "class", "name": name, "methods": [], "line": line_number})
            continue

        method_match = re.fullmatch(
            r"define a method called ([A-Za-z_][A-Za-z0-9_]*)(?: with parameters? (.+))?", line
        )
        if method_match:
            if not blocks or blocks[-1]["kind"] != "class":
                raise CodeInEnglishError(filename, line_number, "methods must be defined inside a class")
            name, raw_parameters = method_match.groups()
            _check_name(name, filename, line_number)
            parameters = re.split(r"\s+and\s+", raw_parameters) if raw_parameters else []
            for parameter in parameters:
                _check_name(parameter, filename, line_number)
            if len(parameters) != len(set(parameters)):
                raise CodeInEnglishError(filename, line_number, "method parameters must be unique")
            loop_scopes.append({"self", *parameters})
            blocks.append({"kind": "method", "name": name, "parameters": parameters, "body": [], "line": line_number})
            continue

        if line == "end method":
            close_block("method", line_number)
            continue
        if line == "end class":
            close_block("class", line_number)
            continue

        if line.startswith("for each "):
            match = re.fullmatch(r"for each\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+([A-Za-z_][A-Za-z0-9_]*)", line)
            if not match:
                raise CodeInEnglishError(filename, line_number, "use: for each ITEM in LIST")
            loop_name, collection_name = match.groups()
            _check_name(loop_name, filename, line_number)
            if collection_name not in visible_names():
                raise CodeInEnglishError(filename, line_number, f"unknown collection {collection_name!r}", kind="unknown_name")
            if collection_kinds.get(collection_name) != "list":
                raise CodeInEnglishError(filename, line_number, f"{collection_name!r} is not a list created with 'make an empty list'")
            loop_scopes.append({loop_name})
            blocks.append({
                "kind": "for", "name": loop_name, "collection": Name(collection_name),
                "line": line_number, "body": [],
            })
            continue

        if line == "otherwise":
            if not blocks or blocks[-1]["kind"] != "if":
                raise CodeInEnglishError(filename, line_number, "otherwise must appear inside an if block")
            frame = blocks[-1]
            if frame["otherwise"] is not None:
                raise CodeInEnglishError(filename, line_number, "only one otherwise is allowed")
            frame["otherwise"] = []
            frame["branch"] = "otherwise"
            continue

        if line == "end if":
            close_block("if", line_number)
            continue
        if line == "end for":
            close_block("for", line_number)
            continue

        instance_match = re.fullmatch(r"make a ([A-Za-z_][A-Za-z0-9_]*) called ([A-Za-z_][A-Za-z0-9_]*)", line)
        if instance_match:
            class_name, name = instance_match.groups()
            if class_name not in classes:
                raise CodeInEnglishError(filename, line_number, f"unknown class {class_name!r}", kind="unknown_name")
            _check_name(name, filename, line_number)
            define_name(name)
            append(CreateInstance(class_name, name))
            continue

        attribute_assignment = re.fullmatch(r"set ([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*) to (.+)", line)
        if attribute_assignment:
            receiver, attribute, raw_value = attribute_assignment.groups()
            if receiver not in visible_names():
                raise CodeInEnglishError(filename, line_number, f"unknown name {receiver!r}", kind="unknown_name")
            value = parse_expression(raw_value, filename=filename, line=line_number)
            _validate_expression(value, visible_names(), filename, line_number)
            append(SetAttribute(Name(receiver), attribute, value))
            continue

        if line.startswith("return "):
            if not any(frame["kind"] == "method" for frame in blocks):
                raise CodeInEnglishError(filename, line_number, "return is only allowed inside a method", kind="unsupported")
            value = parse_expression(line[7:], filename=filename, line=line_number)
            _validate_expression(value, visible_names(), filename, line_number)
            append(Return(value))
            continue

        if line.startswith("call "):
            expression = parse_expression(line, filename=filename, line=line_number)
            _validate_expression(expression, visible_names(), filename, line_number)
            append(expression)
            continue

        creation = re.fullmatch(r"make an empty (list|dictionary) called ([A-Za-z_][A-Za-z0-9_]*)", line)
        if creation:
            kind, name = creation.groups()
            _check_name(name, filename, line_number)
            define_name(name)
            collection_kinds[name] = kind
            append(CreateList(name) if kind == "list" else CreateDictionary(name))
            continue

        item_assignment = re.fullmatch(r"set ([A-Za-z_][A-Za-z0-9_]*) at (.+) to (.+)", line)
        if item_assignment:
            collection, raw_index, raw_value = item_assignment.groups()
            if collection not in visible_names():
                raise CodeInEnglishError(filename, line_number, f"unknown collection {collection!r}", kind="unknown_name")
            index = parse_expression(raw_index, filename=filename, line=line_number)
            value = parse_expression(raw_value, filename=filename, line=line_number)
            current_names = visible_names()
            _validate_expression(index, current_names, filename, line_number)
            _validate_expression(value, current_names, filename, line_number)
            append(SetItem(collection, index, value))
            continue

        addition = re.fullmatch(r"add (.+) to ([A-Za-z_][A-Za-z0-9_]*)", line)
        if addition:
            raw_value, collection = addition.groups()
            if collection not in visible_names():
                raise CodeInEnglishError(filename, line_number, f"unknown collection {collection!r}", kind="unknown_name")
            if collection_kinds.get(collection) != "list":
                raise CodeInEnglishError(filename, line_number, f"{collection!r} is not a list created with 'make an empty list'")
            value = parse_expression(raw_value, filename=filename, line=line_number)
            _validate_expression(value, visible_names(), filename, line_number)
            append(Append(collection, value))
            continue

        assignment = re.fullmatch(r"(?:set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to|let\s+([A-Za-z_][A-Za-z0-9_]*)\s+be)\s+(.+)", line)
        if assignment:
            name = assignment.group(1) or assignment.group(2)
            expression = parse_expression(assignment.group(3), filename=filename, line=line_number)
            _validate_expression(expression, visible_names(), filename, line_number)
            _check_name(name, filename, line_number)
            define_name(name)
            collection_kinds.pop(name, None)
            append(Assign(name, expression))
            continue

        read = re.fullmatch(r"ask for your (.+) and call it ([A-Za-z_][A-Za-z0-9_]*)", line)
        if read:
            prompt, name = read.groups()
            if not re.fullmatch(r"[A-Za-z][A-Za-z ]*", prompt):
                raise CodeInEnglishError(filename, line_number, "use words after 'ask for your'")
            _check_name(name, filename, line_number)
            define_name(name)
            collection_kinds.pop(name, None)
            append(ReadInput(name, prompt.strip()))
            continue

        if line.startswith("show "):
            raw_values = _split_display(line[5:])
            if not raw_values or any(not value for value in raw_values):
                raise CodeInEnglishError(filename, line_number, "show needs one or more values")
            values = [parse_expression(value, filename=filename, line=line_number) for value in raw_values]
            for value in values:
                _validate_expression(value, visible_names(), filename, line_number)
            append(Display(values))
            continue

        if line.startswith(("set ", "let ", "ask ", "if ", "for ", "add ")):
            raise CodeInEnglishError(filename, line_number, f"malformed instruction {line!r}")
        raise CodeInEnglishError(filename, line_number, f"unrecognized instruction {line!r}", kind="unsupported")

    if blocks:
        frame = blocks[-1]
        raise CodeInEnglishError(filename, frame["line"], f"{frame['kind']} block needs 'end {frame['kind']}'")
    return Program(statements)
