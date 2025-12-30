"""照片排序與主頭像設定 API 測試"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, patch
import uuid
import io
from PIL import Image

from app.models.profile import Photo


def create_test_image():
    """創建一個有效的測試 JPEG 圖片"""
    img = Image.new('RGB', (800, 600), color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer


@pytest.fixture
def mock_file_storage():
    """Mock 檔案儲存服務"""
    with patch("app.api.profile.file_storage") as mock:
        # save_photo 返回 (photo_id, photo_url, thumbnail_url)
        mock.save_photo = AsyncMock(return_value=(
            str(uuid.uuid4()),
            "/uploads/photos/test/test.jpg",
            "/uploads/photos/test/test_thumb.jpg"
        ))
        mock.delete_photo = AsyncMock(return_value=True)
        yield mock


async def create_profile_with_photos(
    client: AsyncClient,
    headers: dict,
    mock_file_storage,
    num_photos: int = 3
) -> list[str]:
    """建立 Profile 並上傳指定數量的照片

    Returns:
        list[str]: 按 display_order 排序的照片 ID 列表
    """
    # 建立 Profile
    profile_data = {
        "display_name": "測試用戶",
        "gender": "male",
        "bio": "測試個人簡介"
    }
    resp = await client.post("/api/profile", json=profile_data, headers=headers)
    assert resp.status_code == 201

    # 上傳照片
    photo_ids = []
    for i in range(num_photos):
        # 使用有效的 JPEG 圖片
        file_content = create_test_image()
        files = {"file": (f"test_{i}.jpg", file_content, "image/jpeg")}
        resp = await client.post("/api/profile/photos", files=files, headers=headers)
        assert resp.status_code == 201
        photo_ids.append(resp.json()["id"])

    return photo_ids


class TestReorderPhotos:
    """照片排序測試"""

    @pytest.mark.asyncio
    async def test_reorder_photos_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """正常排序：反轉照片順序"""
        # 建立 3 張照片
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=3
        )

        # 反轉順序
        new_order = list(reversed(photo_ids))
        resp = await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": new_order},
            headers=auth_headers
        )

        assert resp.status_code == 200
        result = resp.json()
        assert len(result) == 3

        # 驗證順序已更新
        for i, photo in enumerate(result):
            assert photo["id"] == new_order[i]
            assert photo["display_order"] == i

    @pytest.mark.asyncio
    async def test_reorder_photos_partial_swap(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """正常排序：交換前兩張照片"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=3
        )

        # 交換前兩張
        new_order = [photo_ids[1], photo_ids[0], photo_ids[2]]
        resp = await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": new_order},
            headers=auth_headers
        )

        assert resp.status_code == 200
        result = resp.json()
        assert result[0]["id"] == photo_ids[1]
        assert result[1]["id"] == photo_ids[0]
        assert result[2]["id"] == photo_ids[2]

    @pytest.mark.asyncio
    async def test_reorder_photos_invalid_count(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """錯誤：照片數量不符"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=3
        )

        # 只傳 2 張照片 ID
        resp = await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": photo_ids[:2]},
            headers=auth_headers
        )

        assert resp.status_code == 400
        assert "數量不符" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_reorder_photos_invalid_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """錯誤：傳入不存在的照片 ID"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=2
        )

        # 替換一個 ID 為假的
        fake_id = str(uuid.uuid4())
        resp = await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": [photo_ids[0], fake_id]},
            headers=auth_headers
        )

        assert resp.status_code == 400
        assert "不存在或不屬於此用戶" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_reorder_photos_duplicate_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """錯誤：傳入重複的照片 ID"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=2
        )

        # 重複傳入同一個 ID
        resp = await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": [photo_ids[0], photo_ids[0]]},
            headers=auth_headers
        )

        assert resp.status_code == 400
        assert "重複" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_reorder_photos_unauthorized(
        self,
        client: AsyncClient
    ):
        """錯誤：未登入"""
        resp = await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": [str(uuid.uuid4())]}
        )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_reorder_photos_no_profile(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """錯誤：無 Profile"""
        resp = await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": [str(uuid.uuid4())]},
            headers=auth_headers
        )

        assert resp.status_code == 404
        assert "個人檔案不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_reorder_single_photo(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """邊界：只有一張照片時也能正常排序"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=1
        )

        resp = await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": photo_ids},
            headers=auth_headers
        )

        assert resp.status_code == 200
        result = resp.json()
        assert len(result) == 1
        assert result[0]["id"] == photo_ids[0]

    @pytest.mark.asyncio
    async def test_order_persists_after_fetch(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """驗證：排序後重新取得 Profile 順序正確"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=3
        )

        # 反轉順序
        new_order = list(reversed(photo_ids))
        await client.put(
            "/api/profile/photos/order",
            json={"photo_ids": new_order},
            headers=auth_headers
        )

        # 重新取得 Profile
        resp = await client.get("/api/profile", headers=auth_headers)
        assert resp.status_code == 200

        photos = resp.json()["photos"]
        for i, photo in enumerate(photos):
            assert photo["id"] == new_order[i]
            assert photo["display_order"] == i


async def approve_photos(
    test_db: AsyncSession,
    photo_ids: list[str]
):
    """將指定照片設為已審核通過"""
    for photo_id in photo_ids:
        result = await test_db.execute(
            select(Photo).where(Photo.id == uuid.UUID(photo_id))
        )
        photo = result.scalar_one_or_none()
        if photo:
            photo.moderation_status = "APPROVED"
    await test_db.commit()


class TestSetProfilePicture:
    """設定主頭像測試"""

    @pytest.mark.asyncio
    async def test_set_profile_picture_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage,
        test_db: AsyncSession
    ):
        """正常設定主頭像：將第二張照片設為主頭像"""
        # 建立 3 張照片
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=3
        )

        # 將所有照片設為已審核通過
        await approve_photos(test_db, photo_ids)

        # 將第二張照片設為主頭像
        resp = await client.put(
            f"/api/profile/photos/{photo_ids[1]}/primary",
            headers=auth_headers
        )

        assert resp.status_code == 200
        result = resp.json()
        assert result["id"] == photo_ids[1]
        assert result["is_profile_picture"] is True
        assert result["display_order"] == 0  # 應該移到第一位

    @pytest.mark.asyncio
    async def test_set_profile_picture_reorders(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage,
        test_db: AsyncSession
    ):
        """驗證設定主頭像後順序調整正確"""
        # 建立 3 張照片：[0, 1, 2]
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=3
        )
        await approve_photos(test_db, photo_ids)

        # 將第三張（index=2）設為主頭像
        await client.put(
            f"/api/profile/photos/{photo_ids[2]}/primary",
            headers=auth_headers
        )

        # 取得 Profile 驗證順序
        resp = await client.get("/api/profile", headers=auth_headers)
        assert resp.status_code == 200

        photos = resp.json()["photos"]
        # 新順序應為 [photo_ids[2], photo_ids[0], photo_ids[1]]
        assert photos[0]["id"] == photo_ids[2]
        assert photos[0]["display_order"] == 0
        assert photos[0]["is_profile_picture"] is True

        assert photos[1]["id"] == photo_ids[0]
        assert photos[1]["display_order"] == 1

        assert photos[2]["id"] == photo_ids[1]
        assert photos[2]["display_order"] == 2

    @pytest.mark.asyncio
    async def test_set_profile_picture_pending_photo(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """錯誤：待審核的照片不能設為主頭像"""
        # 建立照片（預設為 PENDING 狀態）
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=2
        )

        # 嘗試將 PENDING 照片設為主頭像
        resp = await client.put(
            f"/api/profile/photos/{photo_ids[1]}/primary",
            headers=auth_headers
        )

        assert resp.status_code == 400
        assert "已通過審核" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_profile_picture_rejected_photo(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage,
        test_db: AsyncSession
    ):
        """錯誤：被拒絕的照片不能設為主頭像"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=2
        )

        # 將第二張照片設為 REJECTED
        result = await test_db.execute(
            select(Photo).where(Photo.id == uuid.UUID(photo_ids[1]))
        )
        photo = result.scalar_one()
        photo.moderation_status = "REJECTED"
        await test_db.commit()

        # 嘗試將 REJECTED 照片設為主頭像
        resp = await client.put(
            f"/api/profile/photos/{photo_ids[1]}/primary",
            headers=auth_headers
        )

        assert resp.status_code == 400
        assert "已通過審核" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_profile_picture_invalid_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage
    ):
        """錯誤：照片 ID 不存在"""
        # 建立 Profile
        await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=1
        )

        # 使用不存在的照片 ID
        fake_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/profile/photos/{fake_id}/primary",
            headers=auth_headers
        )

        assert resp.status_code == 404
        assert "不存在或不屬於此用戶" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_profile_picture_unauthorized(
        self,
        client: AsyncClient
    ):
        """錯誤：未登入"""
        fake_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/profile/photos/{fake_id}/primary"
        )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_set_profile_picture_no_profile(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """錯誤：無 Profile"""
        fake_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/profile/photos/{fake_id}/primary",
            headers=auth_headers
        )

        assert resp.status_code == 404
        assert "個人檔案不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_profile_picture_already_primary(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage,
        test_db: AsyncSession
    ):
        """邊界：將已是主頭像的照片再次設定"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=2
        )
        await approve_photos(test_db, photo_ids)

        # 第一張照片預設就是主頭像，將其再次設為主頭像
        resp = await client.put(
            f"/api/profile/photos/{photo_ids[0]}/primary",
            headers=auth_headers
        )

        assert resp.status_code == 200
        result = resp.json()
        assert result["id"] == photo_ids[0]
        assert result["is_profile_picture"] is True
        assert result["display_order"] == 0  # 順序不變

    @pytest.mark.asyncio
    async def test_set_profile_picture_persists_after_fetch(
        self,
        client: AsyncClient,
        auth_headers: dict,
        mock_file_storage,
        test_db: AsyncSession
    ):
        """驗證：設定後重新取得 Profile 主頭像正確"""
        photo_ids = await create_profile_with_photos(
            client, auth_headers, mock_file_storage, num_photos=3
        )
        await approve_photos(test_db, photo_ids)

        # 將第三張設為主頭像
        await client.put(
            f"/api/profile/photos/{photo_ids[2]}/primary",
            headers=auth_headers
        )

        # 重新取得 Profile
        resp = await client.get("/api/profile", headers=auth_headers)
        assert resp.status_code == 200

        photos = resp.json()["photos"]
        # 主頭像應該在第一位
        assert photos[0]["id"] == photo_ids[2]
        assert photos[0]["is_profile_picture"] is True

        # 其他照片不是主頭像
        assert photos[1]["is_profile_picture"] is False
        assert photos[2]["is_profile_picture"] is False
