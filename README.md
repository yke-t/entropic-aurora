# arXiv論文日次収集＆翻訳システム（entropic-aurora）

arXivから12カテゴリ（AI/ML/物理）の新着論文を毎日自動取得し、Gemini バッチAPIで日本語翻訳＆要約を行い、Google Driveに保存するZero-Toilシステム。

## セットアップ

```powershell
# 仮想環境作成・有効化
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env を編集してAPIキーを設定
```

## 使い方

```powershell
python main.py
```

## 対象カテゴリ

### AI・機械学習系（7カテゴリ）
`cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`, `cs.NE`, `cs.RO`, `stat.ML`

### 物理系（5カテゴリ）
`quant-ph`, `cond-mat.dis-nn`, `hep-th`, `gr-qc`, `physics.comp-ph`

## コスト

実質月額: 約$16（Google AI Pro $20 - クレジット$10 + API $6.3）
