"""探索與配對功能測試"""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.discovery import FREE_DAILY_LIKE_LIMIT
from app.models.match import Like, Pass
from app.models.profile import InterestTag, Profile
from app.models.user import User


@pytest.fixture
async def completed_profiles(client: AsyncClient, auth_user_pair: dict, test_db: AsyncSession):
    """創建完整的個人檔案（包含照片和興趣）"""
    # Alice 的檔案
    response = await client.post(
        "/api/profile",
        headers={"Authorization": f"Bearer {auth_user_pair['alice']['token']}"},
        json={
            "display_name": "Alice",
            "gender": "female",
            "bio": "喜歡旅遊和美食",
            "location": {
                "latitude": 25.0330,
                "longitude": 121.5654,
                "location_name": "台北市信義區",
            },
        },
    )
    assert response.status_code == 201, (
        f"Failed to create Alice profile: status={response.status_code}, body={response.text}"
    )

    # 更新 Alice 的偏好設定
    response = await client.patch(
        "/api/profile",
        headers={"Authorization": f"Bearer {auth_user_pair['alice']['token']}"},
        json={
            "min_age_preference": 25,
            "max_age_preference": 40,
            "max_distance_km": 50,
            "gender_preference": "male",
        },
    )
    assert response.status_code == 200, (
        f"Failed to update Alice preferences: status={response.status_code}, body={response.text}"
    )

    # Bob 的檔案
    response = await client.post(
        "/api/profile",
        headers={"Authorization": f"Bearer {auth_user_pair['bob']['token']}"},
        json={
            "display_name": "Bob",
            "gender": "male",
            "bio": "熱愛運動和旅遊",
            "location": {
                "latitude": 25.0500,
                "longitude": 121.5500,
                "location_name": "台北市大安區",
            },
        },
    )
    assert response.status_code == 201, (
        f"Failed to create Bob profile: status={response.status_code}, body={response.text}"
    )

    # 更新 Bob 的偏好設定
    response = await client.patch(
        "/api/profile",
        headers={"Authorization": f"Bearer {auth_user_pair['bob']['token']}"},
        json={
            "min_age_preference": 22,
            "max_age_preference": 35,
            "max_distance_km": 30,
            "gender_preference": "female",
        },
    )
    assert response.status_code == 200, (
        f"Failed to update Bob preferences: status={response.status_code}, body={response.text}"
    )

    # 建立測試用的興趣標籤
    result = await test_db.execute(select(InterestTag).limit(5))
    existing_tags = result.scalars().all()

    # 如果沒有興趣標籤，先建立一些
    if len(existing_tags) < 5:
        tags_to_create = [
            InterestTag(name="旅遊", category="lifestyle", icon="✈️"),
            InterestTag(name="美食", category="lifestyle", icon="🍔"),
            InterestTag(name="運動", category="sports", icon="⚽"),
            InterestTag(name="音樂", category="entertainment", icon="🎵"),
            InterestTag(name="電影", category="entertainment", icon="🎬"),
        ]
        for tag in tags_to_create:
            test_db.add(tag)
        await test_db.commit()

        # 重新取得標籤
        result = await test_db.execute(select(InterestTag).limit(5))
        existing_tags = result.scalars().all()

    # 取得標籤 ID
    tag_ids = [str(tag.id) for tag in existing_tags[:5]]

    # 為 Alice 和 Bob 設定興趣標籤
    response = await client.put(
        "/api/profile/interests",
        headers={"Authorization": f"Bearer {auth_user_pair['alice']['token']}"},
        json={"interest_ids": tag_ids[:4]},  # 使用前 4 個標籤
    )
    assert response.status_code == 200, (
        f"Failed to set Alice interests: status={response.status_code}, body={response.text}"
    )

    response = await client.put(
        "/api/profile/interests",
        headers={"Authorization": f"Bearer {auth_user_pair['bob']['token']}"},
        json={"interest_ids": tag_ids[1:5]},  # 使用後 4 個標籤（有共同興趣）
    )
    assert response.status_code == 200, (
        f"Failed to set Bob interests: status={response.status_code}, body={response.text}"
    )

    # 上傳測試照片
    def create_test_image():
        """創建一個有效的測試圖片"""
        img = Image.new("RGB", (100, 100), color="red")
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        return buffer

    # Alice 上傳照片
    test_image = create_test_image()
    response = await client.post(
        "/api/profile/photos",
        headers={"Authorization": f"Bearer {auth_user_pair['alice']['token']}"},
        files={"file": ("photo.jpg", test_image, "image/jpeg")},
    )
    assert response.status_code == 201, (
        f"Failed to upload Alice photo: status={response.status_code}, body={response.text}"
    )

    # Bob 上傳照片
    test_image = create_test_image()
    response = await client.post(
        "/api/profile/photos",
        headers={"Authorization": f"Bearer {auth_user_pair['bob']['token']}"},
        files={"file": ("photo.jpg", test_image, "image/jpeg")},
    )
    assert response.status_code == 201, (
        f"Failed to upload Bob photo: status={response.status_code}, body={response.text}"
    )

    # 驗證檔案完整度
    response = await client.get(
        "/api/profile", headers={"Authorization": f"Bearer {auth_user_pair['alice']['token']}"}
    )
    alice_profile = response.json()
    assert alice_profile.get("is_complete") is True, f"Alice profile not complete: {alice_profile}"

    response = await client.get(
        "/api/profile", headers={"Authorization": f"Bearer {auth_user_pair['bob']['token']}"}
    )
    bob_profile = response.json()
    assert bob_profile.get("is_complete") is True, f"Bob profile not complete: {bob_profile}"

    return auth_user_pair


@pytest.mark.asyncio
async def test_browse_users_without_profile(client: AsyncClient, auth_user_pair: dict):
    """測試：未完成檔案無法瀏覽"""
    response = await client.get(
        "/api/discovery/browse",
        headers={"Authorization": f"Bearer {auth_user_pair['alice']['token']}"},
    )

    assert response.status_code == 400
    assert "個人檔案" in response.json()["detail"]


@pytest.mark.asyncio
async def test_browse_users_success(client: AsyncClient, completed_profiles: dict):
    """測試：成功瀏覽候選人"""
    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    assert response.status_code == 200
    candidates = response.json()

    # Alice 應該看到 Bob
    assert isinstance(candidates, list)
    if len(candidates) > 0:
        candidate = candidates[0]
        assert "display_name" in candidate
        assert "age" in candidate
        assert "distance_km" in candidate
        assert "interests" in candidate
        assert "match_score" in candidate


async def test_browse_returns_common_interests_with_viewer(
    client: AsyncClient, completed_profiles: dict
):
    """探索卡片回傳與瀏覽者的共同興趣（配對理由）

    fixture：Alice 持有 tags[0:4]、Bob 持有 tags[1:5]
    → 共同興趣 = tags[1:4]（3 個），Bob 獨有 tags[4] 不得出現在 common_interests
    """
    alice_headers = completed_profiles["alice"]["headers"]
    bob_headers = completed_profiles["bob"]["headers"]
    alice_interests = {
        i["name"]
        for i in (await client.get("/api/profile", headers=alice_headers)).json()["interests"]
    }
    bob_user_id = (await client.get("/api/profile", headers=bob_headers)).json()["user_id"]

    response = await client.get("/api/discovery/browse?limit=10", headers=alice_headers)
    assert response.status_code == 200
    bob = next(c for c in response.json() if c["user_id"] == bob_user_id)

    assert "common_interests" in bob
    assert len(bob["common_interests"]) == 3
    assert set(bob["common_interests"]) == alice_interests & set(bob["interests"])
    # Bob 獨有的興趣不能混進共同興趣
    assert set(bob["interests"]) - set(bob["common_interests"])


async def _create_candidate_pool(
    test_db: AsyncSession,
    count: int,
    *,
    prefix: str,
    latitude: float,
    last_active: datetime | None = None,
):
    """直接在 DB 建立候選人（繞過 API 以加速大量建立）

    分數構成（viewer 位於台北 25.0330, 121.5654）：
    - latitude=25.33（約 33km）+ last_active=None：距離 5 + 信任 4 = 9 分（低於門檻 15）
    - latitude=25.034（約 0.1km）+ last_active=now：距離 20 + 活躍 20 + 信任 4 = 44 分
    """
    users = []
    for i in range(count):
        user = User(
            email=f"{prefix}{i}@example.com",
            password_hash="test-hash",
            date_of_birth=date(1995, 1, 1),
            is_active=True,
        )
        test_db.add(user)
        users.append(user)
    await test_db.flush()

    for i, user in enumerate(users):
        test_db.add(
            Profile(
                user_id=user.id,
                display_name=f"{prefix}{i}",
                gender="male",
                location=ST_SetSRID(ST_MakePoint(121.5654, latitude), 4326),
                is_complete=True,
                is_visible=True,
                last_active=last_active,
            )
        )
    await test_db.commit()


@pytest.fixture
async def viewer_with_profile(client: AsyncClient, auth_user: dict) -> dict:
    """建立一個只有基本檔案（含位置）的瀏覽者"""
    response = await client.post(
        "/api/profile",
        headers=auth_user["headers"],
        json={
            "display_name": "Viewer",
            "gender": "female",
            "location": {
                "latitude": 25.0330,
                "longitude": 121.5654,
                "location_name": "台北市信義區",
            },
        },
    )
    assert response.status_code == 201, f"Failed to create viewer profile: {response.text}"
    return auth_user


@pytest.mark.asyncio
async def test_browse_fills_limit_when_first_batch_is_low_score(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """測試：候選池前段大多低分時，仍應湊滿 limit 筆高分候選人

    回歸測試：舊實作只撈 limit*3 筆（且無排序）再過濾低分者，
    當低分者集中在前段時會回傳不足 limit 筆，即使資料庫還有高分候選人。
    """
    # 15 個低分候選人先插入（佔滿舊實作 limit*3 的緩衝）
    await _create_candidate_pool(test_db, 15, prefix="lowscore", latitude=25.33)
    # 5 個高分候選人後插入
    await _create_candidate_pool(
        test_db, 5, prefix="highscore", latitude=25.034, last_active=datetime.now(UTC)
    )

    response = await client.get(
        "/api/discovery/browse?limit=5",
        headers=viewer_with_profile["headers"],
    )

    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) == 5, f"應回傳 5 筆高分候選人，實際只有 {len(candidates)} 筆"
    assert all(c["display_name"].startswith("highscore") for c in candidates)


@pytest.mark.asyncio
async def test_browse_returns_all_qualified_when_fewer_than_limit(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """測試：合格候選人少於 limit 時，回傳全部且正常終止"""
    await _create_candidate_pool(test_db, 3, prefix="lowscore", latitude=25.33)
    await _create_candidate_pool(
        test_db, 2, prefix="highscore", latitude=25.034, last_active=datetime.now(UTC)
    )

    response = await client.get(
        "/api/discovery/browse?limit=5",
        headers=viewer_with_profile["headers"],
    )

    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) == 2
    assert all(c["display_name"].startswith("highscore") for c in candidates)


async def _viewer_user_id(test_db: AsyncSession, viewer: dict) -> uuid.UUID:
    return (
        await test_db.execute(select(User.id).where(User.email == viewer["email"]))
    ).scalar_one()


async def _candidate_user_ids_sorted(test_db: AsyncSession, prefix: str) -> list[uuid.UUID]:
    """依 user_id 升冪回傳候選人 id（browse 分批掃描即依此順序）"""
    result = await test_db.execute(
        select(User.id).where(User.email.like(f"{prefix}%")).order_by(User.id)
    )
    return list(result.scalars())


async def _like_viewer(test_db: AsyncSession, from_user_id: uuid.UUID, viewer_id: uuid.UUID):
    test_db.add(Like(from_user_id=from_user_id, to_user_id=viewer_id))
    await test_db.commit()


@pytest.mark.asyncio
async def test_browse_liked_me_candidate_bypasses_score_threshold(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """喜歡我的人即使配對分數低於門檻（9 < 15），仍要出現在候選列表"""
    await _create_candidate_pool(test_db, 3, prefix="lowscore", latitude=25.33)
    viewer_id = await _viewer_user_id(test_db, viewer_with_profile)
    admirer_id = (await _candidate_user_ids_sorted(test_db, "lowscore"))[1]
    await _like_viewer(test_db, admirer_id, viewer_id)

    response = await client.get(
        "/api/discovery/browse?limit=5", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    candidates = response.json()
    assert [c["user_id"] for c in candidates] == [str(admirer_id)]
    # 分數本身維持真實值（低於門檻），只是豁免過濾
    assert candidates[0]["match_score"] < 15


@pytest.mark.asyncio
async def test_browse_liked_me_candidate_ranked_first_among_equal_scores(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """同分情況下，喜歡我的人排在最前面；且 match_score 不因加權而改變"""
    await _create_candidate_pool(
        test_db, 5, prefix="highscore", latitude=25.034, last_active=datetime.now(UTC)
    )
    viewer_id = await _viewer_user_id(test_db, viewer_with_profile)
    # 挑 user_id 最大者（穩定排序下原本會排最後）
    admirer_id = (await _candidate_user_ids_sorted(test_db, "highscore"))[-1]
    await _like_viewer(test_db, admirer_id, viewer_id)

    response = await client.get(
        "/api/discovery/browse?limit=5", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) == 5
    assert candidates[0]["user_id"] == str(admirer_id)
    # 排序加權不可寫進回傳分數（卡片百分比須維持真實，避免洩漏訊號）
    scores = {c["match_score"] for c in candidates}
    assert len(scores) == 1, f"加權不應改變 match_score，實際出現多種分數：{scores}"


@pytest.mark.asyncio
async def test_browse_liked_me_candidate_found_beyond_first_batch(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """喜歡我的人排在掃描順序尾端時，仍須被撈到

    limit=5 → 每批 15 筆；40 個高分候選人第一批就湊滿 limit 後停止掃描。
    若 DB 查詢不把「喜歡我的人」排前，user_id 最大者永遠不會被掃到。
    """
    await _create_candidate_pool(
        test_db, 40, prefix="highscore", latitude=25.034, last_active=datetime.now(UTC)
    )
    viewer_id = await _viewer_user_id(test_db, viewer_with_profile)
    admirer_id = (await _candidate_user_ids_sorted(test_db, "highscore"))[-1]
    await _like_viewer(test_db, admirer_id, viewer_id)

    response = await client.get(
        "/api/discovery/browse?limit=5", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) == 5
    assert candidates[0]["user_id"] == str(admirer_id)


@pytest.mark.asyncio
async def test_browse_does_not_expose_liked_me_signal(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """回傳欄位不得透露「對方已喜歡你」（等同免費送出 Likes You 功能）"""
    await _create_candidate_pool(
        test_db, 2, prefix="highscore", latitude=25.034, last_active=datetime.now(UTC)
    )
    viewer_id = await _viewer_user_id(test_db, viewer_with_profile)
    admirer_id = (await _candidate_user_ids_sorted(test_db, "highscore"))[0]
    await _like_viewer(test_db, admirer_id, viewer_id)

    response = await client.get(
        "/api/discovery/browse?limit=5", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    for candidate in response.json():
        leaked = [k for k in candidate if "like" in k.lower()]
        assert not leaked, f"回傳欄位洩漏喜歡訊號：{leaked}"


@pytest.mark.asyncio
async def test_browse_falls_back_to_low_score_when_no_qualified_candidates(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """合格池（>= MIN_MATCH_SCORE）為空時，自動放寬門檻回傳低分候選人，而非空列表"""
    await _create_candidate_pool(test_db, 3, prefix="lowscore", latitude=25.33)

    response = await client.get(
        "/api/discovery/browse?limit=5", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) == 3
    assert all(c["display_name"].startswith("lowscore") for c in candidates)
    assert all(c["match_score"] < 15 for c in candidates)


@pytest.mark.asyncio
async def test_browse_fallback_not_used_while_qualified_candidates_remain(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """只要還有合格候選人，就不混入低分者（門檻放寬只在合格池耗盡後啟動）"""
    await _create_candidate_pool(test_db, 3, prefix="lowscore", latitude=25.33)
    await _create_candidate_pool(
        test_db, 1, prefix="highscore", latitude=25.034, last_active=datetime.now(UTC)
    )

    response = await client.get(
        "/api/discovery/browse?limit=5", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    candidates = response.json()
    assert [c["display_name"] for c in candidates] == ["highscore0"]


@pytest.mark.asyncio
async def test_browse_sorted_by_match_score_desc(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """測試：回傳結果依配對分數由高到低排序

    inactive 組（近距離但無活躍紀錄）約 24 分，active 組約 44 分，
    先插入低分組確保排序不是插入順序的巧合。
    """
    await _create_candidate_pool(test_db, 3, prefix="inactive", latitude=25.034)
    await _create_candidate_pool(
        test_db, 3, prefix="active", latitude=25.034, last_active=datetime.now(UTC)
    )

    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers=viewer_with_profile["headers"],
    )

    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) == 6
    scores = [c["match_score"] for c in candidates]
    assert scores == sorted(scores, reverse=True), f"分數未由高到低排序: {scores}"
    assert all(c["display_name"].startswith("active") for c in candidates[:3])


# ========== 空池放寬建議 ==========


@pytest.mark.asyncio
async def test_expand_suggestions_distance(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """距離 50km 內沒人、100km 內有 3 人 → 建議放寬距離到 100km（+3）"""
    # viewer 在台北 (25.0330)；latitude=25.75 約 80km
    await _create_candidate_pool(test_db, 3, prefix="far", latitude=25.75)
    await client.patch(
        "/api/profile", headers=viewer_with_profile["headers"], json={"max_distance_km": 50}
    )

    response = await client.get(
        "/api/discovery/expand-suggestions", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    data = response.json()
    distance = next(s for s in data["suggestions"] if s["type"] == "distance")
    assert distance["current_max_distance_km"] == 50
    assert distance["suggested_max_distance_km"] == 100
    assert distance["additional_candidates"] == 3
    # 年齡偏好為預設 18–99，無法再放寬 → 不應出現年齡建議
    assert not [s for s in data["suggestions"] if s["type"] == "age"]


@pytest.mark.asyncio
async def test_expand_suggestions_age(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """候選人 31 歲、偏好 22–27 → 建議放寬到 18–32（+N）"""
    await _create_candidate_pool(
        test_db, 2, prefix="near", latitude=25.034, last_active=datetime.now(UTC)
    )
    await client.patch(
        "/api/profile",
        headers=viewer_with_profile["headers"],
        json={"min_age_preference": 22, "max_age_preference": 27},
    )

    response = await client.get(
        "/api/discovery/expand-suggestions", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    data = response.json()
    age = next(s for s in data["suggestions"] if s["type"] == "age")
    assert (age["current_min_age"], age["current_max_age"]) == (22, 27)
    assert (age["suggested_min_age"], age["suggested_max_age"]) == (18, 32)
    assert age["additional_candidates"] == 2
    # 50km 內已有人但被年齡擋掉；距離放寬不會多出任何人 → 不建議距離
    assert not [s for s in data["suggestions"] if s["type"] == "distance"]


@pytest.mark.asyncio
async def test_expand_suggestions_empty_when_relaxing_does_not_help(
    client: AsyncClient, viewer_with_profile: dict
):
    """放寬後仍然沒人 → 不給任何建議"""
    response = await client.get(
        "/api/discovery/expand-suggestions", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    assert response.json()["suggestions"] == []


@pytest.mark.asyncio
async def test_expand_suggestions_skip_distance_at_cap(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """距離已是上限 500km 時不建議再放寬距離"""
    await _create_candidate_pool(test_db, 1, prefix="far", latitude=25.75)
    await client.patch(
        "/api/profile", headers=viewer_with_profile["headers"], json={"max_distance_km": 500}
    )

    response = await client.get(
        "/api/discovery/expand-suggestions", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    assert not [s for s in response.json()["suggestions"] if s["type"] == "distance"]


@pytest.mark.asyncio
async def test_expand_suggestions_excludes_liked_and_blocked(
    client: AsyncClient, viewer_with_profile: dict, test_db: AsyncSession
):
    """放寬後多出來的人數要套用與 browse 相同的排除規則（已喜歡者不計）"""
    await _create_candidate_pool(test_db, 2, prefix="far", latitude=25.75)
    await client.patch(
        "/api/profile", headers=viewer_with_profile["headers"], json={"max_distance_km": 50}
    )
    viewer_id = await _viewer_user_id(test_db, viewer_with_profile)
    liked_id = (await _candidate_user_ids_sorted(test_db, "far"))[0]
    test_db.add(Like(from_user_id=viewer_id, to_user_id=liked_id))
    await test_db.commit()

    response = await client.get(
        "/api/discovery/expand-suggestions", headers=viewer_with_profile["headers"]
    )

    assert response.status_code == 200
    distance = next(s for s in response.json()["suggestions"] if s["type"] == "distance")
    assert distance["additional_candidates"] == 1


@pytest.mark.asyncio
async def test_expand_suggestions_requires_profile(client: AsyncClient, auth_user: dict):
    response = await client.get("/api/discovery/expand-suggestions", headers=auth_user["headers"])
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_like_user_success(
    client: AsyncClient, completed_profiles: dict, test_db: AsyncSession
):
    """測試：成功喜歡用戶"""
    # Alice 瀏覽候選人
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Alice 喜歡 Bob
    response = await client.post(
        f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["liked"] is True
    assert data["is_match"] is False  # Bob 還沒喜歡 Alice
    assert data["match_id"] is None


@pytest.mark.asyncio
async def test_mutual_like_creates_match(client: AsyncClient, completed_profiles: dict):
    """測試：互相喜歡自動建立配對"""
    # Alice 瀏覽並取得 Bob 的 ID
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Bob 瀏覽並取得 Alice 的 ID
    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"},
    )
    candidates = response.json()
    alice_user_id = next((c["user_id"] for c in candidates if c["display_name"] == "Alice"), None)

    if not alice_user_id:
        pytest.skip("Bob 看不到 Alice")

    # Alice 喜歡 Bob
    await client.post(
        f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    # Bob 喜歡 Alice（應該觸發配對）
    response = await client.post(
        f"/api/discovery/like/{alice_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["liked"] is True
    assert data["is_match"] is True  # 配對成功！
    assert data["match_id"] is not None


@pytest.mark.asyncio
async def test_cannot_like_twice(client: AsyncClient, completed_profiles: dict):
    """測試：不能重複喜歡同一個用戶"""
    # Alice 瀏覽候選人
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # 第一次喜歡（成功）
    response = await client.post(
        f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    # 第二次喜歡（應該失敗）
    response = await client.post(
        f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    assert response.status_code == 400
    assert "已經喜歡" in response.json()["detail"]


@pytest.mark.asyncio
async def test_pass_user(client: AsyncClient, completed_profiles: dict):
    """測試：跳過用戶"""
    # Alice 瀏覽候選人
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Alice 跳過 Bob
    response = await client.post(
        f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True


@pytest.mark.asyncio
async def test_pass_nonexistent_user_returns_404(client: AsyncClient, completed_profiles: dict):
    """測試：跳過不存在的用戶回 404（外鍵違反不應回 500）"""
    response = await client.post(
        f"/api/discovery/pass/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_passed_user_not_shown_in_browse(client: AsyncClient, completed_profiles: dict):
    """測試：24 小時內跳過的用戶不會出現在瀏覽列表"""
    # Alice 瀏覽候選人
    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates_before = response.json()

    if len(candidates_before) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates_before[0]["user_id"]
    bob_name = candidates_before[0]["display_name"]

    # Alice 跳過 Bob
    response = await client.post(
        f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    # 重新瀏覽候選人
    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates_after = response.json()

    # Bob 不應該出現在列表中（24 小時內）
    bob_in_list = any(c["user_id"] == bob_user_id for c in candidates_after)
    assert not bob_in_list, f"{bob_name} 應該被排除但仍出現在候選人列表"


@pytest.mark.asyncio
async def test_passed_user_reappears_after_24_hours(
    client: AsyncClient, completed_profiles: dict, test_db: AsyncSession
):
    """測試：24 小時後跳過的用戶會重新出現"""

    # 獲取 Alice 的 user_id
    result = await test_db.execute(
        select(User.id).where(User.email == completed_profiles["alice"]["email"])
    )
    alice_user_id = result.scalar_one()

    # Alice 瀏覽候選人
    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Alice 跳過 Bob
    response = await client.post(
        f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    # 手動修改跳過時間為 25 小時前（模擬時間過去）
    old_time = datetime.now(UTC) - timedelta(hours=25)
    await test_db.execute(
        Pass.__table__.update()
        .where(Pass.from_user_id == alice_user_id, Pass.to_user_id == bob_user_id)
        .values(passed_at=old_time)
    )
    await test_db.commit()

    # 重新瀏覽候選人
    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates_after = response.json()

    # Bob 應該重新出現（超過 24 小時）
    bob_in_list = any(c["user_id"] == bob_user_id for c in candidates_after)
    assert bob_in_list, "Bob 應該在 24 小時後重新出現"


@pytest.mark.asyncio
async def test_cannot_pass_self(
    client: AsyncClient, completed_profiles: dict, test_db: AsyncSession
):
    """測試：不能跳過自己"""

    # 獲取 Alice 的 user_id
    result = await test_db.execute(
        select(User.id).where(User.email == completed_profiles["alice"]["email"])
    )
    alice_user_id = result.scalar_one()

    response = await client.post(
        f"/api/discovery/pass/{alice_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    assert response.status_code == 400
    assert "不能跳過自己" in response.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_pass_updates_time(
    client: AsyncClient, completed_profiles: dict, test_db: AsyncSession
):
    """測試：重複跳過同一用戶會更新時間"""

    # 獲取 Alice 的 user_id
    result = await test_db.execute(
        select(User.id).where(User.email == completed_profiles["alice"]["email"])
    )
    alice_user_id = result.scalar_one()

    # Alice 瀏覽候選人
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # 第一次跳過
    response = await client.post(
        f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    # 查詢第一次跳過的時間
    result = await test_db.execute(
        select(Pass.passed_at).where(
            Pass.from_user_id == alice_user_id, Pass.to_user_id == bob_user_id
        )
    )
    first_pass_time = result.scalar_one()

    # 等待 1 秒
    await asyncio.sleep(1)

    # 第二次跳過（應該更新時間）
    response = await client.post(
        f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    assert response.status_code == 200

    # 查詢第二次跳過的時間
    await test_db.rollback()  # 重新載入資料
    result = await test_db.execute(
        select(Pass.passed_at).where(
            Pass.from_user_id == alice_user_id, Pass.to_user_id == bob_user_id
        )
    )
    second_pass_time = result.scalar_one()

    # 第二次的時間應該更新
    assert second_pass_time > first_pass_time, "重複跳過應該更新時間"


@pytest.mark.asyncio
async def test_get_matches_empty(client: AsyncClient, completed_profiles: dict):
    """測試：沒有配對時返回空列表"""
    response = await client.get(
        "/api/discovery/matches",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    assert response.status_code == 200
    matches = response.json()
    assert isinstance(matches, list)


@pytest.mark.asyncio
async def test_get_matches_after_match(client: AsyncClient, completed_profiles: dict):
    """測試：配對後可以查看配對列表"""
    # 先建立配對（重複上面的互相喜歡流程）
    # Alice 瀏覽
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Bob 瀏覽
    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"},
    )
    candidates = response.json()
    alice_user_id = next((c["user_id"] for c in candidates if c["display_name"] == "Alice"), None)

    if not alice_user_id:
        pytest.skip("Bob 看不到 Alice")

    # 互相喜歡
    await client.post(
        f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    await client.post(
        f"/api/discovery/like/{alice_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"},
    )

    # Alice 查看配對列表
    response = await client.get(
        "/api/discovery/matches",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    assert response.status_code == 200
    matches = response.json()
    assert len(matches) > 0

    match = matches[0]
    assert "match_id" in match
    assert "matched_user" in match
    assert match["matched_user"]["display_name"] == "Bob"


async def test_matches_return_common_interests_with_viewer(
    client: AsyncClient, completed_profiles: dict
):
    """配對列表也回傳共同興趣（與探索卡片同一套配對理由）

    fixture：Alice 持有 tags[0:4]、Bob 持有 tags[1:5] → 共同興趣 3 個。
    雙方各自查配對列表時，都應看到以「自己」為基準算出的共同興趣。
    """
    alice_headers = completed_profiles["alice"]["headers"]
    bob_headers = completed_profiles["bob"]["headers"]
    alice = (await client.get("/api/profile", headers=alice_headers)).json()
    bob = (await client.get("/api/profile", headers=bob_headers)).json()
    expected = {i["name"] for i in alice["interests"]} & {i["name"] for i in bob["interests"]}
    assert len(expected) == 3  # fixture 前提，變了就該更新這個測試

    # 互相喜歡以建立配對
    await client.post(f"/api/discovery/like/{bob['user_id']}", headers=alice_headers)
    await client.post(f"/api/discovery/like/{alice['user_id']}", headers=bob_headers)

    # Alice 視角
    response = await client.get("/api/discovery/matches", headers=alice_headers)
    assert response.status_code == 200
    matched_bob = next(
        m["matched_user"] for m in response.json() if m["matched_user"]["user_id"] == bob["user_id"]
    )
    assert set(matched_bob["common_interests"]) == expected
    # 對方獨有的興趣不能混進共同興趣
    assert set(matched_bob["interests"]) - set(matched_bob["common_interests"])

    # Bob 視角（對稱）
    response = await client.get("/api/discovery/matches", headers=bob_headers)
    assert response.status_code == 200
    matched_alice = next(
        m["matched_user"]
        for m in response.json()
        if m["matched_user"]["user_id"] == alice["user_id"]
    )
    assert set(matched_alice["common_interests"]) == expected


@pytest.mark.asyncio
async def test_unmatch(client: AsyncClient, completed_profiles: dict):
    """測試：取消配對"""
    # 先建立配對
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    response = await client.get(
        "/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"},
    )
    candidates = response.json()
    alice_user_id = next((c["user_id"] for c in candidates if c["display_name"] == "Alice"), None)

    if not alice_user_id:
        pytest.skip("Bob 看不到 Alice")

    await client.post(
        f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    response = await client.post(
        f"/api/discovery/like/{alice_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"},
    )

    match_id = response.json()["match_id"]

    # Alice 取消配對
    response = await client.delete(
        f"/api/discovery/unmatch/{match_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )

    assert response.status_code == 200
    assert "取消配對" in response.json()["message"]

    # 確認配對列表中沒有 Bob
    response = await client.get(
        "/api/discovery/matches",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    matches = response.json()
    bob_matches = [m for m in matches if m["matched_user"]["display_name"] == "Bob"]
    assert len(bob_matches) == 0


# ==================== 每日喜歡次數限制測試 ====================


def _make_mock_redis(initial_count: int = 0):
    """建立支援 incr/decr/expire 的 Mock Redis（原子性 INCR-then-check 模式）"""
    _storage: dict[str, int] = {}
    mock_conn = AsyncMock()

    async def mock_incr(key: str):
        _storage[key] = _storage.get(key, initial_count) + 1
        return _storage[key]

    async def mock_decr(key: str):
        _storage[key] = _storage.get(key, 0) - 1
        return _storage[key]

    async def mock_expire(key: str, ttl: int):
        return True

    mock_conn.incr = AsyncMock(side_effect=mock_incr)
    mock_conn.decr = AsyncMock(side_effect=mock_decr)
    mock_conn.expire = AsyncMock(side_effect=mock_expire)
    return mock_conn


@pytest.mark.asyncio
async def test_like_within_daily_limit(client: AsyncClient, completed_profiles: dict):
    """測試：每日限制內正常 like 成功"""
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # 初始計數為 0，INCR 後變 1，未超限
    mock_conn = _make_mock_redis(initial_count=0)

    with patch("app.api.discovery.redis_client.get_connection", return_value=mock_conn):
        response = await client.post(
            f"/api/discovery/like/{bob_user_id}",
            headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
        )

    assert response.status_code == 200
    assert response.json()["liked"] is True


@pytest.mark.asyncio
async def test_like_exceeds_daily_limit(client: AsyncClient, completed_profiles: dict):
    """測試：超過每日限制回傳 429"""
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # 初始計數為 50，INCR 後變 51 > 50，觸發限制並 DECR 回滾
    mock_conn = _make_mock_redis(initial_count=FREE_DAILY_LIKE_LIMIT)

    with patch("app.api.discovery.redis_client.get_connection", return_value=mock_conn):
        response = await client.post(
            f"/api/discovery/like/{bob_user_id}",
            headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
        )

    assert response.status_code == 429
    data = response.json()["detail"]
    assert data["message"] == "今日喜歡次數已達上限"
    assert data["daily_limit"] == FREE_DAILY_LIKE_LIMIT
    assert data["remaining"] == 0
    assert "reset_at" in data


@pytest.mark.asyncio
async def test_like_limit_resets_next_day(client: AsyncClient, completed_profiles: dict):
    """測試：跨天後計數歸零（新 key），可再次 like"""
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # 初始計數為 0（模擬跨天後新 key），INCR 後變 1，未超限
    mock_conn = _make_mock_redis(initial_count=0)

    with patch("app.api.discovery.redis_client.get_connection", return_value=mock_conn):
        response = await client.post(
            f"/api/discovery/like/{bob_user_id}",
            headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
        )

    assert response.status_code == 200
    assert response.json()["liked"] is True


@pytest.mark.asyncio
async def test_like_redis_unavailable_fallback(client: AsyncClient, completed_profiles: dict):
    """測試：Redis 不可用時放行，不阻斷核心功能"""
    response = await client.get(
        "/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Mock Redis 連線拋出 RedisError
    import redis.asyncio as aioredis

    mock_conn = AsyncMock()
    mock_conn.incr = AsyncMock(side_effect=aioredis.RedisError("Connection refused"))

    with patch("app.api.discovery.redis_client.get_connection", return_value=mock_conn):
        response = await client.post(
            f"/api/discovery/like/{bob_user_id}",
            headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"},
        )

    # Redis 掛掉時應放行，不阻斷 like
    assert response.status_code == 200
    assert response.json()["liked"] is True
