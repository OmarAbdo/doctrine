"""`doctrine eval label <judge> --traces <file>`: the labelling page for a judge's eval set, opened
in the browser; it runs until Ctrl+C."""

import json
import webbrowser
from pathlib import Path

from doctrine.adapters.cli.commands.eval_command import find_task
from doctrine.adapters.cli.console import complain, load_project, say
from doctrine.adapters.storage.eval_files import EvalFiles
from doctrine.adapters.web.label_page import LabelSession, label_server
from doctrine.domain.evals.labels import parse_traces


def eval_label(cwd: Path, name: str, traces: Path) -> int:
    project = load_project(cwd)
    task = find_task(project, name)
    if task is None:
        return 1
    if not task.judge:
        complain(f"Labels are a judge's eval set; {name} is no judge: mark it judge = true.")
        return 1
    path = cwd / traces
    if not path.is_file():
        complain(f"There is no traces file {path}.")
        return 1
    lines = path.read_text(encoding="utf-8").splitlines()
    session = LabelSession(
        parse_traces(json.loads(line) for line in lines if line.strip()),
        EvalFiles(project.root, task),
    )
    return serve(session)


def serve(session: LabelSession) -> int:
    server = label_server(session, port=0)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    say(f"Labelling {len(session.remaining())} traces at {url}; Ctrl+C here when you are done.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        say("Stopped; every label so far is saved.")
    finally:
        server.server_close()
    return 0
