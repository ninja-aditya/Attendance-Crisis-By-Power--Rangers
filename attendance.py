"""
Attendance Crisis Management System - Core Module

Monitors, analyzes, and addresses low attendance for students or employees.
"""

import json
import os
from datetime import date, datetime


# Attendance thresholds
THRESHOLD_GOOD = 75.0       # >= 75% is good
THRESHOLD_WARNING = 65.0    # 65-74.99% is a warning (at risk)
# < 65% is critical

STATUS_GOOD = "GOOD"
STATUS_WARNING = "WARNING"
STATUS_CRITICAL = "CRITICAL"


class AttendanceManager:
    """Manages attendance records for students or employees."""

    def __init__(self, data_file: str = "attendance_data.json"):
        self.data_file = data_file
        self._records: dict = {}  # {person_id: {"name": str, "attendance": [{"date": str, "present": bool}]}}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load records from the JSON data file, if it exists."""
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as fh:
                self._records = json.load(fh)

    def _save(self) -> None:
        """Persist records to the JSON data file."""
        with open(self.data_file, "w", encoding="utf-8") as fh:
            json.dump(self._records, fh, indent=2)

    # ------------------------------------------------------------------
    # Record management
    # ------------------------------------------------------------------

    def add_person(self, person_id: str, name: str) -> bool:
        """Register a new student or employee.

        Returns True if added, False if the ID already exists.
        """
        if person_id in self._records:
            return False
        self._records[person_id] = {"name": name, "attendance": []}
        self._save()
        return True

    def remove_person(self, person_id: str) -> bool:
        """Remove a student or employee by ID.

        Returns True if removed, False if the ID does not exist.
        """
        if person_id not in self._records:
            return False
        del self._records[person_id]
        self._save()
        return True

    def list_people(self) -> list[dict]:
        """Return a list of all registered people with their IDs and names."""
        return [
            {"id": pid, "name": data["name"]}
            for pid, data in self._records.items()
        ]

    # ------------------------------------------------------------------
    # Attendance marking
    # ------------------------------------------------------------------

    def mark_attendance(
        self,
        person_id: str,
        present: bool,
        attendance_date: date | None = None,
    ) -> bool:
        """Record attendance for a person on a given date.

        If *attendance_date* is None, today's date is used.
        Returns True on success, False if the person does not exist or a
        duplicate entry for that date would be created.
        """
        if person_id not in self._records:
            return False

        target = (attendance_date or date.today()).isoformat()

        # Prevent duplicate entries for the same date
        for entry in self._records[person_id]["attendance"]:
            if entry["date"] == target:
                return False

        self._records[person_id]["attendance"].append(
            {"date": target, "present": present}
        )
        self._save()
        return True

    def update_attendance(
        self,
        person_id: str,
        present: bool,
        attendance_date: date | None = None,
    ) -> bool:
        """Update an existing attendance entry for a person on a given date.

        Returns True if updated, False if no matching entry exists.
        """
        if person_id not in self._records:
            return False

        target = (attendance_date or date.today()).isoformat()
        for entry in self._records[person_id]["attendance"]:
            if entry["date"] == target:
                entry["present"] = present
                self._save()
                return True
        return False

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def get_attendance_percentage(self, person_id: str) -> float | None:
        """Return the attendance percentage for a person.

        Returns None if the person does not exist or has no records.
        """
        if person_id not in self._records:
            return None
        entries = self._records[person_id]["attendance"]
        if not entries:
            return None
        total = len(entries)
        present = sum(1 for e in entries if e["present"])
        return round((present / total) * 100, 2)

    def get_status(self, person_id: str) -> str | None:
        """Return the attendance status for a person.

        Possible values: STATUS_GOOD, STATUS_WARNING, STATUS_CRITICAL, or None
        if the person does not exist or has no records.
        """
        pct = self.get_attendance_percentage(person_id)
        if pct is None:
            return None
        if pct >= THRESHOLD_GOOD:
            return STATUS_GOOD
        if pct >= THRESHOLD_WARNING:
            return STATUS_WARNING
        return STATUS_CRITICAL

    def get_corrective_actions(self, person_id: str) -> list[str]:
        """Return a list of corrective action recommendations.

        An empty list is returned when the person does not exist, has no
        records, or attendance is already GOOD.
        """
        status = self.get_status(person_id)
        pct = self.get_attendance_percentage(person_id)
        if status is None or status == STATUS_GOOD:
            return []

        actions: list[str] = []
        if pct is not None:
            shortage = THRESHOLD_GOOD - pct
            actions.append(
                f"Your attendance is {pct:.1f}% – you need at least "
                f"{THRESHOLD_GOOD:.0f}%. You are {shortage:.1f}% below the "
                "minimum requirement."
            )

        if status == STATUS_CRITICAL:
            actions += [
                "⚠️  CRITICAL: Your attendance has dropped below 65%. "
                "Immediate action is required.",
                "Contact your instructor/supervisor and explain your situation.",
                "Provide valid documentation for all past absences.",
                "Apply for attendance condonation if eligible under institutional policy.",
                "Create a strict daily schedule to ensure you do not miss any more sessions.",
                "Consider withdrawing from elective activities to prioritize attendance.",
            ]
        elif status == STATUS_WARNING:
            actions += [
                "⚡ WARNING: Your attendance is between 65% and 75%. "
                "You are at risk of falling into the critical zone.",
                "Avoid any further unplanned absences.",
                "Speak to your instructor/supervisor about your current situation.",
                "Review your schedule and identify conflicts that may be causing absences.",
                "Set daily reminders so you do not forget sessions.",
            ]
        return actions

    def get_report(self, person_id: str) -> dict | None:
        """Return a complete attendance report for a person.

        Returns None if the person does not exist.
        """
        if person_id not in self._records:
            return None
        data = self._records[person_id]
        entries = data["attendance"]
        total = len(entries)
        present = sum(1 for e in entries if e["present"])
        absent = total - present
        pct = self.get_attendance_percentage(person_id)
        status = self.get_status(person_id)
        return {
            "id": person_id,
            "name": data["name"],
            "total_days": total,
            "days_present": present,
            "days_absent": absent,
            "attendance_percentage": pct,
            "status": status,
            "corrective_actions": self.get_corrective_actions(person_id),
            "attendance_log": sorted(entries, key=lambda e: e["date"]),
        }

    def get_at_risk(self) -> list[dict]:
        """Return summary records for all people with WARNING or CRITICAL status."""
        at_risk = []
        for pid in self._records:
            status = self.get_status(pid)
            if status in (STATUS_WARNING, STATUS_CRITICAL):
                pct = self.get_attendance_percentage(pid)
                at_risk.append(
                    {
                        "id": pid,
                        "name": self._records[pid]["name"],
                        "attendance_percentage": pct,
                        "status": status,
                    }
                )
        return sorted(at_risk, key=lambda r: (r["attendance_percentage"] or 0))

    def get_full_summary(self) -> list[dict]:
        """Return a summary for every registered person."""
        summary = []
        for pid in self._records:
            pct = self.get_attendance_percentage(pid)
            status = self.get_status(pid)
            summary.append(
                {
                    "id": pid,
                    "name": self._records[pid]["name"],
                    "total_days": len(self._records[pid]["attendance"]),
                    "attendance_percentage": pct,
                    "status": status,
                }
            )
        return summary
