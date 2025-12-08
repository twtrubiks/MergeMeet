"""檔案儲存服務測試"""
import pytest
import os
import io
import tempfile
import shutil
from pathlib import Path
from PIL import Image
from unittest.mock import patch, MagicMock

from app.services.file_storage import FileStorageService, file_storage
from app.core.config import settings


@pytest.fixture
def temp_upload_dir():
    """建立臨時上傳目錄"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage_service(temp_upload_dir):
    """建立使用臨時目錄的儲存服務"""
    with patch.object(settings, 'UPLOAD_DIR', temp_upload_dir):
        service = FileStorageService()
        yield service


@pytest.fixture
def sample_image_bytes():
    """產生測試用 JPEG 圖片"""
    img = Image.new('RGB', (800, 600), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def large_image_bytes():
    """產生大型測試圖片（超過 1200x1200）"""
    img = Image.new('RGB', (2000, 1500), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
def png_image_bytes():
    """產生測試用 PNG 圖片（含透明通道）"""
    img = Image.new('RGBA', (400, 400), color=(255, 0, 0, 128))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.read()


class TestFileStorageService:
    """檔案儲存服務單元測試"""

    def test_init_creates_directories(self, temp_upload_dir):
        """測試初始化時建立必要目錄"""
        with patch.object(settings, 'UPLOAD_DIR', temp_upload_dir):
            service = FileStorageService()

            assert service.upload_dir.exists()
            assert service.photos_dir.exists()

    def test_get_user_photo_dir_creates_directory(self, storage_service, temp_upload_dir):
        """測試取得使用者目錄時會自動建立"""
        user_id = "test-user-123"
        user_dir = storage_service._get_user_photo_dir(user_id)

        expected_path = Path(temp_upload_dir) / "photos" / user_id
        assert user_dir == expected_path
        assert user_dir.exists()

    def test_get_file_extension_from_content_type(self, storage_service):
        """測試從 content_type 取得副檔名"""
        assert storage_service._get_file_extension("test.jpg", "image/jpeg") == "jpg"
        assert storage_service._get_file_extension("test.png", "image/png") == "png"
        assert storage_service._get_file_extension("test.gif", "image/gif") == "gif"
        assert storage_service._get_file_extension("test.webp", "image/webp") == "webp"

    def test_get_file_extension_from_filename(self, storage_service):
        """測試從檔名取得副檔名（當 content_type 無效時）"""
        assert storage_service._get_file_extension("photo.jpg", "application/octet-stream") == "jpg"
        assert storage_service._get_file_extension("photo.png", "unknown") == "png"

    def test_get_file_extension_default(self, storage_service):
        """測試預設副檔名"""
        assert storage_service._get_file_extension("noext", "unknown") == "jpg"
        assert storage_service._get_file_extension("", "") == "jpg"


class TestImageValidation:
    """圖片驗證測試"""

    def test_validate_image_valid_jpeg(self, storage_service):
        """測試有效的 JPEG 圖片"""
        error = storage_service.validate_image("image/jpeg", 1024 * 1024)  # 1MB
        assert error is None

    def test_validate_image_valid_png(self, storage_service):
        """測試有效的 PNG 圖片"""
        error = storage_service.validate_image("image/png", 2 * 1024 * 1024)  # 2MB
        assert error is None

    def test_validate_image_invalid_type(self, storage_service):
        """測試無效的檔案類型"""
        error = storage_service.validate_image("application/pdf", 1024)
        assert error is not None
        assert "不支援" in error

    def test_validate_image_too_large(self, storage_service):
        """測試檔案過大"""
        error = storage_service.validate_image("image/jpeg", 10 * 1024 * 1024)  # 10MB
        assert error is not None
        assert "過大" in error

    def test_validate_image_empty_file(self, storage_service):
        """測試空檔案"""
        error = storage_service.validate_image("image/jpeg", 0)
        assert error is not None
        assert "空" in error

    def test_validate_image_text_file(self, storage_service):
        """測試文字檔案"""
        error = storage_service.validate_image("text/plain", 100)
        assert error is not None


class TestImageProcessing:
    """圖片處理測試"""

    def test_process_image_resize(self, storage_service, large_image_bytes):
        """測試圖片縮放"""
        processed = storage_service._process_image(large_image_bytes, (1200, 1200))

        # 驗證處理後的圖片
        img = Image.open(io.BytesIO(processed))
        assert img.width <= 1200
        assert img.height <= 1200

    def test_process_image_keeps_smaller(self, storage_service, sample_image_bytes):
        """測試小於最大尺寸的圖片不會放大"""
        processed = storage_service._process_image(sample_image_bytes, (1200, 1200))

        img = Image.open(io.BytesIO(processed))
        # 原始 800x600，不應該被放大
        assert img.width <= 800
        assert img.height <= 600

    def test_process_image_converts_to_rgb(self, storage_service, png_image_bytes):
        """測試 RGBA 轉換為 RGB"""
        processed = storage_service._process_image(png_image_bytes, (1200, 1200))

        img = Image.open(io.BytesIO(processed))
        assert img.mode == "RGB"

    def test_create_thumbnail_square(self, storage_service, sample_image_bytes):
        """測試縮圖為正方形"""
        thumbnail = storage_service._create_thumbnail(sample_image_bytes)

        img = Image.open(io.BytesIO(thumbnail))
        assert img.width == img.height  # 正方形
        assert img.width <= 200

    def test_create_thumbnail_center_crop(self, storage_service, large_image_bytes):
        """測試縮圖中心裁切"""
        thumbnail = storage_service._create_thumbnail(large_image_bytes)

        img = Image.open(io.BytesIO(thumbnail))
        assert img.width == 200
        assert img.height == 200


class TestSavePhoto:
    """照片儲存測試"""

    @pytest.mark.asyncio
    async def test_save_photo_creates_files(self, storage_service, sample_image_bytes, temp_upload_dir):
        """測試儲存照片會建立主圖和縮圖"""
        user_id = "user-123"

        photo_id, photo_url, thumbnail_url = await storage_service.save_photo(
            user_id=user_id,
            file_content=sample_image_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )

        # 驗證回傳值
        assert photo_id is not None
        assert f"/uploads/photos/{user_id}/" in photo_url
        assert f"/uploads/photos/{user_id}/" in thumbnail_url
        assert "_thumb" in thumbnail_url

        # 驗證檔案存在
        photo_path = Path(temp_upload_dir) / photo_url.lstrip("/uploads/")
        thumbnail_path = Path(temp_upload_dir) / thumbnail_url.lstrip("/uploads/")

        # 由於路徑是 /uploads/photos/... 而 temp_dir 不包含 uploads
        # 需要調整路徑
        photo_path = Path(temp_upload_dir) / "photos" / user_id / f"{photo_id}.jpg"
        thumbnail_path = Path(temp_upload_dir) / "photos" / user_id / f"{photo_id}_thumb.jpg"

        assert photo_path.exists()
        assert thumbnail_path.exists()

    @pytest.mark.asyncio
    async def test_save_photo_processes_image(self, storage_service, large_image_bytes, temp_upload_dir):
        """測試儲存照片時會處理圖片"""
        user_id = "user-456"

        photo_id, photo_url, thumbnail_url = await storage_service.save_photo(
            user_id=user_id,
            file_content=large_image_bytes,
            filename="large.jpg",
            content_type="image/jpeg"
        )

        # 讀取儲存的主圖
        photo_path = Path(temp_upload_dir) / "photos" / user_id / f"{photo_id}.jpg"
        with open(photo_path, "rb") as f:
            saved_image = Image.open(f)
            # 確認已縮小
            assert saved_image.width <= 1200
            assert saved_image.height <= 1200

    @pytest.mark.asyncio
    async def test_save_photo_unique_ids(self, storage_service, sample_image_bytes):
        """測試每次儲存產生唯一 ID"""
        user_id = "user-789"

        id1, _, _ = await storage_service.save_photo(
            user_id=user_id,
            file_content=sample_image_bytes,
            filename="test1.jpg",
            content_type="image/jpeg"
        )

        id2, _, _ = await storage_service.save_photo(
            user_id=user_id,
            file_content=sample_image_bytes,
            filename="test2.jpg",
            content_type="image/jpeg"
        )

        assert id1 != id2


class TestDeletePhoto:
    """照片刪除測試"""

    @pytest.mark.asyncio
    async def test_delete_photo_removes_files(self, storage_service, sample_image_bytes, temp_upload_dir):
        """測試刪除照片會移除檔案"""
        user_id = "user-del-1"

        # 先儲存照片
        photo_id, photo_url, thumbnail_url = await storage_service.save_photo(
            user_id=user_id,
            file_content=sample_image_bytes,
            filename="to_delete.jpg",
            content_type="image/jpeg"
        )

        photo_path = Path(temp_upload_dir) / "photos" / user_id / f"{photo_id}.jpg"
        thumbnail_path = Path(temp_upload_dir) / "photos" / user_id / f"{photo_id}_thumb.jpg"

        # 確認檔案存在
        assert photo_path.exists()
        assert thumbnail_path.exists()

        # 刪除主圖
        result = await storage_service.delete_photo(photo_url)
        assert result is True

        # 確認主圖已刪除
        assert not photo_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_photo(self, storage_service):
        """測試刪除不存在的照片"""
        result = await storage_service.delete_photo("/uploads/photos/fake/nonexistent.jpg")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_photo_empty_url(self, storage_service):
        """測試刪除空 URL"""
        result = await storage_service.delete_photo("")
        assert result is False

        result = await storage_service.delete_photo(None)
        assert result is False


class TestIntegration:
    """整合測試"""

    @pytest.mark.asyncio
    async def test_full_upload_delete_cycle(self, storage_service, sample_image_bytes, temp_upload_dir):
        """測試完整的上傳-刪除流程"""
        user_id = "integration-user"

        # 1. 上傳照片
        photo_id, photo_url, thumbnail_url = await storage_service.save_photo(
            user_id=user_id,
            file_content=sample_image_bytes,
            filename="lifecycle.jpg",
            content_type="image/jpeg"
        )

        photo_path = Path(temp_upload_dir) / "photos" / user_id / f"{photo_id}.jpg"
        thumbnail_path = Path(temp_upload_dir) / "photos" / user_id / f"{photo_id}_thumb.jpg"

        # 2. 驗證檔案存在
        assert photo_path.exists()
        assert thumbnail_path.exists()

        # 3. 驗證可以讀取圖片
        with open(photo_path, "rb") as f:
            img = Image.open(f)
            assert img.format == "JPEG"

        with open(thumbnail_path, "rb") as f:
            thumb = Image.open(f)
            assert thumb.format == "JPEG"
            assert thumb.width == thumb.height  # 正方形

        # 4. 刪除照片
        await storage_service.delete_photo(photo_url)
        await storage_service.delete_photo(thumbnail_url)

        # 5. 驗證檔案已刪除
        assert not photo_path.exists()
        assert not thumbnail_path.exists()

    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self, storage_service, sample_image_bytes, temp_upload_dir):
        """測試多個使用者的檔案隔離"""
        user1 = "user-a"
        user2 = "user-b"

        # 為兩個使用者上傳照片
        id1, url1, _ = await storage_service.save_photo(
            user_id=user1,
            file_content=sample_image_bytes,
            filename="photo1.jpg",
            content_type="image/jpeg"
        )

        id2, url2, _ = await storage_service.save_photo(
            user_id=user2,
            file_content=sample_image_bytes,
            filename="photo2.jpg",
            content_type="image/jpeg"
        )

        # 確認存放在不同目錄
        assert user1 in url1
        assert user2 in url2
        assert user1 not in url2
        assert user2 not in url1

        # 確認各自的檔案存在
        path1 = Path(temp_upload_dir) / "photos" / user1 / f"{id1}.jpg"
        path2 = Path(temp_upload_dir) / "photos" / user2 / f"{id2}.jpg"

        assert path1.exists()
        assert path2.exists()

        # 刪除 user1 的照片不影響 user2
        await storage_service.delete_photo(url1)

        assert not path1.exists()
        assert path2.exists()


class TestEdgeCases:
    """邊界情況測試"""

    @pytest.mark.asyncio
    async def test_special_characters_in_user_id(self, storage_service, sample_image_bytes):
        """測試特殊字元的使用者 ID"""
        # UUID 格式的使用者 ID
        user_id = "550e8400-e29b-41d4-a716-446655440000"

        photo_id, photo_url, _ = await storage_service.save_photo(
            user_id=user_id,
            file_content=sample_image_bytes,
            filename="test.jpg",
            content_type="image/jpeg"
        )

        assert user_id in photo_url
        assert photo_id is not None

    def test_validate_boundary_file_size(self, storage_service):
        """測試檔案大小邊界值"""
        # 剛好 5MB（假設限制是 5MB）
        max_size = settings.MAX_UPLOAD_SIZE

        # 剛好在限制內
        error = storage_service.validate_image("image/jpeg", max_size)
        assert error is None

        # 超過限制 1 byte
        error = storage_service.validate_image("image/jpeg", max_size + 1)
        assert error is not None

    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, storage_service, sample_image_bytes):
        """測試並發上傳"""
        import asyncio

        user_id = "concurrent-user"

        async def upload():
            return await storage_service.save_photo(
                user_id=user_id,
                file_content=sample_image_bytes,
                filename="concurrent.jpg",
                content_type="image/jpeg"
            )

        # 同時上傳 5 張照片
        results = await asyncio.gather(*[upload() for _ in range(5)])

        # 確認所有 ID 都不同
        ids = [r[0] for r in results]
        assert len(set(ids)) == 5  # 5 個唯一 ID
