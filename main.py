"""
arXiv論文日次収集＆翻訳システム - メインエントリーポイント

3段階パイプライン:
1. arXiv API からメタデータ + PDF全件取得（目安300本/日）
2. AIスクリーニング（有益度スコアリング）
3. 翻訳＋要約（上位100本）
4. Google Drive同期フォルダに自動保存

Note: Google Drive for Desktopの同期機能を使用するため、
      Drive APIは不要。ローカルに保存すると自動でクラウドに同期。
"""

import os
import sys
import yaml
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from src.arxiv_client import get_papers_by_category, filter_by_date
from src.pdf_downloader import download_papers
from src.screener import Screener
from src.translator import Translator


def setup_logging(config: dict) -> logging.Logger:
    """ロギング設定"""
    log_config = config.get("logging", {})
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_config.get("level", "INFO")),
        format=log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "arxiv_collector.log", encoding="utf-8")
        ]
    )
    return logging.getLogger(__name__)


def load_config(config_path: str = "config.yaml") -> dict:
    """設定ファイル読み込み"""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_json(data: any, path: Path) -> None:
    """JSONファイル保存"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(data: list, path: Path, columns: list = None) -> None:
    """CSVファイル保存（Excel/スプレッドシート対応）"""
    import csv
    
    if not data:
        return
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # カラム指定がなければ最初のレコードのキーを使用
    if columns is None:
        columns = list(data[0].keys())
    
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig: Excel対応BOM付き
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            # リストをカンマ区切り文字列に変換
            flat_row = {}
            for k, v in row.items():
                if isinstance(v, list):
                    flat_row[k] = " / ".join(str(x) for x in v)
                else:
                    flat_row[k] = v
            writer.writerow(flat_row)


def generate_daily_summary(
    papers: list,
    translated: list,
    date: datetime
) -> str:
    """日次サマリーMarkdown生成"""
    date_str = date.strftime("%Y-%m-%d")
    
    lines = [
        f"# arXiv Daily Summary - {date_str}",
        "",
        f"## 統計",
        f"- 取得論文数: {len(papers)}件",
        f"- 翻訳論文数: {len(translated)}件",
        "",
        f"## Top Papers",
        ""
    ]
    
    for i, t in enumerate(translated[:10], 1):
        title_ja = t.get("title_ja", t.get("original_title", "N/A"))
        summary = t.get("summary_3lines", [])
        hook = t.get("youtube_hook", "")
        
        lines.append(f"### {i}. {title_ja}")
        lines.append(f"**ID**: {t.get('paper_id')}")
        if hook:
            lines.append(f"**Hook**: {hook}")
        if summary:
            lines.append("\n".join(f"- {s}" for s in summary))
        lines.append("")
    
    return "\n".join(lines)


def main():
    """メイン処理"""
    # 環境変数読み込み
    load_dotenv()
    
    # 設定読み込み
    config = load_config()
    logger = setup_logging(config)
    
    # 日付設定（処理対象日）
    target_date = datetime.now()
    date_str = target_date.strftime("%Y%m%d")
    month_str = target_date.strftime("%Y-%m")  # 年月フォルダ用
    
    logger.info(f"=== arXiv論文収集開始: {date_str} ===")
    
    # 出力ディレクトリ（Google Drive同期フォルダ）
    # 実装計画: ArXiv/2026-01/metadata/ の構造
    output_config = config.get("output", {})
    base_dir = Path(output_config.get("base_dir", "./output"))
    output_dir = base_dir / month_str  # 年月フォルダを追加
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"出力先: {output_dir}")
    
    # API設定
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    # ====== Phase 1: arXiv取得 ======
    logger.info("Phase 1: arXiv論文取得開始")
    
    categories = config.get("categories", [])
    arxiv_config = config.get("arxiv", {})
    
    papers = get_papers_by_category(
        categories=categories,
        max_results=arxiv_config.get("max_results_per_query", 100),
        request_interval=arxiv_config.get("request_interval", 3.0)
    )
    
    # メタデータ保存
    metadata_dir = output_dir / output_config.get("subfolders", {}).get("metadata", "metadata")
    metadata_path = metadata_dir / f"metadata_{date_str}.json"
    save_json(papers, metadata_path)
    
    # CSV出力（表形式で閲覧可能）
    metadata_csv_path = metadata_dir / f"metadata_{date_str}.csv"
    metadata_columns = ["id", "title", "authors", "categories", "published", "abstract", "pdf_url"]
    save_csv(papers, metadata_csv_path, metadata_columns)
    logger.info(f"取得論文数: {len(papers)}件（CSV出力済み）")
    
    # ====== Phase 1.5: PDF全件ダウンロード ======
    logger.info("Phase 1.5: PDF全件ダウンロード開始")
    
    papers_dir = output_dir / output_config.get("subfolders", {}).get("papers", "papers")
    download_results = download_papers(papers, papers_dir, max_concurrent=5)
    
    success_count = sum(download_results.values())
    logger.info(f"PDFダウンロード完了: {success_count}/{len(papers)}件")
    
    # ====== Phase 2: AIスクリーニング ======
    if not gemini_api_key:
        logger.warning("GEMINI_API_KEY未設定: スクリーニング・翻訳をスキップ")
        return
    
    logger.info("Phase 2: AIスクリーニング開始")
    
    screener = Screener(gemini_api_key, config.get("gemini", {}).get("model", "gemini-2.5-flash"))
    screening_results = screener.screen_papers(papers)
    
    # スクリーニング結果保存
    screening_dir = output_dir / output_config.get("subfolders", {}).get("screening", "screening")
    screening_path = screening_dir / f"screening_{date_str}.json"
    save_json(screening_results, screening_path)
    
    # 統合CSV出力（metadata + screening スコア）
    # paper_id → id でマッピング
    screening_map = {r.get("paper_id"): r for r in screening_results}
    merged_data = []
    for paper in papers:
        paper_id = paper.get("id")
        screening = screening_map.get(paper_id, {})
        merged = {
            **paper,
            "total_score": screening.get("total_score", ""),
            "usefulness": screening.get("usefulness", ""),
            "novelty": screening.get("novelty", ""),
            "impact": screening.get("impact", ""),
            "explainability": screening.get("explainability", ""),
            "one_line_summary": screening.get("one_line_summary", ""),
            "reason": screening.get("reason", "")
        }
        merged_data.append(merged)
    
    # スコア順にソート
    merged_data.sort(key=lambda x: x.get("total_score", 0) or 0, reverse=True)
    
    merged_csv_path = metadata_dir / f"papers_{date_str}.csv"
    merged_columns = ["id", "title", "authors", "categories", "published", 
                      "total_score", "usefulness", "novelty", "impact", "explainability",
                      "one_line_summary", "reason", "abstract", "pdf_url"]
    save_csv(merged_data, merged_csv_path, merged_columns)
    logger.info(f"統合CSV出力: {len(merged_data)}件 → {merged_csv_path.name}")
    
    # 上位論文選定
    screening_config = config.get("screening", {})
    top_papers = screener.select_top_papers(
        screening_results,
        papers,
        top_n=screening_config.get("top_n", 100),
        min_score=screening_config.get("min_score", 5.0)
    )
    logger.info(f"スクリーニング通過: {len(top_papers)}件")
    
    # ====== Phase 3: 翻訳 ======
    logger.info("Phase 3: 翻訳開始")
    
    translator = Translator(gemini_api_key, config.get("gemini", {}).get("model", "gemini-2.5-flash"))
    translated = translator.translate_papers(top_papers)
    
    # 翻訳結果保存
    translated_dir = output_dir / output_config.get("subfolders", {}).get("translated", "translated")
    translated_path = translated_dir / f"translated_{date_str}.json"
    save_json(translated, translated_path)
    
    # CSV出力（表形式で閲覧可能）
    translated_csv_path = translated_dir / f"translated_{date_str}.csv"
    translated_columns = ["paper_id", "title_ja", "youtube_hook", "summary_3lines", "keywords", "original_title"]
    save_csv(translated, translated_csv_path, translated_columns)
    logger.info(f"翻訳完了: {len(translated)}件（CSV出力済み）")
    
    # ====== 日次サマリー生成 ======
    summary_md = generate_daily_summary(papers, translated, target_date)
    summary_path = output_dir / f"summary_{date_str}.md"
    summary_path.write_text(summary_md, encoding="utf-8")
    
    logger.info(f"=== 処理完了: {date_str} ===")
    logger.info(f"  出力先: {output_dir}")
    logger.info(f"  取得: {len(papers)}件, 翻訳: {len(translated)}件")
    logger.info("  ※ Google Driveへ自動同期されます")


if __name__ == "__main__":
    main()
