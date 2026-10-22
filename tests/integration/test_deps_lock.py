"""Locking a project's dependencies with real pip and a real (local) package index."""

import json
import threading
import zipfile
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from support.projects import write

from doctrine.adapters.cli.commands import deps_command
from doctrine.adapters.tools.package_index import PackageIndex
from doctrine.adapters.tools.pip_resolver import PipResolver
from doctrine.domain.dependencies.locking import Pin


def wheel(folder: Path, name: str, requires: str = "") -> None:
    """A minimal wheel: pip reads its metadata without building anything."""
    info = f"{name}-1.0.dist-info"
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n"
    metadata += f"Requires-Dist: {requires}\n" if requires else ""
    with zipfile.ZipFile(folder / f"{name}-1.0-py3-none-any.whl", "w") as archive:
        archive.writestr(f"{info}/METADATA", metadata)
        archive.writestr(
            f"{info}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        )
        archive.writestr(f"{info}/RECORD", "")


def test_pip_resolves_the_dependencies_and_their_dependencies(tmp_path: Path) -> None:
    wheel(tmp_path, "sample", requires="helper")
    wheel(tmp_path, "helper")
    resolver = PipResolver(options=["--no-index", "--find-links", str(tmp_path)])
    assert resolver.resolve(["sample"]) == [Pin("helper", "1.0"), Pin("sample", "1.0")]


class FakePypi(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        found = self.path == "/sample/1.0/json"
        files = [{"digests": {"sha256": "aa"}}, {"digests": {"sha256": "bb"}}]
        body = json.dumps({"urls": files}).encode("utf-8")
        self.send_response(200 if found else 404)
        self.end_headers()
        self.wfile.write(body if found else b"{}")

    def log_message(self, *details: object) -> None:
        """Quiet."""


@pytest.fixture
def index() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakePypi)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_every_published_files_hash_comes_from_the_index(index: str) -> None:
    assert PackageIndex(index).hashes(Pin("sample", "1.0")) == ["aa", "bb"]
    with pytest.raises(LookupError, match="missing==1.0"):
        PackageIndex(index).hashes(Pin("missing", "1.0"))


def test_a_project_without_dependencies_gets_an_empty_lock(project: Path) -> None:
    assert deps_command.deps_lock(project) == 0
    lock = (project / "requirements.lock").read_text(encoding="utf-8")
    assert [line for line in lock.splitlines() if not line.startswith("#")] == []


def test_a_project_without_pyproject_is_told_so(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / "pyproject.toml").unlink()
    write(project, "README.md", "No pyproject.\n")
    assert deps_command.deps_lock(project) == 1
    assert "pyproject.toml" in capsys.readouterr().err
