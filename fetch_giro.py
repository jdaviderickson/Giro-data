#!/usr/bin/env python3
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATION = "PA836"
CHARS = ["foF2", "hmF2", "foE", "foEs", "MUF(D)"]
DMUF = 3000
HOURS = 48
OUT = Path("data/pa836_latest.json")


def number(s):
    if s in {"---", "-", "N/A", "NA", "null"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def main():
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=HOURS)
    params = {
        "ursiCode": STATION,
        "charName": ",".join(CHARS),
        "DMUF": str(DMUF),
        "fromDate": start.strftime("%Y/%m/%d %H:%M:%S"),
        "toDate": now.strftime("%Y/%m/%d %H:%M:%S"),
    }
    url = "https://lgdc.uml.edu/fastchar/getbest?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://giro.uml.edu/"})
    with urllib.request.urlopen(req, timeout=45) as r:
        text = r.read().decode("utf-8", errors="replace")

    comments, data_lines, records = [], [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            comments.append(line[1:].strip())
            continue
        data_lines.append(line)
        p = line.split()
        # Time CS foF2 QD hmF2 QD foE QD foEs QD MUF(D) QD
        if len(p) >= 12 and p[0][:4].isdigit() and "T" in p[0]:
            try:
                cs = int(p[1])
            except ValueError:
                continue
            records.append({
                "time": p[0], "CS": cs,
                "foF2_MHz": number(p[2]), "foF2_QD": p[3],
                "hmF2_km": number(p[4]), "hmF2_QD": p[5],
                "foE_MHz": number(p[6]), "foE_QD": p[7],
                "foEs_MHz": number(p[8]), "foEs_QD": p[9],
                "MUF3000_MHz": number(p[10]), "MUF3000_QD": p[11],
            })

    payload = {
        "station": STATION,
        "generated_utc": now.isoformat().replace("+00:00", "Z"),
        "requested_from_utc": start.isoformat().replace("+00:00", "Z"),
        "requested_to_utc": now.isoformat().replace("+00:00", "Z"),
        "hours": HOURS, "dmuf_km": DMUF,
        "characteristics": ["foF2", "hmF2", "foE", "foEs", "MUF(D)"],
        "source": "GIRO DIDBase FastChar.GetBest",
        "record_count": len(records), "records": records,
        "header_comments": comments, "raw_table": data_lines,
    }
    if not records:
        raise RuntimeError("GIRO returned data but no measurement rows parsed")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}: {len(records)} parsed records; {len(text)} source characters")


if __name__ == "__main__":
    main()
