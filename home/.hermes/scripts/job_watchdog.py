#!/usr/bin/env python3
import subprocess
import json
import os
import re
import sys
from datetime import datetime

HERMES = "/var/home/charlie/.local/bin/hermes"
NTFY = "/var/home/charlie/.local/bin/ntfy"
STATE_FILE = "/tmp/job-watchdog-state.json"
REPORT_DIR = os.path.expanduser("~/.hermes/cron/output")
MAX_RETRIES = 3

TRANSIENT_PATTERNS = [
    r"timed out after 120s", r"timeout", r"ETIMEDOUT", r"ECONNREFUSED", r"503", r"502", r"unavailable",
    r"adb device unavailable", r"pull failed", r"device not found", r"offline", r"locked", r"busy",
]

ROOT_CAUSE_PATTERNS = [
    r"No virtual environment found", r"uv venv",
    r"the following arguments are required", r"--out",
    r"No such file or directory", r"Permission denied",
    r"config", r"not found", r"invalid",
]


def run_cmd(cmd, **kwargs):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, **kwargs)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, "", str(e)


def get_jobs():
    code, out, err = run_cmd([HERMES, "cron", "list"])
    if code != 0:
        print(f"ERROR: hermes cron list failed: {err}", file=sys.stderr)
        return []

    jobs = []
    lines = out.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"\s*([a-f0-9]+)\s+\[([^\]]+)\]", lines[i])
        if not m:
            i += 1
            continue
        job_id = m.group(1)
        job = {"id": job_id, "status_tag": m.group(2)}
        i += 1
        block = []
        while i < len(lines):
            if re.match(r"\s*[a-f0-9]+\s+\[[^\]]+\]", lines[i]):
                break
            block.append(lines[i])
            i += 1

        for bl in block:
            m2 = re.match(r"\s*Name:\s+(.*)", bl)
            if m2:
                job["name"] = m2.group(1).strip()
            m2 = re.match(r"\s*Last run:\s+(.*)", bl)
            if m2:
                job["last_run"] = m2.group(1).strip()
            m2 = re.match(r"\s*Script:\s+(.*)", bl)
            if m2:
                job["script"] = m2.group(1).strip()
            m2 = re.match(r"\s*Profile:\s+(.*)", bl)
            if m2:
                job["profile"] = m2.group(1).strip()

        if "last_run" in job and "error" in job["last_run"]:
            job["last_status"] = "error"
            parts = job["last_run"].split("error:")
            job["error"] = parts[1].strip() if len(parts) > 1 else ""
            for idx, bl in enumerate(block):
                if "Last run:" in bl:
                    for cont in block[idx + 1:]:
                        s = cont.strip()
                        if s:
                            job["error"] += " | " + s
                    break
        elif "last_run" in job and "ok" in job["last_run"]:
            job["last_status"] = "ok"
        else:
            job["last_status"] = "unknown"

        jobs.append(job)

    return jobs


def classify_error(job):
    text = " ".join([
        job.get("error", ""),
        job.get("last_run", ""),
        job.get("name", ""),
    ]).lower()

    for pat in ROOT_CAUSE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "root_cause"

    for pat in TRANSIENT_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "transient"

    # Name-based fallback for known flaky services
    name = job.get("name", "").lower()
    if "phone-sync" in name:
        return "transient"

    return "unknown"


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def is_silent_mode(state):
    return state.get("silent_mode") is True and state.get("consecutive_success", 0) >= 5


def enter_silent_mode(state):
    state["silent_mode"] = True
    state["consecutive_success"] = 0
    state["consecutive_failure"] = 0


def exit_silent_mode(state):
    state["silent_mode"] = False
    state["consecutive_success"] = 0
    state["consecutive_failure"] = 0


def check_readiness(job):
    name = job.get("name", "").lower()
    if "phone-sync" in name or "phone" in name:
        code, out, err = run_cmd([
            "adb", "-s", "100.87.37.3:5555", "get-state"
        ])
        return code == 0 and "device" in out
    script = job.get("script")
    if script:
        path = os.path.expanduser(f"~/.hermes/scripts/{script}")
        if not os.path.exists(path):
            return False
    return True


def notify(title, message, level="ERROR"):
    run_cmd([NTFY, "send", "-t", title, "-l", level, "charlie-actions"], input=message)


def main():
    jobs = get_jobs()
    failed = [j for j in jobs if j["last_status"] == "error"]
    state = load_state()
    now = datetime.now().isoformat()

    # ---- Silent mode logic ----
    if failed:
        state["silent_mode"] = False
        state["consecutive_success"] = 0
        state["consecutive_failure"] = state.get("consecutive_failure", 0) + 1
    else:
        if state.get("silent_mode") is True:
            silent_log = os.path.expanduser("~/.hermes/cron/output/job-watchdog-silent.log")
            os.makedirs(os.path.dirname(silent_log), exist_ok=True)
            with open(silent_log, "a", encoding="utf-8") as f:
                f.write(f"{now} silent_ok\n")
            save_state(state)
            return 0
        state["consecutive_failure"] = 0
        state["consecutive_success"] = state.get("consecutive_success", 0) + 1
        if state["consecutive_success"] >= 5:
            enter_silent_mode(state)
            silent_log = os.path.expanduser("~/.hermes/cron/output/job-watchdog-silent.log")
            os.makedirs(os.path.dirname(silent_log), exist_ok=True)
            with open(silent_log, "a", encoding="utf-8") as f:
                f.write(f"{now} silent_mode_entered\n")
            save_state(state)
            return 0
    # ---- End silent mode logic ----

    report = []
    report.append(f"# Job Watchdog Report")
    report.append(f"**Time:** {now}")
    report.append(f"**Scanned:** {len(jobs)} jobs")
    report.append(f"**Failed:** {len(failed)} jobs")
    report.append("")

    for job in failed:
        jid = job["id"]
        name = job.get("name", jid)
        error = job.get("error", "")
        cls = classify_error(job)

        retry_key = f"{jid}:retry_count"
        retry_count = state.get(retry_key, 0)

        report.append(f"## {name}")
        report.append(f"- ID: {jid}")
        report.append(f"- Error: {error}")
        report.append(f"- Class: {cls}")
        report.append(f"- Retries: {retry_count}")

        if cls == "root_cause":
            code, out, err = run_cmd([HERMES, "cron", "pause", jid])
            if code == 0:
                report.append("- Action: paused")
                notify("❌ Hermes Job Paused", f"{name}\n{error}", level="ERROR")
            else:
                report.append(f"- Action: pause failed ({err})")
            state[retry_key] = 0

        elif cls == "transient":
            if retry_count >= MAX_RETRIES:
                code, out, err = run_cmd([HERMES, "cron", "pause", jid])
                report.append("- Action: paused (retries exhausted)")
                notify("🚨 Hermes Job Stopped", f"{name}\n{error}\nRetries: {retry_count}", level="CRITICAL")
                state[retry_key] = 0
            else:
                if check_readiness(job):
                    code, out, err = run_cmd([HERMES, "cron", "run", jid])
                    if code == 0:
                        report.append("- Action: retried")
                        notify("✅ Hermes Job Retried", f"{name}\n{error}\nAttempt {retry_count + 1}/{MAX_RETRIES}", level="INFO")
                    else:
                        report.append(f"- Action: retry failed ({err})")
                    state[retry_key] = retry_count + 1
                else:
                    report.append("- Action: skipped (readiness check failed)")
                    state[retry_key] = retry_count
        else:
            report.append("- Action: unknown, manual review needed")
            notify("⚠️ Hermes Job Unknown", f"{name}\n{error}", level="WARNING")

        report.append("")

    state["last_run"] = now
    save_state(state)

    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = os.path.join(REPORT_DIR, f"job-watchdog-{date_str}.md")
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(report))

    print("\n".join(report))


if __name__ == "__main__":
    main()
