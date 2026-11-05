"""Summarise run_benchmark.py JSON results as a table (MiB)."""

import json
import sys
from pathlib import Path

MIB = 2**20


def main() -> None:
    files = [Path(f) for f in sys.argv[1:]]
    groups = ["gunicorn", "runmailer", "django_q", "memcached"]
    hdr = (
        f"{'run':18}"
        + "".join(f"{g + ' n/PSS':>18}" for g in groups)
        + f"{'TOTAL PSS':>11}{'TOTAL USS':>11}{'cron maxRSS':>12}"
    )
    print(hdr)
    for f in files:
        r = json.loads(f.read_text())
        if not r:
            print(f"{f.name}: empty")
            continue
        fin = r["final"]
        cells = "".join(f"{fin[g]['n']:>8} / {fin[g]['pss'] / MIB:7.1f}" for g in groups)
        tot_pss = sum(fin[g]["pss"] for g in groups) / MIB
        tot_uss = sum(fin[g]["uss"] for g in groups) / MIB
        cron = r["cron"]["retry_deferred"]["maxrss_kib"] / 1024
        print(f"{r['label']:18}{cells}{tot_pss:11.1f}{tot_uss:11.1f}{cron:12.1f}")
    print("\nTimeline of total PSS (MiB), max over the run:")
    for f in files:
        r = json.loads(f.read_text())
        if not r:
            continue
        tl = [sum(row[g]["pss"] for g in groups) / MIB for row in r["timeline"]]
        print(
            f"  {r['label']:18} start {tl[0]:7.1f}  end {tl[-1]:7.1f}  max {max(tl):7.1f}  ({len(tl)} samples, {r['http']['requests']} requests)"
        )


if __name__ == "__main__":
    main()
