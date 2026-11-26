#!/usr/bin/env python3
"""Build a static, iframe-ready carousel page from an RSS or Atom feed.

Usage:
    python build.py                      # reads FEED_URL from the environment
    python build.py https://site/feed    # or pass a URL
    python build.py sample.xml           # or a local file, for testing

Optional environment variables:
    ITEM_COUNT      number of items to show (default 5)
    CAROUSEL_TITLE  heading shown above the carousel (default: the feed's own title, set to "" to hide)
    AUTOPLAY_SECS   seconds per slide, 0 to turn off (default 7)
    OUTPUT          output file (default site/index.html)
    LINK_PREFER     guid (default, the Valona item page) or link (the original article)
    LINK_TARGET     _self (default), _top, _parent or _blank
    TEMPLATE        template.html (simple card) or template-phone.html (square phone tile)
    BRAND_HTML, BRAND_TAGLINE, PANEL_LABEL_HTML   header and label text for the phone tile

Uses only the Python standard library.
"""

import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}

HERE = Path(__file__).resolve().parent


# ---------- fetching and parsing ----------

def load_feed(source: str) -> bytes:
    if re.match(r"^https?://", source, re.I):
        req = urllib.request.Request(source, headers={
            "User-Agent": "Mozilla/5.0 (feed-carousel; +https://github.com)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    return Path(source).read_bytes()


def text_of(el) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def strip_tags(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def first_img(s: str) -> str:
    m = re.search(r"""<img[^>]+src=["']([^"']+)["']""", s or "", re.I)
    return html.unescape(m.group(1)) if m else ""


def safe_url(u: str) -> str:
    u = (u or "").strip()
    return u if re.match(r"^https?://", u, re.I) else ""


def parse_date(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def media_image(el) -> str:
    for tag in ("media:thumbnail", "media:content", "media:group/media:thumbnail", "media:group/media:content"):
        for m in el.findall(tag, NS):
            url = m.get("url", "")
            medium = m.get("medium", "")
            mtype = m.get("type", "")
            if url and (tag.endswith("thumbnail") or medium == "image" or mtype.startswith("image") or
                        re.search(r"\.(jpe?g|png|gif|webp|avif)(\?|$)", url, re.I)):
                return url
    return ""


def parse(data: bytes):
    root = ET.fromstring(data)
    items = []
    feed_title = ""

    if root.tag == f"{{{NS['atom']}}}feed":
        feed_title = text_of(root.find("atom:title", NS))
        for e in root.findall("atom:entry", NS):
            link = ""
            for l in e.findall("atom:link", NS):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            body = text_of(e.find("atom:summary", NS)) or text_of(e.find("atom:content", NS))
            raw_content = text_of(e.find("atom:content", NS))
            img = media_image(e) or first_img(body) or first_img(raw_content)
            for l in e.findall("atom:link", NS):
                if not img and l.get("rel") == "enclosure" and l.get("type", "").startswith("image"):
                    img = l.get("href", "")
            items.append({
                "title": strip_tags(text_of(e.find("atom:title", NS))),
                "link": link,
                "date": parse_date(text_of(e.find("atom:published", NS)) or text_of(e.find("atom:updated", NS))),
                "summary": strip_tags(body),
                "image": img,
            })
    else:
        channel = root.find("channel")
        if channel is None:
            channel = root
        feed_title = text_of(channel.find("title"))
        # RSS 2.0 items live in <channel>, RSS 1.0 (RDF) items sit at the root
        rss_items = channel.findall("item") or root.findall("{http://purl.org/rss/1.0/}item")
        for it in rss_items:
            def f(tag):
                return text_of(it.find(tag, NS)) if ":" in tag else (
                    text_of(it.find(tag)) or text_of(it.find("{http://purl.org/rss/1.0/}" + tag)))
            desc = f("description")
            content = f("content:encoded")
            img = media_image(it)
            if not img:
                enc = it.find("enclosure")
                if enc is not None and enc.get("type", "").startswith("image"):
                    img = enc.get("url", "")
            img = img or first_img(content) or first_img(desc)
            items.append({
                "title": strip_tags(f("title")),
                "link": f("link"),
                "guid": f("guid"),
                "date": parse_date(f("pubDate") or f("dc:date")),
                "summary": strip_tags(desc or content),
                "image": img,
                "source": f("source"),
            })

    prefer_guid = os.environ.get("LINK_PREFER", "guid").strip().lower() == "guid"
    for i in items:
        guid = safe_url(i.get("guid", ""))
        if prefer_guid and guid:
            i["link"] = guid
        elif not i["link"]:
            i["link"] = guid
        i["summary"] = re.sub(r"\s*(link to (the )?original article|read more|continue reading)\.?\s*$", "", i["summary"], flags=re.I)
        i["source"] = strip_tags(i.get("source", ""))
        i["link"] = safe_url(i["link"])
        i["image"] = safe_url(i["image"])

    epoch = datetime.min.replace(tzinfo=timezone.utc)
    items.sort(key=lambda i: i["date"] or epoch, reverse=True)
    return strip_tags(feed_title), items


# ---------- rendering ----------

def clip(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def render(feed_title: str, items, heading: str, autoplay: int) -> str:
    target = os.environ.get("LINK_TARGET", "_self").strip() or "_self"
    if target not in ("_self", "_blank", "_parent", "_top"):
        target = "_self"
    tgt = f'target="{target}"' + (' rel="noopener"' if target == "_blank" else "")
    slides = []
    for idx, it in enumerate(items):
        e = html.escape
        date_html = (f'<time datetime="{it["date"].isoformat()}">{it["date"].strftime("%-d %b %Y")}</time>'
                     if it["date"] else "")
        if it.get("source"):
            date_html = f'<span class="src">{e(it["source"])}</span>' + (" · " + date_html if date_html else "")
        img_html = (f'<div class="media"><img src="{e(it["image"])}" alt="" loading="{"eager" if idx == 0 else "lazy"}" '
                    f'referrerpolicy="no-referrer" onerror="this.parentNode.remove()"></div>') if it["image"] else ""
        title = e(clip(it["title"] or "Untitled", 160))
        title_html = (f'<a href="{e(it["link"])}" {tgt}>{title}</a>'
                      if it["link"] else title)
        more = (f'<a class="more" href="{e(it["link"])}" {tgt}>Read more →</a>'
                if it["link"] else "")
        slides.append(f"""
      <article class="slide{' has-img' if it['image'] else ''}" role="group" aria-roledescription="slide" aria-label="{idx + 1} of {len(items)}">
        {img_html}
        <div class="body">
          <div class="meta">{date_html}</div>
          <h2>{title_html}</h2>
          <p>{e(clip(it["summary"], 320))}</p>
          {more}
        </div>
      </article>""")

    dots = "".join(f'<button class="dot" aria-label="Go to item {i + 1}"></button>' for i in range(len(items)))
    updated = datetime.now(timezone.utc).strftime("%-d %b %Y, %H:%M UTC")
    heading_html = f'<h1>{html.escape(heading)}</h1>' if heading else ""

    template = (HERE / os.environ.get("TEMPLATE", "template.html")).read_text(encoding="utf-8")
    return (template
            .replace("{{BRAND}}", os.environ.get("BRAND_HTML", "<i>AH</i>a! Intelligence"))
            .replace("{{TAGLINE}}", html.escape(os.environ.get("BRAND_TAGLINE", "Animal Health AI Intelligence")))
            .replace("{{PANEL_LABEL}}", os.environ.get("PANEL_LABEL_HTML", "What's trending<br>in Animal Health"))
            .replace("{{HEADING}}", heading_html)
            .replace("{{PAGE_TITLE}}", html.escape(heading or feed_title or "Latest news"))
            .replace("{{SLIDES}}", "".join(slides) or '<p class="empty">No items in the feed right now.</p>')
            .replace("{{DOTS}}", dots)
            .replace("{{UPDATED}}", updated)
            .replace("{{AUTOPLAY_MS}}", str(max(0, autoplay) * 1000)))


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FEED_URL", "").strip()
    if not source:
        sys.exit("No feed given. Set FEED_URL or pass a URL/file as the first argument.")
    count = int(os.environ.get("ITEM_COUNT", "5") or 5)
    autoplay = int(os.environ.get("AUTOPLAY_SECS", "7") or 0)
    out = Path(os.environ.get("OUTPUT", HERE / "site" / "index.html"))

    feed_title, items = parse(load_feed(source))
    if not items:
        # Keep yesterday's page rather than publishing an empty carousel
        sys.exit("Feed parsed but contained no items. Leaving the existing page unchanged.")
    items = items[:count]

    heading = os.environ.get("CAROUSEL_TITLE")
    if heading is None:
        heading = feed_title

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(feed_title, items, heading, autoplay), encoding="utf-8")
    print(f"Wrote {len(items)} items from '{feed_title or source}' to {out}")
    for i in items:
        print(f"  - {i['date'].date() if i['date'] else '????-??-??'}  {i['title'][:80]}")


if __name__ == "__main__":
    main()
