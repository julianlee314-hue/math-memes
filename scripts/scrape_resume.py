#!/usr/bin/env python3
"""Single-threaded resume of incomplete year shards."""
import json, time, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/workspace/math-memes-archive")
OUT_DIR = ROOT / "data" / "shards"
OUT = ROOT / "data" / "all_posts.jsonl"
UA = "MatheraArchiveBot/1.0 (educational archive; github.com/julianlee314-hue)"
BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
FIELDS = "id,title,score,url,author,created_utc,over_18,post_hint,num_comments,link_flair_text"
LIMIT = 100
SLEEP = 0.85

def year_bounds(y):
    after = int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp())
    before = int(datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    return after, before

def fetch(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())

def load_ids(shard: Path):
    ids = set()
    oldest = None
    newest = None
    if not shard.exists():
        return ids, oldest, newest
    with shard.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            p = json.loads(line)
            ids.add(p["id"])
            cu = p.get("created_utc")
            if cu is not None:
                oldest = cu if oldest is None else min(oldest, cu)
                newest = cu if newest is None else max(newest, cu)
    return ids, oldest, newest

def scrape_year(year, force_full=False):
    after, before_cap = year_bounds(year)
    shard = OUT_DIR / f"year_{year}.jsonl"
    ids, oldest, newest = load_ids(shard)
    # Complete if we already reached near year start (within 2 days) and have data
    if ids and oldest is not None and oldest <= after + 2 * 86400 and not force_full:
        print(f"[{year}] SKIP complete n={len(ids)} oldest={oldest}", flush=True)
        return year, len(ids), 0

    # Resume cursor: continue older than oldest we have; if empty start at year end
    before = oldest if (oldest and not force_full) else before_cap
    print(f"[{year}] START n={len(ids)} resume_before={before} after={after}", flush=True)
    added = 0
    mode = "a" if ids and not force_full else "w"
    if mode == "w":
        ids = set()
    pages = 0
    with shard.open(mode, encoding="utf-8") as f:
        while before > after:
            params = {
                "subreddit": "mathmemes",
                "limit": str(LIMIT),
                "sort": "desc",
                "fields": FIELDS,
                "after": str(after),
                "before": str(before),
            }
            d = None
            for attempt in range(6):
                try:
                    d = fetch(params)
                    break
                except Exception as e:
                    wait = 5 * (attempt + 1)
                    print(f"[{year}] retry {attempt+1} after {e}; sleep {wait}s", flush=True)
                    time.sleep(wait)
            if d is None:
                print(f"[{year}] FATAL giving up", flush=True)
                break
            if d.get("error"):
                print(f"[{year}] API {d['error']}", flush=True)
                time.sleep(10)
                break
            data = d.get("data") or []
            if not data:
                print(f"[{year}] empty — done", flush=True)
                break
            new = 0
            for p in data:
                pid = p.get("id")
                cu = p.get("created_utc") or 0
                if not pid or pid in ids:
                    continue
                if cu < after or cu >= before_cap:
                    continue
                ids.add(pid)
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
                new += 1
                added += 1
            pages += 1
            oldest_batch = min(p["created_utc"] for p in data)
            print(f"[{year}] page={pages} new={new} total={len(ids)} oldest={oldest_batch}", flush=True)
            if oldest_batch <= after:
                break
            if new == 0:
                before = oldest_batch - 1
            else:
                before = oldest_batch
            if len(data) < LIMIT:
                break
            time.sleep(SLEEP)
    print(f"[{year}] DONE total={len(ids)} added={added}", flush=True)
    return year, len(ids), added

def merge():
    years = list(range(2017, 2027))
    seen = set()
    n = 0
    with OUT.open("w", encoding="utf-8") as out:
        for y in years:
            shard = OUT_DIR / f"year_{y}.jsonl"
            if not shard.exists():
                continue
            with shard.open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    p = json.loads(line)
                    pid = p.get("id")
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    out.write(json.dumps(p, ensure_ascii=False) + "\n")
                    n += 1
    print(f"MERGED unique={n} -> {OUT}", flush=True)
    return n

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Process incomplete / empty years first (high value), then verify others
    order = [2026, 2025, 2024, 2023, 2022, 2020, 2021, 2019, 2018, 2017]
    for y in order:
        scrape_year(y)
        time.sleep(1.0)
    merge()

if __name__ == "__main__":
    main()
