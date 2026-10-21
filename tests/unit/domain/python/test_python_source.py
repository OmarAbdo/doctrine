from textwrap import dedent

from doctrine.domain.rules.findings import Finding
from doctrine.domain.rules.names import NamePolicy
from doctrine.domain.python.source import (
    SourceLimits,
    composition_findings,
    domain_import_findings,
    module_findings,
)

LIMITS = SourceLimits(
    function_lines=6,
    imports_per_module=2,
    interface_methods=2,
    names=NamePolicy(3, frozenset({"i", "_"}), frozenset({"tmp"})),
)


def check(source: str) -> list[Finding]:
    return module_findings("pkg/mod.py", dedent(source), LIMITS)


def rules(findings: list[Finding]) -> list[str]:
    return [finding.rule for finding in findings]


def test_clean_code_has_no_findings() -> None:
    assert (
        check("""
        def total_price(items: list[int]) -> int:
            return sum(items)
    """)
        == []
    )


def test_a_long_function_is_found_with_its_line() -> None:
    body = "\n".join(f"    step_{number} = {number}" for number in range(8))
    findings = check(f"def long_one() -> None:\n{body}\n")
    assert findings == [
        Finding("pkg/mod.py", 1, "function_lines", "long_one has 9 lines; the limit is 6")
    ]


def test_short_and_abbreviated_names_are_found_for_variables_parameters_and_functions() -> None:
    findings = check("""
        def tmp_job(r: int) -> int:
            for i in range(r):
                d = i
            return d
    """)
    assert rules(findings) == ["names", "names", "names"]
    assert "'tmp_job' uses the abbreviation 'tmp'" in findings[0].message


def test_suppression_comments_are_found() -> None:
    findings = check("""
        import os  # noqa: F401
        value: int = "x"  # type: ignore
        # pylint: disable=too-many-branches
    """)
    assert rules(findings) == ["suppression_comments"] * 3


def test_too_many_imports_are_found() -> None:
    findings = check("import os\nimport sys\nimport json\n")
    assert rules(findings) == ["imports_per_module"]


def test_a_large_interface_is_found() -> None:
    findings = check("""
        from typing import Protocol

        class JobStore(Protocol):
            def load(self) -> None: ...
            def save(self) -> None: ...
            def delete(self) -> None: ...
    """)
    assert rules(findings) == ["interface_methods"]


def test_inheriting_from_a_concrete_project_class_is_found() -> None:
    sources = {
        "pkg/base.py": "class Mailer:\n    def send(self) -> None: ...\n",
        "pkg/port.py": "from typing import Protocol\n"
        "class Sender(Protocol):\n    def send(self) -> None: ...\n",
        "pkg/child.py": "from pkg.base import Mailer\nfrom pkg.port import Sender\n"
        "class SmtpMailer(Mailer):\n    pass\n"
        "class GmailSender(Sender):\n    pass\n"
        "class JobError(ValueError):\n    pass\n",
    }
    findings = composition_findings(sources)
    assert findings == [
        Finding(
            "pkg/child.py", 3, "inheritance", "SmtpMailer inherits from Mailer; compose it instead"
        )
    ]


def test_the_domain_imports_only_the_standard_library_and_itself() -> None:
    source = (
        "import json\nimport requests\nfrom pkg.adapters import mail\nfrom pkg.domain import job\n"
    )
    findings = domain_import_findings("pkg/domain/order.py", source, package="pkg")
    assert [finding.message for finding in findings] == [
        "the domain may not import requests",
        "the domain may not import pkg.adapters",
    ]
