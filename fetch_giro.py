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


def parse_value(s):
    s = s.strip()
    if not s or s in {"-", "N/A", "NA", "null"}:
        return None
    try:
        return float(s)
    except ValueError:
        return s


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
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://giro.uml.edu/",
    })
    with urllib.request.urlopen(req, timeout=45) as r:
        text = r.read().decode("utf-8", errors="replace")

    comments = []
    data_lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            comments.append(line[1:].strip())
        else:
            data_lines.append(raw)

    # FastChar returns a whitespace/tabular table. Find the header row by its timestamp field.
    header_idx = None
    for i, line in enumerate(data_lines):
        low = line.lower()
        if "time" in low and ("fof2" in low or "cs" in low):
            header_idx = i
            break

    records = []
    columns = []
    if header_idx is not None:
        header = data_lines[header_idx]
        columns = header.split("\t") if "\t" in header else header.split()
        for line in data_lines[header_idx + 1:]:
            parts = line.split("\t") if "\t" in line else line.split()
            if len(parts) < len(columns):
                continue
            if len(parts) > len(columns):
                parts = parts[:len(columns)]
            records.append({k: parse_value(v) for k, v in zip(columns, parts)})

    # Preserve the raw non-comment table too, so a parser-format change never loses GIRO data.
    payload = {
        "station": STATION,
        "generated_utc": now.isoformat().replace("+00:00", "Z"),
        "requested_from_utc": start.isoformat().replace("+00:00", "Z"),
        "requested_to_utc": now.isoformat().replace("+00:00", "Z"),
        "hours": HOURS,
        "dmuf_km": DMUF,
        "characteristics": ["foF2", "hmF2", "foE", "foEs", "MUF(D)"],
        "source": "GIRO DIDBase FastChar.GetBest",
        "columns": columns,
        "record_count": len(records),
        "records": records,
        "header_comments": comments,
        "raw_table": data_lines,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}: {len(records)} parsed records; {len(text)} source characters")
    if not data_lines:
        raise RuntimeError("GIRO returned no tabular data")


if __name__ == "__main__":
    main()
