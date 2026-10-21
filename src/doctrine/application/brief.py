"""The one screen every session starts with: the outcome and the change in progress."""

from dataclasses import dataclass

OUTSIDE = (
    "This folder is not a doctrine project. Doctrine's command and protected-file rules "
    "still apply. To start a project here: `doctrine init`."
)


@dataclass(frozen=True)
class ProjectStatus:
    name: str
    metric: str
    latest: float | None
    stop_value: float
    item: str | None
    branch: str

    @property
    def line_stopped(self) -> bool:
        return self.latest is not None and self.latest < self.stop_value


def outcome_line(status: ProjectStatus) -> str:
    if status.latest is None:
        return f"Outcome {status.metric}: not recorded yet (`doctrine metric record`)"
    return f"Outcome {status.metric}: {status.latest:g} (stops below {status.stop_value:g})"


def session_brief(status: ProjectStatus | None) -> str:
    if status is None:
        return OUTSIDE
    lines = [f"Doctrine project {status.name}, branch {status.branch}.", outcome_line(status)]
    if status.line_stopped:
        lines.append(
            "LINE STOPPED: only a restore item may change code until the outcome recovers."
        )
    lines.append(
        f"Active item: {status.item}"
        if status.item
        else "No active item: start one with `doctrine item start` before changing anything."
    )
    lines.append(
        "Rules: doctrine check must pass before you claim anything works; "
        "features and fixes start with a failing test (`doctrine test`)."
    )
    return "\n".join(lines)
