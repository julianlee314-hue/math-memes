# Mathera Memes Wall

Unofficial personal archive of **all-time top r/mathmemes** image posts, sorted by Reddit score (upvotes).

**Mathera / Wayfinder-adjacent** bonus shelf — a constellation we can later map onto skills and age bands. This build does **not** map memes to curriculum yet.

## Live

GitHub Pages from `main` `/` → https://julianlee314-hue.github.io/math-memes/

## What's here

- Tile masonry wall (contain, not crop) with score badges
- Lightbox (`<dialog>`) + `#id` deep links, Esc / ← →
- Search + flair/tag chips; favourites in `localStorage` key `math-memes-v1`
- Local image copies only (no hotlinking i.redd.it)
- **NSFW / over_18 posts are included**, marked `nsfw: true` in JSON and with a tile badge/border. Toggle defaults ON for this personal archive (uncheck to hide).

## Data

See `data/memes.json`:

```json
{
  "id": "…",
  "title": "…",
  "image": "images/full/….jpg",
  "thumb": "images/thumbs/….jpg",
  "w": 0, "h": 0,
  "tags": [],
  "credit": { "author": "…", "permalink": "/r/mathmemes/comments/…/" },
  "added": "YYYY-MM-DD",
  "alt": "…",
  "score": 0,
  "nsfw": false
}
```

## Provenance

Live Reddit JSON (`/top.json?t=all`) returns 403 from many datacenter IPs. Metadata was collected via the public [Arctic Shift](https://arctic-shift.photon-reddit.com/) archive API (~76k r/mathmemes posts), then sorted by score; top image/gif/gallery posts downloaded locally.

## Takedown

Not affiliated with Reddit. Authors: open an issue with post id or permalink and we will remove the local copy.
