"""Boss-friendly command interface for Leverage."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from control_plane.company_core import Project,list_projects
from control_plane.company_ops import approve_payout,create_project_plan,intake_project,prepare_payout,project_task_summary,system_snapshot
from control_plane.leverage_core import ResourceManager
from control_plane.finance_core import can_execute_payout
from control_plane.health import company_health
from control_plane.readiness import company_os_readiness
from control_plane.local_sync import sync as sync_local_state
from control_plane.dispatcher import queue_summary

def money(value: float)->str:return f"RM {value:,.2f}"
def _print_company_report()->None:
    snapshot=system_snapshot(); resources=ResourceManager().snapshot()["resources"]; usable=sum(1 for r in resources if r.get("status") in {"safe","warning"})
    print("\nLEVERAGE COMPANY\n================"); print(f"Projects        : {snapshot['projects']} ({snapshot['active_projects']} active)"); print(f"Tasks           : {sum(snapshot['tasks'].values())}"); [print(f"  {key:14}: {snapshot['tasks'][key]}") for key in ("queued","ready","running","completed","blocked","failed")]; print(f"Verified revenue: {money(snapshot['verified_revenue'])}"); print(f"Verified profit : {money(snapshot['verified_profit'])}"); print(f"Payout queue    : {snapshot['payouts_prepared']}"); print(f"Money movement  : {'ENABLED' if snapshot['live_money_movement'] else 'PROTECTED'}"); print(f"Resources known : {usable}/{len(resources) if resources else 0}")
def cmd_status(_: argparse.Namespace)->int:_print_company_report();return 0
def cmd_report(_: argparse.Namespace)->int:
    print("\nOWNER REPORT\n============");_print_company_report();health=company_health();print(f"Company health  : {health['status'].upper()} ({health['summary']['total']} alert(s))");readiness=company_os_readiness();print(f"OS readiness    : {'READY' if readiness['ready'] else 'NOT READY'}");return 0
def cmd_health(_: argparse.Namespace)->int:
    result=company_health();print(f"Company health: {result['status'].upper()}");[print(f"- {a['severity'].upper()}: {a['message']}") for a in result.get('alerts',[])];return 0
def cmd_readiness(_: argparse.Namespace)->int:
    result=company_os_readiness();print("\nLEVERAGE OS READINESS\n=====================");[print(f"{c['status'].upper():4} {c['name']:18} {c['detail']}") for c in result['checks']];print(f"\nRelease gate: {result['release_gate']}");print(f"Status      : {'READY' if result['ready'] else 'NOT READY'}");return 0 if result['ready'] else 1
def cmd_sync(_: argparse.Namespace)->int:return sync_local_state(push=True)
def cmd_install_sync(_: argparse.Namespace)->int:
    task_name="Leverage Local State Sync"; task_command=f'"{Path(sys.executable).resolve()}" "{(ROOT/"cli"/"leverage.py").resolve()}" sync'; result=subprocess.run(["schtasks","/Create","/TN",task_name,"/TR",task_command,"/SC","MINUTE","/MO","5","/F","/RL","LIMITED"],cwd=ROOT,text=True,capture_output=True,check=False)
    if result.returncode!=0:print("Could not install automatic sync.");print(result.stderr.strip() or result.stdout.strip());return 2
    print(f"Automatic sync installed: {task_name} (every 5 minutes)");return 0
def cmd_uninstall_sync(_: argparse.Namespace)->int:
    result=subprocess.run(["schtasks","/Delete","/TN","Leverage Local State Sync","/F"],cwd=ROOT,text=True,capture_output=True,check=False)
    if result.returncode!=0:print(result.stderr.strip() or result.stdout.strip() or "Scheduled task not found.");return 2
    print("Automatic sync removed: Leverage Local State Sync");return 0
def cmd_projects(_: argparse.Namespace)->int:
    projects=list_projects()
    if not projects:print("No projects registered.");return 0
    print("\nPROJECTS\n========");[print(f"{p.id:24} {p.lifecycle_stage:14} {project_task_summary(p.id)['progress']:>5}%  {p.name}") for p in projects];return 0
def cmd_project_create(args: argparse.Namespace)->int:
    project_id=args.id.strip().lower().replace(" ","-");created=intake_project(Project(id=project_id,name=args.name.strip(),type=args.type,description=args.description));tasks=create_project_plan(created.id);print(f"Created project: {created.name}\nID: {created.id}\nInitial tasks: {len(tasks)}\nStage: validation");return 0
def cmd_project_new(_: argparse.Namespace)->int:
    name=input("Project name: ").strip()
    while not name:name=input("Project name: ").strip()
    project_type=input("Type [general]: ").strip() or "general";description=input("What is the project supposed to achieve? ").strip();project_id=input("Short ID [auto]: ").strip().lower().replace(" ","-") or "-".join(name.lower().split());return cmd_project_create(argparse.Namespace(id=project_id,name=name,type=project_type,description=description))
def cmd_project_status(args: argparse.Namespace)->int:
    summary=project_task_summary(args.project);print(f"Project: {args.project}");[print(f"{key.replace('_',' ').title():24}: {summary[key]}{'%' if key=='progress' else ''}") for key in ("progress","queued","ready","running","waiting_on_dependencies","completed","failed","blocked","total")];return 0
def cmd_system_workers(_: argparse.Namespace)->int:
    print("\nWORKER QUEUES\n=============");[print(f"{w['worker']:20} {w['status']:8} ready={w['ready']} running={w['running']} waiting={w['waiting']} blocked={w['blocked']} completed={w['completed']}") for w in queue_summary()];return 0
def cmd_payout_prepare(args: argparse.Namespace)->int:
    request=prepare_payout(args.project,args.amount,args.destination,args.purpose);print("Payout prepared (not transferred).\nID         : %s\nAmount     : %s\nDestination: %s\nStatus     : prepared"%(request['id'],money(request['amount']),request['destination']));return 0
def cmd_payout_approve(args: argparse.Namespace)->int:
    approval=approve_payout(args.payout,"Boss");print(f"Owner approval recorded.\nApproval ID: {approval['id']}");ok,reason=can_execute_payout(args.payout);print(f"Transfer   : {'allowed' if ok else 'blocked'} ({reason})");return 0
def cmd_help(_: argparse.Namespace)->int:
    print("""\nLeverage — Boss commands\n\n  status / report / health / readiness\n  sync / install-sync / uninstall-sync\n  workers                      Worker queue state\n  project list|new|status <id>|create ...\n  payout prepare ... | payout approve <id>\n\nNatural-language instructions to the AI manager remain the preferred interface.\n""");return 0
def build_parser()->argparse.ArgumentParser:
    parser=argparse.ArgumentParser(prog="leverage",add_help=False);sub=parser.add_subparsers(dest="command")
    for name,func in [("status",cmd_status),("report",cmd_report),("health",cmd_health),("readiness",cmd_readiness),("sync",cmd_sync),("install-sync",cmd_install_sync),("uninstall-sync",cmd_uninstall_sync),("workers",cmd_system_workers),("help",cmd_help)]:sub.add_parser(name).set_defaults(func=func)
    project=sub.add_parser("project");ps=project.add_subparsers(dest="project_command");ps.add_parser("list").set_defaults(func=cmd_projects);ps.add_parser("new").set_defaults(func=cmd_project_new);create=ps.add_parser("create");create.add_argument("--id",required=True);create.add_argument("--name",required=True);create.add_argument("--type",default="general");create.add_argument("--description",default="");create.set_defaults(func=cmd_project_create);status=ps.add_parser("status");status.add_argument("project");status.set_defaults(func=cmd_project_status)
    payout=sub.add_parser("payout");payout_sub=payout.add_subparsers(dest="payout_command");prep=payout_sub.add_parser("prepare");prep.add_argument("--project",required=True);prep.add_argument("--amount",required=True,type=float);prep.add_argument("--destination",required=True);prep.add_argument("--purpose",default="owner payout");prep.set_defaults(func=cmd_payout_prepare);approve=payout_sub.add_parser("approve");approve.add_argument("payout");approve.set_defaults(func=cmd_payout_approve);return parser
def main(argv:list[str]|None=None)->int:
    args=build_parser().parse_args(argv);func=getattr(args,"func",None)
    if func is None:return cmd_help(args)
    try:return int(func(args))
    except (KeyError,ValueError,EOFError,KeyboardInterrupt) as exc:print(f"Error: {exc}",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
