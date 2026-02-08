"""
Shorts機能テストスクリプト

既存の2026/1/31メタデータ（1025件）に対して：
1. 昨日の結果をバックアップ
2. 全件Shortsスコアリング
3. ADOPT候補を翻訳
4. 台本生成
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 設定
BASE_DIR = Path("G:/マイドライブ/ArXiv/2026-01")
DATE_STR = "20260131"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def backup_existing():
    """既存結果をバックアップ"""
    backup_dir = BASE_DIR / "backup_20260131"
    backup_dir.mkdir(exist_ok=True)
    
    # バックアップ対象
    files_to_backup = [
        ("translated", f"translated_{DATE_STR}.json"),
        ("translated", f"translated_{DATE_STR}.csv"),
        ("screening", f"screening_{DATE_STR}.json"),
        ("metadata", f"papers_{DATE_STR}.csv"),
    ]
    
    for folder, filename in files_to_backup:
        src = BASE_DIR / folder / filename
        if src.exists():
            dst = backup_dir / filename
            shutil.copy(src, dst)
            print(f"バックアップ: {filename}")
    
    print(f"バックアップ完了: {backup_dir}")
    return backup_dir


def load_metadata():
    """メタデータ読み込み"""
    metadata_path = BASE_DIR / "metadata" / f"metadata_{DATE_STR}.json"
    with open(metadata_path, "r", encoding="utf-8") as f:
        papers = json.load(f)
    print(f"メタデータ読み込み: {len(papers)}件")
    return papers


def run_shorts_scoring(papers, max_papers=None):
    """Shortsスコアリング実行"""
    from src.shorts_scorer import ShortsScorer
    
    scorer = ShortsScorer(GEMINI_API_KEY, "gemini-2.5-flash")
    
    # テスト用に件数制限可能
    target_papers = papers[:max_papers] if max_papers else papers
    
    print(f"Shortsスコアリング開始: {len(target_papers)}件")
    scores = scorer.score_papers(target_papers, delay_seconds=0.5)
    
    # 保存
    shorts_dir = BASE_DIR / "shorts"
    shorts_dir.mkdir(exist_ok=True)
    scores_path = shorts_dir / f"shorts_scores_{DATE_STR}.json"
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)
    
    print(f"Shortsスコア保存: {scores_path}")
    
    # 統計
    candidates = scorer.filter_by_verdict(scores, include_mid=True)
    high = [s for s in scores if s.get("verdict") == "ADOPT_HIGH"]
    mid = [s for s in scores if s.get("verdict") == "ADOPT_MID"]
    
    print(f"\n=== スコアリング結果 ===")
    print(f"ADOPT_HIGH: {len(high)}件")
    print(f"ADOPT_MID: {len(mid)}件")
    print(f"合計候補: {len(candidates)}件")
    
    return scores, candidates


def run_translation(papers, shorts_scores, max_translate=100):
    """Shorts候補を翻訳"""
    from src.translator import Translator
    from src.shorts_scorer import ShortsScorer
    
    # Shorts候補のみ抽出
    scorer = ShortsScorer(GEMINI_API_KEY)
    candidates = scorer.filter_by_verdict(shorts_scores, include_mid=True)
    
    # paper_id -> paperマッピング
    paper_map = {p.get("id"): p for p in papers}
    
    # 候補論文のみ取得（スコア順）
    candidates_sorted = sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)
    target_paper_ids = [c.get("paper_id") for c in candidates_sorted[:max_translate]]
    target_papers = [paper_map.get(pid) for pid in target_paper_ids if pid in paper_map]
    
    print(f"翻訳開始: {len(target_papers)}件（Shorts候補のみ）")
    
    translator = Translator(GEMINI_API_KEY, "gemini-2.5-flash")
    translated = translator.translate_papers(target_papers, delay_seconds=0.5)
    
    # 保存
    translated_dir = BASE_DIR / "translated"
    translated_path = translated_dir / f"translated_{DATE_STR}.json"
    with open(translated_path, "w", encoding="utf-8") as f:
        json.dump(translated, f, ensure_ascii=False, indent=2)
    
    print(f"翻訳保存: {translated_path}")
    return translated, target_papers


def run_script_generation(papers, shorts_scores, max_scripts=10):
    """台本生成"""
    from src.shorts_writer import ShortsWriter
    from src.shorts_scorer import ShortsScorer
    
    # Shorts候補（スコア順）
    scorer = ShortsScorer(GEMINI_API_KEY)
    candidates = scorer.filter_by_verdict(shorts_scores, include_mid=True)
    candidates_sorted = sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)
    
    # paper_id -> paperマッピング
    paper_map = {p.get("id"): p for p in papers}
    
    # 上位N件のみ
    top_candidates = candidates_sorted[:max_scripts]
    top_papers = [paper_map.get(c.get("paper_id")) for c in top_candidates]
    top_papers = [p for p in top_papers if p]  # None除去
    
    print(f"台本生成開始: {len(top_papers)}件")
    
    writer = ShortsWriter(GEMINI_API_KEY, "gemini-2.5-flash")
    scripts = writer.generate_scripts(top_papers, top_candidates, delay_seconds=0.5)
    
    # 保存
    shorts_dir = BASE_DIR / "shorts"
    scripts_path = shorts_dir / f"scripts_{DATE_STR}.json"
    with open(scripts_path, "w", encoding="utf-8") as f:
        json.dump(scripts, f, ensure_ascii=False, indent=2)
    
    print(f"台本保存: {scripts_path}")
    return scripts


def main():
    """メイン処理"""
    print("=== Shorts機能テスト開始 ===\n")
    
    # 1. バックアップ
    print("Step 1: バックアップ")
    backup_existing()
    print()
    
    # 2. メタデータ読み込み
    print("Step 2: メタデータ読み込み")
    papers = load_metadata()
    print()
    
    # 3. Shortsスコアリング（全件は時間がかかるので、テスト用に制限可能）
    # 全件: max_papers=None
    # テスト: max_papers=50
    print("Step 3: Shortsスコアリング")
    scores, candidates = run_shorts_scoring(papers, max_papers=None)  # 全件
    print()
    
    # 4. 翻訳（Shorts候補のみ）
    print("Step 4: 翻訳（Shorts候補のみ）")
    translated, target_papers = run_translation(papers, scores, max_translate=100)
    print()
    
    # 5. 台本生成（上位10件）
    print("Step 5: 台本生成")
    scripts = run_script_generation(papers, scores, max_scripts=10)
    print()
    
    print("=== テスト完了 ===")
    print(f"結果: {BASE_DIR}")


if __name__ == "__main__":
    main()
