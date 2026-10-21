from doctrine.application.brief import ProjectStatus, session_brief


def test_outside_a_project_the_brief_says_how_to_start_one() -> None:
    text = session_brief(None)
    assert "not a doctrine project" in text
    assert "doctrine init" in text


def test_inside_a_project_the_brief_leads_with_the_outcome_and_the_item() -> None:
    status = ProjectStatus(
        name="jobs",
        metric="applications sent per day",
        latest=6.0,
        stop_value=8.0,
        item="7 Search by city (feature)",
        branch="item/7",
    )
    text = session_brief(status)
    lines = text.splitlines()
    assert lines[0].startswith("Doctrine project jobs")
    assert "LINE STOPPED" in text
    assert "applications sent per day: 6 (stops below 8)" in text
    assert "Active item: 7 Search by city (feature)" in text


def test_a_project_without_a_recorded_metric_says_so() -> None:
    status = ProjectStatus(
        name="jobs", metric="sent per day", latest=None, stop_value=8.0, item=None, branch="main"
    )
    text = session_brief(status)
    assert "not recorded yet" in text
    assert "No active item" in text
