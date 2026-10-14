#!/usr/bin/env python3
"""Paginate Arctic Shift for all r/mathmemes posts (lightweight fields), write JSONL."""
import json, time, urllib.parse, urllib.request, sys
from pathlib import Path

OUT = Path("/workspace/math-memes-archive/data/all_posts.jsonl")
UA = "MatheraArchiveBot/1.0 (educational archive; github.com/julianlee314-hue)"
BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
FIELDS = "id,title,score,url,author,created_utc,over_18,post_hint,num_comments,link_flair_text"
LIMIT = 100
SLEEP = 0.55

def fetch(before=None):
    params = {
        "subreddit": "mathmemes",
        "limit": str(LIMIT),
        "sort": "desc",
        "fields": FIELDS,
    }
    if before is not None:
        params["before"] = str(before)
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    before = None
    pages = 0
    total = 0
    with OUT.open("w", encoding="utf-8") as f:
        while True:
            try:
                d = fetch(before)
            except Exception as e:
                print(f"ERROR page={pages} before={before}: {e}", flush=True)
                time.sleep(3)
                try:
                    d = fetch(before)
                except Exception as e2:
                    print(f"FATAL: {e2}", flush=True)
                    break
            data = d.get("data") or []
            if d.get("error"):
                print("API error:", d["error"], flush=True)
                break
            if not data:
                print("empty page — done", flush=True)
                break
            new = 0
            for p in data:
                pid = p.get("id")
                if not pid or pid in seen:
                    continue
                seen.add(pid)
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
                new += 1
                total += 1
            pages += 1
            oldest = min(p["created_utc"] for p in data)
            print(f"page={pages} batch={len(data)} new={new} total={total} oldest={oldest}", flush=True)
            if new == 0:
                # avoid infinite loop on stuck cursor
                before = oldest - 1
            else:
                before = oldest
            if len(data) < LIMIT:
                print("short page — done", flush=True)
                break
            time.sleep(SLEEP)
    print(f"DONE pages={pages} unique={total} -> {OUT}", flush=True)

if __name__ == "__main__":
    main()
