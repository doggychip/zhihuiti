#!/usr/bin/env python3
"""Watch a Zeabur git-triggered deploy and auto-redeploy if the platform drops it.

Zeabur occasionally cancels a build mid-way with no error (observed 2026-07-03:
push e1e5d7ac -> deployment CANCELED during apt-get, old container kept serving).
This script closes the gap: run it after `git push origin main` and it makes sure
the pushed commit actually reaches RUNNING, triggering a manual redeploy if not.

Usage:
    python3 scripts/zeabur_deploy_watch.py [<commit-sha>]

Defaults to the SHA of origin/main. Token is read from ~/.config/zeabur/cli.yaml.
Service/env default to the zhihuiti-oracle service (BigBrain project); override
with ZEABUR_SERVICE_ID / ZEABUR_ENV_ID.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

API = "https://api.zeabur.com/graphql"
SERVICE_ID = os.environ.get("ZEABUR_SERVICE_ID", "69cbe441cb1dac3576fc07e4")
ENV_ID = os.environ.get("ZEABUR_ENV_ID", "69c91d0f76bc68ba374cd817")
TRIGGER_WAIT = 240      # seconds to wait for the git trigger to create a deployment
BUILD_WAIT = 900        # seconds to wait for a build to reach RUNNING
MAX_REDEPLOYS = 2
BAD = {"CANCELED", "REMOVED", "FAILED", "CRASHED"}


def token():
    with open(os.path.expanduser("~/.config/zeabur/cli.yaml")) as f:
        for line in f:
            if line.startswith("token:"):
                return line.split(":", 1)[1].strip()
    sys.exit("no token in ~/.config/zeabur/cli.yaml — run `zeabur auth login`")


def gql(query):
    req = urllib.request.Request(
        API, data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json",
                 "User-Agent": "zeabur-deploy-watch/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        out = json.loads(r.read())
    if out.get("errors"):
        sys.exit(f"zeabur api error: {out['errors'][0]['message']}")
    return out["data"]


def latest_for(sha):
    deps = gql(f'query{{service(_id:"{SERVICE_ID}"){{deployments(environmentID:"{ENV_ID}")'
               f'{{_id status createdAt commitSHA}}}}}}')["service"]["deployments"]
    mine = [d for d in deps if d["commitSHA"] == sha]
    return max(mine, key=lambda d: d["createdAt"]) if mine else None


def redeploy():
    gql(f'mutation{{redeployService(serviceID:"{SERVICE_ID}",environmentID:"{ENV_ID}")}}')
    print("-> redeployService triggered")


def wait_running(sha, deadline):
    while time.time() < deadline:
        dep = latest_for(sha)
        st = dep["status"] if dep else "NOT_TRIGGERED"
        print(f"   {time.strftime('%H:%M:%S')} {st}")
        if st == "RUNNING":
            return True
        if st in BAD:
            return False
        time.sleep(20)
    return None  # still pending at deadline


def main():
    sha = sys.argv[1] if len(sys.argv) > 1 else subprocess.check_output(
        ["git", "rev-parse", "origin/main"], text=True).strip()
    print(f"watching deploy of {sha[:12]} (service {SERVICE_ID[:8]}…)")

    # give the git trigger a chance before forcing anything
    dep = None
    trigger_deadline = time.time() + TRIGGER_WAIT
    while time.time() < trigger_deadline and dep is None:
        dep = latest_for(sha)
        if dep is None:
            print(f"   {time.strftime('%H:%M:%S')} waiting for git trigger…")
            time.sleep(20)
    if dep is None:
        print(f"no deployment for {sha[:12]} after {TRIGGER_WAIT}s — git trigger missed it")
        redeploy()

    for attempt in range(MAX_REDEPLOYS + 1):
        ok = wait_running(sha, time.time() + BUILD_WAIT)
        if ok:
            print(f"OK: {sha[:12]} is RUNNING")
            return 0
        if attempt < MAX_REDEPLOYS:
            print(f"build {'died' if ok is False else 'stalled'} — redeploy attempt {attempt + 1}/{MAX_REDEPLOYS}")
            redeploy()
    sys.exit(f"gave up: {sha[:12]} never reached RUNNING after {MAX_REDEPLOYS} redeploys")


if __name__ == "__main__":
    sys.exit(main())
