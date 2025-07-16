#!/usr/bin/env python3
"""
FortiGate ASIC-byte monthly usage reporter

- Connects to a FortiGate on HTTPS port
- Reads `asic_bytes` for policy ID
- Converts bytes → GiB
- Sends the result to a Discord webhook in the form:
    "Your monthly usage for <MONTH> <YEAR> is <ASIC_GIB>"
"""

import os
import requests
import urllib3
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env into os.environ

# ──── USER SETTINGS ─────────────────────────────────────────────────────────────────────
FGT_HOST        = os.getenv("FGT_HOST")             # FortiGate IP:port
API_TOKEN       = os.getenv("API_TOKEN")            # REST API token
POLICY_ID       = int(os.getenv("POLICY_ID", "1"))  # Firewall policy ID; defaults to 1
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")      # Your webhook
VERIFY_SSL      = os.getenv("VERIFY_SSL", "false").lower()=="true"  # Boolean to verify SSL; defaults to false
# ────────────────────────────────────────────────────────────────────────────────────────

# Silence urllib3 InsecureRequestWarning (warning for self-signed cert)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_asic_gib() -> float:
    # Return `asic_bytes` for POLICY_ID as GiB (binary)
    url = f"https://{FGT_HOST}/api/v2/monitor/firewall/policy"
    params = {"policyid": POLICY_ID}
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}

    try:
        r = requests.get(url, headers=headers, params=params,
                         verify=VERIFY_SSL, timeout=10)
        r.raise_for_status()
    except requests.RequestException as exc:
        sys.exit(f"API request failed: {exc}")

    payload = r.json()
    stat_obj = (payload.get("results") or payload.get("data") or [None])[0]
    if not stat_obj or "asic_bytes" not in stat_obj:
        sys.exit("`asic_bytes` field missing; check firmware or endpoint.")

    asic_bytes = int(stat_obj["asic_bytes"])
    return asic_bytes / 1024**3   # bytes → GiB


def send_to_discord(asic_gib: float):
    # Post the formatted usage message to the Discord webhook
    now = datetime.now()
    month_year = now.strftime("%B %Y")  # e.g. "July 2025"
    content = f"Your monthly usage for {month_year} is {asic_gib:.2f} GiB"

    try:
        r = requests.post(DISCORD_WEBHOOK, json={"content": content}, timeout=10)
        r.raise_for_status()
        print("Message sent to Discord.")
    except requests.RequestException as exc:
        sys.exit(f"Discord webhook failed: {exc}")


if __name__ == "__main__":
    gib = fetch_asic_gib()
    send_to_discord(gib)