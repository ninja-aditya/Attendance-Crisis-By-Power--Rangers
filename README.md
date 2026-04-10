# Attendance Crisis Management System

A Python-based system to **monitor, analyze, and address low attendance** among students or employees. It helps users understand their attendance status and take corrective actions before reaching critical levels.

---

## Features

| Feature | Description |
|---|---|
| **Person registration** | Add / remove students or employees by ID |
| **Attendance marking** | Record daily presence or absence (with optional date override) |
| **Attendance update** | Correct an already-recorded entry |
| **Percentage calculation** | Automatic calculation of attendance percentage |
| **Status classification** | GOOD ≥ 75 % · WARNING 65–74 % · CRITICAL < 65 % |
| **Corrective actions** | Personalized recommendations for at-risk individuals |
| **At-risk report** | One-command view of everyone who needs attention |
| **Full summary** | Overview of all registered people |
| **Data persistence** | Records are saved to a local JSON file between runs |

---

## Requirements

- Python 3.10+
- `pytest` (for running tests)

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Quick Start

```bash
# Register students / employees
python main.py add S001 "Alice Smith"
python main.py add S002 "Bob Jones"

# Mark attendance
python main.py mark S001 present 2024-03-01
python main.py mark S001 absent  2024-03-02
python main.py mark S002 absent  2024-03-01

# View individual report
python main.py report S001

# View everyone at risk
python main.py at-risk

# View full summary
python main.py summary
```

---

## CLI Commands

```
add     <id> <name>                         Register a new person
remove  <id>                                Remove a person
list                                        List all registered people
mark    <id> <present|absent> [YYYY-MM-DD]  Mark attendance for a date
update  <id> <present|absent> [YYYY-MM-DD]  Update an existing attendance entry
report  <id>                                Show full report for a person
at-risk                                     List all WARNING / CRITICAL people
summary                                     Show a summary for everyone
```

---

## Attendance Status Levels

| Status | Attendance | Action required |
|---|---|---|
| **GOOD** | ≥ 75 % | None – keep it up! |
| **WARNING** | 65 – 74.99 % | At risk – avoid further absences |
| **CRITICAL** | < 65 % | Immediate action required |

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Project Structure

```
├── attendance.py          # Core AttendanceManager class
├── main.py                # CLI entry point
├── requirements.txt       # Python dependencies
├── attendance_data.json   # Auto-created data file (git-ignored)
└── tests/
    └── test_attendance.py # Unit tests (37 tests)
```