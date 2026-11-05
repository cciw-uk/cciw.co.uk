#!/usr/bin/env python
"""
Run the production process set (as in config/supervisor.conf.template) from a
benchmark environment created by setup_env.sh, apply a small HTTP load, and
record memory usage (RSS/PSS/USS/swap) of each process group over time.

Processes run inside an unprivileged user+UTS namespace with hostname
"cciw-bench", so that cciw/settings.py treats them as PRODUCTION (DEBUG off,
memcached cache, Sentry init, etc.).

Usage (from repo root, using the main dev venv which has psutil + requests):

    .venv/bin/python scripts/memory_benchmark/run_benchmark.py ../cciw-bench/py3.13 --duration 300

Writes JSON results to scripts/memory_benchmark/results/ (or --out).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import psutil
import requests

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
HOSTNAME = "cciw-bench"
HTTP_HOST = "www.cciw.co.uk"


@dataclass
class Proc:
    name: str
    popen: subprocess.Popen
    samples: list[dict] = field(default_factory=list)


def ns_cmd(cmd: list[str]) -> list[str]:
    # Run inside new user + UTS namespace with our hostname.
    return [
        "unshare",
        "--user",
        "--map-root-user",
        "--uts",
        "sh",
        "-c",
        f'hostname {HOSTNAME} && exec "$@"',
        "sh",
        *cmd,
    ]


def tree(popen: subprocess.Popen) -> list[psutil.Process]:
    try:
        p = psutil.Process(popen.pid)
        return [p] + p.children(recursive=True)
    except psutil.NoSuchProcess:
        return []


def measure(procs: list[psutil.Process]) -> dict:
    out = {"rss": 0, "pss": 0, "uss": 0, "swap": 0, "n": 0, "procs": []}
    for p in procs:
        try:
            m = p.memory_full_info()
            cmd = " ".join(p.cmdline())[:120]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        # skip the unshare/sh wrappers
        if p.name() in ("unshare", "sh"):
            continue
        out["n"] += 1
        for k in ("rss", "pss", "uss", "swap"):
            out[k] += getattr(m, k)
        out["procs"].append({"pid": p.pid, "cmd": cmd, "rss": m.rss, "pss": m.pss, "uss": m.uss})
    return out


def crawl(base: str, session: requests.Session, start: list[str], limit: int) -> list[str]:
    seen: list[str] = []
    queue = list(start)
    while queue and len(seen) < limit:
        path = queue.pop(0)
        if path in seen:
            continue
        try:
            r = session.get(base + path, timeout=30, allow_redirects=False)
        except requests.RequestException:
            continue
        seen.append(path)
        if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
            continue
        for href in re.findall(r'href="([^"#]+)"', r.text):
            u = urlparse(urljoin(base + path, href))
            if u.netloc not in ("", urlparse(base).netloc, HTTP_HOST):
                continue
            p = u.path + (("?" + u.query) if u.query else "")
            if any(x in p for x in ("logout", "delete", "/static/", "/media/", "/usermedia/", "export", "download")):
                continue
            if p not in seen and p not in queue:
                queue.append(p)
    return seen


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Host": HTTP_HOST, "X-Forwarded-Proto": "https"})

    # Production cookies are 'Secure' and we use a Host header that doesn't
    # match the URL, so the normal cookie jar won't send them. Handle cookies
    # manually instead.
    jar: dict[str, str] = {}

    def store_cookies(resp, *a, **kw):
        for c in resp.cookies:
            jar[c.name] = c.value
        s.cookies.clear()
        s.headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in jar.items())

    s.hooks["response"].append(store_cookies)
    return s


def login(base: str, s: requests.Session) -> bool:
    r = s.get(base + "/admin/login/", timeout=30)
    m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
    if not m:
        return False
    r = s.post(
        base + "/admin/login/?next=/admin/",
        data={"csrfmiddlewaretoken": m.group(1), "username": "admin", "password": "admin"},
        headers={"Referer": f"https://{HTTP_HOST}/admin/login/"},
        timeout=30,
        allow_redirects=False,
    )
    return r.status_code == 302


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("env_dir", type=Path, help="e.g. ../cciw-bench/py3.14")
    ap.add_argument("--duration", type=int, default=300, help="seconds of load")
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--clients", type=int, default=2, help="concurrent HTTP clients")
    ap.add_argument("--think", type=float, default=0.5, help="avg seconds between requests per client")
    ap.add_argument("--interval", type=float, default=5)
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--workers", type=int, default=4, help="gunicorn workers (production: 4)")
    ap.add_argument("--extra-env", action="append", default=[], help="KEY=VAL for server processes")
    ap.add_argument("--label", default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    env_dir = args.env_dir.resolve()
    src, home, venv = env_dir / "src", env_dir / "home", env_dir / "src" / ".venv"
    py = str(venv / "bin" / "python")
    pyver = subprocess.check_output([py, "-c", "import sys; print(sys.version.split()[0])"], text=True).strip()
    label = args.label or f"py{pyver}"
    (home / "logs").mkdir(parents=True, exist_ok=True)
    subprocess.run([str(REPO / "scripts" / "services.sh"), "start"], check=True)

    env = {
        "PATH": f"{venv}/bin:/usr/bin:/bin",
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    for kv in args.extra_env:
        k, v = kv.split("=", 1)
        env[k] = v
    logf = open(home / "logs" / f"bench-{label}.log", "w")  # noqa: SIM115
    sock = home / "cciw_memcached.sock"
    commands = {
        "memcached": ["/usr/bin/memcached", "-m", "24", "-s", str(sock)],
        "gunicorn": [
            f"{venv}/bin/gunicorn",
            "--bind",
            f"127.0.0.1:{args.port}",
            "--workers",
            str(args.workers),
            f"--pid={home}/gunicorn.pid",
            "cciw.wsgi",
        ],
        "runmailer": [py, f"{src}/manage.py", "runmailer_pg"],
        "django_q": [py, f"{src}/manage.py", "qcluster"],
    }
    procs: list[Proc] = []
    for name, cmd in commands.items():
        popen = subprocess.Popen(
            # memcached doesn't need the namespace, and fails inside it
            cmd if name == "memcached" else ns_cmd(cmd),
            cwd=home,
            env=env,
            stdout=logf,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        procs.append(Proc(name, popen))
        if name == "memcached":
            time.sleep(1)

    base = f"http://127.0.0.1:{args.port}"
    stop = threading.Event()
    stats = {"requests": 0, "errors": 0, "status": {}}
    lock = threading.Lock()

    def cleanup(*_):
        stop.set()
        for p in procs:
            try:
                os.killpg(p.popen.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for p in procs:
            try:
                p.popen.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(p.popen.pid, signal.SIGKILL)

    signal.signal(signal.SIGTERM, lambda *a: (cleanup(), sys.exit(1)))
    results: dict = {}
    try:
        # Wait for gunicorn
        for _ in range(120):
            try:
                if make_session().get(base + "/health-check/", timeout=5).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.5)
        else:
            raise SystemExit("gunicorn didn't come up, see log " + logf.name)

        s = make_session()
        anon_urls = crawl(base, s, ["/"], 60)
        s = make_session()
        assert login(base, s), "admin login failed"
        officer_urls = crawl(base, s, ["/officers/", "/admin/"], 60)
        print(f"{label}: {len(anon_urls)} anon URLs, {len(officer_urls)} officer URLs", flush=True)

        def client(i: int) -> None:
            rnd = random.Random(i)
            anon = make_session()
            officer = make_session()
            login(base, officer)
            while not stop.is_set():
                r_ = rnd.random()
                if r_ < 0.02:
                    sess, path = anon, f"/task-queue-debug/?message=bench{rnd.randint(0, 10**6)}"
                elif r_ < 0.4:
                    sess, path = officer, rnd.choice(officer_urls)
                else:
                    sess, path = anon, rnd.choice(anon_urls)
                try:
                    resp = sess.get(base + path, timeout=60, allow_redirects=False)
                    with lock:
                        stats["requests"] += 1
                        stats["status"][resp.status_code] = stats["status"].get(resp.status_code, 0) + 1
                except requests.RequestException:
                    with lock:
                        stats["errors"] += 1
                stop.wait(rnd.expovariate(1 / args.think))

        time.sleep(args.warmup)
        threads = [threading.Thread(target=client, args=(i,), daemon=True) for i in range(args.clients)]
        for t in threads:
            t.start()
        t0 = time.time()
        timeline = []
        while time.time() - t0 < args.duration:
            row = {"t": round(time.time() - t0, 1)}
            for p in procs:
                m = measure(tree(p.popen))
                row[p.name] = {k: m[k] for k in ("rss", "pss", "uss", "swap", "n")}
                p.samples.append(m)
            timeline.append(row)
            tot = sum(row[p.name]["pss"] for p in procs)
            print(f"t={row['t']:6.1f} total PSS {tot / 2**20:7.1f} MiB  reqs={stats['requests']}", flush=True)
            time.sleep(args.interval)
        stop.set()

        # Cron-like command: peak RSS and wall time
        cron = {}
        for cmdname in ["retry_deferred", "check"]:
            t1 = time.time()
            child = subprocess.Popen(
                ns_cmd([py, f"{src}/manage.py", cmdname]), cwd=home, env=env, stdout=logf, stderr=subprocess.STDOUT
            )
            _, status, ru = os.wait4(child.pid, 0)
            child.returncode = status
            cron[cmdname] = {"wall_s": round(time.time() - t1, 2), "maxrss_kib": ru.ru_maxrss}

        final = {p.name: p.samples[-1] for p in procs}
        results = {
            "label": label,
            "python": pyver,
            "args": {k: str(v) for k, v in vars(args).items()},
            "http": stats,
            "final": final,
            "timeline": timeline,
            "cron": cron,
        }
    finally:
        cleanup()

    out = args.out or HERE / "results" / f"{label}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1))
    print(f"\nResults written to {out}")
    print_summary(results)


def print_summary(results: dict) -> None:
    mib = 2**20
    print(f"\n== {results['label']} (Python {results['python']}) ==")
    print(f"HTTP: {results['http']}")
    print(f"{'group':12} {'n':>3} {'RSS':>9} {'PSS':>9} {'USS':>9}  (MiB, final sample)")
    tot = {"rss": 0, "pss": 0, "uss": 0}
    for name, m in results["final"].items():
        print(f"{name:12} {m['n']:3} {m['rss'] / mib:9.1f} {m['pss'] / mib:9.1f} {m['uss'] / mib:9.1f}")
        for k in tot:
            tot[k] += m[k]
        for p in m["procs"]:
            print(
                f"   {p['pid']:>7} {p['rss'] / mib:8.1f} {p['pss'] / mib:8.1f} {p['uss'] / mib:8.1f}  {p['cmd'][:70]}"
            )
    print(f"{'TOTAL':12}     {tot['rss'] / mib:9.1f} {tot['pss'] / mib:9.1f} {tot['uss'] / mib:9.1f}")
    print(f"cron-like commands: {results['cron']}")


if __name__ == "__main__":
    main()
