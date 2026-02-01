"""
PDF Downloader - arXiv論文のPDFをダウンロード

Features:
- 並列ダウンロード対応
- リトライ処理（指数バックオフ）
- プログレスバー表示
"""

import httpx
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

# デフォルト設定
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3
BACKOFF_FACTOR = 2


async def download_pdf_async(
    paper: Dict[str, Any],
    output_dir: Path,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES
) -> bool:
    """
    単一のPDFを非同期でダウンロード
    
    Args:
        paper: 論文メタデータ
        output_dir: 保存先ディレクトリ
        timeout: タイムアウト秒数
        max_retries: 最大リトライ回数
    
    Returns:
        成功時True
    """
    pdf_url = paper.get("pdf_url")
    if not pdf_url:
        logger.warning(f"No PDF URL for paper: {paper.get('id')}")
        return False
    
    paper_id = paper.get("id", "unknown").replace("/", "_")
    output_path = output_dir / f"{paper_id}.pdf"
    
    # 既にダウンロード済みならスキップ
    if output_path.exists():
        logger.debug(f"Already exists: {output_path}")
        return True
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()
                
                output_path.write_bytes(response.content)
                logger.debug(f"Downloaded: {output_path}")
                return True
                
        except Exception as e:
            wait_time = BACKOFF_FACTOR ** attempt
            logger.warning(
                f"Retry {attempt + 1}/{max_retries} for {paper_id}: {e}. "
                f"Waiting {wait_time}s..."
            )
            await asyncio.sleep(wait_time)
    
    logger.error(f"Failed to download: {paper_id}")
    return False


async def download_papers_batch(
    papers: List[Dict[str, Any]],
    output_dir: Path,
    max_concurrent: int = 5
) -> Dict[str, bool]:
    """
    複数のPDFを並列でダウンロード
    
    Args:
        papers: 論文メタデータのリスト
        output_dir: 保存先ディレクトリ
        max_concurrent: 最大同時ダウンロード数
    
    Returns:
        {paper_id: success}の辞書
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    semaphore = asyncio.Semaphore(max_concurrent)
    results: Dict[str, bool] = {}
    
    async def download_with_limit(paper: Dict[str, Any]) -> None:
        async with semaphore:
            paper_id = paper.get("id", "unknown")
            success = await download_pdf_async(paper, output_dir)
            results[paper_id] = success
    
    tasks = [download_with_limit(paper) for paper in papers]
    
    # プログレスバー付きで実行
    for coro in tqdm(
        asyncio.as_completed(tasks),
        total=len(tasks),
        desc="Downloading PDFs"
    ):
        await coro
    
    success_count = sum(results.values())
    logger.info(f"Downloaded {success_count}/{len(papers)} PDFs")
    
    return results


def download_papers(
    papers: List[Dict[str, Any]],
    output_dir: str | Path,
    max_concurrent: int = 5
) -> Dict[str, bool]:
    """
    PDFダウンロードの同期ラッパー
    
    Args:
        papers: 論文メタデータのリスト
        output_dir: 保存先ディレクトリ
        max_concurrent: 最大同時ダウンロード数
    
    Returns:
        {paper_id: success}の辞書
    """
    output_path = Path(output_dir)
    return asyncio.run(download_papers_batch(papers, output_path, max_concurrent))


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    test_papers = [
        {
            "id": "2401.00001",
            "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf"
        }
    ]
    
    results = download_papers(test_papers, "./output/papers")
    print(f"Results: {results}")
