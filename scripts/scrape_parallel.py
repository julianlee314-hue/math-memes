#!/usr/bin/env python3
"""Parallel Arctic Shift scrape by year windows for r/mathmemes."""
import json, time, urllib.parse, urllib.request, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = Path("/workspace/math-memes-archive")
OUT_DIR = ROOT / "data" / "shards"
OUT = ROOT / "data" / "all_posts.jsonl"
UA = "MatheraArchiveBot/1.0 (educational archive; github.com/julianlee314-hue)"
BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
FIELDS = "id,title,score,url,author,created_utc,over_18,post_hint,num_comments,link_flair_text"
LIMIT = 100
SLEEP = 0.35

# subreddit earliest_post ~ 1484631556 (2017-01)
START_YEAR = 2017
END_YEAR = 2027  # inclusive upper bound window

def year_bounds(y):
    after = int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp())
    before = int(datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    return after, before

def fetch(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())

def scrape_window(year):
    after, before_cap = year_bounds(year)
    shard = OUT_DIR / f"year_{year}.jsonl"
    seen = set()
    # walk descending within window using before cursor
    before = before_cap
    pages = 0
    total = 0
    with shard.open("w", encoding="utf-8") as f:
        while True:
            params = {
                "subreddit": "mathmemes",
                "limit": str(LIMIT),
                "sort": "desc",
                "fields": FIELDS,
                "after": str(after),
                "before": str(before),
            }
            for attempt in range(4):
                try:
                    d = fetch(params)
                    break
                except Exception as e:
                    time.sleep(1.5 * (attempt + 1))
                    d = None
                    last = e
            else:
                print(f"[{year}] FATAL {last}", flush=True)
                break
            data = (d or {}).get("data") or []
            if (d or {}).get("error"):
                print(f"[{year}] API {d['error']}", flush=True)
                break
            if not data:
                break
            new = 0
            for p in data:
                pid = p.get("id")
                cu = p.get("created_utc") or 0
                if not pid or pid in seen:
                    continue
                if cu < after or cu >= before_cap:
                    continue
                seen.add(pid)
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
                new += 1
                total += 1
            pages += 1
            oldest = min(p["created_utc"] for p in data)
            print(f"[{year}] page={pages} new={new} total={total} oldest={oldest}", flush=True)
            if oldest <= after or new == 0:
                # nudge cursor
                if new == 0:
                    before = oldest - 1
                    if before <= after:
                        break
                else:
                    before = oldest
            else:
                before = oldest
            if len(data) < LIMIT:
                break
            time.sleep(SLEEP)
    print(f"[{year}] DONE total={total} -> {shard}", flush=True)
    return year, total

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    years = list(range(START_YEAR, END_YEAR))
    # 2017..2026
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(scrape_window, y): y for y in years}
        for fut in as_completed(futs):
            results.append(fut.result())
    # merge
    seen = set()
    n = 0
    with OUT.open("w", encoding="utf-8") as out:
        for y in years:
            shard = OUT_DIR / f"year_{y}.jsonl"
            if not shard.exists():
                continue
            with shard.open(encoding="utf-8") as f:
                for line in f:
                    p = json.loads(line)
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    out.write(json.dumps(p, ensure_ascii=False) + "\n")
                    n += 1
    print(f"MERGED unique={n} -> {OUT}", flush=True)
    print("YEARS", results, flush=True)

if __name__ == "__main__":
    main()
