"""The single source of truth for the structure and directives of an .en file."""

from dataclasses import dataclass
import re

from .errors import CodeInEnglishError


SUPPORTED_VERSIONS: frozenset[tuple[int, int]] = frozenset({(0, 1), (0, 2)})
MIGRATION_PATHS: dict[tuple[int, int] | None, tuple[int, int]] = {
    None: (0, 1),
    (0, 1): (0, 2),
}
LIBRARY_DIRECTIVE = "import codeinpython library"


@dataclass(frozen=True)
class SourceLine:
    line: int
    col_offset: int
    text: str


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    hint: str | None = None
    related: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class SourceContract:
    version: tuple[int, int] | None
    target: str
    form: str | None
    lines: tuple[SourceLine, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def ok(self) -> bool:
        return not any(item.severity == "error" for item in self.diagnostics)


class ENSourceError(CodeInEnglishError):
    def __init__(self, diagnostics: tuple[Diagnostic, ...]):
        self.diagnostics = diagnostics
        first = diagnostics[0] if diagnostics else Diagnostic("EN-E000", "error", "invalid source", "<string>", 1, 1, 1, 2)
        self.filename = first.file
        self.line = first.line
        self.column = first.column
        self.message = first.message
        self.kind = "source"
        super().__init__(first.file, first.line, first.message, kind="source", column=first.column)
        self.args = (f"{first.file}:{first.line}:{first.column}: {first.message}",)


def read_contract(source: str, filename: str) -> SourceContract:
    """Parse the source contract without raising for malformed user source."""
    source = source.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = source.splitlines()
    if not raw_lines and source == "":
        raw_lines = []
    diagnostics: list[Diagnostic] = []

    def report(code: str, severity: str, line: int, message: str, *, column: int = 1,
               hint: str | None = None, related: tuple[tuple[int, int], ...] = ()) -> None:
        diagnostics.append(Diagnostic(code, severity, message, filename, line, column, line, column + 1, hint, related))

    def content_kind(text: str) -> str:
        stripped = text.strip()
        if not stripped:
            return "blank"
        if stripped.startswith("#?"):
            return "request"
        if stripped.startswith("#"):
            return "comment"
        return "code"

    header_index: int | None = None
    version: tuple[int, int] | None = None
    first_content: int | None = next((i for i, text in enumerate(raw_lines) if content_kind(text) not in ("blank", "comment")), None)
    version_re = re.compile(r"en (\d+)\.(\d+)")
    for i, text in enumerate(raw_lines):
        stripped = text.strip()
        if content_kind(text) in ("blank", "comment"):
            continue
        match = version_re.fullmatch(stripped)
        if match:
            if header_index is None and i == first_content:
                header_index = i
                version = (int(match.group(1)), int(match.group(2)))
                if version not in SUPPORTED_VERSIONS:
                    supported = ", ".join(f"en {major}.{minor}" for major, minor in sorted(SUPPORTED_VERSIONS)) or "none"
                    newer = bool(SUPPORTED_VERSIONS) and version > max(SUPPORTED_VERSIONS)
                    if version in MIGRATION_PATHS:
                        hint = "Run python -m codeinenglish migrate."
                    elif newer:
                        hint = "Upgrade codeinenglish."
                    else:
                        hint = None
                    suffix = f" {hint}" if hint else ""
                    report("EN-E103", "error", i + 1,
                           f"This file says en {version[0]}.{version[1]}, but this install supports only {supported}.{suffix}",
                           hint=hint)
            else:
                code = "EN-E104" if header_index is not None else "EN-E101"
                if code == "EN-E104":
                    message = "There is more than one version line. Keep only the first."
                else:
                    message = f'The version line must come before everything except comments. Move "{stripped}" above line {i + 1}.'
                related = ((header_index + 1, 1),) if header_index is not None else ()
                report(code, "error", i + 1, message, related=related)
        elif stripped == "en" or stripped.startswith("en ") or stripped.startswith("en\t"):
            if i == first_content:
                report("EN-E102", "error", i + 1, f'"{stripped}" is not a valid version. Write it like "en 0.2".')

    legacy = version is None
    if legacy:
        report("EN-W401", "warning", first_content + 1 if first_content is not None else 1,
               'No version line: treating this file as legacy. Run "python -m codeinenglish migrate".')

    versioned_02 = version == (0, 2)
    target = "python"
    target_directive: tuple[str, int, bool] | None = None
    targets: list[tuple[str, int, bool]] = []
    directive_indices: set[int] = set()
    content_started = False
    request_lines: list[SourceLine] = []
    instructions: list[SourceLine] = []
    request_block_count = 0
    in_request = False
    request_nonempty = False
    saw_request_marker = False
    saw_legacy_marker = False
    request_like_comments: list[tuple[int, str]] = []

    for i, original in enumerate(raw_lines):
        line_number = i + 1
        stripped = original.strip()
        kind = content_kind(original)
        if kind == "blank":
            if versioned_02 and in_request:
                in_request = False
            continue
        if i == header_index:
            continue
        if versioned_02 and in_request and kind != "request":
            in_request = False
        if kind == "comment" or (kind == "request" and not versioned_02):
            if versioned_02:
                if not instructions and not saw_request_marker and re.search(r"\b(write|create|make|build|find|return)\b.{0,60}\b(program|function|numbers|values|list|string|array)\b", stripped[1:], re.I):
                    request_like_comments.append((line_number, stripped))
                continue
            if stripped.startswith("#?"):
                saw_legacy_marker = True
            # Legacy mode retains all comment lines for problem extraction; instruction parser ignores them.
            indent = len(original) - len(original.lstrip())
            comment_text = original[indent + 1:]
            removed = indent + 1
            if comment_text.startswith(" "):
                comment_text = comment_text[1:]
                removed += 1
            request_lines.append(SourceLine(line_number, removed, comment_text.rstrip()))
            continue
        if kind == "request" and versioned_02:
            if not in_request:
                request_block_count += 1
                in_request = True
                if request_block_count > 1:
                    report("EN-E301", "error", line_number,
                           "Only one #? request is allowed per file. Move the second one to its own file.")
            saw_request_marker = True
            indent = len(original) - len(original.lstrip())
            content = original[indent + 2:]
            if content.startswith(" "):
                content = content[1:]
            if content.strip():
                request_nonempty = True
            request_lines.append(SourceLine(line_number, indent + 2 + (1 if original[indent + 2:].startswith(" ") else 0), content))
            content_started = True
            continue

        folded = stripped.casefold()
        is_alias = folded == LIBRARY_DIRECTIVE
        target_match = folded == "target" or folded.startswith("target ") or folded.startswith("target\t")
        if is_alias or target_match:
            if versioned_02 and is_alias:
                report("EN-E203", "error", line_number,
                       '"import codeinpython library" is not allowed in en 0.2. Write "target python".', hint="target python")
                continue
            if target_match:
                # 0.2 keywords are exact lowercase; 0.1 and legacy retain case folding.
                if versioned_02 and not stripped.startswith("target"):
                    report("EN-E202", "error", line_number,
                           f'Unknown target directive "{stripped}". Supported targets: python, javascript.')
                    continue
                words = stripped.split()
                if len(words) != 2 or (versioned_02 and words[0] != "target"):
                    report("EN-E202", "error", line_number, f'Unknown target directive "{stripped}". Supported targets: python, javascript.')
                    continue
                name = words[1] if versioned_02 else words[1].casefold()
                if name not in ("python", "javascript"):
                    report("EN-E202", "error", line_number, f'Unknown target "{name}". Supported targets: python, javascript.')
                    continue
            else:
                name = "python"
            if content_started:
                report("EN-E204", "error", line_number, '"target" must come before the instructions or the request.')
                continue
            targets.append((name, line_number, is_alias))
            directive_indices.add(i)
            if len(targets) > 1:
                previous, previous_line, _ = targets[0]
                if name == previous:
                    code = "EN-E205"
                    message = f"Line {line_number} repeats the target already set on line {previous_line}. Remove the repeated line."
                else:
                    code = "EN-E201"
                    message = f"Line {line_number} asks for target {name}, but line {previous_line} already chose {previous}. Keep only one target line."
                report(code, "error", line_number, message, related=((previous_line, 1),))
            else:
                target_directive = (name, line_number, is_alias)
                target = name
            continue

        if versioned_02 and kind == "comment":
            continue
        content_started = True
        instructions.append(SourceLine(line_number, 0, original))

    if versioned_02 and not instructions and not saw_request_marker:
        for line_number, _comment in request_like_comments:
            report("EN-W402", "warning", line_number,
                   'This comment looks like a request but is ignored in en 0.2. Use "#?" to make it a request.')

    if legacy and saw_legacy_marker:
        marker_line = next(line.line for line in request_lines if raw_lines[line.line - 1].lstrip().startswith("#?"))
        report("EN-W403", "warning", marker_line,
               f'Line {marker_line} starts with "#?", which is only a request marker in en 0.2. Without a version line, legacy rules decide what it is: documentation in a file with instructions, request text in a comment-only file. Add "en 0.2" above it to use the marker.')

    if versioned_02:
        if saw_request_marker and instructions:
            report("EN-E302", "error", request_lines[0].line,
                   "A file cannot mix #? requests with instruction lines.")
        if saw_request_marker and not request_nonempty:
            report("EN-E303", "error", request_lines[0].line, "This #? request is empty.")
        if not saw_request_marker and not instructions:
            report("EN-E305", "error", first_content + 1 if first_content is not None else 1,
                   "Nothing to generate: no instructions and no #? request.")
        form = "problem" if saw_request_marker and not instructions else "instructions" if instructions else None
        if form == "problem":
            lines = request_lines
        elif form == "instructions":
            lines = [SourceLine(i + 1, 0, text) for i, text in enumerate(raw_lines)
                     if i != header_index and i not in directive_indices and content_kind(text) != "comment"]
        else:
            lines = []
    else:
        if target_directive and (target_directive[2] or not instructions):
            form = "problem"
            lines = request_lines
        else:
            form = "instructions"
            lines = [SourceLine(i + 1, 0, text) for i, text in enumerate(raw_lines)
                     if i != header_index and i not in directive_indices]

    return SourceContract(version, target, form, tuple(lines), tuple(diagnostics))
