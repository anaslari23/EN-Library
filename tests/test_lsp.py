"""Tests for the zero-dependency Language Server Protocol (LSP) server."""

from __future__ import annotations

import io
import json
import unittest

from codeinenglish.lsp import LanguageServer


def _make_rpc_message(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def _read_rpc_messages(output_bytes: bytes) -> list[dict]:
    messages = []
    stream = io.BytesIO(output_bytes)
    while True:
        headers = {}
        while True:
            line = stream.readline()
            if not line:
                return messages
            line_str = line.decode("ascii", errors="replace").strip()
            if not line_str:
                break
            if ":" in line_str:
                k, v = line_str.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        length = int(headers.get("content-length", 0))
        if length <= 0:
            return messages
        body = stream.read(length)
        messages.append(json.loads(body.decode("utf-8")))


class LSPTests(unittest.TestCase):
    def test_initialize_and_shutdown(self):
        req_init = _make_rpc_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"capabilities": {}}
        })
        req_shut = _make_rpc_message({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "shutdown",
            "params": {}
        })
        req_exit = _make_rpc_message({
            "jsonrpc": "2.0",
            "method": "exit"
        })

        reader = io.BytesIO(req_init + req_shut + req_exit)
        writer = io.BytesIO()

        server = LanguageServer(reader=reader, writer=writer)
        server.run()

        messages = _read_rpc_messages(writer.getvalue())
        self.assertEqual(len(messages), 2)
        # initialize response
        self.assertEqual(messages[0]["id"], 1)
        self.assertIn("capabilities", messages[0]["result"])
        self.assertEqual(messages[0]["result"]["capabilities"]["textDocumentSync"], 1)
        # shutdown response
        self.assertEqual(messages[1]["id"], 2)
        self.assertIsNone(messages[1]["result"])

    def test_did_open_publishes_diagnostics(self):
        # File with missing version header (warns EN-W401)
        req_open = _make_rpc_message({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///path/to/test.en",
                    "languageId": "en",
                    "version": 1,
                    "text": "set x to 5.\n"
                }
            }
        })
        req_exit = _make_rpc_message({"jsonrpc": "2.0", "method": "exit"})

        reader = io.BytesIO(req_open + req_exit)
        writer = io.BytesIO()

        server = LanguageServer(reader=reader, writer=writer)
        server.run()

        messages = _read_rpc_messages(writer.getvalue())
        self.assertEqual(len(messages), 1)
        notif = messages[0]
        self.assertEqual(notif["method"], "textDocument/publishDiagnostics")
        self.assertEqual(notif["params"]["uri"], "file:///path/to/test.en")
        diags = notif["params"]["diagnostics"]
        self.assertTrue(any(d["code"] == "EN-W401" for d in diags))

    def test_codelens(self):
        req_lens = _make_rpc_message({
            "jsonrpc": "2.0",
            "id": 10,
            "method": "textDocument/codeLens",
            "params": {"textDocument": {"uri": "file:///path/to/test.en"}}
        })
        req_exit = _make_rpc_message({"jsonrpc": "2.0", "method": "exit"})

        reader = io.BytesIO(req_lens + req_exit)
        writer = io.BytesIO()

        server = LanguageServer(reader=reader, writer=writer)
        server.run()

        messages = _read_rpc_messages(writer.getvalue())
        self.assertEqual(len(messages), 1)
        lenses = messages[0]["result"]
        self.assertGreaterEqual(len(lenses), 2)
        titles = [item["command"]["title"] for item in lenses]
        self.assertTrue(any("Run" in t for t in titles))
        self.assertTrue(any("Generate" in t for t in titles))


if __name__ == "__main__":
    unittest.main()

