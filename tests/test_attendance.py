"""Unit tests for the Attendance Crisis Management System."""

import json
import os
import tempfile
from datetime import date

import pytest

from attendance import (
    AttendanceManager,
    STATUS_GOOD,
    STATUS_WARNING,
    STATUS_CRITICAL,
    THRESHOLD_GOOD,
    THRESHOLD_WARNING,
)


@pytest.fixture
def manager(tmp_path):
    """Return a fresh AttendanceManager backed by a temp file."""
    data_file = str(tmp_path / "test_attendance.json")
    return AttendanceManager(data_file=data_file)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestPersonRegistration:
    def test_add_person_success(self, manager):
        assert manager.add_person("S001", "Alice") is True

    def test_add_person_duplicate(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.add_person("S001", "Bob") is False

    def test_remove_person_success(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.remove_person("S001") is True

    def test_remove_person_not_found(self, manager):
        assert manager.remove_person("NONEXISTENT") is False

    def test_list_people_empty(self, manager):
        assert manager.list_people() == []

    def test_list_people(self, manager):
        manager.add_person("S001", "Alice")
        manager.add_person("S002", "Bob")
        people = manager.list_people()
        ids = {p["id"] for p in people}
        assert ids == {"S001", "S002"}


# ---------------------------------------------------------------------------
# Attendance marking
# ---------------------------------------------------------------------------

class TestMarkAttendance:
    def test_mark_present(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.mark_attendance("S001", True, date(2024, 1, 10)) is True

    def test_mark_absent(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.mark_attendance("S001", False, date(2024, 1, 11)) is True

    def test_mark_duplicate_date_rejected(self, manager):
        manager.add_person("S001", "Alice")
        manager.mark_attendance("S001", True, date(2024, 1, 10))
        assert manager.mark_attendance("S001", False, date(2024, 1, 10)) is False

    def test_mark_unknown_person(self, manager):
        assert manager.mark_attendance("UNKNOWN", True) is False

    def test_mark_defaults_to_today(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.mark_attendance("S001", True) is True
        report = manager.get_report("S001")
        assert report["total_days"] == 1

    def test_update_attendance(self, manager):
        manager.add_person("S001", "Alice")
        manager.mark_attendance("S001", True, date(2024, 1, 10))
        assert manager.update_attendance("S001", False, date(2024, 1, 10)) is True
        report = manager.get_report("S001")
        assert report["days_present"] == 0

    def test_update_nonexistent_entry(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.update_attendance("S001", True, date(2024, 1, 10)) is False

    def test_update_unknown_person(self, manager):
        assert manager.update_attendance("UNKNOWN", True) is False


# ---------------------------------------------------------------------------
# Percentage calculation
# ---------------------------------------------------------------------------

class TestAttendancePercentage:
    def test_percentage_all_present(self, manager):
        manager.add_person("S001", "Alice")
        for day in range(1, 11):
            manager.mark_attendance("S001", True, date(2024, 1, day))
        assert manager.get_attendance_percentage("S001") == 100.0

    def test_percentage_all_absent(self, manager):
        manager.add_person("S001", "Alice")
        for day in range(1, 11):
            manager.mark_attendance("S001", False, date(2024, 1, day))
        assert manager.get_attendance_percentage("S001") == 0.0

    def test_percentage_mixed(self, manager):
        manager.add_person("S001", "Alice")
        # 7 present out of 10 = 70%
        for day in range(1, 11):
            manager.mark_attendance("S001", day <= 7, date(2024, 1, day))
        assert manager.get_attendance_percentage("S001") == 70.0

    def test_percentage_no_records(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.get_attendance_percentage("S001") is None

    def test_percentage_unknown_person(self, manager):
        assert manager.get_attendance_percentage("UNKNOWN") is None


# ---------------------------------------------------------------------------
# Status classification
# ---------------------------------------------------------------------------

class TestStatus:
    def _setup_percentage(self, manager, person_id: str, name: str, pct: float):
        """Add *pct* % attendance over 100 days for the given person."""
        manager.add_person(person_id, name)
        present_days = int(pct)
        for day_offset in range(100):
            d = date(2024, 1, 1)
            from datetime import timedelta
            d = d + timedelta(days=day_offset)
            manager.mark_attendance(person_id, day_offset < present_days, d)

    def test_status_good(self, manager):
        self._setup_percentage(manager, "S001", "Alice", 80.0)
        assert manager.get_status("S001") == STATUS_GOOD

    def test_status_good_at_boundary(self, manager):
        self._setup_percentage(manager, "S001", "Alice", 75.0)
        assert manager.get_status("S001") == STATUS_GOOD

    def test_status_warning(self, manager):
        self._setup_percentage(manager, "S001", "Alice", 70.0)
        assert manager.get_status("S001") == STATUS_WARNING

    def test_status_warning_at_boundary(self, manager):
        self._setup_percentage(manager, "S001", "Alice", 65.0)
        assert manager.get_status("S001") == STATUS_WARNING

    def test_status_critical(self, manager):
        self._setup_percentage(manager, "S001", "Alice", 60.0)
        assert manager.get_status("S001") == STATUS_CRITICAL

    def test_status_no_records(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.get_status("S001") is None

    def test_status_unknown_person(self, manager):
        assert manager.get_status("UNKNOWN") is None


# ---------------------------------------------------------------------------
# Corrective actions
# ---------------------------------------------------------------------------

class TestCorrectiveActions:
    def _mark_days(self, manager, person_id: str, present_count: int, total: int):
        from datetime import timedelta
        base = date(2024, 1, 1)
        for i in range(total):
            manager.mark_attendance(person_id, i < present_count, base + timedelta(days=i))

    def test_no_actions_when_good(self, manager):
        manager.add_person("S001", "Alice")
        self._mark_days(manager, "S001", 80, 100)
        assert manager.get_corrective_actions("S001") == []

    def test_actions_when_warning(self, manager):
        manager.add_person("S001", "Alice")
        self._mark_days(manager, "S001", 70, 100)
        actions = manager.get_corrective_actions("S001")
        assert len(actions) > 0
        assert any("WARNING" in a or "at risk" in a.lower() for a in actions)

    def test_actions_when_critical(self, manager):
        manager.add_person("S001", "Alice")
        self._mark_days(manager, "S001", 60, 100)
        actions = manager.get_corrective_actions("S001")
        assert len(actions) > 0
        assert any("CRITICAL" in a for a in actions)

    def test_no_actions_when_no_records(self, manager):
        manager.add_person("S001", "Alice")
        assert manager.get_corrective_actions("S001") == []


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

class TestReport:
    def test_report_structure(self, manager):
        manager.add_person("S001", "Alice")
        manager.mark_attendance("S001", True, date(2024, 1, 1))
        manager.mark_attendance("S001", False, date(2024, 1, 2))
        report = manager.get_report("S001")
        assert report is not None
        assert report["id"] == "S001"
        assert report["name"] == "Alice"
        assert report["total_days"] == 2
        assert report["days_present"] == 1
        assert report["days_absent"] == 1
        assert report["attendance_percentage"] == 50.0
        assert report["status"] == STATUS_CRITICAL
        assert isinstance(report["corrective_actions"], list)
        assert isinstance(report["attendance_log"], list)

    def test_report_unknown_person(self, manager):
        assert manager.get_report("UNKNOWN") is None

    def test_at_risk_returns_warning_and_critical(self, manager):
        from datetime import timedelta
        base = date(2024, 1, 1)

        # Good student – should NOT appear
        manager.add_person("S001", "Good")
        for i in range(100):
            manager.mark_attendance("S001", i < 80, base + timedelta(days=i))

        # Warning student
        manager.add_person("S002", "Warn")
        for i in range(100):
            manager.mark_attendance("S002", i < 70, base + timedelta(days=i))

        # Critical student
        manager.add_person("S003", "Crit")
        for i in range(100):
            manager.mark_attendance("S003", i < 60, base + timedelta(days=i))

        at_risk = manager.get_at_risk()
        ids = {r["id"] for r in at_risk}
        assert "S001" not in ids
        assert "S002" in ids
        assert "S003" in ids

    def test_full_summary(self, manager):
        manager.add_person("S001", "Alice")
        manager.mark_attendance("S001", True, date(2024, 1, 1))
        summary = manager.get_full_summary()
        assert len(summary) == 1
        assert summary[0]["id"] == "S001"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_data_persists_across_instances(self, tmp_path):
        data_file = str(tmp_path / "persist.json")
        m1 = AttendanceManager(data_file=data_file)
        m1.add_person("S001", "Alice")
        m1.mark_attendance("S001", True, date(2024, 1, 1))

        m2 = AttendanceManager(data_file=data_file)
        assert m2.get_attendance_percentage("S001") == 100.0

    def test_data_file_created(self, tmp_path):
        data_file = str(tmp_path / "new_data.json")
        m = AttendanceManager(data_file=data_file)
        m.add_person("S001", "Alice")
        assert os.path.exists(data_file)

    def test_data_file_valid_json(self, tmp_path):
        data_file = str(tmp_path / "valid.json")
        m = AttendanceManager(data_file=data_file)
        m.add_person("S001", "Alice")
        with open(data_file) as f:
            data = json.load(f)
        assert "S001" in data
