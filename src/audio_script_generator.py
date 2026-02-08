"""
Audio Script Generator - 音声ナレーション台本生成

Canva CSVの4項目（hook, line1, line2, ending）を
1行の音声読み上げ用台本に変換

Features:
- 各文末に「。」を付加
- 改行なし
- 17〜18秒で読める長さ
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AudioScriptGenerator:
    """音声ナレーション台本生成"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_script(self, canva_text: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一のCanvaテキストから音声台本生成
        
        Args:
            canva_text: Canvaテキスト（hook, line1, line2, ending）
        
        Returns:
            音声台本データ
        """
        # 4項目を取得
        hook = canva_text.get("hook", "").strip()
        line1 = canva_text.get("line1", "").strip()
        line2 = canva_text.get("line2", "").strip()
        ending = canva_text.get("ending", "").strip()
        
        # 各文末に「。」を付加（既にあれば重複しない）
        parts = []
        for text in [hook, line1, line2, ending]:
            if text:
                # 末尾の句読点を除去して「。」を付加
                text = text.rstrip("。、.!?！？")
                parts.append(text + "。")
        
        # 1行に結合（改行なし）
        audio_script = "".join(parts)
        
        return {
            "paper_id": canva_text.get("paper_id", ""),
            "audio_script": audio_script
        }
    
    def generate_scripts(self, canva_texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        複数のCanvaテキストから音声台本生成
        
        Args:
            canva_texts: Canvaテキストのリスト
        
        Returns:
            音声台本のリスト
        """
        results = []
        for i, text in enumerate(canva_texts):
            self.logger.info(f"Audio script {i+1}/{len(canva_texts)}: {text.get('paper_id', '')}")
            result = self.generate_script(text)
            results.append(result)
        return results
    
    def save_csv(self, scripts: List[Dict[str, Any]], output_path: Path) -> None:
        """
        音声台本CSV保存
        
        Args:
            scripts: 音声台本のリスト
            output_path: 出力先パス
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["audio_script"],
                extrasaction="ignore"
            )
            writer.writeheader()
            for row in scripts:
                writer.writerow(row)
        
        self.logger.info(f"Audio script CSV保存: {output_path} ({len(scripts)}件)")
    
    @staticmethod
    def from_canva_csv(canva_csv_path: Path) -> List[Dict[str, Any]]:
        """
        Canva CSVから読み込み
        
        Args:
            canva_csv_path: Canva CSVパス
        
        Returns:
            Canvaテキストのリスト
        """
        texts = []
        with open(canva_csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                texts.append(row)
        return texts
    
    @staticmethod
    def from_canva_json(canva_json_path: Path) -> List[Dict[str, Any]]:
        """
        Canva JSONから読み込み
        
        Args:
            canva_json_path: Canva JSONパス
        
        Returns:
            Canvaテキストのリスト
        """
        with open(canva_json_path, "r", encoding="utf-8") as f:
            return json.load(f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # テスト
    generator = AudioScriptGenerator()
    
    test_canva = {
        "paper_id": "test001",
        "hook": "医者が不要になる",
        "line1": "AIが専門医を超えた診断精度を達成",
        "line2": "肺がん検出で人間の95%を上回る99%を記録",
        "ending": "もう戻れない"
    }
    
    result = generator.generate_script(test_canva)
    print(f"audio_script: {result['audio_script']}")
