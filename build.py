#!/usr/bin/env python3
"""Generate the static dylan.jbf.com reference site from official catalog metadata + curated short quotes."""
from __future__ import annotations

import json, re, html, hashlib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = Path("/workspace/dylan-src")
DATA = ROOT / "data"

SLUG_FIX = {
    "song-to-woody": "song-woody",
    "masters-war": "masters-war-mono",
    "to-ramona": "ramona",
    "just-like-tom-thumbs-blues": "just-tom-thumbs-blues",
    "just-like-woman": "just-woman",
    "this-wheels-fire": "wheels-fire",
    "crash-on-levee-down-in-flood": "crash-levee-down-flood",
    "the-man-in-me": "man-me",
    "knockin-heaven-door": "knockin-heavens-door",
    "on-night-like-this": "night",
    "something-there-is-about-you": "something-there-about-you",
    "one-more-cup-coffee": "one-more-cup-coffee-valley-below",
    "romance-in-durango": "romance-durango",
    "we-better-talk-this-over": "we-better-talk-over",
    "in-garden": "garden",
    "pressing-on": "pressing",
    "sweetheart-like-you": "sweetheart-you",
    "tryin-get-heaven": "trying-get-heaven",
    "floater-too-much-you": "floater-too-much-ask",
    "this-dream-you": "dream-you",
    "ive-made-up-my-mind-give-myself-you": "ive-made-up-my-mind-to-give-myself-to-you",
    "mother-muses": "mother-of-muses",
    "crossing-rubicon": "crossing-the-rubicon",
    "my-own-version-you": "my-own-version-of-you",
    "sign-cross": "sign-on-the-cross",
    "up-to-me": "me",
    "tight-connection-my-heart": "tight-connection-my-heart-has-anyone-seen-my-love",
}

# Studio albums first for browsing; official type inferred from title.
COMPILATION_HINTS = (
    "greatest", "essential", "best of", "biograph", "the original mono",
    "copyright collections",
)
LIVE_HINTS = ("live", "before the flood", "hard rain", "budokan", "real live",
              "unplugged", "rolling thunder", "shadow kingdom", "dylan & the dead",
              "brandeis", "1974 live")
BOOTLEG_HINTS = ("bootleg series",)

def url_slug(u: str) -> str:
    return u.rstrip("/").split("/")[-1]

def file_slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "item"

def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)

def album_kind(title: str) -> str:
    t = title.lower()
    if any(h in t for h in BOOTLEG_HINTS):
        return "Bootleg Series"
    if any(h in t for h in LIVE_HINTS):
        return "Live"
    if any(h in t for h in COMPILATION_HINTS):
        return "Compilation"
    if "pat garrett" in t:
        return "Soundtrack"
    if "christmas" in t:
        return "Studio"
    return "Studio"

def load():
    songs = json.loads((SRC / "songs.json").read_text())
    albums = json.loads((SRC / "albums_full.json").read_text())
    for a in albums:
        a["slug"] = a.get("slug") or url_slug(a["url"])
        a["kind"] = album_kind(a["title"])
        a["track_count"] = len(a.get("tracks") or [])
    song_by_slug = {}
    for s in songs:
        s["slug"] = url_slug(s["url"])
        song_by_slug[s["slug"]] = s
    album_by_url = {a["url"].rstrip("/"): a for a in albums}
    album_by_slug = {a["slug"]: a for a in albums}

    # attach first-release album + year to songs
    for s in songs:
        rel = (s.get("release_url") or "").rstrip("/")
        alb = album_by_url.get(rel)
        s["album"] = s.get("release") or (alb["title"] if alb else "")
        s["album_slug"] = alb["slug"] if alb else ""
        s["year"] = alb["year"] if alb else None
        if not s["year"] and s["album"] in ("Private: False Prophet", "Private: I Contain Multitudes", "Private: Murder Most Foul"):
            s["year"] = 2020
            s["album"] = "Rough and Rowdy Ways"
            s["album_slug"] = "rough-and-rowdy-ways"

    quotes = []
    seen = set()
    for line in (DATA / "quotes-raw.tsv").read_text().splitlines():
        if not line.strip() or "\tSKIP" in line:
            continue
        slug, text, tags = line.split("\t")
        slug = SLUG_FIX.get(slug, slug)
        if slug not in song_by_slug:
            raise SystemExit(f"unmatched slug: {slug}")
        key = (slug, text)
        if key in seen:
            continue
        seen.add(key)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        qid = file_slug(slug) + "-" + hashlib.sha1(text.encode()).hexdigest()[:8]
        song = song_by_slug[slug]
        quotes.append({
            "id": qid,
            "text": text,
            "tags": tag_list,
            "song": song["title"],
            "song_slug": slug,
            "album": song["album"],
            "album_slug": song["album_slug"],
            "year": song["year"],
            "official": song["url"],
        })

    # song.quotes / tags
    quotes_by_song = defaultdict(list)
    for q in quotes:
        quotes_by_song[q["song_slug"]].append(q)
    for s in songs:
        qs = quotes_by_song.get(s["slug"], [])
        s["quotes"] = qs
        tags = []
        for q in qs:
            for t in q["tags"]:
                if t not in tags:
                    tags.append(t)
        s["tags"] = tags

    # related songs: share a tag, prefer those with quotes
    by_tag = defaultdict(list)
    for s in songs:
        for t in s["tags"]:
            by_tag[t].append(s["slug"])
    for s in songs:
        related = []
        for t in s["tags"]:
            for other in by_tag[t]:
                if other != s["slug"] and other not in related:
                    related.append(other)
        s["related"] = related[:8]

    subjects = defaultdict(lambda: {"slug": "", "name": "", "quotes": [], "songs": []})
    for q in quotes:
        for t in q["tags"]:
            rec = subjects[t]
            rec["slug"] = file_slug(t)
            rec["name"] = t
            rec["quotes"].append(q["id"])
            if q["song_slug"] not in rec["songs"]:
                rec["songs"].append(q["song_slug"])

    return {
        "songs": songs,
        "song_by_slug": song_by_slug,
        "albums": albums,
        "album_by_slug": album_by_slug,
        "quotes": quotes,
        "subjects": subjects,
    }

NAV = '''
<header class="site-head">
  <a class="mark" href="{root}">Dylan</a>
  <form class="find" action="{root}search.html" method="get" role="search">
    <label class="sr" for="q-{qid}">Search</label>
    <input id="q-{qid}" type="search" name="q" placeholder="Search lines, songs, subjects…" autocomplete="off">
  </form>
  <nav>
    <a href="{root}quotes/">Quotes</a>
    <a href="{root}subjects/">Subjects</a>
    <a href="{root}albums/">Albums</a>
    <a href="{root}songs/">Songs</a>
  </nav>
</header>
'''

FEEDBACK_BTNS = '''
<div class="feedback-group" role="group" aria-label="Feedback">
  <button type="button" class="feedback-btn feedback-up" data-feedback="up" aria-label="This is working">
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><circle cx="9" cy="10" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r="1" fill="currentColor" stroke="none"/></svg>
  </button>
  <button type="button" class="feedback-btn feedback-down" data-feedback="down" aria-label="Something is wrong">
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 16s1.5-2 4-2 4 2 4 2"/><circle cx="9" cy="10" r="1" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r="1" fill="currentColor" stroke="none"/></svg>
  </button>
</div>
'''

FOOT = '''
<footer class="site-foot">
  <p>Short, widely cited lines for writing and talks — not full lyrics. Official catalog from <a href="https://www.bobdylan.com/">bobdylan.com</a>. Each song links there for the complete text.</p>
  <p>dylan.jbf.com · Jeff Franzen</p>
</footer>
'''

def page(title, body, root, extra_css="", extra_js="", description=""):
    desc = description or "A searchable index of Bob Dylan’s songs and the lines people cite."
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400;1,8..60,600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{root}assets/styles.css">
  {extra_css}
</head>
<body>
{NAV.format(root=root, qid=file_slug(title)[:24] or "p")}
{FEEDBACK_BTNS}
<main>
{body}
</main>
{FOOT}
<script src="{root}assets/search.js"></script>
<script src="{root}assets/feedback.js"></script>
{extra_js}
</body>
</html>
'''

def cite(q):
    year = f", {q['year']}" if q.get("year") else ""
    album = f", {q['album']}" if q.get("album") else ""
    return f"{q['song']}{album}{year}"

def quote_block(q, root):
    tags = " ".join(f'<a class="tag" href="{root}subjects/{file_slug(t)}.html">{esc(t)}</a>' for t in q["tags"])
    year = f" · {q['year']}" if q.get("year") else ""
    album_link = (
        f'<a href="{root}albums/{esc(q["album_slug"])}.html">{esc(q["album"])}</a>{year}'
        if q.get("album_slug") else esc(q.get("album") or "")
    )
    return f'''
<figure class="quote">
  <blockquote><a href="{root}quotes/{esc(q["id"])}.html">{esc(q["text"])}</a></blockquote>
  <figcaption>
    <a href="{root}songs/{esc(q["song_slug"])}.html">{esc(q["song"])}</a>
    <span class="meta">{album_link}</span>
    <span class="tags">{tags}</span>
  </figcaption>
</figure>
'''

def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def build(db):
    songs, albums, quotes, subjects = db["songs"], db["albums"], db["quotes"], db["subjects"]
    song_by_slug, album_by_slug = db["song_by_slug"], db["album_by_slug"]

    # search index (compact)
    index = {
        "quotes": [
            {"id": q["id"], "text": q["text"], "song": q["song"], "song_slug": q["song_slug"],
             "album": q["album"], "year": q["year"], "tags": q["tags"]}
            for q in quotes
        ],
        "songs": [
            {"slug": s["slug"], "title": s["title"], "album": s["album"], "year": s["year"],
             "tags": s["tags"], "n": len(s["quotes"])}
            for s in songs
        ],
        "albums": [
            {"slug": a["slug"], "title": a["title"], "year": a["year"], "kind": a["kind"],
             "n": a["track_count"]}
            for a in albums
        ],
        "subjects": [
            {"slug": s["slug"], "name": s["name"], "n": len(s["quotes"])}
            for s in sorted(subjects.values(), key=lambda x: (-len(x["quotes"]), x["name"]))
        ],
    }
    write(DATA / "index.json", json.dumps(index, ensure_ascii=False, indent=0))
    write(DATA / "quotes.json", json.dumps(quotes, ensure_ascii=False, indent=0))
    write(ROOT / "assets" / "index.json", json.dumps(index, ensure_ascii=False))

    # HOME
    featured_ids = [
        "the answer, my friend",
        "the times they are a-changin",
        "how does it feel",
        "he not busy being born",
        "you don’t need a weatherman",
        "there must be some way out of here",
        "come in, she said",
        "it’s not dark yet",
        "i contain multitudes",
        "i was so much older then",
        "knock, knock, knockin",
        "may you stay forever young",
    ]
    featured = []
    for needle in featured_ids:
        for q in quotes:
            if needle in q["text"].lower() and q not in featured:
                featured.append(q)
                break
    # fill if needed
    for q in quotes:
        if len(featured) >= 12:
            break
        if q not in featured:
            featured.append(q)

    sub_list = sorted(subjects.values(), key=lambda x: (-len(x["quotes"]), x["name"]))
    studio = [a for a in albums if a["kind"] == "Studio"]
    studio.sort(key=lambda a: (a["year"] or 9999, a["title"]))

    home_body = f'''
<section class="hero">
  <h1>The lines you reach for, and the catalog behind them.</h1>
  <p class="lede">A searchable index of Bob Dylan’s official songs, tagged by subject, with the short quotations people actually cite in writing, talks, and discussion. Full lyrics stay on the official site.</p>
  <p class="counts">{len(quotes)} quotations · {len(songs)} songs · {len(albums)} official releases · {len(subjects)} subjects</p>
</section>
<section>
  <h2>Cited often</h2>
  <div class="quote-list">
    {''.join(quote_block(q, '') for q in featured[:12])}
  </div>
</section>
<section>
  <h2>Browse by subject</h2>
  <ul class="subject-cloud">
    {''.join(f'<li><a href="subjects/{esc(s["slug"])}.html">{esc(s["name"])} <span>{len(s["quotes"])}</span></a></li>' for s in sub_list)}
  </ul>
</section>
<section>
  <h2>Studio albums</h2>
  <ol class="album-list compact">
    {''.join(f'<li><span class="year">{a["year"] or "—"}</span> <a href="albums/{esc(a["slug"])}.html">{esc(a["title"])}</a></li>' for a in studio)}
  </ol>
</section>
'''
    write(ROOT / "index.html", page("Dylan — songs, subjects, and cited lines", home_body, "", description="Search Bob Dylan’s official catalog and the short, well-known lines people cite."))

    # SEARCH (JS reads query string)
    search_body = '''
<section class="hero">
  <h1>Search</h1>
  <p class="lede" id="search-status">Type a word, a song, a year, or a subject.</p>
</section>
<div id="search-results" class="search-results"></div>
'''
    write(ROOT / "search.html", page("Search — Dylan", search_body, "", extra_js='<script>document.addEventListener("DOMContentLoaded", () => window.DylanSearch && DylanSearch.page());</script>'))

    # QUOTES INDEX
    quotes_sorted = sorted(quotes, key=lambda q: (q["year"] or 9999, q["song"], q["text"]))
    q_body = f'''
<section class="hero">
  <h1>Quotations</h1>
  <p class="lede">{len(quotes)} short, widely cited lines, each with a stable URL you can point to. Not full lyrics.</p>
</section>
<div class="quote-list">
{''.join(quote_block(q, '../') for q in quotes_sorted)}
</div>
'''
    write(ROOT / "quotes" / "index.html", page("Quotations — Dylan", q_body, "../"))

    for q in quotes:
        tags = " ".join(f'<a class="tag" href="../subjects/{file_slug(t)}.html">{esc(t)}</a>' for t in q["tags"])
        year = f" ({q['year']})" if q.get("year") else ""
        album = (
            f'<a href="../albums/{esc(q["album_slug"])}.html">{esc(q["album"])}</a>{year}'
            if q.get("album_slug") else esc(q.get("album") or "")
        )
        attr = f"Bob Dylan, “{q['song']}”"
        if q.get("album"):
            attr += f", {q['album']}"
        if q.get("year"):
            attr += f", {q['year']}"
        body = f'''
<article class="cite-page">
  <p class="kicker">Quotation</p>
  <blockquote class="display">{esc(q["text"])}</blockquote>
  <p class="attribution">
    <a href="../songs/{esc(q["song_slug"])}.html">{esc(q["song"])}</a>
    · {album}
  </p>
  <p class="tags">{tags}</p>
  <div class="cite-box">
    <button type="button" class="copy" data-copy="{esc(q['text'])} — {esc(attr)}">Copy citation</button>
    <p class="cite-text">{esc(q["text"])} — {esc(attr)}</p>
  </div>
  <p class="official"><a href="{esc(q["official"])}">Full song on bobdylan.com</a></p>
</article>
'''
        write(ROOT / "quotes" / f"{q['id']}.html", page(f"“{q['text']}” — {q['song']}", body, "../", extra_js="""
<script>
document.querySelectorAll('.copy').forEach(b => b.addEventListener('click', async () => {{
  try {{ await navigator.clipboard.writeText(b.dataset.copy); b.textContent = 'Copied'; }}
  catch (e) {{ b.textContent = 'Select and copy below'; }}
}}));
</script>
"""))

    # SUBJECTS
    s_index = f'''
<section class="hero">
  <h1>Subjects</h1>
  <p class="lede">Themes and keywords across the cited lines.</p>
</section>
<ul class="subject-cloud">
  {''.join(f'<li><a href="{esc(s["slug"])}.html">{esc(s["name"])} <span>{len(s["quotes"])}</span></a></li>' for s in sub_list)}
</ul>
'''
    write(ROOT / "subjects" / "index.html", page("Subjects — Dylan", s_index, "../"))
    q_by_id = {q["id"]: q for q in quotes}
    for s in subjects.values():
        qs = [q_by_id[i] for i in s["quotes"]]
        qs.sort(key=lambda q: (q["year"] or 9999, q["song"]))
        song_links = []
        for sl in s["songs"]:
            song = song_by_slug[sl]
            song_links.append(f'<li><a href="../songs/{esc(sl)}.html">{esc(song["title"])}</a></li>')
        body = f'''
<section class="hero">
  <p class="kicker"><a href="./">Subjects</a></p>
  <h1>{esc(s["name"])}</h1>
  <p class="lede">{len(qs)} cited lines in {len(s["songs"])} songs.</p>
</section>
<div class="quote-list">
{''.join(quote_block(q, '../') for q in qs)}
</div>
<h2>Songs</h2>
<ul class="plain">{''.join(song_links)}</ul>
'''
        write(ROOT / "subjects" / f"{s['slug']}.html", page(f"{s['name']} — Dylan", body, "../"))

    # ALBUMS
    albums_sorted = sorted(albums, key=lambda a: (a["year"] or 9999, a["title"]))
    groups = defaultdict(list)
    for a in albums_sorted:
        groups[a["kind"]].append(a)
    parts = []
    for kind in ("Studio", "Soundtrack", "Live", "Bootleg Series", "Compilation"):
        if kind not in groups:
            continue
        items = "".join(
            f'<li><span class="year">{a["year"] or "—"}</span> <a href="{esc(a["slug"])}.html">{esc(a["title"])}</a> <span class="meta">{a["track_count"] or "—"} tracks</span></li>'
            for a in groups[kind]
        )
        parts.append(f"<h2>{esc(kind)}</h2><ol class='album-list'>{items}</ol>")
    write(ROOT / "albums" / "index.html", page("Albums — Dylan", "<section class='hero'><h1>Official releases</h1><p class='lede'>Titles, years, and tracklists from bobdylan.com.</p></section>" + "".join(parts), "../"))

    # map tracks to our song slugs
    for a in albums:
        track_html = []
        # For huge live boxes, show a note and first-release uniqueness later; still list if reasonable
        tracks = a.get("tracks") or []
        huge = len(tracks) > 80
        shown = tracks[:40] if huge else tracks
        for t in shown:
            sl = url_slug(t["url"])
            title = t["title"]
            # strip leading "N. "
            title = re.sub(r"^\d+\.\s*", "", title)
            if sl in song_by_slug:
                track_html.append(f'<li><span class="n">{t["n"]}</span> <a href="../songs/{esc(sl)}.html">{esc(title)}</a></li>')
            else:
                track_html.append(f'<li><span class="n">{t["n"]}</span> {esc(title)}</li>')
        more = f"<p class='note'>{len(tracks)} tracks on this official release. The first {len(shown)} are listed here; see <a href='{esc(a['url'])}'>bobdylan.com</a> for the complete set.</p>" if huge else ""
        empty = "<p class='note'>No tracklist was published on the official album page.</p>" if not tracks else ""
        # quotes from songs whose first release is this album, or that appear on it
        album_song_slugs = {url_slug(t["url"]) for t in tracks if t.get("url")}
        album_quotes = [q for q in quotes if q["album_slug"] == a["slug"] or q["song_slug"] in album_song_slugs]
        # de-dupe
        seenq = set()
        uniq = []
        for q in album_quotes:
            if q["id"] not in seenq:
                seenq.add(q["id"])
                uniq.append(q)
        qhtml = f"<h2>Cited lines</h2><div class='quote-list'>{''.join(quote_block(q, '../') for q in uniq)}</div>" if uniq else ""
        released = f"<p class='meta'>Released {esc(a['released'])}</p>" if a.get("released") else ""
        body = f'''
<article>
  <p class="kicker"><a href="./">Albums</a> · {esc(a["kind"])}</p>
  <h1>{esc(a["title"])}</h1>
  <p class="lede">{a["year"] or ""}{(" · " + str(len(tracks)) + " tracks") if tracks else ""}</p>
  {released}
  {qhtml}
  <h2>Tracks</h2>
  {empty}{more}
  <ol class="tracks">{''.join(track_html)}</ol>
  <p class="official"><a href="{esc(a["url"])}">Album on bobdylan.com</a></p>
</article>
'''
        write(ROOT / "albums" / f"{a['slug']}.html", page(f"{a['title']} ({a['year']}) — Dylan", body, "../"))

    # SONGS INDEX — those with quotes first, then A–Z of all
    with_q = sorted([s for s in songs if s["quotes"]], key=lambda s: s["title"].lower())
    all_az = sorted(songs, key=lambda s: s["title"].lower())
    def song_li(s, root="../"):
        year = f" ({s['year']})" if s.get("year") else ""
        n = f" · {len(s['quotes'])} quoted" if s["quotes"] else ""
        return f'<li><a href="{root}songs/{esc(s["slug"])}.html">{esc(s["title"])}</a> <span class="meta">{esc(s.get("album") or "")}{year}{n}</span></li>'
    songs_body = f'''
<section class="hero">
  <h1>Songs</h1>
  <p class="lede">{len(songs)} official titles. {len(with_q)} have a cited line in this index.</p>
</section>
<h2>With a cited line</h2>
<ul class="song-list">{''.join(song_li(s) for s in with_q)}</ul>
<h2>All official songs</h2>
<ul class="song-list dense">{''.join(song_li(s) for s in all_az)}</ul>
'''
    write(ROOT / "songs" / "index.html", page("Songs — Dylan", songs_body, "../"))

    for s in songs:
        qs = s["quotes"]
        tags = " ".join(f'<a class="tag" href="../subjects/{file_slug(t)}.html">{esc(t)}</a>' for t in s["tags"])
        album = (
            f'<a href="../albums/{esc(s["album_slug"])}.html">{esc(s["album"])}</a>'
            if s.get("album_slug") else esc(s.get("album") or "—")
        )
        year = f" · {s['year']}" if s.get("year") else ""
        related = []
        for sl in s["related"]:
            other = song_by_slug[sl]
            related.append(f'<li><a href="{esc(sl)}.html">{esc(other["title"])}</a></li>')
        rel = f"<h2>Related</h2><ul class='plain'>{''.join(related)}</ul>" if related else ""
        played = ""
        if s.get("times"):
            played = f"<p class='meta'>Played live {s['times']:,} times" + (f", first {esc(s['first'])}" if s.get("first") else "") + " (official count).</p>"
        qhtml = f"<div class='quote-list'>{''.join(quote_block(q, '../') for q in qs)}</div>" if qs else "<p class='note'>No short citation is indexed for this title yet. The official lyric is on bobdylan.com.</p>"
        body = f'''
<article>
  <p class="kicker"><a href="./">Songs</a></p>
  <h1>{esc(s["title"])}</h1>
  <p class="lede">{album}{year}</p>
  <p class="tags">{tags}</p>
  {played}
  <h2>Cited lines</h2>
  {qhtml}
  {rel}
  <p class="official"><a href="{esc(s["url"])}">Full song on bobdylan.com</a></p>
</article>
'''
        write(ROOT / "songs" / f"{s['slug']}.html", page(f"{s['title']} — Dylan", body, "../"))

    print(f"built: {len(quotes)} quotes, {len(songs)} songs, {len(albums)} albums, {len(subjects)} subjects")

if __name__ == "__main__":
    build(load())
