"""本地檔案儲存服務"""
import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io

from app.core.config import settings

logger = logging.getLogger(__name__)

# 支援的圖片格式
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# 縮圖尺寸
THUMBNAIL_SIZE = (200, 200)
# 主圖最大尺寸
MAX_IMAGE_SIZE = (1200, 1200)


class FileStorageService:
    """本地檔案儲存服務"""

    def __init__(self):
        """初始化儲存服務，建立上傳目錄"""
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.photos_dir = self.upload_dir / "photos"
        self.chat_dir = self.upload_dir / "chat"
        self._ensure_directories()

    def _ensure_directories(self):
        """確保上傳目錄存在"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        self.chat_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_photo_dir(self, user_id: str) -> Path:
        """取得使用者照片目錄"""
        user_dir = self.photos_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _get_chat_image_dir(self, match_id: str) -> Path:
        """取得聊天圖片目錄"""
        chat_image_dir = self.chat_dir / str(match_id)
        chat_image_dir.mkdir(parents=True, exist_ok=True)
        return chat_image_dir

    def _get_file_extension(self, filename: str, content_type: str) -> str:
        """取得檔案副檔名"""
        # 優先從 content_type 判斷
        mime_to_ext = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
        }
        if content_type in mime_to_ext:
            return mime_to_ext[content_type]

        # 從檔名取得
        if filename and "." in filename:
            ext = filename.rsplit(".", 1)[1].lower()
            if ext in ALLOWED_EXTENSIONS:
                return ext

        # 預設使用 jpg
        return "jpg"

    def _process_image(
        self, file_content: bytes, max_size: Tuple[int, int]
    ) -> bytes:
        """
        處理圖片：調整大小並壓縮

        Args:
            file_content: 原始檔案內容
            max_size: 最大尺寸 (width, height)

        Returns:
            處理後的圖片內容
        """
        img = Image.open(io.BytesIO(file_content))

        # 轉換為 RGB（處理 RGBA 或其他模式）
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 調整大小（保持比例）
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 儲存到記憶體
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        output.seek(0)

        return output.read()

    def _create_thumbnail(self, file_content: bytes) -> bytes:
        """
        建立縮圖

        Args:
            file_content: 原始檔案內容

        Returns:
            縮圖內容
        """
        img = Image.open(io.BytesIO(file_content))

        # 轉換為 RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 建立縮圖（裁切為正方形）
        width, height = img.size
        min_dim = min(width, height)

        # 從中心裁切
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim

        img = img.crop((left, top, right, bottom))
        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # 儲存到記憶體
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=80, optimize=True)
        output.seek(0)

        return output.read()

    async def save_photo(
        self,
        user_id: str,
        file_content: bytes,
        filename: str,
        content_type: str,
    ) -> Tuple[str, str, str]:
        """
        儲存照片及縮圖

        Args:
            user_id: 使用者 ID
            file_content: 檔案內容
            filename: 原始檔名
            content_type: MIME 類型

        Returns:
            Tuple[photo_id, photo_url, thumbnail_url]
        """
        # 產生唯一 ID
        photo_id = str(uuid.uuid4())

        # 取得使用者目錄
        user_dir = self._get_user_photo_dir(user_id)

        # 處理主圖
        processed_image = self._process_image(file_content, MAX_IMAGE_SIZE)
        photo_filename = f"{photo_id}.jpg"
        photo_path = user_dir / photo_filename

        # 建立縮圖
        thumbnail_content = self._create_thumbnail(file_content)
        thumbnail_filename = f"{photo_id}_thumb.jpg"
        thumbnail_path = user_dir / thumbnail_filename

        # 寫入檔案
        try:
            with open(photo_path, "wb") as f:
                f.write(processed_image)

            with open(thumbnail_path, "wb") as f:
                f.write(thumbnail_content)

            logger.info(f"Photo saved: {photo_path}")

        except Exception as e:
            # 清理失敗的檔案
            if photo_path.exists():
                photo_path.unlink()
            if thumbnail_path.exists():
                thumbnail_path.unlink()
            logger.error(f"Failed to save photo: {e}")
            raise

        # 回傳 URL 路徑
        photo_url = f"/uploads/photos/{user_id}/{photo_filename}"
        thumbnail_url = f"/uploads/photos/{user_id}/{thumbnail_filename}"

        return photo_id, photo_url, thumbnail_url

    async def delete_photo(self, photo_url: str) -> bool:
        """
        刪除照片及其縮圖

        Args:
            photo_url: 照片 URL 路徑

        Returns:
            是否刪除成功
        """
        if not photo_url:
            return False

        try:
            # 從 URL 路徑取得檔案路徑
            # /uploads/photos/{user_id}/{filename} -> photos/{user_id}/{filename}
            # 移除 /uploads/ 前綴
            relative_path = photo_url.lstrip("/")
            if relative_path.startswith("uploads/"):
                relative_path = relative_path[8:]  # 移除 "uploads/"

            photo_path = self.upload_dir / relative_path

            # 刪除主圖
            if photo_path.exists():
                photo_path.unlink()
                logger.info(f"Deleted photo: {photo_path}")
            else:
                logger.warning(f"Photo not found: {photo_path}")
                return False

            # 刪除縮圖（如果原本不是縮圖的話）
            if "_thumb" not in photo_path.stem:
                thumbnail_path = photo_path.with_name(
                    photo_path.stem + "_thumb" + photo_path.suffix
                )
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
                    logger.info(f"Deleted thumbnail: {thumbnail_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete photo {photo_url}: {e}")
            return False

    def validate_image(self, content_type: str, file_size: int) -> Optional[str]:
        """
        驗證圖片

        Args:
            content_type: MIME 類型
            file_size: 檔案大小

        Returns:
            錯誤訊息，None 表示通過驗證
        """
        if content_type not in ALLOWED_MIME_TYPES:
            return f"不支援的圖片格式，僅支援: {', '.join(ALLOWED_EXTENSIONS)}"

        if file_size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE / 1024 / 1024
            return f"檔案過大，最大允許 {max_mb:.0f}MB"

        if file_size == 0:
            return "檔案不能為空"

        return None

    def _process_gif_thumbnail(self, file_content: bytes) -> bytes:
        """
        建立 GIF 縮圖（使用第一幀）

        Args:
            file_content: 原始 GIF 檔案內容

        Returns:
            縮圖內容（JPEG 格式）
        """
        img = Image.open(io.BytesIO(file_content))

        # 取得第一幀
        if hasattr(img, "n_frames") and img.n_frames > 1:
            img.seek(0)

        # 轉換為 RGB
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 建立縮圖（裁切為正方形）
        width, height = img.size
        min_dim = min(width, height)

        # 從中心裁切
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim

        img = img.crop((left, top, right, bottom))
        img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

        # 儲存到記憶體
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=80, optimize=True)
        output.seek(0)

        return output.read()

    async def save_chat_image(
        self,
        match_id: str,
        user_id: str,
        file_content: bytes,
        filename: str,
        content_type: str,
    ) -> Tuple[str, str, str, int, int, bool]:
        """
        儲存聊天圖片及縮圖

        Args:
            match_id: 配對 ID
            user_id: 使用者 ID
            file_content: 檔案內容
            filename: 原始檔名
            content_type: MIME 類型

        Returns:
            Tuple[image_id, image_url, thumbnail_url, width, height, is_gif]
        """
        # 產生唯一 ID
        image_id = str(uuid.uuid4())

        # 取得聊天圖片目錄
        chat_image_dir = self._get_chat_image_dir(match_id)

        # 判斷是否為 GIF
        is_gif = content_type == "image/gif"

        # 取得原始圖片尺寸
        img = Image.open(io.BytesIO(file_content))
        original_width, original_height = img.size

        if is_gif:
            # GIF 保持原格式
            image_filename = f"{image_id}.gif"
            image_path = chat_image_dir / image_filename

            # 縮圖使用第一幀
            thumbnail_content = self._process_gif_thumbnail(file_content)
            thumbnail_filename = f"{image_id}_thumb.jpg"
            thumbnail_path = chat_image_dir / thumbnail_filename

            # 寫入檔案
            try:
                with open(image_path, "wb") as f:
                    f.write(file_content)

                with open(thumbnail_path, "wb") as f:
                    f.write(thumbnail_content)

                logger.info(f"Chat GIF saved: {image_path}")

            except Exception as e:
                # 清理失敗的檔案
                if image_path.exists():
                    image_path.unlink()
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
                logger.error(f"Failed to save chat GIF: {e}")
                raise

        else:
            # 一般圖片處理
            processed_image = self._process_image(file_content, MAX_IMAGE_SIZE)
            image_filename = f"{image_id}.jpg"
            image_path = chat_image_dir / image_filename

            # 建立縮圖
            thumbnail_content = self._create_thumbnail(file_content)
            thumbnail_filename = f"{image_id}_thumb.jpg"
            thumbnail_path = chat_image_dir / thumbnail_filename

            # 寫入檔案
            try:
                with open(image_path, "wb") as f:
                    f.write(processed_image)

                with open(thumbnail_path, "wb") as f:
                    f.write(thumbnail_content)

                logger.info(f"Chat image saved: {image_path}")

            except Exception as e:
                # 清理失敗的檔案
                if image_path.exists():
                    image_path.unlink()
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
                logger.error(f"Failed to save chat image: {e}")
                raise

        # 回傳 URL 路徑
        image_url = f"/uploads/chat/{match_id}/{image_filename}"
        thumbnail_url = f"/uploads/chat/{match_id}/{thumbnail_filename}"

        return image_id, image_url, thumbnail_url, original_width, original_height, is_gif


# 建立單例
file_storage = FileStorageService()
