#!/usr/bin/env python3
"""Select top image posts (incl. NSFW), download originals, thumbs, memes.json."""
from __future__ import annotations
import json, re, time, urllib.request, shutil, html
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/workspace/math-memes-archive")
JSONL = ROOT / "data" / "all_posts.jsonl"
SITE = ROOT / "site"
FULL = SITE / "images" / "full"
THUMBS = SITE / "images" / "thumbs"
OUT_JSON = SITE / "data" / "memes.json"
SKIP_LOG = ROOT / "data" / "skipped.jsonl"
META_OUT = ROOT / "data" / "selected_top.json"
STATS = ROOT / "data" / "build_stats.json"

UA = "MatheraArchiveBot/1.0 (educational archive; github.com/julianlee314-hue)"
TOP_N = 1000
MAX_WIDTH = 1600
THUMB_W = 480
SLEEP = 0.3
EXT_OK = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

def is_image_url(url: str, hint: str | None) -> bool:
    if not url:
        return False
    u = url.lower()
    if "reddit.com/gallery/" in u:
        return True
    if any(h in u for h in ("i.redd.it", "i.imgur.com", "preview.redd.it")):
        return True
    if "imgur.com/" in u and "/a/" not in u:
        return True
    if any(u.split("?")[0].endswith(e) for e in EXT_OK):
        return True
    if hint in ("image", "hosted:image"):
        return True
    return False

def normalize_imgur(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?imgur\.com/([A-Za-z0-9]+)(?:\.[a-z]+)?/?$", url)
    if m:
        return f"https://i.imgur.com/{m.group(1)}.jpg"
    return url

def pick_ext(url: str, content_type: str | None) -> str:
    path = url.split("?")[0].lower()
    for e in EXT_OK:
        if path.endswith(e):
            return ".jpg" if e == ".jpeg" else e
    if content_type:
        ct = content_type.lower()
        if "png" in ct: return ".png"
        if "gif" in ct: return ".gif"
        if "webp" in ct: return ".webp"
    return ".jpg"

def download(url: str, dest_stem: Path) -> tuple[bool, Path | str]:
    url = normalize_imgur(url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
            ct = resp.headers.get("Content-Type")
            ext = pick_ext(url, ct)
            if ct and "gif" in ct.lower():
                ext = ".gif"
            dest = dest_stem.with_suffix(ext)
            dest.write_bytes(data)
            if dest.stat().st_size < 80:
                dest.unlink(missing_ok=True)
                return False, "too_small"
            return True, dest
    except Exception as e:
        return False, str(e)

def make_thumb(src: Path, dest: Path) -> tuple[int, int]:
    from PIL import Image
    w = h = 0
    try:
        im = Image.open(src)
        w, h = im.size
        animated = getattr(im, "is_animated", False) and getattr(im, "n_frames", 1) > 1
        if not animated and w > MAX_WIDTH:
            ratio = MAX_WIDTH / float(w)
            nw, nh = MAX_WIDTH, max(1, int(h * ratio))
            resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
            suf = src.suffix.lower()
            if suf in (".jpg", ".jpeg"):
                resized.convert("RGB").save(src, quality=88, optimize=True)
            elif suf == ".png":
                resized.save(src, optimize=True)
            elif suf == ".webp":
                resized.save(src, quality=85, method=4)
            else:
                resized.save(src)
            w, h = nw, nh
            im = Image.open(src)
        tw = THUMB_W
        th = max(1, int(h * (tw / w))) if w else tw
        frame = im.copy()
        if animated:
            frame.seek(0)
        if frame.mode not in ("RGB", "L"):
            frame = frame.convert("RGB")
        frame = frame.resize((tw, th), Image.Resampling.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        frame.save(dest, "JPEG", quality=80, optimize=True)
        return w, h
    except Exception:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return w, h

def fetch_post_full(pid: str) -> dict | None:
    url = f"https://arctic-shift.photon-reddit.com/api/posts/ids?ids={pid}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read().decode())
        data = d.get("data") or []
        return data[0] if data else None
    except Exception:
        return None

def gallery_first_image(pid: str) -> str | None:
    p = fetch_post_full(pid)
    if not p:
        return None
    mm = p.get("media_metadata") or {}
    gd = p.get("gallery_data") or {}
    items = gd.get("items") or []
    order = [it.get("media_id") for it in items if it.get("media_id")] or list(mm.keys())
    for mid in order:
        meta = mm.get(mid) or {}
        m = meta.get("m") or "image/jpg"
        ext = "png" if "png" in m else "gif" if "gif" in m else "webp" if "webp" in m else "jpg"
        return f"https://i.redd.it/{mid}.{ext}"
    return None

def resolve_image_url(p: dict) -> str | None:
    url = p.get("url") or ""
    if "v.redd.it" in url:
        return None
    if "reddit.com/gallery/" in url:
        return gallery_first_image(p["id"])
    if not is_image_url(url, p.get("post_hint")):
        return None
    return normalize_imgur(url)

def load_posts():
    posts = []
    with JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                posts.append(json.loads(line))
    return posts

def main():
    FULL.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    (SITE / "data").mkdir(parents=True, exist_ok=True)

    posts = load_posts()
    print(f"loaded {len(posts)} posts", flush=True)
    posts.sort(key=lambda p: p.get("score") or 0, reverse=True)

    candidates = []
    skipped_meta = []
    nsfw_in_top = 0
    for p in posts:
        url = p.get("url") or ""
        hint = p.get("post_hint")
        if "v.redd.it" in url or hint == "hosted:video":
            skipped_meta.append({"id": p.get("id"), "reason": "video", "score": p.get("score")})
            continue
        if not is_image_url(url, hint):
            skipped_meta.append({"id": p.get("id"), "reason": "no_image", "url": url, "score": p.get("score")})
            continue
        # NSFW INCLUDED — never skip for over_18
        if p.get("over_18"):
            nsfw_in_top += 1
        candidates.append(p)
        if len(candidates) >= TOP_N:
            break

    print(f"candidates={len(candidates)} nsfw_among_candidates={nsfw_in_top}", flush=True)
    META_OUT.write_text(json.dumps(candidates, indent=2), encoding="utf-8")

    memes = []
    dl_fail = 0
    with SKIP_LOG.open("w", encoding="utf-8") as skipf:
        for s in skipped_meta[:5000]:
            skipf.write(json.dumps(s) + "\n")

        for i, p in enumerate(candidates):
            pid = p["id"]
            url = p.get("url") or ""
            src_url = resolve_image_url(p)
            if not src_url:
                skipf.write(json.dumps({"id": pid, "reason": "resolve_fail", "url": url, "score": p.get("score")}) + "\n")
                print(f"[{i+1}/{len(candidates)}] RESOLVE FAIL {pid}", flush=True)
                continue

            existing = list(FULL.glob(f"{pid}.*"))
            if existing and existing[0].stat().st_size > 100:
                dest = existing[0]
            else:
                ok, info = download(src_url, FULL / pid)
                if not ok:
                    dl_fail += 1
                    skipf.write(json.dumps({"id": pid, "reason": "download_fail", "error": str(info), "url": src_url, "score": p.get("score")}) + "\n")
                    print(f"[{i+1}/{len(candidates)}] FAIL {pid} {info}", flush=True)
                    time.sleep(SLEEP)
                    continue
                dest = info  # Path

            thumb_path = THUMBS / f"{pid}.jpg"
            w, h = make_thumb(dest, thumb_path)
            author = p.get("author") or "unknown"
            permalink = f"/r/mathmemes/comments/{pid}/"
            tags = []
            flair = p.get("link_flair_text")
            if flair:
                tags.append(str(flair).strip())
            if p.get("over_18"):
                tags.append("NSFW")
            meme = {
                "id": pid,
                "title": p.get("title") or "",
                "image": f"images/full/{dest.name}",
                "thumb": f"images/thumbs/{thumb_path.name}",
                "w": w,
                "h": h,
                "tags": tags,
                "credit": {"author": author, "permalink": permalink},
                "added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "alt": p.get("title") or "math meme",
                "score": int(p.get("score") or 0),
                "nsfw": bool(p.get("over_18")),
                "created_utc": p.get("created_utc"),
            }
            memes.append(meme)
            flag = " NSFW" if meme["nsfw"] else ""
            print(f"[{i+1}/{len(candidates)}] OK{flag} {pid} score={meme['score']} {dest.name} {w}x{h}", flush=True)
            time.sleep(SLEEP)

    memes.sort(key=lambda m: m["score"], reverse=True)
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": "r/mathmemes all-time (Arctic Shift archive; sorted by score desc)",
        "count": len(memes),
        "nsfw_count": sum(1 for m in memes if m.get("nsfw")),
        "note": "NSFW posts included and marked nsfw:true for personal archive; UI toggle can hide later.",
        "memes": memes,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    stats = {
        "posts_scanned": len(posts),
        "image_candidates": len(candidates),
        "archived": len(memes),
        "download_fail": dl_fail,
        "nsfw_archived": payload["nsfw_count"],
        "skipped_non_image_sample": len(skipped_meta),
    }
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"WROTE {OUT_JSON} count={len(memes)} nsfw={payload['nsfw_count']} dl_fail={dl_fail}", flush=True)

if __name__ == "__main__":
    main()
