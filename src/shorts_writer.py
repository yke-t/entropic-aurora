"""
Shorts Writer - YouTube Shorts 30秒台本生成

Features:
- 6ブロック構成（フック→問題提起→解決策→証拠→影響→余韻）
- 動画タイトル・サムネイルテキスト生成
- ハッシュタグ生成
"""

import google.generativeai as genai
from typing import List, Dict, Any
import json
import logging
import time

logger = logging.getLogger(__name__)

# Shorts台本生成プロンプト
SHORTS_SCRIPT_PROMPT = """
あなたはYouTube Shortsの人気クリエイターです。
以下の論文を30秒のShorts台本に変換してください。

## 構成ルール（6ブロック・各5秒）

### ブロック1: フック（0-5秒）
- 視聴者が「え？」と思う一言
- 例: 「もう医者いらないかも」「プログラマー、終わりです」

### ブロック2: 問題提起（5-10秒）
- 現状の課題や常識を提示
- 例: 「今までCTスキャンの読影は医師が何時間もかけてた」

### ブロック3: 解決策（10-15秒）
- このAI/技術が何をするか
- 例: 「このAIは3秒で診断、しかも精度95%」

### ブロック4: 証拠（15-20秒）
- 数字やデータで裏付け
- 例: 「専門医と比較して、なんと上回る正答率」

### ブロック5: 影響（20-25秒）
- これが広まるとどうなるか
- 例: 「途上国の医療格差が一気に解消されるかも」

### ブロック6: 余韻（25-30秒）
- 断定や不安を残す一言（フォロー誘導はしない）
- 例: 「これ、もう止まらない」「気づいた時には遅いかも」

## 論文情報
タイトル: {title}
アブストラクト: {abstract}
Shortsスコア: {shorts_score}点
煽りタイトル: {best_title}

## 出力形式（JSON）
{{
    "video_title": "<YouTube動画タイトル（40字以内）>",
    "thumbnail_text": "<サムネイル用テキスト（10字以内）>",
    "blocks": [
        {{"block": 1, "type": "フック", "script": "台本", "visual_note": "映像メモ"}},
        {{"block": 2, "type": "問題提起", "script": "台本", "visual_note": "映像メモ"}},
        {{"block": 3, "type": "解決策", "script": "台本", "visual_note": "映像メモ"}},
        {{"block": 4, "type": "証拠", "script": "台本", "visual_note": "映像メモ"}},
        {{"block": 5, "type": "影響", "script": "台本", "visual_note": "映像メモ"}},
        {{"block": 6, "type": "余韻", "script": "台本", "visual_note": "映像メモ"}}
    ],
    "full_script": "<全文ナレーション>",
    "hashtags": ["#AI", "#論文解説", "#テック"]
}}
"""


class ShortsWriter:
    """YouTube Shorts 30秒台本生成"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Args:
            api_key: Gemini APIキー
            model: 使用モデル名
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_script(
        self,
        paper: Dict[str, Any],
        shorts_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        単一論文から台本生成
        
        Args:
            paper: 論文メタデータ
            shorts_score: Shortsスコアリング結果
        
        Returns:
            台本データ
        """
        # best_titleを取得（clickbait_potentialから）
        clickbait = shorts_score.get("clickbait_potential", {})
        best_title = clickbait.get("best_title", paper.get("title", ""))
        
        prompt = SHORTS_SCRIPT_PROMPT.format(
            title=paper.get("title", ""),
            abstract=paper.get("abstract", "")[:2000],
            shorts_score=shorts_score.get("total_score", 0),
            best_title=best_title
        )
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text
            
            # JSON部分を抽出
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            if start != -1 and end > start:
                result = json.loads(result_text[start:end])
                result["paper_id"] = paper.get("id")
                result["shorts_score"] = shorts_score.get("total_score", 0)
                result["verdict"] = shorts_score.get("verdict", "")
                result["best_title"] = best_title
                return result
            else:
                self.logger.warning(f"Invalid response format for: {paper.get('id')}")
                return {"paper_id": paper.get("id"), "error": "Invalid format"}
                
        except Exception as e:
            self.logger.error(f"Script generation error for {paper.get('id')}: {e}")
            return {"paper_id": paper.get("id"), "error": str(e)}
    
    def generate_scripts(
        self,
        papers: List[Dict[str, Any]],
        shorts_scores: List[Dict[str, Any]],
        delay_seconds: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        複数論文から台本生成
        
        Args:
            papers: 論文メタデータのリスト
            shorts_scores: Shortsスコアリング結果のリスト
            delay_seconds: リクエスト間の待機秒数
        
        Returns:
            台本データのリスト
        """
        # paper_id -> shorts_scoreのマッピング
        score_map = {s.get("paper_id"): s for s in shorts_scores}
        
        results = []
        
        for i, paper in enumerate(papers):
            paper_id = paper.get("id")
            shorts_score = score_map.get(paper_id, {})
            
            self.logger.info(f"Generating script {i+1}/{len(papers)}: {paper_id}")
            result = self.generate_script(paper, shorts_score)
            results.append(result)
            
            if i < len(papers) - 1:
                time.sleep(delay_seconds)
        
        return results


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set in .env")
        exit(1)
    
    writer = ShortsWriter(api_key)
    
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
    
    result = writer.generate_script(test_paper, test_score)
    print(json.dumps(result, ensure_ascii=False, indent=2))
