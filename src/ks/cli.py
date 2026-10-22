import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from ks.config import ConfigError, load_env
from ks.digest import digest, kind, line
from ks.http import PlaneError, UrlHttp
from ks.plane import PartialWrite, Plane, Refused, decision


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _show(plane: Plane, args: argparse.Namespace) -> None:
    issue = plane.get_issue(args.ref)
    comments = plane.comments(issue.ref)
    related = plane.related(issue.ref)
    if args.json:
        print(json.dumps({**asdict(issue), "comments": [asdict(c) for c in comments], "related": related}, indent=2))
        return
    print(f"{issue.ref}  {kind(issue)}  {issue.title}")
    print(f"state: {issue.state}  priority: {issue.priority}  parent: {issue.parent_ref or '-'}  "
          f"labels: {', '.join(issue.labels) or '-'}")
    print()
    print(issue.body_md)
    print()
    print("### comments")
    for c in comments:
        print(f"-- {c.actor} ({c.created_at})")
        print(c.text_md)
        print()
    if related:
        print(f"related: {', '.join(related)}")


def _decision(plane: Plane, args: argparse.Namespace) -> None:
    found = decision(plane.comments(args.ref))
    print("none" if found is None else f"{found[0]}: {found[1]}")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ks", description="KNOWSTRUCT command line for Plane")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    sub.add_parser("whoami", help="show the API user").set_defaults(
        run=lambda pl, a: print(pl.me()))
    sub.add_parser("projects", help="list projects").set_defaults(
        run=lambda pl, a: [print(f"{x.identifier}  {x.name}") for x in pl.projects()])

    s = sub.add_parser("digest", help="what waits on you")
    s.add_argument("--today", default=None, help="YYYY-MM-DD (default: local date)")
    s.set_defaults(run=lambda pl, a: print(digest(pl, a.today or date.today().isoformat()), end=""))

    s = sub.add_parser("show", help="show one issue")
    s.add_argument("ref")
    s.add_argument("--json", action="store_true")
    s.set_defaults(run=_show)

    s = sub.add_parser("list", help="list issues of a project")
    s.add_argument("project")
    s.add_argument("--state")
    s.add_argument("--label")
    s.set_defaults(run=lambda pl, a: [
        print(line(i, date.today().isoformat(), None)) for i in pl.list_issues(a.project, a.state, a.label)])

    s = sub.add_parser("create", help="create an issue")
    s.add_argument("project")
    s.add_argument("--label", required=True)
    s.add_argument("--title", required=True)
    body = s.add_mutually_exclusive_group(required=True)
    body.add_argument("--body-file")
    body.add_argument("--body")
    s.add_argument("--state", default="Backlog")
    s.add_argument("--priority", default="none")
    s.add_argument("--parent")
    s.add_argument("--relates", nargs="*", default=[])
    s.set_defaults(run=lambda pl, a: print(pl.create_issue(
        a.project, a.title, _read(a.body_file) if a.body_file else a.body, a.label,
        state=a.state, priority=a.priority, parent=a.parent, relates=tuple(a.relates)).ref))

    s = sub.add_parser("update", help="update an issue")
    s.add_argument("ref")
    s.add_argument("--state")
    s.add_argument("--body-file")
    s.add_argument("--title")
    s.add_argument("--priority")

    def update(pl: Plane, a: argparse.Namespace) -> None:
        issue = pl.update_issue(
            a.ref, state=a.state, body_md=_read(a.body_file) if a.body_file else None,
            title=a.title, priority=a.priority)
        print(f"{issue.ref}  {issue.state}")
    s.set_defaults(run=update)

    s = sub.add_parser("comment", help="comment on an issue")
    s.add_argument("ref")
    src = s.add_mutually_exclusive_group(required=True)
    src.add_argument("--file")
    src.add_argument("--text")
    s.set_defaults(run=lambda pl, a: print(pl.comment(a.ref, _read(a.file) if a.file else a.text).id))

    s = sub.add_parser("relate", help="link two issues")
    s.add_argument("ref")
    s.add_argument("other")
    s.set_defaults(run=lambda pl, a: (
        pl.relate(a.ref, a.other), print(f"{a.ref.upper()} relates to {a.other.upper()}")))

    s = sub.add_parser("decision", help="show the decision on an issue")
    s.add_argument("ref")
    s.set_defaults(run=_decision)
    return p


def main(argv: list[str] | None = None, plane: Plane | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2
    try:
        if plane is None:
            plane = Plane(UrlHttp(load_env()))
        args.run(plane, args)
    except (PlaneError, PartialWrite, Refused, KeyError, ValueError, ConfigError, OSError) as e:
        message = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
