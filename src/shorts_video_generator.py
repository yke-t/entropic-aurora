"""
Shorts Video Generator - Canva CSV + VOICEVOX音声生成 統合モジュール

Features:
- Canva Bulk Create用CSV生成（hook, line1, line2, ending, audio_script）
- VOICEVOX Engineで音声ファイル生成（video_01.wav, video_02.wav, ...）
- ADOPT_HIGH/ADOPT_MID論文のみ対象
"""

import os
import json
import csv
import time
import logging
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# MoviePyレンダラー（オプション）
try:
    from src.moviepy_renderer import MoviePyRenderer
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

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


class ShortsVideoGenerator:
    """Canva CSV + VOICEVOX音声生成 統合クラス"""
    
    def __init__(
        self,
        gemini_api_key: str,
        voicevox_url: str = "http://localhost:50021",
        speaker_id: int = 2,  # 四国めたん（ノーマル）
        model: str = "gemini-2.5-flash"
    ):
        """
        Args:
            gemini_api_key: Gemini APIキー
            voicevox_url: VOICEVOX Engine URL
            speaker_id: 話者ID（2=四国めたん ノーマル）
            model: Geminiモデル名
        """
        genai.configure(api_key=gemini_api_key)
        self.gemini_model = genai.GenerativeModel(model)
        self.voicevox_url = voicevox_url
        self.speaker_id = speaker_id
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_canva_text(
        self,
        paper: Dict[str, Any],
        shorts_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """単一論文からCanvaテキスト生成"""
        clickbait = shorts_score.get("clickbait_potential", {})
        best_title = clickbait.get("best_title", "") if isinstance(clickbait, dict) else ""
        
        prompt = CANVA_TEXT_PROMPT.format(
            title=paper.get("title", ""),
            abstract=paper.get("abstract", "")[:1500],
            best_title=best_title,
            shorts_score=shorts_score.get("total_score", 0)
        )
        
        try:
            response = self.gemini_model.generate_content(prompt)
            result_text = response.text
            
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            if start != -1 and end > start:
                result = json.loads(result_text[start:end])
                
                # 改行を除去
                for key in ["hook", "line1", "line2", "ending"]:
                    if key in result:
                        result[key] = result[key].replace("\n", "").replace("\r", "")
                
                result["paper_id"] = paper.get("id")
                
                # audio_script生成
                result["audio_script"] = self._create_audio_script(result)
                
                return result
            else:
                return {"paper_id": paper.get("id"), "error": "Invalid format"}
                
        except Exception as e:
            self.logger.error(f"Text generation error for {paper.get('id')}: {e}")
            return {"paper_id": paper.get("id"), "error": str(e)}
    
    def _create_audio_script(self, canva_text: Dict[str, Any]) -> str:
        """4項目を結合してaudio_script生成"""
        parts = []
        for key in ["hook", "line1", "line2", "ending"]:
            text = canva_text.get(key, "").strip()
            if text:
                text = text.rstrip("。、.!?！？")
                parts.append(text + "。")
        return "".join(parts)
    
    def generate_audio(
        self,
        text: str,
        output_path: Path,
        speed_scale: float = 0.9,
        intonation_scale: float = 0.2
    ) -> bool:
        """VOICEVOX Engineで音声生成（mp3形式）"""
        try:
            # 1. audio_query取得
            query_response = requests.post(
                f"{self.voicevox_url}/audio_query",
                params={"text": text, "speaker": self.speaker_id},
                timeout=30
            )
            query_response.raise_for_status()
            query = query_response.json()
            
            # 話速・抑揚設定
            query["speedScale"] = speed_scale
            query["intonationScale"] = intonation_scale
            
            # 2. synthesis（音声生成）
            synthesis_response = requests.post(
                f"{self.voicevox_url}/synthesis",
                params={"speaker": self.speaker_id},
                json=query,
                timeout=60
            )
            synthesis_response.raise_for_status()
            
            # 3. 一時ファイルにwav保存
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(synthesis_response.content)
                tmp_wav_path = tmp.name
            
            # 4. ffmpegでmp3変換
            import shutil
            ffmpeg_path = shutil.which("ffmpeg")
            if not ffmpeg_path:
                # WinGetのデフォルトインストールパス
                winget_ffmpeg = Path(os.path.expanduser(
                    "~/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.0.1-full_build/bin/ffmpeg.exe"
                ))
                if winget_ffmpeg.exists():
                    ffmpeg_path = str(winget_ffmpeg)
                else:
                    raise FileNotFoundError("ffmpeg not found in PATH or WinGet location")
            
            try:
                subprocess.run(
                    [ffmpeg_path, "-y", "-i", tmp_wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", str(output_path)],
                    capture_output=True,
                    check=True
                )
            finally:
                # 一時ファイル削除
                if os.path.exists(tmp_wav_path):
                    os.remove(tmp_wav_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Audio generation error: {e}")
            return False
    
    def process_papers(
        self,
        papers: List[Dict[str, Any]],
        shorts_scores: List[Dict[str, Any]],
        output_dir: Path,
        date_str: str,
        delay_seconds: float = 0.5,
        enable_moviepy: bool = True
    ) -> Dict[str, Any]:
        """
        論文からCSV + 音声ファイル + 動画を生成
        
        Args:
            papers: 論文メタデータのリスト
            shorts_scores: Shortsスコアのリスト
            output_dir: 出力先ディレクトリ
            date_str: 日付文字列（YYYYMMDD）
            delay_seconds: リクエスト間の待機秒数
            enable_moviepy: MoviePyで動画生成するか（デフォルト: True）
        
        Returns:
            処理結果サマリー
        """
        # ADOPT候補のみ抽出（スコア順）
        score_map = {s.get("paper_id"): s for s in shorts_scores}
        candidates = [s for s in shorts_scores if s.get("verdict") in ("ADOPT_HIGH", "ADOPT_MID")]
        candidates_sorted = sorted(candidates, key=lambda x: x.get("total_score", 0), reverse=True)
        
        paper_map = {p.get("id"): p for p in papers}
        
        results = []
        audio_results = []
        
        for i, candidate in enumerate(candidates_sorted):
            paper_id = candidate.get("paper_id")
            paper = paper_map.get(paper_id)
            if not paper:
                continue
            
            self.logger.info(f"Processing {i+1}/{len(candidates_sorted)}: {paper_id}")
            
            # 1. Canvaテキスト生成
            canva_text = self.generate_canva_text(paper, candidate)
            results.append(canva_text)
            
            # 2. 音声生成
            if "error" not in canva_text:
                audio_path = output_dir / "audio" / f"video_{i+1:02d}.mp3"
                success = self.generate_audio(
                    canva_text.get("audio_script", ""),
                    audio_path,
                    speed_scale=0.9,
                    intonation_scale=0.2
                )
                audio_results.append({
                    "index": i+1,
                    "paper_id": paper_id,
                    "path": str(audio_path) if success else None,
                    "success": success
                })
            
            if i < len(candidates_sorted) - 1:
                time.sleep(delay_seconds)
        
        # CSV保存
        csv_path = output_dir / f"shorts_video_{date_str}.csv"
        self._save_csv(results, csv_path)
        
        # JSON保存
        json_path = output_dir / f"shorts_video_{date_str}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # MoviePy動画生成
        video_results = []
        if enable_moviepy and MOVIEPY_AVAILABLE:
            self.logger.info("Starting MoviePy video rendering...")
            renderer = MoviePyRenderer(
                output_dir=output_dir,
                resolution=(1080, 1920),
                fps=30
            )
            
            for item in audio_results:
                if not item.get("success"):
                    continue
                
                idx = item["index"]
                # 対応するテキストデータを取得
                canva_text = results[idx - 1] if idx <= len(results) else {}
                
                if "error" in canva_text:
                    continue
                
                texts = {
                    "hook": canva_text.get("hook", ""),
                    "line1": canva_text.get("line1", ""),
                    "line2": canva_text.get("line2", ""),
                    "ending": canva_text.get("ending", "")
                }
                
                audio_path = Path(item["path"])
                video_path = output_dir / "video" / f"video_{idx:02d}.mp4"
                
                result_path = renderer.render_video(
                    texts=texts,
                    audio_path=audio_path,
                    output_path=video_path
                )
                
                video_results.append({
                    "index": idx,
                    "path": str(result_path) if result_path else None,
                    "success": result_path is not None
                })
        
        return {
            "total_processed": len(results),
            "audio_generated": sum(1 for a in audio_results if a.get("success")),
            "video_generated": sum(1 for v in video_results if v.get("success")),
            "csv_path": str(csv_path),
            "audio_dir": str(output_dir / "audio"),
            "video_dir": str(output_dir / "video") if video_results else None
        }
    
    def _save_csv(self, results: List[Dict[str, Any]], output_path: Path) -> None:
        """CSV保存（Canva Bulk Create用）"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        valid_results = [r for r in results if "error" not in r]
        
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["hook", "line1", "line2", "ending", "audio_script"],
                extrasaction="ignore"
            )
            writer.writeheader()
            for row in valid_results:
                writer.writerow(row)
        
        self.logger.info(f"CSV保存: {output_path} ({len(valid_results)}件)")
