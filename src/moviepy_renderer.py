"""
MoviePy Renderer - YouTube Shorts動画レンダリング

Features:
- 9:16縦型動画（1080x1920）
- 背景：グラデーション or テンプレート画像
- テキスト：hook/line1/line2/endingを順次表示（フェードイン）
- 音声：VOICEVOX生成音声を同期
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import tempfile

from moviepy import (
    VideoClip,
    AudioFileClip,
    CompositeVideoClip,
    TextClip,
    ImageClip,
    concatenate_videoclips,
)
from moviepy.video.fx import FadeIn, FadeOut
from PIL import Image, ImageDraw
import numpy as np

logger = logging.getLogger(__name__)


class MoviePyRenderer:
    """YouTube Shorts動画レンダラー"""
    
    # デフォルト設定
    DEFAULT_WIDTH = 1080
    DEFAULT_HEIGHT = 1920
    DEFAULT_FPS = 30
    
    # グラデーション色（ダークテーマ）
    GRADIENT_TOP = (15, 10, 40)      # 深い紫
    GRADIENT_BOTTOM = (5, 20, 50)    # 深い青
    
    # テキスト設定（Windows日本語フォント）
    TEXT_FONT = "C:/Windows/Fonts/meiryo.ttc"  # メイリオ（日本語対応）
    TEXT_COLOR = "white"
    HOOK_FONT_SIZE = 80
    LINE_FONT_SIZE = 50      # 元に戻す
    ENDING_FONT_SIZE = 80
    
    def __init__(
        self,
        output_dir: Path,
        resolution: Tuple[int, int] = (1080, 1920),
        fps: int = 30
    ):
        """
        Args:
            output_dir: 出力ディレクトリ
            resolution: 解像度 (width, height)
            fps: フレームレート
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width, self.height = resolution
        self.fps = fps
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _create_gradient_background(self, duration: float) -> VideoClip:
        """グラデーション背景を生成"""
        def make_frame(t):
            # 静的グラデーション
            img = Image.new('RGB', (self.width, self.height))
            draw = ImageDraw.Draw(img)
            
            for y in range(self.height):
                ratio = y / self.height
                r = int(self.GRADIENT_TOP[0] * (1 - ratio) + self.GRADIENT_BOTTOM[0] * ratio)
                g = int(self.GRADIENT_TOP[1] * (1 - ratio) + self.GRADIENT_BOTTOM[1] * ratio)
                b = int(self.GRADIENT_TOP[2] * (1 - ratio) + self.GRADIENT_BOTTOM[2] * ratio)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b))
            
            return np.array(img)
        
        # 1フレームだけ生成して使い回す（パフォーマンス向上）
        frame = make_frame(0)
        return ImageClip(frame, duration=duration)
    
    def _create_text_clip(
        self,
        text: str,
        font_size: int,
        duration: float,
        start_time: float,
        fade_duration: float = 0.3,
        position: str = "center"
    ) -> TextClip:
        """フェードイン付きテキストクリップを生成"""
        # テキストエリア: 幅は画面の80%、高さは十分に取る
        text_width = int(self.width * 0.85)   # 85%の幅（左右マージン合計15%）
        text_height = int(self.height * 0.20)  # 各テキストに20%の高さを確保
        
        txt_clip = TextClip(
            text=text,
            font_size=font_size,
            font=self.TEXT_FONT,
            color=self.TEXT_COLOR,
            stroke_color="black",
            stroke_width=2,
            size=(text_width, text_height),  # 縦横両方指定
            method="caption",
            text_align="center",
        )
        
        # フェードインを適用
        txt_clip = txt_clip.with_effects([FadeIn(fade_duration)])
        txt_clip = txt_clip.with_duration(duration)
        txt_clip = txt_clip.with_start(start_time)
        txt_clip = txt_clip.with_position(position)
        
        return txt_clip
    
    def render_video(
        self,
        texts: Dict[str, str],
        audio_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
        background: str = "gradient"
    ) -> Optional[Path]:
        """
        動画をレンダリング
        
        Args:
            texts: テキストデータ {hook, line1, line2, ending}
            audio_path: 音声ファイルパス（Noneの場合は無音）
            output_path: 出力パス（Noneの場合は自動生成）
            background: "gradient" または "image:/path/to/image.png"
        
        Returns:
            生成された動画のパス（失敗時はNone）
        """
        try:
            # 音声から動画長さを決定
            if audio_path and Path(audio_path).exists():
                audio_clip = AudioFileClip(str(audio_path))
                total_duration = audio_clip.duration + 0.5  # 余白追加
            else:
                audio_clip = None
                total_duration = 20.0  # デフォルト20秒
            
            # 背景クリップ
            if background.startswith("image:"):
                img_path = background[6:]
                bg_clip = ImageClip(img_path, duration=total_duration)
                bg_clip = bg_clip.resized((self.width, self.height))
            else:
                bg_clip = self._create_gradient_background(total_duration)
            
            # テキストクリップ（順次表示）
            text_clips = []
            
            # 各テキストの表示タイミング（音声に合わせて均等配分）
            segment_duration = total_duration / 4
            
            # hook (0-25%)
            if texts.get("hook"):
                hook_clip = self._create_text_clip(
                    texts["hook"],
                    self.HOOK_FONT_SIZE,
                    duration=segment_duration,  # 重複削除
                    start_time=0,
                    position=("center", self.height * 0.30)
                )
                text_clips.append(hook_clip)
            
            # line1 (25-50%)
            if texts.get("line1"):
                line1_clip = self._create_text_clip(
                    texts["line1"],
                    self.LINE_FONT_SIZE,
                    duration=segment_duration,  # 重複削除
                    start_time=segment_duration,
                    position=("center", self.height * 0.30)
                )
                text_clips.append(line1_clip)
            
            # line2 (50-75%)
            if texts.get("line2"):
                line2_clip = self._create_text_clip(
                    texts["line2"],
                    self.LINE_FONT_SIZE,
                    duration=segment_duration,  # 重複削除
                    start_time=segment_duration * 2,
                    position=("center", self.height * 0.30)
                )
                text_clips.append(line2_clip)
            
            # ending (75-100%)
            if texts.get("ending"):
                ending_clip = self._create_text_clip(
                    texts["ending"],
                    self.ENDING_FONT_SIZE,
                    duration=segment_duration,  # 重複削除
                    start_time=segment_duration * 3,
                    position=("center", self.height * 0.30)
                )
                text_clips.append(ending_clip)
            
            # 合成
            final_clip = CompositeVideoClip(
                [bg_clip] + text_clips,
                size=(self.width, self.height)
            )
            
            # 音声を追加
            if audio_clip:
                final_clip = final_clip.with_audio(audio_clip)
            
            # 出力パス
            if output_path is None:
                output_path = self.output_dir / "output.mp4"
            else:
                output_path = Path(output_path)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # レンダリング
            self.logger.info(f"Rendering video: {output_path}")
            final_clip.write_videofile(
                str(output_path),
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                logger=None  # MoviePyのログを抑制
            )
            
            # クリーンアップ
            final_clip.close()
            if audio_clip:
                audio_clip.close()
            
            self.logger.info(f"Video saved: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Render error: {e}")
            return None
    
    def render_batch(
        self,
        video_data_list: list,
        audio_dir: Path,
        output_subdir: str = "video"
    ) -> Dict[str, any]:
        """
        複数動画を一括レンダリング
        
        Args:
            video_data_list: [{"index": 1, "texts": {...}}, ...]
            audio_dir: 音声ファイルディレクトリ
            output_subdir: 出力サブディレクトリ名
        
        Returns:
            {"success": int, "failed": int, "paths": [...]}
        """
        video_dir = self.output_dir / output_subdir
        video_dir.mkdir(parents=True, exist_ok=True)
        
        results = {"success": 0, "failed": 0, "paths": []}
        
        for item in video_data_list:
            idx = item.get("index", 0)
            texts = item.get("texts", {})
            
            audio_path = audio_dir / f"video_{idx:02d}.mp3"
            output_path = video_dir / f"video_{idx:02d}.mp4"
            
            self.logger.info(f"Rendering {idx}/{len(video_data_list)}...")
            
            result_path = self.render_video(
                texts=texts,
                audio_path=audio_path if audio_path.exists() else None,
                output_path=output_path
            )
            
            if result_path:
                results["success"] += 1
                results["paths"].append(str(result_path))
            else:
                results["failed"] += 1
        
        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # テスト
    renderer = MoviePyRenderer(
        output_dir=Path("output"),
        resolution=(1080, 1920),
        fps=30
    )
    
    test_texts = {
        "hook": "医者が不要になる",
        "line1": "AIが専門医を超えた診断精度を達成",
        "line2": "肺がん検出で人間の95%を上回る99%を記録",
        "ending": "もう戻れない"
    }
    
    result = renderer.render_video(
        texts=test_texts,
        output_path=Path("output/test_video.mp4")
    )
    
    if result:
        print(f"[OK] Video created: {result}")
    else:
        print("[FAIL] Video creation failed")
