#!/usr/bin/env python3
"""初期設定: python3 setup.py --tag あなたのID-22 --url https://ユーザー名.github.io/リポジトリ名 [--x @アカウント]"""
import argparse, json, re
from pathlib import Path
p = Path(__file__).parent / "config.json"
cfg = json.loads(p.read_text(encoding="utf-8"))
ap = argparse.ArgumentParser()
ap.add_argument("--tag"); ap.add_argument("--url"); ap.add_argument("--x"); ap.add_argument("--name")
a = ap.parse_args()
if a.tag:
    if not re.fullmatch(r"[a-z0-9\-]+-22", a.tag):
        raise SystemExit("トラッキングIDは「xxxx-22」の形式です")
    cfg["amazon_tag"] = a.tag
if a.url: cfg["base_url"] = a.url.rstrip("/")
if a.x: cfg["x_account"] = a.x
if a.name: cfg["site_name"] = a.name
p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(cfg, ensure_ascii=False, indent=2))
