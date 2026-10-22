"""The `doctrine` command line."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from doctrine.adapters.claude.hooks import HANDLERS, run_hook
from doctrine.adapters.cli.commands import (
    check_commands,
    init_command,
    item_commands,
    selftest_command,
)
from doctrine.adapters.cli.gates import ci_commands, coverage_gate, description_gate, eval_gate
from doctrine.adapters.cli.console import NoProjectError, complain
from doctrine.domain.governance.work_item import KINDS

Handler = Callable[[argparse.Namespace], int]


def work_parsers(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    commands.add_parser("check", help="run every rule on every service")
    test = commands.add_parser("test", help="run the tests and record the run as evidence")
    test.add_argument("paths", nargs="*")
    item = commands.add_parser("item", help="the one change in progress").add_subparsers(
        dest="action", required=True
    )
    start = item.add_parser("start")
    start.add_argument("--kind", choices=sorted(KINDS), required=True)
    start.add_argument("--title", required=True)
    start.add_argument("--scope", nargs="+", required=True)
    item.add_parser("show")
    resume = item.add_parser("resume", help="go on with a finished item after review feedback")
    resume.add_argument("id")
    item.add_parser("done")
    metric = commands.add_parser("metric").add_subparsers(dest="action", required=True)
    metric.add_parser("record")
    commands.add_parser("selftest", help="the share of bad samples and bypasses doctrine catches")
    init = commands.add_parser("init", help="start a doctrine project in this folder")
    init.add_argument("--name", required=True)
    init.add_argument("--approver", required=True)


def ci_parsers(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    gates = commands.add_parser("ci", help="checks CI runs on a pull request")
    gates.add_argument(
        "gate", choices=["goalposts", "scope", "red-first", "coverage", "description", "evals"]
    )
    gates.add_argument("--base", required=True)
    hook = commands.add_parser("hook", help="Claude Code hook entry point (event JSON on stdin)")
    hook.add_argument("event", choices=sorted(HANDLERS))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="doctrine")
    commands = root.add_subparsers(dest="command", required=True)
    work_parsers(commands)
    ci_parsers(commands)
    return root


def dispatch(arguments: argparse.Namespace, cwd: Path) -> int:
    simple: dict[str, Handler] = {
        "check": lambda _: check_commands.check_command(cwd),
        "test": lambda args: check_commands.test_command(cwd, args.paths),
        "hook": lambda args: run_hook(args.event),
        "selftest": lambda _: selftest_command.selftest_command(),
        "init": lambda args: init_command.init_command(cwd, args.name, args.approver),
    }
    if arguments.command in simple:
        return simple[arguments.command](arguments)
    actions: dict[tuple[str, str], Handler] = {
        ("item", "start"): lambda args: item_commands.item_start(
            cwd, args.kind, args.title, args.scope
        ),
        ("item", "show"): lambda _: item_commands.item_show(cwd),
        ("item", "resume"): lambda args: item_commands.item_resume(cwd, args.id),
        ("item", "done"): lambda _: item_commands.item_done(cwd),
        ("metric", "record"): lambda _: item_commands.metric_record(cwd),
        ("ci", "goalposts"): lambda args: ci_commands.goalposts_command(cwd, args.base),
        ("ci", "scope"): lambda args: ci_commands.scope_command(cwd, args.base),
        ("ci", "red-first"): lambda args: ci_commands.red_first_command(cwd, args.base),
        ("ci", "coverage"): lambda args: coverage_gate.coverage_command(cwd, args.base),
        ("ci", "description"): lambda _: description_gate.description_command(),
        ("ci", "evals"): lambda args: eval_gate.evals_command(cwd, args.base),
    }
    action = str(getattr(arguments, "action", None) or getattr(arguments, "gate", ""))
    return actions[(str(arguments.command), action)](arguments)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        return dispatch(arguments, Path.cwd())
    except NoProjectError as error:
        complain(str(error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
