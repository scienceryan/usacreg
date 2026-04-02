#!/usr/bin/env python3
"""
USA Climbing Region 21 Page Monitor
Checks https://usaclimbing.org/compete/region-21/ for changes
and sends a desktop notification + prints an alert when the page updates.

Usage:
    python3 check_region21.py                  # check every 60 minutes (default)
    python3 check_region21.py --interval 30    # check every 30 minutes
    python3 check_region21.py --once           # check once and exit

Requirements:
    pip install requests beautifulsoup4

Optional (for email alerts):
    Set EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD, SMTP_HOST env vars.

Run in background (Linux/Mac):
    nohup python3 check_region21.py --interval 60 > region21.log 2>&1 &
"""

import argparse
import hashlib
import json
import os
import platform
import smtplib
import subprocess
import sys
import time
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run: pip install requests beautifulsoup4")
    sys.exit(1)

URL = "https://usaclimbing.org/compete/region-21/"
STATE_FILE = Path.home() / ".region21_monitor_state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


# ── Content extraction ────────────────────────────────────────────────────────

def fetch_page():
    """Fetch the page and return the HTML text."""
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_content(html: str) -> dict:
    """
    Pull out the parts of the page most likely to change:
      - The full text of the main content area
      - A hash of that text (used to detect changes quickly)
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove nav / footer noise so only body content matters
    for tag in soup.select("nav, footer, header, script, style"):
        tag.decompose()

    # Focus on the main content if possible, fall back to body
    main = soup.select_one("main, #main, .main-content, article") or soup.body
    text = main.get_text(separator="\n", strip=True) if main else soup.get_text()

    # Specifically grab the Upcoming Events block
    events_section = ""
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if "upcoming" in heading.get_text(strip=True).lower():
            # Grab siblings until the next heading
            siblings = []
            for sib in heading.find_next_siblings():
                if sib.name in ("h2", "h3", "h4"):
                    break
                siblings.append(sib.get_text(separator=" ", strip=True))
            events_section = "\n".join(siblings).strip()
            break

    content_hash = hashlib.sha256(text.encode()).hexdigest()

    return {
        "hash": content_hash,
        "events_section": events_section,
        "full_text_preview": text[:500],  # first 500 chars for context
    }


# ── State persistence ─────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── Notifications ─────────────────────────────────────────────────────────────

def desktop_notify(title: str, message: str):
    """Send a desktop notification (macOS, Linux, Windows)."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{message}" with title "{title}"'],
                check=False
            )
        elif system == "Linux":
            subprocess.run(
                ["notify-send", title, message],
                check=False
            )
        elif system == "Windows":
            # Requires win10toast: pip install win10toast
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, message, duration=10)
            except ImportError:
                pass  # silently skip if not installed
    except FileNotFoundError:
        pass  # notification tool not available


def send_email(subject: str, body: str):
    """
    Send an email alert. Configure with environment variables:
        EMAIL_FROM      sender address
        EMAIL_TO        recipient address
        EMAIL_PASSWORD  sender password (for Gmail: use an App Password)
        SMTP_HOST       SMTP host (default: smtp.gmail.com)
        SMTP_PORT       SMTP port (default: 587)
    """
    from_addr = os.environ.get("EMAIL_FROM")
    to_addr = os.environ.get("EMAIL_TO")
    password = os.environ.get("EMAIL_PASSWORD")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    if not all([from_addr, to_addr, password]):
        return  # email not configured

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(from_addr, password)
            server.send_message(msg)
        print(f"  📧 Email alert sent to {to_addr}")
    except Exception as e:
        print(f"  ⚠️  Email failed: {e}")


def alert(old: dict, new: dict):
    """Fire all configured alerts when a change is detected."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    old_events = old.get("events_section", "(none)")
    new_events = new.get("events_section", "(none)")

    summary = (
        f"Change detected at {now}\n"
        f"URL: {URL}\n\n"
        f"--- PREVIOUS Upcoming Events ---\n{old_events or '(empty)'}\n\n"
        f"--- NEW Upcoming Events ---\n{new_events or '(empty)'}\n"
    )

    print("\n" + "=" * 60)
    print("🚨  REGION 21 PAGE CHANGED!")
    print("=" * 60)
    print(summary)
    print("=" * 60 + "\n")

    desktop_notify("Region 21 Updated!", "The USA Climbing Region 21 page changed. Check for new events!")
    send_email("🧗 Region 21 Page Changed!", summary)


# ── Main loop ─────────────────────────────────────────────────────────────────

def check(verbose: bool = True) -> bool:
    """
    Fetch the page and compare to last known state.
    Returns True if the page changed.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if verbose:
        print(f"[{now}] Checking {URL} ...", end=" ", flush=True)

    try:
        html = fetch_page()
        new_content = extract_content(html)
    except requests.RequestException as e:
        print(f"FETCH ERROR: {e}")
        return False

    state = load_state()
    old_hash = state.get("hash")
    changed = old_hash is not None and old_hash != new_content["hash"]

    if old_hash is None:
        print("First run — baseline saved.")
        events = new_content["events_section"]
        print(f"  Current Upcoming Events: {events or '(none listed)'}")
    elif changed:
        print("CHANGED! 🚨")
        alert(state, new_content)
    else:
        print("No change.")
        if verbose:
            events = new_content["events_section"]
            print(f"  Upcoming Events: {events or '(none listed)'}")

    # Always save latest state
    save_state(new_content)
    return changed


def main():
    parser = argparse.ArgumentParser(description="Monitor USA Climbing Region 21 for changes.")
    parser.add_argument("--interval", type=int, default=60,
                        help="Check interval in minutes (default: 60)")
    parser.add_argument("--once", action="store_true",
                        help="Check once and exit")
    args = parser.parse_args()

    print(f"🧗 USA Climbing Region 21 Monitor")
    print(f"   URL:      {URL}")
    print(f"   State:    {STATE_FILE}")
    if not args.once:
        print(f"   Interval: every {args.interval} minute(s)")
        print(f"   Press Ctrl+C to stop.\n")

    check()

    if args.once:
        return

    while True:
        time.sleep(args.interval * 60)
        check()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitor stopped.")