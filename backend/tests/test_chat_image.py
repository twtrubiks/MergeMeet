"""聊天圖片上傳功能測試"""
import pytest
import uuid
import io
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from PIL import Image

from app.models.user import User
from app.models.match import Match, Message


def create_test_image(width: int = 100, height: int = 100, format: str = "JPEG") -> bytes:
    """創建測試圖片"""
    img = Image.new("RGB", (width, height), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer.read()


def create_test_gif() -> bytes:
    """創建測試 GIF"""
    frames = []
    for color in ["red", "green", "blue"]:
        img = Image.new("RGB", (100, 100), color=color)
        frames.append(img)

    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0
    )
    buffer.seek(0)
    return buffer.read()


@pytest.fixture
async def matched_users_for_image(client: AsyncClient, test_db: AsyncSession):
    """創建已配對的測試用戶（用於圖片測試）"""
    # 註冊 Alice
    response_a = await client.post("/api/auth/register", json={
        "email": "alice_img@example.com",
        "password": "Alice1234",
        "date_of_birth": "1995-06-15"
    })
    assert response_a.status_code == 201
    alice_token = response_a.json()["access_token"]

    # 註冊 Bob
    response_b = await client.post("/api/auth/register", json={
        "email": "bob_img@example.com",
        "password": "Bob12345",
        "date_of_birth": "1990-03-20"
    })
    assert response_b.status_code == 201
    bob_token = response_b.json()["access_token"]

    # 創建 Alice 的檔案
    await client.post("/api/profile/",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={
            "display_name": "Alice",
            "gender": "female",
            "bio": "測試用戶",
            "location": {
                "latitude": 25.0330,
                "longitude": 121.5654,
                "location_name": "台北市"
            }
        }
    )

    # 創建 Bob 的檔案
    await client.post("/api/profile/",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={
            "display_name": "Bob",
            "gender": "male",
            "bio": "測試用戶",
            "location": {
                "latitude": 25.0500,
                "longitude": 121.5500,
                "location_name": "台北市"
            }
        }
    )

    # 獲取用戶 ID
    result = await test_db.execute(select(User).where(User.email == "alice_img@example.com"))
    alice = result.scalar_one()

    result = await test_db.execute(select(User).where(User.email == "bob_img@example.com"))
    bob = result.scalar_one()

    # 直接創建配對
    user1_id, user2_id = (alice.id, bob.id) if alice.id < bob.id else (bob.id, alice.id)
    match = Match(
        user1_id=user1_id,
        user2_id=user2_id,
        status="ACTIVE"
    )
    test_db.add(match)
    await test_db.commit()
    await test_db.refresh(match)

    return {
        "alice": {"token": alice_token, "user_id": str(alice.id)},
        "bob": {"token": bob_token, "user_id": str(bob.id)},
        "match_id": str(match.id)
    }


@pytest.mark.asyncio
async def test_upload_image_success(client: AsyncClient, matched_users_for_image: dict):
    """測試成功上傳圖片"""
    match_id = matched_users_for_image["match_id"]
    alice_token = matched_users_for_image["alice"]["token"]

    # 創建測試圖片
    image_content = create_test_image(800, 600)

    response = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("test.jpg", image_content, "image/jpeg")}
    )

    assert response.status_code == 200
    data = response.json()
    assert "image_id" in data
    assert "image_url" in data
    assert "thumbnail_url" in data
    assert data["width"] == 800
    assert data["height"] == 600
    assert data["is_gif"] is False
    assert f"/uploads/chat/{match_id}/" in data["image_url"]
    assert f"/uploads/chat/{match_id}/" in data["thumbnail_url"]


@pytest.mark.asyncio
async def test_upload_gif_success(client: AsyncClient, matched_users_for_image: dict):
    """測試成功上傳 GIF"""
    match_id = matched_users_for_image["match_id"]
    alice_token = matched_users_for_image["alice"]["token"]

    # 創建測試 GIF
    gif_content = create_test_gif()

    response = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("test.gif", gif_content, "image/gif")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_gif"] is True
    assert data["image_url"].endswith(".gif")
    assert data["thumbnail_url"].endswith(".jpg")  # 縮圖仍是 JPG


@pytest.mark.asyncio
async def test_upload_image_unauthorized(client: AsyncClient, matched_users_for_image: dict):
    """測試非配對成員無法上傳"""
    match_id = matched_users_for_image["match_id"]

    # 註冊新用戶 Charlie（不在配對中）
    response_c = await client.post("/api/auth/register", json={
        "email": "charlie_img@example.com",
        "password": "Charlie123",
        "date_of_birth": "1988-01-01"
    })
    assert response_c.status_code == 201
    charlie_token = response_c.json()["access_token"]

    # 創建 Charlie 的檔案
    await client.post("/api/profile/",
        headers={"Authorization": f"Bearer {charlie_token}"},
        json={
            "display_name": "Charlie",
            "gender": "male",
            "bio": "測試用戶",
            "location": {
                "latitude": 25.0,
                "longitude": 121.5,
                "location_name": "台北市"
            }
        }
    )

    # 嘗試上傳到別人的配對
    image_content = create_test_image()
    response = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers={"Authorization": f"Bearer {charlie_token}"},
        files={"file": ("test.jpg", image_content, "image/jpeg")}
    )

    assert response.status_code == 404
    assert "無權上傳" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_image_invalid_format(client: AsyncClient, matched_users_for_image: dict):
    """測試上傳非圖片格式"""
    match_id = matched_users_for_image["match_id"]
    alice_token = matched_users_for_image["alice"]["token"]

    # 上傳文字檔
    text_content = b"This is not an image"
    response = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("test.txt", text_content, "text/plain")}
    )

    assert response.status_code == 400
    assert "不支援的圖片格式" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_image_empty_file(client: AsyncClient, matched_users_for_image: dict):
    """測試上傳空檔案"""
    match_id = matched_users_for_image["match_id"]
    alice_token = matched_users_for_image["alice"]["token"]

    response = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("test.jpg", b"", "image/jpeg")}
    )

    assert response.status_code == 400
    assert "不能為空" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_image_to_inactive_match(client: AsyncClient, matched_users_for_image: dict, test_db: AsyncSession):
    """測試上傳到已解除配對"""
    match_id = matched_users_for_image["match_id"]
    alice_token = matched_users_for_image["alice"]["token"]

    # 將配對設為 UNMATCHED
    result = await test_db.execute(select(Match).where(Match.id == match_id))
    match = result.scalar_one()
    match.status = "UNMATCHED"
    await test_db.commit()

    # 嘗試上傳
    image_content = create_test_image()
    response = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("test.jpg", image_content, "image/jpeg")}
    )

    assert response.status_code == 404
    assert "不存在或您無權" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_image_to_nonexistent_match(client: AsyncClient, matched_users_for_image: dict):
    """測試上傳到不存在的配對"""
    alice_token = matched_users_for_image["alice"]["token"]
    fake_match_id = str(uuid.uuid4())

    image_content = create_test_image()
    response = await client.post(
        f"/api/messages/matches/{fake_match_id}/upload-image",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("test.jpg", image_content, "image/jpeg")}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_image_message_in_chat_history(client: AsyncClient, matched_users_for_image: dict, test_db: AsyncSession):
    """測試圖片訊息出現在聊天記錄"""
    match_id = matched_users_for_image["match_id"]
    alice_token = matched_users_for_image["alice"]["token"]
    alice_user_id = matched_users_for_image["alice"]["user_id"]

    # 上傳圖片
    image_content = create_test_image()
    upload_response = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("test.jpg", image_content, "image/jpeg")}
    )
    assert upload_response.status_code == 200
    upload_data = upload_response.json()

    # 直接在資料庫中創建圖片訊息（模擬 WebSocket 發送）
    image_message_content = json.dumps({
        "image_url": upload_data["image_url"],
        "thumbnail_url": upload_data["thumbnail_url"],
        "width": upload_data["width"],
        "height": upload_data["height"]
    })

    message = Message(
        match_id=match_id,
        sender_id=alice_user_id,
        content=image_message_content,
        message_type="IMAGE"
    )
    test_db.add(message)
    await test_db.commit()

    # 查詢聊天記錄
    history_response = await client.get(
        f"/api/messages/matches/{match_id}/messages",
        headers={"Authorization": f"Bearer {alice_token}"}
    )

    assert history_response.status_code == 200
    history_data = history_response.json()
    assert len(history_data["messages"]) == 1
    assert history_data["messages"][0]["message_type"] == "IMAGE"

    # 驗證 content 是有效的 JSON
    msg_content = json.loads(history_data["messages"][0]["content"])
    assert "image_url" in msg_content
    assert "thumbnail_url" in msg_content


@pytest.mark.asyncio
async def test_upload_png_success(client: AsyncClient, matched_users_for_image: dict):
    """測試成功上傳 PNG 圖片"""
    match_id = matched_users_for_image["match_id"]
    alice_token = matched_users_for_image["alice"]["token"]

    # 創建 PNG 測試圖片
    image_content = create_test_image(400, 300, "PNG")

    response = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers={"Authorization": f"Bearer {alice_token}"},
        files={"file": ("test.png", image_content, "image/png")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_gif"] is False
    assert data["width"] == 400
    assert data["height"] == 300
