# arXiv論文日次収集＆翻訳システム - タスクリスト

## Phase 1: プロジェクト基盤構築
- [ ] プロジェクトディレクトリ作成
- [ ] Python仮想環境セットアップ
- [ ] 依存ライブラリインストール
- [ ] `.env` ファイル作成（API Keys）
- [ ] `config.yaml` 作成（カテゴリ、スクリーニング基準）

## Phase 2: arXiv取得 + PDF全件ダウンロード
- [ ] `src/arxiv_client.py` 実装
  - [ ] 12カテゴリの新着論文取得（全件（目安300本/日））
  - [ ] 日付フィルタリング（前日分）
  - [ ] 重複排除
- [ ] `src/pdf_downloader.py` 実装
  - [ ] PDF全件ダウンロード（300本/日）
  - [ ] リトライ処理

## Phase 3: AIスクリーニング機能
- [ ] `src/screener.py` 実装
  - [ ] Gemini バッチAPI接続
  - [ ] 有益度スコアリング（1-10）
  - [ ] 上位100本の選定ロジック
- [ ] スクリーニングプロンプト作成

## Phase 4: Gemini翻訳＆要約機能（バッチAPI）
- [ ] `src/translator.py` 実装
  - [ ] Gemini バッチAPI接続（50%オフ）
  - [ ] タイトル＋Abstract翻訳
  - [ ] 3行要約生成（YouTubeショート用）
  - [ ] キーワード抽出

## Phase 5: Google Drive連携
- [ ] Google Cloud Console設定
- [ ] `src/drive_uploader.py` 実装
  - [ ] 日付・カテゴリ別フォルダ自動作成
  - [ ] 全データアップロード（PDF全件＋翻訳＋メタデータ）

## Phase 6: 統合＆自動化
- [ ] `main.py` 実装（3段階パイプライン）
- [ ] エラーハンドリング＆リトライ
- [ ] ロギング設定
- [ ] Windows Task Scheduler設定（深夜バッチ）
- [ ] 動作検証
- [ ] README.md 作成
