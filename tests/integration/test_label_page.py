"""The labelling page on a real local server: one trace at a time, each label saved at once."""

import json
import threading
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from doctrine.adapters.storage.eval_files import EvalFiles
from doctrine.adapters.web.label_page import LabelSession, label_server
from doctrine.domain.evals.labels import Trace
from doctrine.domain.evals.task import AiTask

JUDGE = AiTask(name="fit-judge", prompt="prompts/judge.md", command=("x",), minimum=0.8, judge=True)
TRACES = [
    Trace(id="t1", input="Senior <b>Python</b> role", output="fits"),
    Trace(id="t2", input="Java role", output="fits"),
]


@pytest.fixture
def page(tmp_path: Path) -> Iterator[str]:
    server = label_server(LabelSession(TRACES, EvalFiles(tmp_path, JUDGE)), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:
        return str(response.read().decode("utf-8"))


def post(url: str, fields: dict[str, str]) -> str:
    data = urllib.parse.urlencode(fields).encode("utf-8")
    with urllib.request.urlopen(url, data=data, timeout=10) as response:
        return str(response.read().decode("utf-8"))


def test_each_label_is_saved_and_the_next_trace_shown(page: str, tmp_path: Path) -> None:
    first = get(page)
    assert "Senior &lt;b&gt;Python&lt;/b&gt; role" in first
    assert "0 of 2 labelled" in first
    second = post(f"{page}/label", {"id": "t1", "verdict": "pass", "note": ""})
    assert "Java role" in second
    done = post(f"{page}/label", {"id": "t2", "verdict": "fail", "note": "Java isn't Python"})
    assert "All 2 traces are labelled: 1 pass, 1 fail." in done
    rows = (tmp_path / JUDGE.cases).read_text(encoding="utf-8").splitlines()
    assert [json.loads(row)["expected"] for row in rows] == ["pass", "fail"]
    assert json.loads(rows[1])["note"] == "Java isn't Python"


def test_a_page_started_again_goes_on_where_it_stopped(page: str, tmp_path: Path) -> None:
    post(f"{page}/label", {"id": "t1", "verdict": "pass", "note": ""})
    again = LabelSession(TRACES, EvalFiles(tmp_path, JUDGE))
    assert [trace.id for trace in again.remaining()] == ["t2"]
