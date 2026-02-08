# arXiv論文日次収集＆翻訳システム - タスクリスト

## Phase 1-6: 基盤機能 ✅
- [x] arXiv論文取得・PDFダウンロード
- [x] AIスクリーニング（研究評価）
- [x] 翻訳・要約
- [x] Google Drive同期
- [x] 統合パイプライン（main.py）

## Phase 7: YouTube Shorts機能 ✅
- [x] `src/shorts_scorer.py` - Shorts適性スコアリング（6軸100点満点）
- [x] `src/shorts_writer.py` - 30秒台本生成（6ブロック）
- [x] 統合CSV（papers_*.csv）にShorts列追加
- [x] テスト実行完了（1025件→187件候補）

## Phase 8: Canva動画量産機能
- [x] `src/canva_generator.py` - Canva Bulk Create用CSV生成
- [x] `src/audio_script_generator.py` - 音声ナレーション台本生成
- [x] `src/shorts_video_generator.py` - 統合モジュール（CSV + VOICEVOX音声）
- [/] 全件生成（現在10件テスト済み、187件対応待ち）
- [ ] main.pyへの統合

## Phase 9: MoviePy動画レンダリング ✅
- [x] `src/moviepy_renderer.py` - MoviePy動画レンダラー
- [x] shorts_video_generatorへの統合（`enable_moviepy=True`）
- [x] E2Eテスト完了

### 将来タスク
- [ ] 画像テンプレート対応（Canva無料版で背景作成→差替）
- [ ] Remotion移行検討（リッチアニメーション必要時）

---

## 📅 将来のリマインダー

### 2026-03-01: min_score見直し
- [ ] `min_score: 65` で1か月運用後、実データを分析
  - ADOPT_HIGH の平均再生数
  - ADOPT_MID の"事故バズ"率
  - 閾値を70に上げるか維持か判断
