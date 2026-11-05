"""
Measure memory used by importing/setting up the CCIW Django project, step by step.
Run with the benchmark venv's python, e.g.

    scripts/memory_benchmark/import_memory.sh ../cciw-bench/py3.14

Prints USS/RSS (MiB) after each step, and with --tracemalloc, top allocating files.
"""

import argparse
import gc
import os
import sys
import time


def uss() -> tuple[float, float]:
    rss = pss = 0
    with open("/proc/self/smaps_rollup") as f:
        for line in f:
            k, v = line.split(":", 1)
            if k == "Rss":
                rss = int(v.split()[0])
            elif k in ("Private_Clean", "Private_Dirty"):
                pss += int(v.split()[0])
    return rss / 1024, pss / 1024


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracemalloc", action="store_true")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()
    if args.tracemalloc:
        import tracemalloc

        tracemalloc.start(1)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cciw.settings_local")
    rows = []

    def step(name: str) -> None:
        gc.collect()
        r, u = uss()
        rows.append((name, r, u))

    step("start")
    import django

    django.setup()
    step("django.setup()")
    import cciw.urls  # noqa

    from django.urls import get_resolver

    _ = get_resolver().url_patterns
    step("urls")
    from django.core.wsgi import get_wsgi_application

    get_wsgi_application()
    step("wsgi app")
    print(sys.version.split()[0], "gc thresholds:", gc.get_threshold(), "objects:", len(gc.get_objects()))
    print(f"modules loaded: {len(sys.modules)}")
    for name, r, u in rows:
        print(f"{name:20} RSS {r:7.1f}  USS {u:7.1f} MiB")
    if args.tracemalloc:
        import tracemalloc

        snap = tracemalloc.take_snapshot()
        total = sum(s.size for s in snap.statistics("filename"))
        print(f"tracemalloc total: {total / 2**20:.1f} MiB")
        # group by package
        by_pkg: dict[str, int] = {}
        for s in snap.statistics("filename"):
            fn = s.traceback[0].filename
            if "site-packages/" in fn:
                key = fn.split("site-packages/")[1].split("/")[0]
            elif "/lib/python3" in fn:
                key = "stdlib:" + fn.split("/lib/python3")[1].split("/")[1]
            else:
                key = fn
            by_pkg[key] = by_pkg.get(key, 0) + s.size
        for k, v in sorted(by_pkg.items(), key=lambda kv: -kv[1])[: args.top]:
            print(f"  {v / 2**20:7.2f} MiB  {k}")


if __name__ == "__main__":
    t = time.time()
    main()
