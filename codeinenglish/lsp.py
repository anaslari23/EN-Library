"""Zero-dependency Language Server Protocol (LSP) server for EN Language.

Enables full editing support (live diagnostics, error highlighting, and CodeLenses)
across any editor that supports LSP: VS Code, JetBrains (PyCharm, IntelliJ),
Neovim, Sublime Text, Cursor, Helix, Emacs, etc.
"""

from __future__ import annotations

import json
import sys
from typing import BinaryIO

from .contract import Diagnostic, read_contract
from .errors import CodeInEnglishError
from .parser import parse_program


class LanguageServer:
    def __init__(self, reader: BinaryIO = sys.stdin.buffer, writer: BinaryIO = sys.stdout.buffer):
        self.reader = reader
        self.writer = writer
        self.documents: dict[str, str] = {}
        self.running = True

    def run(self) -> int:
        while self.running:
            message = self._read_message()
            if message is None:
                break
            self._handle_message(message)
        return 0

    def _read_message(self) -> dict | None:
        headers = {}
        while True:
            line = self.reader.readline()
            if not line:
                return None
            line_str = line.decode("ascii", errors="replace").strip()
            if not line_str:
                break
            if ":" in line_str:
                k, v = line_str.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        length = int(headers.get("content-length", 0))
        if length <= 0:
            return None
        body = self.reader.read(length)
        if len(body) < length:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _send_response(self, request_id: int | str, result: object) -> None:
        self._send_payload({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _send_error(self, request_id: int | str, code: int, message: str) -> None:
        self._send_payload({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})

    def _send_notification(self, method: str, params: object) -> None:
        self._send_payload({"jsonrpc": "2.0", "method": method, "params": params})

    def _send_payload(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        try:
            self.writer.write(header + body)
            self.writer.flush()
        except (BrokenPipeError, OSError):
            self.running = False

    def _handle_message(self, message: dict) -> None:
        method = message.get("method")
        msg_id = message.get("id")

        if method == "initialize":
            self._handle_initialize(msg_id, message.get("params", {}))
        elif method == "initialized":
            pass  # notification, no response
        elif method == "shutdown":
            self._send_response(msg_id, None)
        elif method == "exit":
            self.running = False
        elif method == "textDocument/didOpen":
            doc = message["params"]["textDocument"]
            uri, text = doc["uri"], doc["text"]
            self.documents[uri] = text
            self._validate_document(uri, text)
        elif method == "textDocument/didChange":
            params = message["params"]
            uri = params["textDocument"]["uri"]
            changes = params["contentChanges"]
            if changes:
                text = changes[-1]["text"]
                self.documents[uri] = text
                self._validate_document(uri, text)
        elif method == "textDocument/didClose":
            uri = message["params"]["textDocument"]["uri"]
            self.documents.pop(uri, None)
            self._send_notification("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": []})
        elif method == "textDocument/codeLens":
            self._handle_codelens(msg_id, message.get("params", {}))
        elif method == "workspace/executeCommand":
            self._handle_execute_command(msg_id, message.get("params", {}))
        elif msg_id is not None:
            # Unsupported request
            self._send_error(msg_id, -32601, f"Method '{method}' not found")

    def _handle_initialize(self, msg_id: int | str, params: dict) -> None:
        capabilities = {
            "textDocumentSync": 1,  # 1 = Full sync
            "codeLensProvider": {
                "resolveProvider": False
            },
            "executeCommandProvider": {
                "commands": ["codeinenglish.run", "codeinenglish.generate"]
            }
        }
        self._send_response(msg_id, {
            "capabilities": capabilities,
            "serverInfo": {
                "name": "codeinenglish-lsp",
                "version": "0.3.0"
            }
        })

    def _validate_document(self, uri: str, text: str) -> None:
        filename = uri.split("/")[-1]
        contract = read_contract(text, filename)
        diagnostics = []

        for d in contract.diagnostics:
            diagnostics.append({
                "range": {
                    "start": {"line": max(0, d.line - 1), "character": max(0, d.column - 1)},
                    "end": {"line": max(0, d.end_line - 1), "character": max(0, d.end_column - 1)}
                },
                "severity": 1 if d.severity == "error" else 2,
                "code": d.code,
                "source": "codeinenglish",
                "message": d.message + (f"\nHint: {d.hint}" if d.hint else "")
            })

        # If contract is syntactically fine so far, try parsing instruction programs
        if contract.ok and contract.form == "instructions":
            try:
                source_lines = [""] * max((item.line for item in contract.lines), default=0)
                for item in contract.lines:
                    source_lines[item.line - 1] = item.text
                parse_program("\n".join(source_lines), filename)
            except CodeInEnglishError as error:
                line = getattr(error, "line", 1)
                col = getattr(error, "column", 1)
                diagnostics.append({
                    "range": {
                        "start": {"line": max(0, line - 1), "character": max(0, col - 1)},
                        "end": {"line": max(0, line - 1), "character": max(0, col)}
                    },
                    "severity": 1,
                    "code": "EN-E400",
                    "source": "codeinenglish",
                    "message": error.message
                })

        self._send_notification("textDocument/publishDiagnostics", {
            "uri": uri,
            "diagnostics": diagnostics
        })

    def _handle_codelens(self, msg_id: int | str, params: dict) -> None:
        uri = params.get("textDocument", {}).get("uri", "")
        lenses = [
            {
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                "command": {
                    "title": "▶ Run (Offline Interpreter)",
                    "command": "codeinenglish.run",
                    "arguments": [uri]
                }
            },
            {
                "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 0}},
                "command": {
                    "title": "⚡ Generate Target Source",
                    "command": "codeinenglish.generate",
                    "arguments": [uri]
                }
            }
        ]
        self._send_response(msg_id, lenses)

    def _handle_execute_command(self, msg_id: int | str, params: dict) -> None:
        command = params.get("command")
        args = params.get("arguments", [])
        self._send_response(msg_id, {"status": "ok", "command": command, "args": args})


def run_lsp_server() -> int:
    server = LanguageServer()
    return server.run()

