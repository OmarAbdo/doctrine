from doctrine.application.brief import ProjectStatus, session_brief


def test_before_launch_the_brief_says_when_the_line_arms() -> None:
    status = ProjectStatus(
        name="hunter",
        metric="applications sent per day",
        latest=0.0,
        stop_value=8.0,
        item=None,
        branch="main",
        launched=False,
    )
    text = session_brief(status)
    assert "LINE STOPPED" not in text
    assert "not launched: the line arms once a recorded value reaches 8" in text
