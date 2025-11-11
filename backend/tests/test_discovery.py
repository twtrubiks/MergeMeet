"""探索與配對功能測試"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

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
async def completed_profiles(client: AsyncClient, test_users: dict):
    """創建完整的個人檔案"""
    # Alice 的檔案
    await client.post("/api/profile",
        headers={"Authorization": f"Bearer {test_users['alice']['token']}"},
        json={
            "display_name": "Alice",
            "gender": "female",
            "bio": "喜歡旅遊和美食",
            "location": {"lat": 25.0330, "lng": 121.5654},
            "location_name": "台北市信義區",
            "min_age_preference": 25,
            "max_age_preference": 40,
            "max_distance_km": 50,
            "gender_preference": "male"
        }
    )

    # Bob 的檔案
    await client.post("/api/profile",
        headers={"Authorization": f"Bearer {test_users['bob']['token']}"},
        json={
            "display_name": "Bob",
            "gender": "male",
            "bio": "熱愛運動和旅遊",
            "location": {"lat": 25.0500, "lng": 121.5500},
            "location_name": "台北市大安區",
            "min_age_preference": 22,
            "max_age_preference": 35,
            "max_distance_km": 30,
            "gender_preference": "female"
        }
    )

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
