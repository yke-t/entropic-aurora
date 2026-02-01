"""
Translator - Gemini バッチAPIで論文を日本語翻訳＆要約

Features:
- タイトル＋Abstract翻訳
- 3行要約生成（YouTubeショート用）
- キーワード抽出
- バッチAPI対応（50%オフ）
"""

import google.generativeai as genai
from typing import List, Dict, Any
import json
import logging
import time

logger = logging.getLogger(__name__)

# 翻訳・要約用プロンプトテンプレート
TRANSLATION_PROMPT = """
あなたは学術論文の翻訳・要約エキスパートです。
以下の論文のタイトルとアブストラクトを日本語に翻訳し、わかりやすく要約してください。

## 論文情報
タイトル: {title}
カテゴリ: {categories}
アブストラクト: {abstract}

## 出力形式（JSON）
{{
    "title_ja": "<タイトルの日本語訳>",
    "abstract_ja": "<アブストラクトの日本語訳（200字程度に要約）>",
    "summary_3lines": [
        "<1行目: この研究は何か>",
        "<2行目: 何が新しいか>",
        "<3行目: 何に役立つか>"
    ],
    "keywords": ["<キーワード1>", "<キーワード2>", "<キーワード3>"],
    "youtube_hook": "<YouTubeショート用の興味を引く一言（20字以内）>"
}}
"""


class Translator:
    """論文翻訳クラス"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Args:
            api_key: Gemini APIキー
            model: 使用モデル名
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def translate_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一論文を翻訳・要約
        
        Args:
            paper: 論文メタデータ
        
        Returns:
            翻訳結果
        """
        prompt = TRANSLATION_PROMPT.format(
            title=paper.get("title", ""),
            categories=", ".join(paper.get("categories", [])),
            abstract=paper.get("abstract", "")[:3000]
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
                result["original_title"] = paper.get("title")
                return result
            else:
                self.logger.warning(f"Invalid response format for: {paper.get('id')}")
                return {"paper_id": paper.get("id"), "error": "Invalid format"}
                
        except Exception as e:
            self.logger.error(f"Translation error for {paper.get('id')}: {e}")
            return {"paper_id": paper.get("id"), "error": str(e)}
    
    def translate_papers(
        self,
        papers: List[Dict[str, Any]],
        delay_seconds: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        複数論文を翻訳・要約
        
        Args:
            papers: 論文メタデータのリスト
            delay_seconds: リクエスト間の待機秒数
        
        Returns:
            翻訳結果のリスト
        """
        results = []
        
        for i, paper in enumerate(papers):
            self.logger.info(f"Translating {i+1}/{len(papers)}: {paper.get('id')}")
            result = self.translate_paper(paper)
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
    
    translator = Translator(api_key)
    
    test_paper = {
        "id": "test001",
        "title": "Attention Is All You Need",
        "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        "categories": ["cs.CL", "cs.LG"]
    }
    
    result = translator.translate_paper(test_paper)
    print(json.dumps(result, ensure_ascii=False, indent=2))
