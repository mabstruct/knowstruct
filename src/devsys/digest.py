from datetime import date

from devsys.plane import Issue, Plane, decision

KINDS = ("idea", "analysis", "requirement", "proposal", "spike", "iteration", "task")
PROJECT_ORDER = ("KS", "CLAWSTRUCT", "CONSTRUCT", "ZENSTRUCT")
OPEN_TASK_STATES = ("backlog", "todo", "in progress")


def age(created_or_updated: str, today: str) -> str:
    days = (date.fromisoformat(today) - date.fromisoformat(created_or_updated[:10])).days
    return f"{days}d"


def kind(issue: Issue) -> str:
    names = {label.lower() for label in issue.labels}
    return next((k for k in KINDS if k in names), "-")


def line(issue: Issue, today: str, decision: tuple[str, str] | None) -> str:
    k = kind(issue)
    text = f"{issue.ref:<14}{k:<12}{issue.title}  ({issue.state} {age(issue.updated_at or issue.created_at, today)})"
    if decision is not None:
        text += f"  → {decision[0]}: {decision[1]}"
    if k == "task" and issue.priority != "none":
        text += f"  [{issue.priority}]"
    return text


def _project_key(identifier: str) -> tuple[int, str]:
    if identifier in PROJECT_ORDER:
        return PROJECT_ORDER.index(identifier), ""
    return len(PROJECT_ORDER), identifier


def digest(plane: Plane, today: str) -> str:
    review: list[str] = []
    todo: list[str] = []
    tasks: list[str] = []
    for project in sorted((p.identifier for p in plane.projects()), key=_project_key):
        for issue in plane.list_issues(project):
            state = issue.state.lower()
            if state == "review":
                review.append(line(issue, today, decision(plane.comments(issue.ref))))
            elif state == "todo":
                todo.append(line(issue, today, None))
            if kind(issue) == "task" and state in OPEN_TASK_STATES:
                tasks.append(line(issue, today, None))
    sections = [
        ("### waiting on you (Review)", review),
        ("### approved, nobody on it (Todo)", todo),
        ("### open tasks", tasks),
    ]
    blocks = ["\n".join([title, *lines]) for title, lines in sections if lines]
    return "\n\n".join(blocks) + "\n" if blocks else "nothing waiting\n"
