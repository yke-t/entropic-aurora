# 引き継ぎプロンプト（Handover Prompt）

以下をコピーして新しいManagerセッションに貼り付けてください。

---

## 🚀 引き継ぎプロンプト

```
# プロジェクト: arXiv論文日次収集＆翻訳システム（entropic-aurora）

## 概要
arXivから12カテゴリ（AI/ML/物理）の新着論文を毎日自動取得し、Gemini バッチAPIで日本語翻訳＆要約を行い、Google Driveに保存するZero-Toilシステム。

## プロジェクトパス
C:\Users\yke\Projects\entropic-aurora\

## 設計ドキュメント
- docs/IMPLEMENTATION_PLAN.md: 実装計画（承認済み）
- docs/TASK.md: タスクリスト

## 主要な設計決定（確定済み）
1. **3段階パイプライン**: メタデータ+PDF全件取得（目安300本/日） → AIスクリーニング → 翻訳(上位100本)
2. **Gemini バッチAPI**: 50%オフで非同期処理
3. **全データ保存**: メタデータ/スクリーニング結果/翻訳/PDF全件をGoogle Driveに保存
4. **12カテゴリ**: cs.AI, cs.LG, cs.CL, cs.CV, cs.NE, cs.RO, stat.ML, quant-ph, cond-mat.dis-nn, hep-th, gr-qc, physics.comp-ph

## 現在の進捗
- [x] 実装計画作成・承認
- [ ] Phase 1: プロジェクト基盤構築 ← ここから開始

## 次のアクション
Phase 1から実装を開始してください：
1. プロジェクトディレクトリ作成
2. Python仮想環境セットアップ
3. requirements.txt作成
4. .env.example作成
5. config.yaml作成

## コスト
- 実質月額: 約$16（Google AI Pro $20 - クレジット$10 + API $6.3）

## 用途
- YouTubeショート素材生成
- NotebookLMでポッドキャスト化
```

---

## 📋 チェックリスト

新しいManagerに引き継ぐ前に確認：

- [x] 実装計画が承認されている
- [x] タスクリストが最新
- [x] プロジェクトパスが明確
- [x] 設計決定が文書化されている
