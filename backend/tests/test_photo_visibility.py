"""照片公開可見性測試

驗證巡邏制審核語意在所有公開面的落地：
- PENDING 照片可見（先上架、事後審核）
- REJECTED 照片不得出現在探索卡片、配對列表、對話頭像
- 完整度只計算未被駁回的照片
"""

import uuid
from io import BytesIO

import pytest
import pytest_asyncio
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.discovery import _get_user_avatar
from app.models.match import Match
from app.models.profile import InterestTag, Photo, Profile, check_profile_completeness
from app.models.user import User


def _create_test_image() -> BytesIO:
    """創建一個有效的測試 JPEG 圖片"""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer


async def _upload_photo(client: AsyncClient, token: str) -> dict:
    """上傳一張照片並回傳 PhotoResponse"""
    response = await client.post(
        "/api/profile/photos",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("photo.jpg", _create_test_image(), "image/jpeg")},
    )
    assert response.status_code == 201, f"Failed to upload photo: {response.text}"
    return response.json()


async def _reject_photo(test_db: AsyncSession, photo_id: str):
    """將照片標記為審核駁回"""
    result = await test_db.execute(select(Photo).where(Photo.id == uuid.UUID(photo_id)))
    photo = result.scalar_one()
    photo.moderation_status = "REJECTED"
    photo.rejection_reason = "測試駁回"
    await test_db.commit()


async def _create_match(test_db: AsyncSession, user_a: uuid.UUID, user_b: uuid.UUID) -> str:
    """直接建立配對（確保 user1_id < user2_id）"""
    user1_id, user2_id = (user_a, user_b) if user_a < user_b else (user_b, user_a)
    match = Match(user1_id=user1_id, user2_id=user2_id, status="ACTIVE")
    test_db.add(match)
    await test_db.commit()
    await test_db.refresh(match)
    return str(match.id)


@pytest_asyncio.fixture
async def visibility_profiles(client: AsyncClient, auth_user_pair: dict, test_db: AsyncSession):
    """建立 Alice / Bob 完整檔案；Bob 有兩張照片（第一張為主頭像）"""
    alice_token = auth_user_pair["alice"]["token"]
    bob_token = auth_user_pair["bob"]["token"]

    for name, gender, token, prefs in [
        ("Alice", "female", alice_token, {"gender_preference": "male"}),
        ("Bob", "male", bob_token, {"gender_preference": "female"}),
    ]:
        response = await client.post(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "display_name": name,
                "gender": gender,
                "bio": "喜歡旅遊和美食",
                "location": {
                    "latitude": 25.0330,
                    "longitude": 121.5654,
                    "location_name": "台北市信義區",
                },
            },
        )
        assert response.status_code == 201, f"Failed to create {name} profile: {response.text}"

        response = await client.patch(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"min_age_preference": 18, "max_age_preference": 99, **prefs},
        )
        assert response.status_code == 200, f"Failed to update {name} prefs: {response.text}"

    # 建立興趣標籤並設定給雙方
    result = await test_db.execute(select(InterestTag).limit(4))
    tags = result.scalars().all()
    if len(tags) < 4:
        for tag in [
            InterestTag(name="旅遊", category="lifestyle", icon="✈️"),
            InterestTag(name="美食", category="lifestyle", icon="🍔"),
            InterestTag(name="運動", category="sports", icon="⚽"),
            InterestTag(name="音樂", category="entertainment", icon="🎵"),
        ]:
            test_db.add(tag)
        await test_db.commit()
        result = await test_db.execute(select(InterestTag).limit(4))
        tags = result.scalars().all()

    tag_ids = [str(tag.id) for tag in tags[:4]]
    for token in (alice_token, bob_token):
        response = await client.put(
            "/api/profile/interests",
            headers={"Authorization": f"Bearer {token}"},
            json={"interest_ids": tag_ids},
        )
        assert response.status_code == 200, f"Failed to set interests: {response.text}"

    # Alice 一張照片、Bob 兩張照片（第一張自動成為主頭像）
    await _upload_photo(client, alice_token)
    bob_photos = [await _upload_photo(client, bob_token) for _ in range(2)]

    # 取得雙方 user_id
    users = {}
    for name in ("alice", "bob"):
        result = await test_db.execute(
            select(User).where(User.email == auth_user_pair[name]["email"])
        )
        users[name] = result.scalar_one()

    return {
        "alice": {"token": alice_token, "user_id": users["alice"].id},
        "bob": {"token": bob_token, "user_id": users["bob"].id},
        "bob_photos": bob_photos,
    }


@pytest.mark.asyncio
async def test_browse_hides_rejected_photo(
    client: AsyncClient, visibility_profiles: dict, test_db: AsyncSession
):
    """探索卡片不含 REJECTED 照片，但 PENDING 照片可見（巡邏制）"""
    rejected, pending = visibility_profiles["bob_photos"]
    await _reject_photo(test_db, rejected["id"])

    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {visibility_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    bob_card = next(
        (u for u in response.json() if u["user_id"] == str(visibility_profiles["bob"]["user_id"])),
        None,
    )
    assert bob_card is not None, "Bob 應出現在探索結果中（PENDING 照片不影響上架）"
    assert rejected["url"] not in bob_card["photos"]
    assert pending["url"] in bob_card["photos"]


@pytest.mark.asyncio
async def test_matches_list_hides_rejected_photo(
    client: AsyncClient, visibility_profiles: dict, test_db: AsyncSession
):
    """配對列表不含 REJECTED 照片"""
    rejected, pending = visibility_profiles["bob_photos"]
    await _reject_photo(test_db, rejected["id"])
    await _create_match(
        test_db, visibility_profiles["alice"]["user_id"], visibility_profiles["bob"]["user_id"]
    )

    response = await client.get(
        "/api/discovery/matches",
        headers={"Authorization": f"Bearer {visibility_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    matches = response.json()
    assert len(matches) == 1
    photos = matches[0]["matched_user"]["photos"]
    assert rejected["url"] not in photos
    assert pending["url"] in photos


@pytest.mark.asyncio
async def test_conversation_avatar_skips_rejected_photo(
    client: AsyncClient, visibility_profiles: dict, test_db: AsyncSession
):
    """對話列表頭像不使用 REJECTED 照片，改用下一張可見照片"""
    rejected, pending = visibility_profiles["bob_photos"]
    await _reject_photo(test_db, rejected["id"])  # 主頭像被駁回
    await _create_match(
        test_db, visibility_profiles["alice"]["user_id"], visibility_profiles["bob"]["user_id"]
    )

    response = await client.get(
        "/api/messages/conversations",
        headers={"Authorization": f"Bearer {visibility_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    conversations = response.json()
    assert len(conversations) == 1
    assert conversations[0]["other_user_avatar"] == pending["url"]
    assert conversations[0]["other_user_avatar_thumb"] == pending["thumbnail_url"]


@pytest.mark.asyncio
async def test_conversation_avatar_none_when_all_rejected(
    client: AsyncClient, visibility_profiles: dict, test_db: AsyncSession
):
    """對方所有照片皆被駁回時，頭像為 None"""
    for photo in visibility_profiles["bob_photos"]:
        await _reject_photo(test_db, photo["id"])
    await _create_match(
        test_db, visibility_profiles["alice"]["user_id"], visibility_profiles["bob"]["user_id"]
    )

    response = await client.get(
        "/api/messages/conversations",
        headers={"Authorization": f"Bearer {visibility_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    conversations = response.json()
    assert len(conversations) == 1
    assert conversations[0]["other_user_avatar"] is None
    assert conversations[0]["other_user_avatar_thumb"] is None


# ========== 完整度與 public_photos 單元測試（不需資料庫） ==========


def _make_profile(photos: list[Photo]) -> Profile:
    """建立含基本資料與 3 個興趣的暫時性 Profile"""
    profile = Profile(display_name="測試用戶", gender="male", bio="測試簡介")
    profile.photos = photos
    profile.interests = [InterestTag(name=f"tag{i}", category="lifestyle") for i in range(3)]
    return profile


def test_completeness_ignores_rejected_photos():
    """完整度：只有被駁回的照片時不算完整"""
    profile = _make_profile(
        [Photo(url="/uploads/a.jpg", display_order=0, moderation_status="REJECTED")]
    )
    assert check_profile_completeness(profile) is False


def test_completeness_counts_pending_photo():
    """完整度：PENDING 照片計入（巡邏制）"""
    profile = _make_profile(
        [Photo(url="/uploads/a.jpg", display_order=0, moderation_status="PENDING")]
    )
    assert check_profile_completeness(profile) is True


def test_public_photos_filters_rejected_and_sorts():
    """public_photos：排除 REJECTED 並依 display_order 排序"""
    photo_b = Photo(url="/uploads/b.jpg", display_order=1, moderation_status="APPROVED")
    photo_a = Photo(url="/uploads/a.jpg", display_order=0, moderation_status="PENDING")
    rejected = Photo(url="/uploads/x.jpg", display_order=2, moderation_status="REJECTED")
    profile = _make_profile([photo_b, rejected, photo_a])

    assert [p.url for p in profile.public_photos] == ["/uploads/a.jpg", "/uploads/b.jpg"]


def test_match_notification_avatar_skips_rejected_photo():
    """配對通知頭像：REJECTED 照片即使掛著主頭像旗標也不得回傳"""
    rejected_primary = Photo(
        url="/uploads/x.jpg",
        display_order=0,
        moderation_status="REJECTED",
        is_profile_picture=True,
    )
    pending = Photo(
        url="/uploads/a.jpg",
        display_order=1,
        moderation_status="PENDING",
        is_profile_picture=False,
    )
    profile = _make_profile([rejected_primary, pending])

    assert _get_user_avatar(profile) == "/uploads/a.jpg"


def test_match_notification_avatar_none_when_all_rejected():
    """配對通知頭像：全部照片被駁回時回傳 None"""
    rejected = Photo(
        url="/uploads/x.jpg",
        display_order=0,
        moderation_status="REJECTED",
        is_profile_picture=True,
    )

    assert _get_user_avatar(_make_profile([rejected])) is None
    assert _get_user_avatar(None) is None
