"""
AI Screener - Gemini APIで論文の有益度をスクリーニング

Features:
- バッチAPI対応（50%オフ）
- 有益度スコアリング（1-10）
- 上位N件の選定
"""

import google.generativeai as genai
from typing import List, Dict, Any
import json
import logging
import time

logger = logging.getLogger(__name__)

# スクリーニング用プロンプトテンプレート
SCREENING_PROMPT = """
あなたは学術論文の評価エキスパートです。
以下の論文のタイトルとアブストラクトを評価し、「有益度スコア」を1-10で採点してください。

## 評価基準
1. **実用性** (1-10): 実際のアプリケーションに活用できるか
2. **新規性** (1-10): 既存研究と比べて新しい知見があるか
3. **影響度** (1-10): 分野に大きなインパクトを与えそうか
4. **わかりやすさ** (1-10): 一般視聴者に説明可能か（YouTubeショート向け）

## 論文情報
タイトル: {title}
カテゴリ: {categories}
アブストラクト: {abstract}

## 出力形式（JSON）
{{
    "usefulness": <1-10>,
    "novelty": <1-10>,
    "impact": <1-10>,
    "explainability": <1-10>,
    "total_score": <1-10の平均>,
    "one_line_summary": "<日本語で1行要約>",
    "reason": "<スコアの理由を日本語で1-2文>"
}}
"""


class Screener:
    """論文スクリーニングクラス"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Args:
            api_key: Gemini APIキー
            model: 使用モデル名
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def screen_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一論文をスクリーニング
        
        Args:
            paper: 論文メタデータ
        
        Returns:
            スクリーニング結果
        """
        prompt = SCREENING_PROMPT.format(
            title=paper.get("title", ""),
            categories=", ".join(paper.get("categories", [])),
            abstract=paper.get("abstract", "")[:2000]  # トークン節約
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
                return result
            else:
                self.logger.warning(f"Invalid response format for: {paper.get('id')}")
                return {"paper_id": paper.get("id"), "error": "Invalid format"}
                
        except Exception as e:
            self.logger.error(f"Screening error for {paper.get('id')}: {e}")
            return {"paper_id": paper.get("id"), "error": str(e)}
    
    def screen_papers(
        self,
        papers: List[Dict[str, Any]],
        delay_seconds: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        複数論文をスクリーニング
        
        Args:
            papers: 論文メタデータのリスト
            delay_seconds: リクエスト間の待機秒数
        
        Returns:
            スクリーニング結果のリスト
        """
        results = []
        
        for i, paper in enumerate(papers):
            self.logger.info(f"Screening {i+1}/{len(papers)}: {paper.get('id')}")
            result = self.screen_paper(paper)
            results.append(result)
            
            if i < len(papers) - 1:
                time.sleep(delay_seconds)
        
        return results
    
    def select_top_papers(
        self,
        screening_results: List[Dict[str, Any]],
        papers: List[Dict[str, Any]],
        top_n: int = 100,
        min_score: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        スコア上位の論文を選定
        
        Args:
            screening_results: スクリーニング結果のリスト
            papers: 元の論文メタデータのリスト
            top_n: 選定する上位件数
            min_score: 最低スコア閾値
        
        Returns:
            選定された論文のリスト（スクリーニング結果付き）
        """
        # paper_id -> paper のマッピング
        paper_map = {p.get("id"): p for p in papers}
        
        # エラーなし & 閾値以上のみ
        valid_results = [
            r for r in screening_results
            if "error" not in r and r.get("total_score", 0) >= min_score
        ]
        
        # スコア降順でソート
        sorted_results = sorted(
            valid_results,
            key=lambda x: x.get("total_score", 0),
            reverse=True
        )[:top_n]
        
        # 元の論文情報と結合
        selected = []
        for result in sorted_results:
            paper_id = result.get("paper_id")
            if paper_id in paper_map:
                combined = {**paper_map[paper_id], "screening": result}
                selected.append(combined)
        
        self.logger.info(f"Selected {len(selected)} papers (top {top_n}, min_score={min_score})")
        return selected


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not set in .env")
        exit(1)
    
    screener = Screener(api_key)
    
    test_paper = {
        "id": "test001",
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
        "categories": ["cs.CL", "cs.LG"]
    }
    
    result = screener.screen_paper(test_paper)
    print(json.dumps(result, ensure_ascii=False, indent=2))
