# arXiv論文日次収集＆翻訳システム（entropic-aurora）

arXivから12カテゴリ（AI/ML/物理）の新着論文を毎日自動取得し、Gemini バッチAPIで日本語翻訳＆要約を行い、Google Driveに保存するZero-Toilシステム。

## 機能

### 基盤機能
- arXiv論文取得・PDFダウンロード
- AIスクリーニング（研究評価）
- 翻訳・要約
- Google Drive同期

### YouTube Shorts生成
- Shorts適性スコアリング（6軸100点満点）
- 30秒台本生成（6ブロック構成）
- VOICEVOX音声生成
- **MoviePy動画レンダリング**（1080x1920, 9:16縦型）

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

### 追加セットアップ（動画生成用）

```powershell
# ImageMagick（テキスト描画用）
winget install ImageMagick.ImageMagick

# FFmpeg（音声・動画処理用）
winget install Gyan.FFmpeg

# VOICEVOX Engine（音声合成用）
# https://voicevox.hiroshiba.jp/ からダウンロード
```

## 使い方

```powershell
# 基本パイプライン
python main.py

# Shorts動画E2Eテスト
python test_moviepy_e2e.py
```

## 対象カテゴリ

### AI・機械学習系（7カテゴリ）
`cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`, `cs.NE`, `cs.RO`, `stat.ML`

### 物理系（5カテゴリ）
`quant-ph`, `cond-mat.dis-nn`, `hep-th`, `gr-qc`, `physics.comp-ph`

## コスト

実質月額: 約$16（Google AI Pro $20 - クレジット$10 + API $6.3）
