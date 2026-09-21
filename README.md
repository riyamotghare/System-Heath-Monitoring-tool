# IT Support & System Health Monitoring Tool

A local Python + Streamlit application that monitors the health of the machine it runs on, runs basic network connectivity checks, and manages IT support tickets stored in SQLite.

## Overview
Built as a learning and portfolio project to practice operating system fundamentals, basic networking, Python automation, SQL, and incident/ticket handling. It runs entirely on a local laptop with no cloud services.

## Problem Statement
IT support staff regularly need to (1) check whether a machine is under resource pressure, (2) check whether a host is reachable, and (3) record and track the issues users report. This project combines those three tasks in one small dashboard.

## Features
- **System Health:** CPU, RAM and disk utilization; total/available RAM and disk space; hostname, OS and version, CPU cores, uptime; configurable thresholds with warnings that name the resource.
- **Network Diagnostics:** ping a hostname or IP using the OS `ping` command, with input validation, timeout handling, raw output display, and a note that failed ping does not always mean a service is down.
- **Support Tickets:** create tickets (title, category, priority, description, troubleshooting attempted), view and filter them, update status (Open / In Progress / Resolved). Tickets persist in SQLite.
- **Dashboard:** four tabs, success/warning/error messages, and empty states.

## Technology Stack
Python 3.9+, Streamlit, psutil, SQLite (`sqlite3`), Pandas, Plotly, `subprocess`.

## Architecture and Workflow
```
Browser (Streamlit UI)  -->  app.py
                               |-- monitor.py  --> psutil (metrics), subprocess (ping)
                               |-- database.py --> SQLite file (tickets.db)
```
1. The user interacts with a widget in the browser.
2. Streamlit reruns `app.py` from top to bottom.
3. `app.py` calls functions in `monitor.py` or `database.py`.
4. Results are displayed as metrics, tables, or messages.

## Installation
```bash
git clone <your-repo-url>
cd it-support-system-health

python -m venv venv

# Windows (PowerShell)
venv\Scripts\Activate.ps1
# Windows (Command Prompt)
venv\Scripts\activate.bat
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

## Usage
```bash
streamlit run app.py
```
Open http://localhost:8501 in your browser if it does not open automatically.

## Testing Checklist
- [ ] System Health tab shows CPU, RAM, disk, hostname, OS, cores and uptime.
- [ ] Lowering a threshold in the sidebar (e.g. RAM to 5%) shows a warning naming RAM.
- [ ] Ping `127.0.0.1` or `google.com` shows a success message and command output.
- [ ] Ping `10.255.255.1` or `nonexistent.invalid` shows a failure/timeout without crashing.
- [ ] Input such as `bad;host` is rejected with an error message.
- [ ] Creating a ticket shows a success message and the ticket appears in the table.
- [ ] Updating a ticket status changes it in the table.
- [ ] After stopping and restarting the app, tickets are still there.

## Limitations
- Monitors only the local machine; no metric history or background alerting.
- No authentication or user roles; one local SQLite file.
- Ping tests ICMP only; it cannot confirm a specific service or port is working.
- Not designed for production or enterprise use.

## Future Improvements
- Store metric history in SQLite and chart trends over time.
- Add TCP port checks (e.g. port 80/443) alongside ping.
- Add ticket assignment, comments, and CSV export.
- Add automated tests for `monitor.py` and `database.py`.
- Add email or notification alerts when thresholds are exceeded.
