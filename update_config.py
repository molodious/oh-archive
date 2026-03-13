#!/usr/bin/env python3
"""
Update config.json with the next Office Hours date from Google Calendar.
Run this standalone or it's called automatically by update_archive.py.
"""

import json, requests, subprocess, os
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent.parent  # workspace root
ARCHIVE_DIR = Path(__file__).parent
CONFIG_FILE = ARCHIVE_DIR / "config.json"

OH115_DATE = datetime.fromisoformat('2026-03-02T20:00:00-05:00')

def get_token():
    with open(WORKSPACE / 'credentials/google_tokens.json') as f:
        tokens = json.load(f)
    with open(WORKSPACE / 'credentials/google_oauth.json') as f:
        oauth = json.load(f)
    r = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': oauth['installed']['client_id'],
        'client_secret': oauth['installed']['client_secret'],
        'refresh_token': tokens['refresh_token'],
        'grant_type': 'refresh_token'
    })
    return r.json()['access_token']

def get_next_oh():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    now = datetime.now(timezone.utc).isoformat()

    r = requests.get(
        'https://www.googleapis.com/calendar/v3/calendars/primary/events',
        headers=headers,
        params={
            'timeMin': now,
            'maxResults': 5,
            'singleEvents': True,
            'orderBy': 'startTime',
            'q': 'MPEP Office Hours'
        }
    )

    events = [
        e for e in r.json().get('items', [])
        if 'Office Hours' in e.get('summary', '') and 'dateTime' in e['start']
    ]

    if not events:
        return None

    event = events[0]
    dt_str = event['start']['dateTime']
    dt = datetime.fromisoformat(dt_str)

    # Compute OH number from reference date
    diff_days = (dt.date() - OH115_DATE.date()).days
    oh_num = 115 + round(diff_days / 14)

    return {
        "number": oh_num,
        "isoDate": dt_str,
        "display": dt.strftime("%a, %b %-d, %Y"),
        "time": "8:00 PM ET"
    }

def main():
    print("Fetching next OH from Google Calendar...")
    next_oh = get_next_oh()

    if not next_oh:
        print("  ⚠️  No upcoming OH events found in calendar.")
        return False

    config = {"nextOH": next_oh}

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"  ✅ OH{next_oh['number']} · {next_oh['display']} at {next_oh['time']}")

    # Commit and push
    os.chdir(ARCHIVE_DIR)
    subprocess.run(['git', 'add', 'config.json'], check=True)
    result = subprocess.run(['git', 'diff', '--cached', '--quiet'])
    if result.returncode != 0:
        subprocess.run(['git', 'commit', '-m', f"Update next OH to OH{next_oh['number']}"], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print("  ✅ Pushed to GitHub Pages")
    else:
        print("  ➡️  config.json unchanged, no push needed")

    return True

if __name__ == '__main__':
    main()
