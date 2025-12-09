"""探索與配對功能測試"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from io import BytesIO
from PIL import Image

from app.models.user import User
from app.models.profile import Profile, InterestTag
from app.models.match import Like, Match


@pytest.fixture
async def test_users(client: AsyncClient):
    """創建測試用戶（Alice 和 Bob）"""
    # 註冊 Alice
    response_a = await client.post("/api/auth/register", json={
        "email": "alice@example.com",
        "password": "Alice1234",
        "date_of_birth": "1995-06-15"
    })
    assert response_a.status_code == 201
    token_a = response_a.json()["access_token"]

    # 註冊 Bob
    response_b = await client.post("/api/auth/register", json={
        "email": "bob@example.com",
        "password": "Bob12345",
        "date_of_birth": "1990-03-20"
    })
    assert response_b.status_code == 201
    token_b = response_b.json()["access_token"]

    return {
        "alice": {"token": token_a, "email": "alice@example.com"},
        "bob": {"token": token_b, "email": "bob@example.com"}
    }


@pytest.fixture
async def completed_profiles(client: AsyncClient, test_users: dict, test_db: AsyncSession):
    """創建完整的個人檔案（包含照片和興趣）"""
    # Alice 的檔案
    response = await client.post("/api/profile",
        headers={"Authorization": f"Bearer {test_users['alice']['token']}"},
        json={
            "display_name": "Alice",
            "gender": "female",
            "bio": "喜歡旅遊和美食",
            "location": {
                "latitude": 25.0330,
                "longitude": 121.5654,
                "location_name": "台北市信義區"
            }
        }
    )
    assert response.status_code == 201, f"Failed to create Alice profile: status={response.status_code}, body={response.text}"

    # 更新 Alice 的偏好設定
    response = await client.patch("/api/profile",
        headers={"Authorization": f"Bearer {test_users['alice']['token']}"},
        json={
            "min_age_preference": 25,
            "max_age_preference": 40,
            "max_distance_km": 50,
            "gender_preference": "male"
        }
    )
    assert response.status_code == 200, f"Failed to update Alice preferences: status={response.status_code}, body={response.text}"

    # Bob 的檔案
    response = await client.post("/api/profile",
        headers={"Authorization": f"Bearer {test_users['bob']['token']}"},
        json={
            "display_name": "Bob",
            "gender": "male",
            "bio": "熱愛運動和旅遊",
            "location": {
                "latitude": 25.0500,
                "longitude": 121.5500,
                "location_name": "台北市大安區"
            }
        }
    )
    assert response.status_code == 201, f"Failed to create Bob profile: status={response.status_code}, body={response.text}"

    # 更新 Bob 的偏好設定
    response = await client.patch("/api/profile",
        headers={"Authorization": f"Bearer {test_users['bob']['token']}"},
        json={
            "min_age_preference": 22,
            "max_age_preference": 35,
            "max_distance_km": 30,
            "gender_preference": "female"
        }
    )
    assert response.status_code == 200, f"Failed to update Bob preferences: status={response.status_code}, body={response.text}"

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
    response = await client.put("/api/profile/interests",
        headers={"Authorization": f"Bearer {test_users['alice']['token']}"},
        json={"interest_ids": tag_ids[:4]}  # 使用前 4 個標籤
    )
    assert response.status_code == 200, f"Failed to set Alice interests: status={response.status_code}, body={response.text}"

    response = await client.put("/api/profile/interests",
        headers={"Authorization": f"Bearer {test_users['bob']['token']}"},
        json={"interest_ids": tag_ids[1:5]}  # 使用後 4 個標籤（有共同興趣）
    )
    assert response.status_code == 200, f"Failed to set Bob interests: status={response.status_code}, body={response.text}"

    # 上傳測試照片
    def create_test_image():
        """創建一個有效的測試圖片"""
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return buffer

    # Alice 上傳照片
    test_image = create_test_image()
    response = await client.post("/api/profile/photos",
        headers={"Authorization": f"Bearer {test_users['alice']['token']}"},
        files={"file": ("photo.jpg", test_image, "image/jpeg")}
    )
    assert response.status_code == 201, f"Failed to upload Alice photo: status={response.status_code}, body={response.text}"

    # Bob 上傳照片
    test_image = create_test_image()
    response = await client.post("/api/profile/photos",
        headers={"Authorization": f"Bearer {test_users['bob']['token']}"},
        files={"file": ("photo.jpg", test_image, "image/jpeg")}
    )
    assert response.status_code == 201, f"Failed to upload Bob photo: status={response.status_code}, body={response.text}"

    # 驗證檔案完整度
    response = await client.get("/api/profile",
        headers={"Authorization": f"Bearer {test_users['alice']['token']}"}
    )
    alice_profile = response.json()
    assert alice_profile.get('is_complete') == True, f"Alice profile not complete: {alice_profile}"

    response = await client.get("/api/profile",
        headers={"Authorization": f"Bearer {test_users['bob']['token']}"}
    )
    bob_profile = response.json()
    assert bob_profile.get('is_complete') == True, f"Bob profile not complete: {bob_profile}"

    return test_users


@pytest.mark.asyncio
async def test_browse_users_without_profile(client: AsyncClient, test_users: dict):
    """測試：未完成檔案無法瀏覽"""
    response = await client.get("/api/discovery/browse",
        headers={"Authorization": f"Bearer {test_users['alice']['token']}"}
    )

    assert response.status_code == 400
    assert "個人檔案" in response.json()["detail"]


@pytest.mark.asyncio
async def test_browse_users_success(client: AsyncClient, completed_profiles: dict):
    """測試：成功瀏覽候選人"""
    response = await client.get("/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
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


@pytest.mark.asyncio
async def test_like_user_success(client: AsyncClient, completed_profiles: dict, test_db: AsyncSession):
    """測試：成功喜歡用戶"""
    # Alice 瀏覽候選人
    response = await client.get("/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Alice 喜歡 Bob
    response = await client.post(f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
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
    response = await client.get("/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Bob 瀏覽並取得 Alice 的 ID
    response = await client.get("/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"}
    )
    candidates = response.json()
    alice_user_id = next((c["user_id"] for c in candidates if c["display_name"] == "Alice"), None)

    if not alice_user_id:
        pytest.skip("Bob 看不到 Alice")

    # Alice 喜歡 Bob
    await client.post(f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )

    # Bob 喜歡 Alice（應該觸發配對）
    response = await client.post(f"/api/discovery/like/{alice_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"}
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
    response = await client.get("/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # 第一次喜歡（成功）
    response = await client.post(f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    assert response.status_code == 200

    # 第二次喜歡（應該失敗）
    response = await client.post(f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    assert response.status_code == 400
    assert "已經喜歡" in response.json()["detail"]


@pytest.mark.asyncio
async def test_pass_user(client: AsyncClient, completed_profiles: dict):
    """測試：跳過用戶"""
    # Alice 瀏覽候選人
    response = await client.get("/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Alice 跳過 Bob
    response = await client.post(f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True


@pytest.mark.asyncio
async def test_passed_user_not_shown_in_browse(client: AsyncClient, completed_profiles: dict):
    """測試：24 小時內跳過的用戶不會出現在瀏覽列表"""
    # Alice 瀏覽候選人
    response = await client.get("/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates_before = response.json()

    if len(candidates_before) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates_before[0]["user_id"]
    bob_name = candidates_before[0]["display_name"]

    # Alice 跳過 Bob
    response = await client.post(f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    assert response.status_code == 200

    # 重新瀏覽候選人
    response = await client.get("/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates_after = response.json()

    # Bob 不應該出現在列表中（24 小時內）
    bob_in_list = any(c["user_id"] == bob_user_id for c in candidates_after)
    assert not bob_in_list, f"{bob_name} 應該被排除但仍出現在候選人列表"


@pytest.mark.asyncio
async def test_passed_user_reappears_after_24_hours(client: AsyncClient, completed_profiles: dict, test_db: AsyncSession):
    """測試：24 小時後跳過的用戶會重新出現"""
    from app.models.match import Pass
    from app.models.user import User
    from datetime import datetime, timedelta, timezone

    # 獲取 Alice 的 user_id
    result = await test_db.execute(
        select(User.id).where(User.email == completed_profiles['alice']['email'])
    )
    alice_user_id = result.scalar_one()

    # Alice 瀏覽候選人
    response = await client.get("/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Alice 跳過 Bob
    response = await client.post(f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    assert response.status_code == 200

    # 手動修改跳過時間為 25 小時前（模擬時間過去）
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    await test_db.execute(
        Pass.__table__.update()
        .where(
            Pass.from_user_id == alice_user_id,
            Pass.to_user_id == bob_user_id
        )
        .values(passed_at=old_time)
    )
    await test_db.commit()

    # 重新瀏覽候選人
    response = await client.get("/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates_after = response.json()

    # Bob 應該重新出現（超過 24 小時）
    bob_in_list = any(c["user_id"] == bob_user_id for c in candidates_after)
    assert bob_in_list, "Bob 應該在 24 小時後重新出現"


@pytest.mark.asyncio
async def test_cannot_pass_self(client: AsyncClient, completed_profiles: dict, test_db: AsyncSession):
    """測試：不能跳過自己"""
    from app.models.user import User

    # 獲取 Alice 的 user_id
    result = await test_db.execute(
        select(User.id).where(User.email == completed_profiles['alice']['email'])
    )
    alice_user_id = result.scalar_one()

    response = await client.post(f"/api/discovery/pass/{alice_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )

    assert response.status_code == 400
    assert "不能跳過自己" in response.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_pass_updates_time(client: AsyncClient, completed_profiles: dict, test_db: AsyncSession):
    """測試：重複跳過同一用戶會更新時間"""
    from app.models.match import Pass
    from app.models.user import User
    from sqlalchemy import select
    from datetime import datetime, timezone

    # 獲取 Alice 的 user_id
    result = await test_db.execute(
        select(User.id).where(User.email == completed_profiles['alice']['email'])
    )
    alice_user_id = result.scalar_one()

    # Alice 瀏覽候選人
    response = await client.get("/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # 第一次跳過
    response = await client.post(f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    assert response.status_code == 200

    # 查詢第一次跳過的時間
    result = await test_db.execute(
        select(Pass.passed_at).where(
            Pass.from_user_id == alice_user_id,
            Pass.to_user_id == bob_user_id
        )
    )
    first_pass_time = result.scalar_one()

    # 等待 1 秒
    import asyncio
    await asyncio.sleep(1)

    # 第二次跳過（應該更新時間）
    response = await client.post(f"/api/discovery/pass/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    assert response.status_code == 200

    # 查詢第二次跳過的時間
    await test_db.rollback()  # 重新載入資料
    result = await test_db.execute(
        select(Pass.passed_at).where(
            Pass.from_user_id == alice_user_id,
            Pass.to_user_id == bob_user_id
        )
    )
    second_pass_time = result.scalar_one()

    # 第二次的時間應該更新
    assert second_pass_time > first_pass_time, "重複跳過應該更新時間"


@pytest.mark.asyncio
async def test_get_matches_empty(client: AsyncClient, completed_profiles: dict):
    """測試：沒有配對時返回空列表"""
    response = await client.get("/api/discovery/matches",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )

    assert response.status_code == 200
    matches = response.json()
    assert isinstance(matches, list)


@pytest.mark.asyncio
async def test_get_matches_after_match(client: AsyncClient, completed_profiles: dict):
    """測試：配對後可以查看配對列表"""
    # 先建立配對（重複上面的互相喜歡流程）
    # Alice 瀏覽
    response = await client.get("/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    # Bob 瀏覽
    response = await client.get("/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"}
    )
    candidates = response.json()
    alice_user_id = next((c["user_id"] for c in candidates if c["display_name"] == "Alice"), None)

    if not alice_user_id:
        pytest.skip("Bob 看不到 Alice")

    # 互相喜歡
    await client.post(f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    await client.post(f"/api/discovery/like/{alice_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"}
    )

    # Alice 查看配對列表
    response = await client.get("/api/discovery/matches",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )

    assert response.status_code == 200
    matches = response.json()
    assert len(matches) > 0

    match = matches[0]
    assert "match_id" in match
    assert "matched_user" in match
    assert match["matched_user"]["display_name"] == "Bob"


@pytest.mark.asyncio
async def test_unmatch(client: AsyncClient, completed_profiles: dict):
    """測試：取消配對"""
    # 先建立配對
    response = await client.get("/api/discovery/browse?limit=1",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    candidates = response.json()

    if len(candidates) == 0:
        pytest.skip("沒有可配對的候選人")

    bob_user_id = candidates[0]["user_id"]

    response = await client.get("/api/discovery/browse?limit=10",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"}
    )
    candidates = response.json()
    alice_user_id = next((c["user_id"] for c in candidates if c["display_name"] == "Alice"), None)

    if not alice_user_id:
        pytest.skip("Bob 看不到 Alice")

    await client.post(f"/api/discovery/like/{bob_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    response = await client.post(f"/api/discovery/like/{alice_user_id}",
        headers={"Authorization": f"Bearer {completed_profiles['bob']['token']}"}
    )

    match_id = response.json()["match_id"]

    # Alice 取消配對
    response = await client.delete(f"/api/discovery/unmatch/{match_id}",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )

    assert response.status_code == 200
    assert "取消配對" in response.json()["message"]

    # 確認配對列表中沒有 Bob
    response = await client.get("/api/discovery/matches",
        headers={"Authorization": f"Bearer {completed_profiles['alice']['token']}"}
    )
    matches = response.json()
    bob_matches = [m for m in matches if m["matched_user"]["display_name"] == "Bob"]
    assert len(bob_matches) == 0
