"""The labelling page: a local web page that shows one trace at a time with Pass and Fail buttons
and a note, and saves each label at once as a case of the judge's eval set. It listens on this
computer only (127.0.0.1)."""

import json
import urllib.parse
from collections import Counter
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from doctrine.adapters.storage.eval_files import EvalFiles
from doctrine.domain.evals.labels import Trace, label_row, unlabelled

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Label traces</title>
<style>body{{font:16px system-ui,sans-serif;max-width:860px;margin:24px auto;padding:0 16px}}
pre{{white-space:pre-wrap;background:#f4f4f4;padding:12px;border-radius:6px}}
button{{font-size:18px;padding:10px 28px;margin-right:12px}}
textarea{{width:100%;height:4em;font:inherit}}</style></head><body>{body}</body></html>"""
FORM = """<p>{progress}</p><h2>Input</h2><pre>{input}</pre><h2>Output</h2><pre>{output}</pre>
<form method="post" action="/label"><input type="hidden" name="id" value="{id}">
<p><textarea name="note" placeholder="Why (optional)"></textarea></p>
<button name="verdict" value="pass">Pass</button><button name="verdict" value="fail">Fail</button>
</form>"""


def shown(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
    return escape(text)


class LabelSession:
    def __init__(self, traces: list[Trace], files: EvalFiles) -> None:
        self.traces, self.files = traces, files

    def remaining(self) -> list[Trace]:
        return unlabelled(self.traces, {str(row.get("id")) for row in self.files.case_rows()})

    def label(self, trace_id: str, verdict: str, note: str) -> None:
        trace = next((trace for trace in self.remaining() if trace.id == trace_id), None)
        if trace is not None:
            self.files.add_case(label_row(trace, verdict, note))

    def page(self) -> str:
        left = self.remaining()
        if not left:
            counts = Counter(str(row.get("expected")) for row in self.files.case_rows())
            done = f"All {len(self.traces)} traces are labelled: "
            return PAGE.format(body=f"<p>{done}{counts['pass']} pass, {counts['fail']} fail.</p>")
        trace = left[0]
        progress = f"{len(self.traces) - len(left)} of {len(self.traces)} labelled"
        form = FORM.format(
            progress=progress,
            input=shown(trace.input),
            output=shown(trace.output),
            id=escape(trace.id),
        )
        return PAGE.format(body=form)


def handler_for(session: LabelSession) -> type[BaseHTTPRequestHandler]:
    class LabelHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_page(session.page())

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            fields = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
            first = {name: values[0] for name, values in fields.items()}
            session.label(first.get("id", ""), first.get("verdict", ""), first.get("note", ""))
            self.send_page(session.page())

        def send_page(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *details: Any) -> None:
            """Quiet: each label is in the eval set, not in the console."""

    return LabelHandler


def label_server(session: LabelSession, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), handler_for(session))
