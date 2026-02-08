"""
Canva CSV生成テスト

既存のShortsスコアデータから
ADOPT_HIGH/ADOPT_MID論文のみを対象に
Canva Bulk Create用CSVを生成
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 設定
BASE_DIR = Path("G:/マイドライブ/ArXiv/2026-01")
DATE_STR = "20260131"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def main():
    print("=== Canva CSV生成テスト ===\n")
    
    # 1. メタデータ読み込み
    print("Step 1: メタデータ読み込み")
    with open(BASE_DIR / "metadata" / f"metadata_{DATE_STR}.json", "r", encoding="utf-8") as f:
        papers = json.load(f)
    print(f"  論文数: {len(papers)}")
    
    # 2. Shortsスコア読み込み
    print("Step 2: Shortsスコア読み込み")
    with open(BASE_DIR / "shorts" / f"shorts_scores_{DATE_STR}.json", "r", encoding="utf-8") as f:
        shorts_scores = json.load(f)
    
    # ADOPT候補のみ抽出
    candidates = [s for s in shorts_scores if s.get("verdict") in ("ADOPT_HIGH", "ADOPT_MID")]
    candidates_sorted = sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)
    print(f"  ADOPT候補: {len(candidates_sorted)}件")
    
    # 3. Canvaテキスト生成
    from src.canva_generator import CanvaGenerator
    
    generator = CanvaGenerator(GEMINI_API_KEY)
    
    # paper_id -> paperマッピング
    paper_map = {p.get("id"): p for p in papers}
    
    # 上位件数（テスト用に制限可能）
    max_generate = 50  # 全件なら len(candidates_sorted)
    target_candidates = candidates_sorted[:max_generate]
    target_papers = [paper_map.get(c.get("paper_id")) for c in target_candidates]
    target_papers = [p for p in target_papers if p]  # None除去
    
    print(f"Step 3: Canvaテキスト生成 ({len(target_papers)}件)")
    texts = generator.generate_texts(target_papers, target_candidates, delay_seconds=0.5)
    
    # 4. CSV保存
    print("Step 4: CSV保存")
    csv_path = BASE_DIR / "shorts" / f"canva_{DATE_STR}.csv"
    generator.save_csv(texts, csv_path)
    
    # 5. JSON保存（デバッグ用）
    json_path = BASE_DIR / "shorts" / f"canva_{DATE_STR}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== 完了 ===")
    print(f"  CSV: {csv_path}")
    print(f"  JSON: {json_path}")


if __name__ == "__main__":
    main()
