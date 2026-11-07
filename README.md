# デスク環境ラボ — Amazonアソシエイト収益化キット

在宅ワーク・デスク周りの「失敗しない選び方」記事でAmazonアソシエイト収益を得るための、サイト＋運用エージェント一式です。

## 構成
| パス | 役割 |
|---|---|
| `content/articles/*.md` | 記事（6本作成済み） |
| `build.py` | 静的サイト生成 → `dist/`（標準ライブラリのみ） |
| `check.py` | 規約・ステマ規制・品質チェック（`--release` で公開前の厳格モード） |
| `setup.py` | トラッキングID・URL・Xアカウントの設定 |
| `.claude/agents/` | 運用エージェント6体 |
| `.claude/commands/` | `/cycle`（週次サイクル）、`/new-article <キーワード>` |
| `.github/workflows/deploy.yml` | push で チェック→ビルド→GitHub Pages 公開 |
| `docs/` | PLAN（戦略）/ KEYWORDS（キーワード表）/ COMPLIANCE（規約）/ LOG（作業記録） |
| `sns/queue.md` | X投稿の在庫（14本） |

## エージェント
| 名前 | 仕事 |
|---|---|
| affiliate-director | 司令塔。次にやることを決めて他を動かす |
| keyword-researcher | 新規ドメインでも勝てる購買直前ロングテールを選ぶ |
| article-writer | 比較・選び方記事を書く（価格直書き・虚偽の体験談は禁止） |
| compliance-checker | アソシエイト規約・景表法・薬機法の監査 |
| sns-promoter | X投稿案を作り、SEOが効くまでの集客を担う |
| performance-analyst | レポートCSVから伸ばす／直す記事を判断 |

## 日々の使い方
```bash
python3 build.py && python3 -m http.server -d dist 8000   # ローカル確認
```
Claude Code で `/cycle` を週2回 → `git push` で自動公開。
