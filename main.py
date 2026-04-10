"""
Attendance Crisis Management System - CLI Entry Point
"""

import sys
from datetime import date, datetime

from attendance import AttendanceManager, STATUS_GOOD, STATUS_WARNING, STATUS_CRITICAL

# ANSI colour helpers (disabled on Windows without colour support)
_USE_COLOR = sys.stdout.isatty()


def _color(text: str, code: str) -> str:
    if _USE_COLOR:
        return f"\033[{code}m{text}\033[0m"
    return text


def _green(t):
    return _color(t, "32")


def _yellow(t):
    return _color(t, "33")


def _red(t):
    return _color(t, "31")


def _bold(t):
    return _color(t, "1")


def _status_colored(status: str | None) -> str:
    if status == STATUS_GOOD:
        return _green(status)
    if status == STATUS_WARNING:
        return _yellow(status)
    if status == STATUS_CRITICAL:
        return _red(status)
    return status or "N/A"


def _separator(char: str = "-", width: int = 60) -> str:
    return char * width


def _print_report(report: dict) -> None:
    print(_separator("="))
    print(_bold(f"Attendance Report for {report['name']} (ID: {report['id']})"))
    print(_separator())
    pct = report["attendance_percentage"]
    status = report["status"]
    pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
    print(f"  Total days recorded : {report['total_days']}")
    print(f"  Days present        : {report['days_present']}")
    print(f"  Days absent         : {report['days_absent']}")
    print(f"  Attendance          : {_bold(pct_str)}")
    print(f"  Status              : {_status_colored(status)}")

    if report["corrective_actions"]:
        print()
        print(_bold("Corrective Actions:"))
        for action in report["corrective_actions"]:
            print(f"  • {action}")

    if report["attendance_log"]:
        print()
        print(_bold("Attendance Log:"))
        for entry in report["attendance_log"]:
            mark = _green("✓ Present") if entry["present"] else _red("✗ Absent")
            print(f"  {entry['date']}  {mark}")
    print(_separator("="))


def cmd_add(manager: AttendanceManager, args: list[str]) -> None:
    """add <id> <name>  – Register a new person."""
    if len(args) < 2:
        print("Usage: add <id> <name>")
        return
    person_id, name = args[0], " ".join(args[1:])
    if manager.add_person(person_id, name):
        print(f"✓ Added: {name} (ID: {person_id})")
    else:
        print(f"✗ ID '{person_id}' already exists.")


def cmd_remove(manager: AttendanceManager, args: list[str]) -> None:
    """remove <id>  – Remove a person."""
    if not args:
        print("Usage: remove <id>")
        return
    person_id = args[0]
    if manager.remove_person(person_id):
        print(f"✓ Removed person with ID '{person_id}'.")
    else:
        print(f"✗ ID '{person_id}' not found.")


def cmd_list(manager: AttendanceManager, _args: list[str]) -> None:
    """list  – List all registered people."""
    people = manager.list_people()
    if not people:
        print("No people registered yet.")
        return
    print(_bold(f"{'ID':<15} {'Name':<30}"))
    print(_separator())
    for p in people:
        print(f"{p['id']:<15} {p['name']:<30}")


def cmd_mark(manager: AttendanceManager, args: list[str]) -> None:
    """mark <id> <present|absent> [YYYY-MM-DD]  – Mark attendance."""
    if len(args) < 2:
        print("Usage: mark <id> <present|absent> [YYYY-MM-DD]")
        return
    person_id = args[0]
    status_arg = args[1].lower()
    if status_arg not in ("present", "absent", "p", "a"):
        print("Status must be 'present' (or 'p') / 'absent' (or 'a').")
        return
    present = status_arg in ("present", "p")

    attendance_date: date | None = None
    if len(args) >= 3:
        try:
            attendance_date = date.fromisoformat(args[2])
        except ValueError:
            print(f"Invalid date format '{args[2]}'. Use YYYY-MM-DD.")
            return

    if manager.mark_attendance(person_id, present, attendance_date):
        day = attendance_date or date.today()
        mark = "Present" if present else "Absent"
        print(f"✓ Marked {mark} for '{person_id}' on {day}.")
    else:
        print(
            f"✗ Could not mark attendance. Either '{person_id}' does not exist "
            "or attendance for this date is already recorded."
        )


def cmd_update(manager: AttendanceManager, args: list[str]) -> None:
    """update <id> <present|absent> [YYYY-MM-DD]  – Update an existing attendance entry."""
    if len(args) < 2:
        print("Usage: update <id> <present|absent> [YYYY-MM-DD]")
        return
    person_id = args[0]
    status_arg = args[1].lower()
    if status_arg not in ("present", "absent", "p", "a"):
        print("Status must be 'present' (or 'p') / 'absent' (or 'a').")
        return
    present = status_arg in ("present", "p")

    attendance_date: date | None = None
    if len(args) >= 3:
        try:
            attendance_date = date.fromisoformat(args[2])
        except ValueError:
            print(f"Invalid date format '{args[2]}'. Use YYYY-MM-DD.")
            return

    if manager.update_attendance(person_id, present, attendance_date):
        day = attendance_date or date.today()
        mark = "Present" if present else "Absent"
        print(f"✓ Updated attendance to {mark} for '{person_id}' on {day}.")
    else:
        print(
            f"✗ No existing entry found for '{person_id}' on the given date, "
            "or the ID does not exist."
        )


def cmd_report(manager: AttendanceManager, args: list[str]) -> None:
    """report <id>  – Show full attendance report for a person."""
    if not args:
        print("Usage: report <id>")
        return
    person_id = args[0]
    report = manager.get_report(person_id)
    if report is None:
        print(f"✗ ID '{person_id}' not found.")
        return
    _print_report(report)


def cmd_at_risk(manager: AttendanceManager, _args: list[str]) -> None:
    """at-risk  – List all people with WARNING or CRITICAL attendance."""
    at_risk = manager.get_at_risk()
    if not at_risk:
        print(_green("✓ No one is currently at risk. All attendance levels are GOOD."))
        return
    print(_bold(f"\n{'ID':<15} {'Name':<25} {'Attendance':>12}  {'Status':<10}"))
    print(_separator())
    for r in at_risk:
        pct = r["attendance_percentage"]
        pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
        print(
            f"{r['id']:<15} {r['name']:<25} {pct_str:>12}  "
            f"{_status_colored(r['status'])}"
        )


def cmd_summary(manager: AttendanceManager, _args: list[str]) -> None:
    """summary  – Show a summary for all registered people."""
    summary = manager.get_full_summary()
    if not summary:
        print("No people registered yet.")
        return
    print(_bold(f"\n{'ID':<15} {'Name':<25} {'Days':>6} {'Attendance':>12}  {'Status':<10}"))
    print(_separator())
    for r in summary:
        pct = r["attendance_percentage"]
        pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
        print(
            f"{r['id']:<15} {r['name']:<25} {r['total_days']:>6} {pct_str:>12}  "
            f"{_status_colored(r['status'])}"
        )


COMMANDS = {
    "add": cmd_add,
    "remove": cmd_remove,
    "list": cmd_list,
    "mark": cmd_mark,
    "update": cmd_update,
    "report": cmd_report,
    "at-risk": cmd_at_risk,
    "summary": cmd_summary,
}


def _print_help() -> None:
    print(_bold("\nAttendance Crisis Management System"))
    print(_separator())
    print("Commands:")
    for name, fn in COMMANDS.items():
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        print(f"  {name:<12}  {doc}")
    print()


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    manager = AttendanceManager()

    if not argv or argv[0] in ("-h", "--help", "help"):
        _print_help()
        return 0

    command = argv[0]
    args = argv[1:]

    if command not in COMMANDS:
        print(f"Unknown command '{command}'. Use --help to see available commands.")
        return 1

    COMMANDS[command](manager, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
