"""Simple Leverage CLI for Boss.

Designed for everyday management, not developer administration.
Run from the repository root with: python cli/leverage.py <command>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from control_plane.company_core import Project, list_projects
from control_plane.company_ops import (
    approve_payout,
    create_project_plan,
    intake_project,
    prepare_payout,
    project_task_summary,
    system_snapshot,
)
from control_plane.leverage_core import ResourceManager
from control_plane.finance_core import can_execute_payout


def money(value: float) -> str:
    return f"RM {value:,.2f}"


def cmd_status(_: argparse.Namespace) -> int:
    snapshot = system_snapshot()
    resources = ResourceManager().snapshot()["resources"]
    online = sum(1 for r in resources if r.get("status") in {"safe", "warning"})
    print("\nLEVERAGE\n========")
    print(f"Projects        : {snapshot['projects']} ({snapshot['active_projects']} active)")
    print(f"Tasks           : {sum(snapshot['tasks'].values())}")
    print(f"  queued        : {snapshot['tasks']['queued']}")
    print(f"  running       : {snapshot['tasks']['running']}")
    print(f"  completed     : {snapshot['tasks']['completed']}")
    print(f"  blocked       : {snapshot['tasks']['blocked']}")
    print(f"  failed        : {snapshot['tasks']['failed']}")
    print(f"Revenue entries : {snapshot['revenue_entries']}")
    print(f"Payout queue    : {snapshot['payouts_prepared']}")
    print(f"Money movement  : {'ENABLED' if snapshot['live_money_movement'] else 'PROTECTED'}")
    print(f"Resources known : {online}/{len(resources) if resources else 0}")
    return 0


def cmd_projects(args: argparse.Namespace) -> int:
    projects = list_projects()
    if not projects:
        print("No projects registered.")
        return 0
    print("\nPROJECTS\n========")
    for project in projects:
        summary = project_task_summary(project.id)
        print(f"{project.id:24} {project.lifecycle_stage:14} {summary['progress']:>5}%  {project.name}")
    return 0


def cmd_project_create(args: argparse.Namespace) -> int:
    project_id = args.id.strip().lower().replace(" ", "-")
    project = Project(
        id=project_id,
        name=args.name.strip(),
        type=args.type,
        description=args.description,
    )
    created = intake_project(project)
    tasks = create_project_plan(created.id)
    print(f"Created project: {created.name}")
    print(f"ID: {created.id}")
    print(f"Initial tasks: {len(tasks)}")
    print("Stage: validation")
    return 0


def cmd_project_status(args: argparse.Namespace) -> int:
    summary = project_task_summary(args.project)
    print(f"Project: {args.project}")
    for key in ("progress", "queued", "running", "completed", "failed", "blocked", "total"):
        value = f"{summary[key]}%" if key == "progress" else summary[key]
        print(f"{key.replace('_', ' ').title():12}: {value}")
    return 0


def cmd_payout_prepare(args: argparse.Namespace) -> int:
    request = prepare_payout(args.project, args.amount, args.destination, args.purpose)
    print("Payout prepared (not transferred).")
    print(f"ID         : {request['id']}")
    print(f"Amount     : {money(request['amount'])}")
    print(f"Destination: {request['destination']}")
    print("Status     : prepared")
    return 0


def cmd_payout_approve(args: argparse.Namespace) -> int:
    approval = approve_payout(args.payout, "Boss")
    print("Owner approval recorded.")
    print(f"Approval ID: {approval['id']}")
    ok, reason = can_execute_payout(args.payout)
    print(f"Transfer   : {'allowed' if ok else 'blocked'} ({reason})")
    return 0


def cmd_system_workers(_: argparse.Namespace) -> int:
    data = json.loads((ROOT / "control_plane" / "workers.json").read_text(encoding="utf-8"))
    print("\nWORKERS\n=======")
    for worker in data.get("workers", []):
        print(f"{worker['id']:20} {worker.get('status', 'unknown'):10} {worker.get('role', '')}")
    return 0


def cmd_help(_: argparse.Namespace) -> int:
    print("""\nLeverage commands\n\n  status                         Company health at a glance\n  project list                   Show all projects\n  project create                Create a project and its starter workflow\n  project status <id>           Show project task progress\n  workers                       Show worker fleet\n  payout prepare                Prepare an owner payout (no transfer)\n  payout approve <id>           Record Boss approval (no transfer)\n  help                          Show this guide\n""")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leverage", add_help=False)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("workers").set_defaults(func=cmd_system_workers)
    sub.add_parser("help").set_defaults(func=cmd_help)

    project = sub.add_parser("project")
    project_sub = project.add_subparsers(dest="project_command")
    project_sub.add_parser("list").set_defaults(func=cmd_projects)
    create = project_sub.add_parser("create")
    create.add_argument("--id", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--type", default="general")
    create.add_argument("--description", default="")
    create.set_defaults(func=cmd_project_create)
    ps = project_sub.add_parser("status")
    ps.add_argument("project")
    ps.set_defaults(func=cmd_project_status)

    payout = sub.add_parser("payout")
    payout_sub = payout.add_subparsers(dest="payout_command")
    prep = payout_sub.add_parser("prepare")
    prep.add_argument("--project", required=True)
    prep.add_argument("--amount", required=True, type=float)
    prep.add_argument("--destination", required=True)
    prep.add_argument("--purpose", default="owner payout")
    prep.set_defaults(func=cmd_payout_prepare)
    approve = payout_sub.add_parser("approve")
    approve.add_argument("payout")
    approve.set_defaults(func=cmd_payout_approve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        return cmd_help(args)
    try:
        return int(func(args))
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
