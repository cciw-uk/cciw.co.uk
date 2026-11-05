Memory benchmark: Python 3.13 vs 3.14
=====================================

Scripts used to reproduce/investigate the production memory blow-up seen when
upgrading to Python 3.14 (Oct 2026).

Prerequisites: dev environment from ``scripts/dev_setup.sh`` (postgres with the
``cciw_dev`` DB + ``fixtures/dev_db.json``), ``memcached`` binary
(``sudo apt install memcached``), unprivileged user namespaces (``unshare``).

1. Create isolated environments (git worktrees in ``../cciw-bench/py<VER>``)::

     # newer uv is needed to know the latest Python patch releases:
     curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=$HOME/.local/uv-latest UV_NO_MODIFY_PATH=1 sh
     export UV=$HOME/.local/uv-latest/uv
     for v in 3.13.13 3.13.18 3.14.4 3.14.10; do scripts/memory_benchmark/setup_env.sh $v; done

   Use full patch versions: a venv made with ``--python 3.14`` silently
   follows uv's "minor version" link to whatever patch release is newest.

2. Run everything (≈30 min)::

     scripts/memory_benchmark/run_all.sh 300

   ``run_benchmark.py`` starts the processes from ``config/supervisor.conf.template``
   (memcached, gunicorn with 4 workers, ``runmailer_pg``, ``qcluster``) in a UTS
   namespace with hostname ``cciw-bench`` so settings.py uses PRODUCTION mode,
   applies a small load (2 clients, ~2 req/s: anonymous pages, logged-in
   officer/admin pages, occasional django-q tasks), samples RSS/PSS/USS of each
   process tree, and runs a cron-like ``manage.py retry_deferred`` at the end.

3. Per-process import cost::

     scripts/memory_benchmark/import_memory.sh ../cciw-bench/py3.14.10 [--tracemalloc]

Results (Nov 2026, 300s, see ``results/``) — PSS in MiB
---------------------------------------------------------

==================  ========  =========  ========  =========
run                 gunicorn  runmailer  django_q  TOTAL PSS
==================  ========  =========  ========  =========
py3.13.13           636 (5)   154 (1)    204 (5)   1000
py3.13.18           635 (5)   155 (1)    201 (5)    998
py3.14.4            750 (9)   174 (2)    678 (8)   1607
py3.14.10           722 (9)   174 (2)    679 (8)   1580
py3.14.10 + fork    698 (5)   168 (1)    218 (5)   1091
3.14.10 + settings  699 (5)   168 (1)    219 (5)   1093
==================  ========  =========  ========  =========

(n) = number of processes. "+ fork" = multiprocessing start method forced back
to "fork" (``force_fork/sitecustomize.py``).

Findings
--------

Python 3.14 uses ~+580 MiB more in total, which matches production going from
~60% to ~100% RAM and filling swap.

1. **~475 MiB: multiprocessing default start method changed to "forkserver"**
   on Linux in 3.14. django-q's ``qcluster`` uses ``multiprocessing.Process``
   with the default context. With "fork", the sentinel/pusher/monitor/worker
   children share the parent's already-imported Django via copy-on-write
   (~10 MiB USS each). With "forkserver" each child re-imports Django and the
   whole project from scratch (~115 MiB USS each), plus 2 forkserver processes.

2. **~25 MiB: resource_tracker processes.** ``django_q/conf.py`` creates a
   ``multiprocessing`` Queue/Value at import time. Under a non-fork start method
   this launches a ``multiprocessing.resource_tracker`` helper process (~7 MiB)
   in *every* process that imports django_q (each gunicorn worker, runmailer,
   qcluster) — 6 extra processes.

3. **~90 MiB: general per-process growth** (~+10 MiB per Django process).
   Mostly larger code objects / more objects created at import time in 3.14
   (tracemalloc: +12 MiB Python heap, of which +8 MiB in unmarshalled code).
   This is inherent to 3.14, small, but multiplied by 6-7 Django processes.

4. 3.14.0–3.14.4 incremental GC (reverted in 3.14.5) adds a little more growth
   under load (gunicorn +28 MiB vs 3.14.10 over 5 min) — minor here.

Fix: ``cciw/settings.py`` now sets the start method to "fork" (a no-op on 3.13),
which removes items 1 and 2 (verified: "3.14.10 + settings" row above,
``results/run-settingsfix``). The remaining ~+90 MiB (~9%) vs 3.13 is item 3.
