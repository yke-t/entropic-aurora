"""
Canva Generator - Canva Bulk Create用 20秒動画テキストCSV生成

Features:
- ADOPT_HIGH/ADOPT_MID論文のみ対象
- 4項目テキスト生成（hook, line1, line2, ending）
- 改行なしCSV出力
"""

import google.generativeai as genai
from typing import List, Dict, Any
import json
import csv
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Canva用テキスト生成プロンプト
CANVA_TEXT_PROMPT = """
あなたはYouTube Shorts動画のコピーライターです。
以下の論文情報から、20秒動画用の4行テキストを生成してください。

## 制約（厳守）
- 日本語のみ
- 疑問形は禁止
- 絵文字は禁止
- 改行禁止（各項目は1行で完結）
- 煽りすぎて事実と矛盾しないこと

## 生成内容

### hook（12〜14文字）
- 終了宣言 / 超越表現 / 断定調
- 例: 「医者が不要になる」「プログラマー終了」

### line1（18〜22文字）
- 人間・仕事・専門家との比較
- 例: 「AIが専門医を超えた診断精度を達成」

### line2（25〜30文字）
- 能力・結果・数値を含める
- 例: 「肺がん検出で人間の95%を上回る99%を記録」

### ending（8〜10文字）
- 不安・余韻・断定（CTA禁止）
- 例: 「もう戻れない」「止まらない」

## 論文情報
タイトル: {title}
アブストラクト: {abstract}
煽りタイトル案: {best_title}
Shortsスコア: {shorts_score}

## 出力形式（JSON）
{{
    "hook": "<12〜14文字>",
    "line1": "<18〜22文字>",
    "line2": "<25〜30文字>",
    "ending": "<8〜10文字>"
}}
"""


class CanvaGenerator:
    """Canva Bulk Create用CSV生成"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Args:
            api_key: Gemini APIキー
            model: 使用モデル名
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_text(
        self,
        paper: Dict[str, Any],
        shorts_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        単一論文からCanva用テキスト生成
        
        Args:
            paper: 論文メタデータ
            shorts_score: Shortsスコアリング結果
        
        Returns:
            4項目テキスト
        """
        clickbait = shorts_score.get("clickbait_potential", {})
        best_title = clickbait.get("best_title", "") if isinstance(clickbait, dict) else ""
        
        prompt = CANVA_TEXT_PROMPT.format(
            title=paper.get("title", ""),
            abstract=paper.get("abstract", "")[:1500],
            best_title=best_title,
            shorts_score=shorts_score.get("total_score", 0)
        )
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # JSON部分を抽出
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            if start != -1 and end > start:
                result = json.loads(result_text[start:end])
                
                # 改行を除去（安全策）
                for key in ["hook", "line1", "line2", "ending"]:
                    if key in result:
                        result[key] = result[key].replace("\n", "").replace("\r", "")
                
                result["paper_id"] = paper.get("id")
                return result
            else:
                self.logger.warning(f"Invalid response format for: {paper.get('id')}")
                return {"paper_id": paper.get("id"), "error": "Invalid format"}
                
        except Exception as e:
            self.logger.error(f"Canva text generation error for {paper.get('id')}: {e}")
            return {"paper_id": paper.get("id"), "error": str(e)}
    
    def generate_texts(
        self,
        papers: List[Dict[str, Any]],
        shorts_scores: List[Dict[str, Any]],
        delay_seconds: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        複数論文からCanva用テキスト生成
        
        Args:
            papers: 論文メタデータのリスト
            shorts_scores: Shortsスコアリング結果のリスト
            delay_seconds: リクエスト間の待機秒数
        
        Returns:
            テキストデータのリスト
        """
        # paper_id -> shorts_scoreマッピング
        score_map = {s.get("paper_id"): s for s in shorts_scores}
        
        results = []
        
        for i, paper in enumerate(papers):
            paper_id = paper.get("id")
            shorts_score = score_map.get(paper_id, {})
            
            self.logger.info(f"Canva text {i+1}/{len(papers)}: {paper_id}")
            result = self.generate_text(paper, shorts_score)
            results.append(result)
            
            if i < len(papers) - 1:
                time.sleep(delay_seconds)
        
        return results
    
    def save_csv(
        self,
        texts: List[Dict[str, Any]],
        output_path: Path
    ) -> None:
        """
        Canva Bulk Create用CSV保存
        
        Args:
            texts: テキストデータのリスト
            output_path: 出力先パス
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # エラーなしのみ
        valid_texts = [t for t in texts if "error" not in t]
        
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["hook", "line1", "line2", "ending"],
                extrasaction="ignore"
            )
            writer.writeheader()
            for row in valid_texts:
                writer.writerow(row)
        
        self.logger.info(f"Canva CSV保存: {output_path} ({len(valid_texts)}件)")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set in .env")
        exit(1)
    
    generator = CanvaGenerator(api_key)
    
    test_paper = {
        "id": "test001",
        "title": "GPT-4 Outperforms Human Doctors in Medical Diagnosis",
        "abstract": "We show that GPT-4 achieves 95% accuracy in diagnosing diseases from medical images, surpassing expert radiologists who achieved 87% accuracy."
    }
    
    test_score = {
        "paper_id": "test001",
        "total_score": 85,
        "verdict": "ADOPT_HIGH",
        "clickbait_potential": {
            "best_title": "医者が不要になる日が来た"
        }
    }
    
    result = generator.generate_text(test_paper, test_score)
    print(json.dumps(result, ensure_ascii=False, indent=2))
