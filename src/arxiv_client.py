"""
arXiv API Client - arXivから論文メタデータを取得

Features:
- 指定カテゴリの新着論文取得
- 日付フィルタリング（前日分）
- 重複排除
- arXiv API推奨のリクエスト間隔遵守
"""

import arxiv
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import logging

logger = logging.getLogger(__name__)


def get_papers_by_category(
    categories: List[str],
    max_results: int = 100,
    request_interval: float = 3.0
) -> List[Dict[str, Any]]:
    """
    指定カテゴリから論文を取得
    
    Args:
        categories: arXivカテゴリのリスト (e.g., ['cs.AI', 'cs.LG'])
        max_results: カテゴリあたりの最大取得件数
        request_interval: リクエスト間隔（秒）
    
    Returns:
        論文メタデータのリスト
    """
    all_papers: List[Dict[str, Any]] = []
    seen_ids: set = set()
    
    for category in categories:
        logger.info(f"Fetching papers from category: {category}")
        
        try:
            # arXiv APIクエリ構築
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            client = arxiv.Client()
            results = client.results(search)
            
            for result in results:
                paper_id = result.entry_id.split("/")[-1]
                
                # 重複排除
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)
                
                paper = {
                    "id": paper_id,
                    "title": result.title,
                    "abstract": result.summary,
                    "authors": [author.name for author in result.authors],
                    "categories": result.categories,
                    "primary_category": result.primary_category,
                    "published": result.published.isoformat(),
                    "updated": result.updated.isoformat(),
                    "pdf_url": result.pdf_url,
                    "entry_id": result.entry_id,
                }
                all_papers.append(paper)
            
            logger.info(f"Fetched {len(all_papers)} papers from {category}")
            
        except Exception as e:
            logger.error(f"Error fetching papers from {category}: {e}")
        
        # arXiv APIの推奨間隔を遵守
        time.sleep(request_interval)
    
    logger.info(f"Total unique papers fetched: {len(all_papers)}")
    return all_papers


def filter_by_date(
    papers: List[Dict[str, Any]],
    target_date: datetime = None
) -> List[Dict[str, Any]]:
    """
    指定日付の論文のみフィルタリング
    
    Args:
        papers: 論文メタデータのリスト
        target_date: 対象日（デフォルト: 前日）
    
    Returns:
        フィルタリング済みの論文リスト
    """
    if target_date is None:
        target_date = datetime.now() - timedelta(days=1)
    
    target_date_str = target_date.strftime("%Y-%m-%d")
    
    filtered = [
        paper for paper in papers
        if paper["published"].startswith(target_date_str)
        or paper["updated"].startswith(target_date_str)
    ]
    
    logger.info(f"Filtered to {len(filtered)} papers for date {target_date_str}")
    return filtered


if __name__ == "__main__":
    # テスト実行
    logging.basicConfig(level=logging.INFO)
    
    test_categories = ["cs.AI"]
    papers = get_papers_by_category(test_categories, max_results=5)
    
    for paper in papers[:3]:
        print(f"\n{'='*50}")
        print(f"Title: {paper['title'][:80]}...")
        print(f"ID: {paper['id']}")
        print(f"Categories: {paper['categories']}")
