"""
Drive Uploader - Google Driveへのファイルアップロード

Features:
- サービスアカウント認証
- 日付・カテゴリ別フォルダ自動作成
- PDF/JSON/Markdownアップロード
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Drive API スコープ
SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveUploader:
    """Google Drive アップローダー"""
    
    def __init__(self, credentials_path: str, root_folder_id: str):
        """
        Args:
            credentials_path: サービスアカウントJSONファイルのパス
            root_folder_id: ルートフォルダのID（ArXiv/）
        """
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )
        self.service = build("drive", "v3", credentials=self.credentials)
        self.root_folder_id = root_folder_id
        self.folder_cache: Dict[str, str] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_or_create_folder(
        self,
        folder_name: str,
        parent_id: Optional[str] = None
    ) -> str:
        """
        フォルダを取得または作成
        
        Args:
            folder_name: フォルダ名
            parent_id: 親フォルダID（Noneの場合はroot_folder_id）
        
        Returns:
            フォルダID
        """
        parent_id = parent_id or self.root_folder_id
        cache_key = f"{parent_id}/{folder_name}"
        
        # キャッシュ確認
        if cache_key in self.folder_cache:
            return self.folder_cache[cache_key]
        
        # 既存フォルダを検索
        query = (
            f"name = '{folder_name}' and "
            f"'{parent_id}' in parents and "
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"trashed = false"
        )
        results = self.service.files().list(
            q=query, fields="files(id, name)"
        ).execute()
        
        files = results.get("files", [])
        if files:
            folder_id = files[0]["id"]
            self.folder_cache[cache_key] = folder_id
            return folder_id
        
        # 新規作成
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id]
        }
        folder = self.service.files().create(
            body=metadata, fields="id"
        ).execute()
        
        folder_id = folder["id"]
        self.folder_cache[cache_key] = folder_id
        self.logger.info(f"Created folder: {folder_name}")
        
        return folder_id
    
    def get_monthly_folder(self, date: Optional[datetime] = None) -> str:
        """
        月別フォルダ（YYYY-MM）を取得または作成
        
        Args:
            date: 対象日（デフォルト: 今日）
        
        Returns:
            フォルダID
        """
        date = date or datetime.now()
        folder_name = date.strftime("%Y-%m")
        return self.get_or_create_folder(folder_name)
    
    def upload_file(
        self,
        file_path: Path,
        folder_id: str,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ファイルをアップロード
        
        Args:
            file_path: ローカルファイルパス
            folder_id: アップロード先フォルダID
            mime_type: MIMEタイプ（自動検出も可能）
        
        Returns:
            {"id": file_id, "name": file_name, "webViewLink": url}
        """
        file_path = Path(file_path)
        
        # MIMEタイプの自動判定
        if mime_type is None:
            suffix = file_path.suffix.lower()
            mime_map = {
                ".pdf": "application/pdf",
                ".json": "application/json",
                ".md": "text/markdown",
                ".txt": "text/plain",
            }
            mime_type = mime_map.get(suffix, "application/octet-stream")
        
        metadata = {
            "name": file_path.name,
            "parents": [folder_id]
        }
        
        media = MediaFileUpload(
            str(file_path), mimetype=mime_type, resumable=True
        )
        
        file = self.service.files().create(
            body=metadata,
            media_body=media,
            fields="id, name, webViewLink"
        ).execute()
        
        self.logger.debug(f"Uploaded: {file_path.name}")
        return file
    
    def upload_papers_batch(
        self,
        papers_dir: Path,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        論文PDF一括アップロード
        
        Args:
            papers_dir: PDFが格納されたディレクトリ
            date: 対象日
        
        Returns:
            {"uploaded": count, "files": [uploaded_files]}
        """
        monthly_folder = self.get_monthly_folder(date)
        papers_folder = self.get_or_create_folder("papers", monthly_folder)
        
        uploaded = []
        papers_dir = Path(papers_dir)
        
        for pdf_file in papers_dir.glob("*.pdf"):
            try:
                result = self.upload_file(pdf_file, papers_folder)
                uploaded.append(result)
            except Exception as e:
                self.logger.error(f"Upload failed: {pdf_file.name} - {e}")
        
        self.logger.info(f"Uploaded {len(uploaded)} PDFs")
        return {"uploaded": len(uploaded), "files": uploaded}
    
    def upload_json_data(
        self,
        data: Any,
        filename: str,
        subfolder: str,
        date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        JSONデータをアップロード
        
        Args:
            data: JSONシリアライズ可能なデータ
            filename: ファイル名
            subfolder: サブフォルダ名（metadata/screening/translated）
            date: 対象日
        
        Returns:
            アップロード結果
        """
        import tempfile
        
        monthly_folder = self.get_monthly_folder(date)
        target_folder = self.get_or_create_folder(subfolder, monthly_folder)
        
        # 一時ファイルに書き出してアップロード
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            temp_path = Path(f.name)
        
        try:
            # ファイル名を変更
            final_path = temp_path.parent / filename
            temp_path.rename(final_path)
            
            result = self.upload_file(final_path, target_folder, "application/json")
            return result
        finally:
            # 一時ファイル削除
            if final_path.exists():
                final_path.unlink()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    folder_id = os.getenv("DRIVE_FOLDER_ID")
    
    if not credentials_path or not folder_id:
        print("GOOGLE_APPLICATION_CREDENTIALS and DRIVE_FOLDER_ID must be set in .env")
        exit(1)
    
    uploader = DriveUploader(credentials_path, folder_id)
    
    # テスト: フォルダ作成
    monthly_id = uploader.get_monthly_folder()
    print(f"Monthly folder ID: {monthly_id}")
