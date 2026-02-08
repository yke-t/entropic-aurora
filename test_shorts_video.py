"""
Shorts動画生成テスト

既存データを使用して：
1. Canva用CSV生成（5列: hook, line1, line2, ending, audio_script）
2. VOICEVOX音声ファイル生成（video_01.wav, ...）
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

# テスト用：最大生成数
MAX_GENERATE = 10  # 全件なら None


def main():
    print("=== Shorts動画生成テスト ===\n")
    
    # 1. メタデータ読み込み
    print("Step 1: メタデータ読み込み")
    with open(BASE_DIR / "metadata" / f"metadata_{DATE_STR}.json", "r", encoding="utf-8") as f:
        papers = json.load(f)
    print(f"  論文数: {len(papers)}")
    
    # 2. Shortsスコア読み込み
    print("Step 2: Shortsスコア読み込み")
    with open(BASE_DIR / "shorts" / f"shorts_scores_{DATE_STR}.json", "r", encoding="utf-8") as f:
        shorts_scores = json.load(f)
    
    candidates = [s for s in shorts_scores if s.get("verdict") in ("ADOPT_HIGH", "ADOPT_MID")]
    print(f"  ADOPT候補: {len(candidates)}件")
    
    # 3. 統合モジュールで処理
    from src.shorts_video_generator import ShortsVideoGenerator
    
    generator = ShortsVideoGenerator(GEMINI_API_KEY)
    
    # 件数制限
    if MAX_GENERATE:
        candidates_sorted = sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)
        limited_candidates = candidates_sorted[:MAX_GENERATE]
        limited_paper_ids = {c.get("paper_id") for c in limited_candidates}
        limited_papers = [p for p in papers if p.get("id") in limited_paper_ids]
        
        print(f"Step 3: 処理開始 ({len(limited_candidates)}件)")
        result = generator.process_papers(
            limited_papers,
            limited_candidates,
            BASE_DIR / "shorts",
            DATE_STR,
            delay_seconds=0.5
        )
    else:
        print(f"Step 3: 処理開始 (全{len(candidates)}件)")
        result = generator.process_papers(
            papers,
            shorts_scores,
            BASE_DIR / "shorts",
            DATE_STR,
            delay_seconds=0.5
        )
    
    print(f"\n=== 完了 ===")
    print(f"  CSV生成: {result.get('total_processed')}件")
    print(f"  音声生成: {result.get('audio_generated')}件")
    print(f"  出力先: {result.get('csv_path')}")
    print(f"  音声: {result.get('audio_dir')}")


if __name__ == "__main__":
    main()
