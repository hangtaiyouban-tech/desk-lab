#!/usr/bin/env python3
"""Amazonアソシエイト規約・ステマ規制・品質チェッカー

使い方:
  python3 check.py            # 全記事チェック（ERRORがあれば終了コード1）
  python3 check.py --release  # 公開前チェック（トラッキングID未設定もERROR扱い）
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
RELEASE = "--release" in sys.argv

# (正規表現, レベル, 理由)
RULES = [
    (r"[0-9０-９,，]+\s*円", "ERROR", "価格の直書きは規約違反リスク（PA-API以外の価格表示不可）。価格帯は「数千円台」等の幅表現に"),
    (r"最安値|日本一|業界No\.?1|No\.1|絶対|必ず痩せ|100%", "ERROR", "根拠のない最上級・断定表現（景品表示法）"),
    (r"実際に(使って|使用して|買って)|使ってみた|愛用|私も(使|買)", "ERROR", "未使用製品の体験談は虚偽表示。実体験を書く場合は本人確認のうえ check_ignore に記録"),
    (r"amzn\.to/", "WARN", "短縮URLはSNSでは可だが、記事では長いURL（tag付き）を推奨"),
    (r"(レビュー|口コミ)\s*★", "WARN", "星評価の転載はAmazonのレビュー転載にあたる可能性"),
    (r"m\.media-amazon\.com|images-amazon\.com|images-na\.ssl", "ERROR", "Amazon画像の直リンク/転載は不可（PA-API・SiteStripe経由のみ）"),
    (r"メール|LINEで(送|共有)|PDF", "WARN", "メール・PDF・オフライン配布でのリンク利用は規約で禁止。文脈を確認"),
]


def check_file(p: Path):
    issues = []
    raw = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        return [("ERROR", 0, "front matter がない")]
    fm, body = m.group(1), m.group(2)
    for key in ("title", "description", "date", "category", "keyword"):
        if not re.search(rf"^{key}:\s*\S", fm, re.M):
            issues.append(("ERROR", 0, f"front matter に {key} がない"))
    t = re.search(r"^title:\s*(.*)$", fm, re.M)
    if t and not (20 <= len(t.group(1)) <= 40):
        issues.append(("WARN", 0, f"タイトル長 {len(t.group(1))}字（推奨20〜40字）"))
    d = re.search(r"^description:\s*(.*)$", fm, re.M)
    if d and not (60 <= len(d.group(1)) <= 130):
        issues.append(("WARN", 0, f"description長 {len(d.group(1))}字（推奨60〜130字）"))
    kw = re.search(r"^keyword:\s*(.*)$", fm, re.M)
    if kw and t and kw.group(1).split()[0] not in t.group(1):
        issues.append(("WARN", 0, "タイトルに主キーワードが入っていない"))

    ignore = set(re.findall(r"^check_ignore:\s*(.*)$", fm, re.M))
    body_lines = body.splitlines()
    for i, ln in enumerate(body_lines, 1):
        if ln.startswith("[["):
            continue
        for pat, lvl, why in RULES:
            if pat in ignore:
                continue
            if re.search(pat, ln):
                issues.append((lvl, i, f"{why}: 「{ln.strip()[:40]}」"))

    links = len(re.findall(r"\[\[(amazon|asin):", body)) + len(re.findall(r"amazon\.co\.jp", body))
    chars = len(re.sub(r"\s", "", body))
    if links == 0:
        issues.append(("ERROR", 0, "Amazonリンクが1つもない（収益導線なし）"))
    if chars < 1500:
        issues.append(("WARN", 0, f"本文 {chars}字（1500字以上推奨）"))
    if links > max(4, chars // 300):
        issues.append(("WARN", 0, f"リンク {links}個は多すぎ（広告過多に見える）"))
    if not re.search(r"^## .*(まとめ|結論)", body, re.M):
        issues.append(("WARN", 0, "「まとめ／結論」見出しがない"))
    return issues


def main():
    errors = 0
    if CFG["amazon_tag"] in ("", "YOURTAG-22"):
        lvl = "ERROR" if RELEASE else "WARN"
        print(f"[{lvl}] config.json: amazon_tag が未設定（YOURTAG-22 のまま）")
        errors += lvl == "ERROR"
    if "example.github.io" in CFG["base_url"]:
        lvl = "ERROR" if RELEASE else "WARN"
        print(f"[{lvl}] config.json: base_url が仮のまま")
        errors += lvl == "ERROR"
    files = sorted((ROOT / "content/articles").glob("*.md"))
    for p in files:
        iss = check_file(p)
        for lvl, ln, msg in iss:
            print(f"[{lvl}] {p.name}:{ln} {msg}")
            errors += lvl == "ERROR"
    print(f"--- {len(files)} files, {errors} errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
