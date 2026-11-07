---
description: 週次の収益化サイクルを1回まわす（キーワード→記事2本→規約チェック→SNS案→ビルド）
---
affiliate-director エージェントとして、docs/PLAN.md の「週次サイクル」を1回実行してください。
1. data/report.csv があれば performance-analyst で分析
2. keyword-researcher で次のキーワード2件を選定
3. article-writer で記事2本を執筆
4. compliance-checker で監査し `python3 check.py` の ERROR を0に
5. sns-promoter で新記事の投稿案を sns/queue.md に追加
6. `python3 build.py` でビルド
7. docs/LOG.md に記録し、ユーザーがやるべき作業を最後にまとめる
$ARGUMENTS
