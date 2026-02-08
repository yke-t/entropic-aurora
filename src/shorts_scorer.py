"""
Shorts Scorer - YouTube Shorts適性スコアリング

Features:
- 6軸評価（clickbait, life_impact, human, numbers, use_case, implementation）
- 100点満点スコアリング
- 3段階verdict判定（ADOPT_HIGH/ADOPT_MID/SKIP）
"""

import google.generativeai as genai
from typing import List, Dict, Any
import json
import logging
import time

logger = logging.getLogger(__name__)

# Shorts適性スコアリングプロンプト
SHORTS_SCORING_PROMPT = """
あなたはYouTube Shortsの編集者です。
以下の論文が「30秒Shorts」として再生されやすいか評価してください。

## 評価基準（100点満点）

### 1. 煽りタイトル変換可能性 (最大25点) 【最重要】
まず、以下の形式でタイトルを3案作成してください：
- 「◯◯が終わる」形式
- 「人間不要」「もう◯◯しなくていい」形式
- その他インパクト形式

その上で評価：
- 嘘にならず強いタイトルが作れる: 25点
- 作れるが少し誇張が必要: 15点
- 正直に作ると弱い: 5点
- 煽れない: 0点

### 2. 人生・仕事への影響度 (最大20点)
この研究が普及した場合、一般人の仕事・判断・生活に直接影響があるか？
- 仕事がなくなる/大きく変わる: 20点
- 生活に影響: 12点
- 専門家のみ影響: 5点
- 影響なし: 0点

### 3. 人間・専門家との比較 (最大20点)
"human", "expert", "doctor", "professional" との比較実験があるか
- 人間を上回る結果あり: 20点
- 比較実験あり: 12点
- 言及のみ: 5点
- なし: 0点

### 4. 数字インパクト (最大15点)
精度90%+、速度10倍+、コスト50%減など
- 衝撃的な数字あり: 15点
- 良い数字あり: 8点
- 普通/なし: 0点

### 5. 用途の具体性 (最大10点)
医療、法律、教育、プログラミングなど明確な分野
- 生活に近い分野: 10点
- 専門分野: 5点
- 抽象的: 0点

### 6. 実装の現実性 (最大10点)
- 今すぐ使える: 10点
- 近い将来: 5点
- 遠い/研究段階: 0点

## 論文情報
タイトル: {title}
アブストラクト: {abstract}

## 出力形式（JSON）
{{
    "clickbait_potential": {{
        "score": <0-25>,
        "generated_titles": ["タイトル案1", "タイトル案2", "タイトル案3"],
        "best_title": "<最も使えるタイトル>",
        "is_honest": true
    }},
    "life_impact": {{"score": <0-20>, "affected_jobs": ["職種1"], "reason": "理由"}},
    "human_comparison": {{"score": <0-20>, "found_keywords": [], "evidence": "根拠"}},
    "strong_numbers": {{"score": <0-15>, "numbers": [], "evidence": "根拠"}},
    "use_case": {{"score": <0-10>, "domains": []}},
    "implementation": {{"score": <0-10>, "availability": "状況"}},
    "total_score": <合計点>,
    "one_line_hook": "<Shorts冒頭の一言（15字以内）>"
}}
"""


def judge_verdict(total_score: int) -> str:
    """
    スコアからverdict判定
    
    Args:
        total_score: 合計スコア（0-100）
    
    Returns:
        ADOPT_HIGH (80+) / ADOPT_MID (65-79) / SKIP (<65)
    """
    if total_score >= 80:
        return "ADOPT_HIGH"
    elif total_score >= 65:
        return "ADOPT_MID"
    else:
        return "SKIP"


class ShortsScorer:
    """YouTube Shorts適性スコアリング"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Args:
            api_key: Gemini APIキー
            model: 使用モデル名
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def score_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一論文をスコアリング
        
        Args:
            paper: 論文メタデータ
        
        Returns:
            スコアリング結果
        """
        prompt = SHORTS_SCORING_PROMPT.format(
            title=paper.get("title", ""),
            abstract=paper.get("abstract", "")[:2500]
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
                
                # verdict判定（Python側で実施）
                total_score = result.get("total_score", 0)
                result["verdict"] = judge_verdict(total_score)
                
                return result
            else:
                self.logger.warning(f"Invalid response format for: {paper.get('id')}")
                return {"paper_id": paper.get("id"), "error": "Invalid format", "verdict": "SKIP"}
                
        except Exception as e:
            self.logger.error(f"Scoring error for {paper.get('id')}: {e}")
            return {"paper_id": paper.get("id"), "error": str(e), "verdict": "SKIP"}
    
    def score_papers(
        self,
        papers: List[Dict[str, Any]],
        delay_seconds: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        複数論文をスコアリング
        
        Args:
            papers: 論文メタデータのリスト
            delay_seconds: リクエスト間の待機秒数
        
        Returns:
            スコアリング結果のリスト
        """
        results = []
        
        for i, paper in enumerate(papers):
            self.logger.info(f"Shorts scoring {i+1}/{len(papers)}: {paper.get('id')}")
            result = self.score_paper(paper)
            results.append(result)
            
            if i < len(papers) - 1:
                time.sleep(delay_seconds)
        
        return results
    
    def filter_by_verdict(
        self,
        scores: List[Dict[str, Any]],
        include_mid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        verdict判定で動画化対象のみ抽出
        
        Args:
            scores: スコアリング結果のリスト
            include_mid: ADOPT_MIDも含めるか
        
        Returns:
            ADOPT_HIGH + ADOPT_MID（オプション）のリスト
        """
        if include_mid:
            valid_verdicts = ("ADOPT_HIGH", "ADOPT_MID")
        else:
            valid_verdicts = ("ADOPT_HIGH",)
        
        return [s for s in scores if s.get("verdict") in valid_verdicts]


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set in .env")
        exit(1)
    
    scorer = ShortsScorer(api_key)
    
    test_paper = {
        "id": "test001",
        "title": "GPT-4 Outperforms Human Doctors in Medical Diagnosis",
        "abstract": "We show that GPT-4 achieves 95% accuracy in diagnosing diseases from medical images, surpassing expert radiologists who achieved 87% accuracy. The model is freely available as an API."
    }
    
    result = scorer.score_paper(test_paper)
    print(json.dumps(result, ensure_ascii=False, indent=2))
