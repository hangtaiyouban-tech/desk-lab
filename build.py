#!/usr/bin/env python3
"""静的アフィリエイトサイト生成スクリプト（標準ライブラリのみ）

使い方: python3 build.py   -> dist/ にサイトを出力

記事: content/articles/*.md
  先頭に front matter:
    ---
    title: 記事タイトル
    description: メタディスクリプション
    date: 2026-11-07
    category: カテゴリ
    keyword: 狙うキーワード
    ---
  本文中のショートコード（行単独で書く）:
    [[amazon:検索語|ボタン文言]]   -> Amazon検索結果へのアソシエイトリンク（ボタン）
    [[asin:B0XXXXXXXX|商品名]]     -> 商品ページへのアソシエイトリンク（ASIN確認済みのときのみ）
"""
import html
import json
import re
import shutil
import urllib.parse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
OUT = ROOT / "dist"
DISCLOSURE = f"Amazonのアソシエイトとして、{CFG['site_name']}は適格販売により収入を得ています。"
REL_AMZ = 'rel="sponsored nofollow noopener" target="_blank"'


# ---------- Amazon links ----------
def amazon_search_url(q: str) -> str:
    return f"https://{CFG['amazon_domain']}/s?" + urllib.parse.urlencode({"k": q, "tag": CFG["amazon_tag"]})


def amazon_asin_url(asin: str) -> str:
    return f"https://{CFG['amazon_domain']}/dp/{asin}?tag={CFG['amazon_tag']}"


def btn(url: str, label: str) -> str:
    return f'<p class="cta"><a class="btn" href="{html.escape(url)}" {REL_AMZ}>{html.escape(label)}</a></p>'


def shortcodes(text: str) -> str:
    def amz(m):
        q = m.group(1).strip()
        label = (m.group(2) or "").strip() or f"Amazonで「{q}」を見る"
        return btn(amazon_search_url(q), label)

    def asin(m):
        return btn(amazon_asin_url(m.group(1).strip()), (m.group(2) or "Amazonで見る").strip())

    text = re.sub(r"\[\[amazon:([^|\]]+)(?:\|([^\]]*))?\]\]", amz, text)
    return re.sub(r"\[\[asin:([A-Z0-9]{10})(?:\|([^\]]*))?\]\]", asin, text)


# ---------- minimal markdown ----------
def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)

    def link(m):
        url = m.group(2)
        if "amazon." in url:
            rel = " " + REL_AMZ
        elif url.startswith("http"):
            rel = ' rel="noopener" target="_blank"'
        else:
            rel = ""
        return f'<a href="{url}"{rel}>{m.group(1)}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, s)


BLOCK_START = re.compile(r"^(#{2,4}\s|\||\s*[-*]\s|\s*\d+\.\s|>|\[\[)")


def md_to_html(md: str):
    lines = md.splitlines()
    out, toc, i, hcount = [], [], 0, 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("[[") and ln.rstrip().endswith("]]"):
            out.append(shortcodes(ln.strip())); i += 1; continue
        m = re.match(r"^(#{2,4})\s+(.*)", ln)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            hcount += 1
            hid = f"h-{hcount}"
            if lvl == 2:
                toc.append((hid, txt))
            out.append(f'<h{lvl} id="{hid}">{inline(txt)}</h{lvl}>'); i += 1; continue
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            rows = [r for r in rows if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            t = ['<div class="tbl"><table>']
            for ri, r in enumerate(rows):
                tag = "th" if ri == 0 else "td"
                t.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in r) + "</tr>")
            t.append("</table></div>")
            out.append("".join(t)); continue
        for pat, tag in ((r"^\s*[-*]\s+", "ul"), (r"^\s*\d+\.\s+", "ol")):
            if re.match(pat, ln):
                items = []
                while i < len(lines) and re.match(pat, lines[i]):
                    items.append(re.sub(pat, "", lines[i])); i += 1
                out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
                break
        else:
            if ln.startswith(">"):
                q = []
                while i < len(lines) and lines[i].startswith(">"):
                    q.append(lines[i].lstrip("> ")); i += 1
                out.append('<div class="point">' + "<br>".join(inline(x) for x in q) + "</div>"); continue
            if not ln.strip():
                i += 1; continue
            para = []
            while i < len(lines) and lines[i].strip() and not BLOCK_START.match(lines[i]):
                para.append(lines[i]); i += 1
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
    return "\n".join(out), toc


def parse_article(p: Path):
    raw = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"front matter がありません: {p}")
    meta = {}
    for ln in m.group(1).splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            meta[k.strip()] = v.strip()
    meta.setdefault("date", date.today().isoformat())
    meta["slug"] = p.stem
    meta["body"] = m.group(2)
    return meta


# ---------- templates ----------
def page(title, desc, body, canonical="", extra_head=""):
    full = title if title == CFG["site_name"] else f"{title}｜{CFG['site_name']}"
    e = html.escape
    return f"""<!doctype html>
<html lang="{CFG['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(full)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:title" content="{e(full)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(canonical)}">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="style.css">
{extra_head}
</head>
<body>
<div class="prbar">本サイトはアフィリエイト広告（Amazonアソシエイト）を利用しています</div>
<header class="site"><a href="index.html" class="logo">{e(CFG['site_name'])}</a>
<p class="tagline">{e(CFG['site_description'])}</p></header>
<main>
{body}
</main>
<footer class="site">
<p class="disclosure">{e(DISCLOSURE)}</p>
<p><a href="about.html">運営者情報・広告ポリシー</a> ／ <a href="privacy.html">プライバシーポリシー</a></p>
<p>© {date.today().year} {e(CFG['site_name'])}</p>
</footer>
</body>
</html>
"""


def article_page(a, body_html, toc, related):
    e = html.escape
    url = f"{CFG['base_url']}/{a['slug']}.html"
    toc_html = ""
    if len(toc) >= 3:
        toc_html = '<nav class="toc"><p>目次</p><ol>' + "".join(
            f'<li><a href="#{hid}">{e(t)}</a></li>' for hid, t in toc) + "</ol></nav>"
    rel_html = ""
    if related:
        rel_html = '<section class="related"><h2>あわせて読みたい</h2><ul>' + "".join(
            f'<li><a href="{r["slug"]}.html">{e(r["title"])}</a></li>' for r in related) + "</ul></section>"
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"],
          "description": a.get("description", ""), "datePublished": a["date"],
          "dateModified": a.get("updated", a["date"]),
          "author": {"@type": "Organization", "name": CFG["author"]}}
    head = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
    upd = f" ／ 更新 {a['updated']}" if a.get("updated") else ""
    body = f"""<article>
<p class="crumb"><a href="index.html">ホーム</a> › {e(a.get('category', ''))}</p>
<h1>{e(a['title'])}</h1>
<p class="meta"><span class="pr">PR</span> 公開 {a['date']}{upd} ／ {e(CFG['author'])}</p>
<p class="notice">※この記事にはアフィリエイトリンク（広告）が含まれます。価格・在庫・仕様はリンク先のAmazonで最新情報をご確認ください。</p>
{toc_html}
{body_html}
{rel_html}
</article>"""
    return page(a["title"], a.get("description", ""), body, canonical=url, extra_head=head)


CSS = """:root{--bg:#fff;--fg:#1d1d1f;--mut:#666;--line:#e5e5e5;--acc:#e47911;--soft:#f7f7f5;--pt:#fff8ec;--ptl:#f3d19e;--ptf:#3b2c12;--link:#0a66c2}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--mut:#aaa;--line:#333;--soft:#1e1e1e;--pt:#2a2114;--ptl:#5a4420;--ptf:#f3e3c4;--link:#6cb4ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.85 -apple-system,"Hiragino Sans","Noto Sans JP",sans-serif}
a{color:var(--link)}main{max-width:760px;margin:0 auto;padding:0 16px 48px}
.prbar{background:var(--soft);color:var(--mut);font-size:12px;text-align:center;padding:4px 16px}
header.site{max-width:760px;margin:0 auto;padding:20px 16px 8px;border-bottom:1px solid var(--line)}
.logo{font-weight:800;font-size:22px;color:var(--fg);text-decoration:none}.tagline{margin:4px 0 0;color:var(--mut);font-size:13px}
h1{font-size:26px;line-height:1.45;margin:20px 0 8px}h2{font-size:21px;border-left:5px solid var(--acc);padding-left:10px;margin-top:44px}
h3{font-size:18px;margin-top:28px}.meta,.crumb{color:var(--mut);font-size:13px;margin:4px 0}
.pr{display:inline-block;border:1px solid var(--mut);border-radius:3px;padding:0 5px;font-size:11px;margin-right:4px}
.notice{background:var(--soft);font-size:13px;padding:8px 12px;border-radius:6px;color:var(--mut)}
.toc{border:1px solid var(--line);border-radius:8px;padding:8px 16px;margin:20px 0}.toc p{font-weight:700;margin:4px 0}
.point{background:var(--pt);border:1px solid var(--ptl);border-radius:8px;padding:12px 16px;margin:16px 0;color:var(--ptf)}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:16px 0}th,td{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}th{background:var(--soft)}
.cta{text-align:center;margin:20px 0}.btn{display:inline-block;background:var(--acc);color:#fff;font-weight:700;text-decoration:none;padding:12px 24px;border-radius:8px;max-width:100%}
.btn:hover{opacity:.9}.cards{list-style:none;padding:0}.cards li{border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.cards a{font-weight:700;font-size:17px;text-decoration:none}.cards p{margin:4px 0 0;color:var(--mut);font-size:14px}
footer.site{border-top:1px solid var(--line);max-width:760px;margin:0 auto;padding:16px;font-size:12px;color:var(--mut)}"""


def static_pages():
    e = html.escape
    x = f" ／ X: {e(CFG['x_account'])}" if CFG.get("x_account") else ""
    about = f"""<h1>運営者情報・広告ポリシー</h1>
<p>{e(CFG['site_name'])}は、在宅ワークやデスク周りの道具について「買ってから後悔しない選び方」を整理して紹介する情報サイトです。</p>
<h2>広告について</h2>
<p>当サイトはAmazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。</p>
<p>{e(DISCLOSURE)}</p>
<p>記事内のリンクには広告が含まれます。紹介料の有無によって評価や順位を変えることはありません。価格・在庫・仕様は変動するため、購入前に必ずリンク先の最新情報をご確認ください。</p>
<h2>記事の作り方</h2>
<p>メーカー公表の仕様・公式情報・一般的な選定基準をもとに比較・整理しています。実際に使用していない製品について使用感を書くことはありません。</p>
<h2>お問い合わせ</h2>
<p>運営者: {e(CFG['author'])}{x}</p>"""
    privacy = """<h1>プライバシーポリシー</h1>
<h2>アクセス解析</h2><p>当サイトではサイト改善のためアクセス解析ツールを利用する場合があります。データは匿名で収集され、個人を特定するものではありません。</p>
<h2>広告・Cookie</h2><p>当サイトはAmazonアソシエイト・プログラムに参加しています。第三者（Amazonを含む）がコンテンツおよび宣伝を提供し、訪問者から直接情報を収集し、訪問者のブラウザにCookieを設定したりこれを認識したりする場合があります。</p>
<h2>免責事項</h2><p>掲載情報は正確を期していますが、その完全性を保証するものではありません。リンク先での購入等によるトラブルについて責任を負いかねます。</p>"""
    return [("about.html", "運営者情報・広告ポリシー", about), ("privacy.html", "プライバシーポリシー", privacy)]


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    for f in (ROOT / "static").glob("*"):
        if f.is_file():
            shutil.copy(f, OUT / f.name)

    arts = sorted((parse_article(p) for p in (ROOT / "content/articles").glob("*.md")),
                  key=lambda a: a["date"], reverse=True)
    for a in arts:
        body_html, toc = md_to_html(a["body"])
        same = [r for r in arts if r is not a and r.get("category") == a.get("category")]
        related = (same or [r for r in arts if r is not a])[:4]
        (OUT / f"{a['slug']}.html").write_text(article_page(a, body_html, toc, related), encoding="utf-8")

    cats = {}
    for a in arts:
        cats.setdefault(a.get("category", "その他"), []).append(a)
    e = html.escape
    idx = [f"<h1>{e(CFG['site_name'])}</h1><p>{e(CFG['site_description'])}</p>"]
    for c, lst in cats.items():
        idx.append(f"<h2>{e(c)}</h2><ul class='cards'>")
        idx += [f'<li><a href="{a["slug"]}.html">{e(a["title"])}</a><p>{e(a.get("description", ""))}</p></li>' for a in lst]
        idx.append("</ul>")
    (OUT / "index.html").write_text(page(CFG["site_name"], CFG["site_description"], "\n".join(idx),
                                         canonical=CFG["base_url"] + "/"), encoding="utf-8")
    for fn, t, b in static_pages():
        (OUT / fn).write_text(page(t, t, b, canonical=f"{CFG['base_url']}/{fn}"), encoding="utf-8")

    urls = [CFG["base_url"] + "/"] + [f"{CFG['base_url']}/{a['slug']}.html" for a in arts]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"<url><loc>{html.escape(u)}</loc></url>" for u in urls] + ["</urlset>"]
    (OUT / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {CFG['base_url']}/sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {len(arts)} articles -> {OUT}")


if __name__ == "__main__":
    build()
