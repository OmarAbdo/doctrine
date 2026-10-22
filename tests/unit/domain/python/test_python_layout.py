from doctrine.domain.python.layout import (
    folder_findings,
    hexagonal_findings,
    layer_findings,
    kind_of_test_findings,
)


def test_the_application_may_not_import_adapters() -> None:
    source = "from pkg.domain import job\nfrom pkg.adapters.mail import send\n"
    findings = layer_findings("pkg/application/apply.py", source, package="pkg")
    assert [finding.message for finding in findings] == [
        "the application may not import pkg.adapters.mail"
    ]


def test_a_hexagonal_package_has_only_its_three_parts_at_the_top() -> None:
    files = [
        "pkg/__init__.py",
        "pkg/domain/job.py",
        "pkg/application/apply.py",
        "pkg/adapters/cli.py",
        "pkg/helpers.py",
        "pkg/utils/strings.py",
    ]
    findings = hexagonal_findings("pkg", files)
    assert [finding.message for finding in findings] == [
        "pkg/helpers.py: a hexagonal package holds only domain/, application/ and adapters/",
        "pkg/utils: a hexagonal package holds only domain/, application/ and adapters/",
    ]


def test_a_folder_with_too_many_modules_is_found() -> None:
    files = [f"pkg/domain/part_{number}.py" for number in range(4)] + ["pkg/domain/__init__.py"]
    findings = folder_findings(files, limit=3)
    assert [finding.message for finding in findings] == [
        "pkg/domain holds 4 modules; the limit is 3: group them into sub-folders by responsibility",
    ]


def test_every_module_has_a_test_of_its_kind_and_unit_tests_stay_off_adapters() -> None:
    modules = [
        "pkg/domain/job.py",
        "pkg/domain/city.py",
        "pkg/adapters/mail.py",
        "pkg/adapters/files.py",
    ]
    tests = {
        "tests/unit/test_job.py": "from pkg.domain.job import Job\n",
        "tests/unit/test_mail_unit.py": "from pkg.adapters.mail import send\n",
        "tests/integration/test_files.py": "from pkg.adapters import files\n",
    }
    messages = [finding.message for finding in kind_of_test_findings("pkg", modules, tests)]
    assert messages == [
        "tests/unit/test_mail_unit.py: a unit test may not import pkg.adapters.mail "
        "(use tests/integration)",
        "pkg/domain/city.py has no unit test that imports it",
        "pkg/adapters/mail.py has no integration test that imports it",
    ]
