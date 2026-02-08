"""
MoviePy統合 E2Eテスト

VOICEVOX Engineが起動していない場合は音声・動画生成をスキップ
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUT_DIR = Path("output/test_e2e")

def main():
    print("=== MoviePy E2E Test ===\n")
    
    # テストデータ
    test_papers = [{
        "id": "test_e2e_001",
        "title": "GPT-5 Achieves Human-Level Reasoning in Scientific Discovery",
        "abstract": "We present GPT-5, a large language model that demonstrates human-level performance in scientific reasoning tasks. In blind evaluations, GPT-5 outperformed PhD-level scientists in hypothesis generation and experimental design, achieving 94% accuracy compared to 78% for human experts."
    }]
    
    test_scores = [{
        "paper_id": "test_e2e_001",
        "total_score": 92,
        "verdict": "ADOPT_HIGH",
        "clickbait_potential": {"best_title": "科学者が失業する日"}
    }]
    
    # ShortsVideoGenerator
    from src.shorts_video_generator import ShortsVideoGenerator, MOVIEPY_AVAILABLE
    
    print(f"MoviePy available: {MOVIEPY_AVAILABLE}")
    
    generator = ShortsVideoGenerator(
        gemini_api_key=GEMINI_API_KEY,
        voicevox_url="http://localhost:50021",
        speaker_id=2
    )
    
    # VOICEVOX起動確認
    import requests
    try:
        resp = requests.get("http://localhost:50021/version", timeout=2)
        voicevox_ok = resp.status_code == 200
        print(f"VOICEVOX: OK (version {resp.text})")
    except:
        voicevox_ok = False
        print("VOICEVOX: Not running (audio/video skipped)")
    
    # 処理実行
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    result = generator.process_papers(
        papers=test_papers,
        shorts_scores=test_scores,
        output_dir=OUTPUT_DIR,
        date_str="test",
        enable_moviepy=MOVIEPY_AVAILABLE and voicevox_ok
    )
    
    print("\n=== Result ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 生成ファイル確認
    print("\n=== Generated Files ===")
    for path in OUTPUT_DIR.rglob("*"):
        if path.is_file():
            print(f"  {path.relative_to(OUTPUT_DIR)} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
