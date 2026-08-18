"""Boss-friendly command interface for Leverage.

The CLI is intentionally simple. Boss normally gives instructions to the AI
manager; this interface is a lightweight backup/direct control surface.
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
from control_plane.health import company_health
from control_plane.readiness import company_os_readiness


def money(value: float) -> str:
    return f"RM {value:,.2f}"


def _print_company_report() -> None:
    snapshot = system_snapshot()
    resources = ResourceManager().snapshot()["resources"]
    usable = sum(1 for r in resources if r.get("status") in {"safe", "warning"})
    print("\nLEVERAGE COMPANY\n================")
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
    print(f"Resources known : {usable}/{len(resources) if resources else 0}")


def cmd_status(_: argparse.Namespace) -> int:
    _print_company_report()
    return 0


def cmd_report(_: argparse.Namespace) -> int:
    print("\nOWNER REPORT")
    print("============")
    _print_company_report()
    health = company_health()
    print(f"Company health  : {health['status'].upper()} ({health['summary']['total']} alert(s))")
    readiness = company_os_readiness()
    print(f"OS readiness    : {'READY' if readiness['ready'] else 'NOT READY'}")
    print("Trading project remains PAUSED. No new project is currently active.")
    return 0


def cmd_health(_: argparse.Namespace) -> int:
    result = company_health()
    print(f"Company health: {result['status'].upper()}")
    for alert in result.get("alerts", []):
        print(f"- {alert['severity'].upper()}: {alert['message']}")
    return 0


def cmd_readiness(_: argparse.Namespace) -> int:
    result = company_os_readiness()
    print("\nLEVERAGE OS READINESS\n=====================")
    for check in result["checks"]:
        print(f"{check['status'].upper():4} {check['name']:18} {check['detail']}")
    print(f"\nRelease gate: {result['release_gate']}")
    print(f"Status      : {'READY' if result['ready'] else 'NOT READY'}")
    return 0 if result["ready"] else 1


def cmd_projects(_: argparse.Namespace) -> int:
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


def cmd_project_new(_: argparse.Namespace) -> int:
    print("\nNEW LEVERAGE PROJECT\n====================")
    print("Press Enter to accept the suggested value.\n")
    name = input("Project name: ").strip()
    while not name:
        print("Project name is required.")
        name = input("Project name: ").strip()
    project_type = input("Type [general]: ").strip() or "general"
    description = input("What is the project supposed to achieve? ").strip()
    project_id = input("Short ID [auto]: ").strip().lower().replace(" ", "-")
    if not project_id:
        project_id = "-".join(name.lower().split())
    return cmd_project_create(argparse.Namespace(id=project_id, name=name, type=project_type, description=description))


def cmd_project_status(args: argparse.Namespace) -> int:
    summary = project_task_summary(args.project)
    print(f"Project: {args.project}")
    for key in ("progress", "queued", "running", "completed", "failed", "blocked", "total"):
        value = f"{summary[key]}%" if key == "progress" else summary[key]
        print(f"{key.replace('_', ' ').title():12}: {value}")
    return 0


def cmd_system_workers(_: argparse.Namespace) -> int:
    data = json.loads((ROOT / "control_plane" / "workers.json").read_text(encoding="utf-8"))
    print("\nWORKERS\n=======")
    for worker in data.get("workers", []):
        print(f"{worker['id']:20} {worker.get('status', 'unknown'):10} {worker.get('role', '')}")
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


def cmd_help(_: argparse.Namespace) -> int:
    print("""
Leverage — Boss commands

  status                       Quick company status
  report                       Owner report + OS readiness
  health                       Show company health alerts
  readiness                    Check whether Leverage is ready for the next income project
  workers                      Show the worker fleet
  project list                 Show all projects
  project new                  Create a project with simple questions
  project status <id>          Show project progress
  payout prepare ...           Prepare a payout (never transfers money)
  payout approve <id>         Record Boss approval (never transfers money)
  help                        Show this guide

Natural-language instructions to the AI manager remain the preferred interface.
""")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="leverage", add_help=False)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("report").set_defaults(func=cmd_report)
    sub.add_parser("health").set_defaults(func=cmd_health)
    sub.add_parser("readiness").set_defaults(func=cmd_readiness)
    sub.add_parser("workers").set_defaults(func=cmd_system_workers)
    sub.add_parser("help").set_defaults(func=cmd_help)

    project = sub.add_parser("project")
    project_sub = project.add_subparsers(dest="project_command")
    project_sub.add_parser("list").set_defaults(func=cmd_projects)
    project_sub.add_parser("new").set_defaults(func=cmd_project_new)
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
    except (KeyError, ValueError, EOFError, KeyboardInterrupt) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
