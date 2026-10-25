"""聊天 API 的歸屬與邊界測試

情境：Alice–Bob、Bob–Charlie 為進行中的配對，Alice–Charlie 已解除配對。
每個端點都要確認「只能存取自己、且仍在進行中的配對」，而不只是「自己有任何配對」。
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.match import Match, Message
from app.models.profile import Photo, Profile
from app.models.user import User

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def at(minutes: int) -> datetime:
    return BASE + timedelta(minutes=minutes)


def make_match(a: User, b: User, status: str = "ACTIVE", matched_minutes: int = 0) -> Match:
    low, high = sorted([a.id, b.id])
    return Match(user1_id=low, user2_id=high, status=status, matched_at=at(matched_minutes))


def message(match: Match, sender: User, content: str, minutes: int, **fields) -> Message:
    return Message(
        match_id=match.id, sender_id=sender.id, content=content, sent_at=at(minutes), **fields
    )


@pytest.fixture
async def chat(client: AsyncClient, test_db: AsyncSession) -> dict:
    users = {}
    for name in ("alice", "bob", "charlie", "dave", "eve"):
        user = User(email=f"{name}@chat.example", password_hash="x", date_of_birth=date(1995, 1, 1))
        users[name] = user
    users["eve"].is_active = False
    test_db.add_all(users.values())
    await test_db.commit()
    test_db.add_all(
        Profile(user_id=user.id, display_name=name.title(), gender="female", bio="bio")
        for name, user in users.items()
    )
    matches = {
        "ab": make_match(users["alice"], users["bob"], matched_minutes=1),
        "bc": make_match(users["bob"], users["charlie"], matched_minutes=2),
        "ac": make_match(users["alice"], users["charlie"], status="UNMATCHED", matched_minutes=3),
        "bd": make_match(users["bob"], users["dave"], matched_minutes=30),
        # 對方已停用、且是最新的配對：排在最前面，跳過它不可中斷後面的對話
        "be": make_match(users["bob"], users["eve"], matched_minutes=50),
    }
    test_db.add_all(matches.values())
    await test_db.commit()
    return {
        "users": users,
        "matches": matches,
        "headers": {
            name: {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}
            for name, user in users.items()
        },
    }


async def unread_ids(db: AsyncSession) -> set[uuid.UUID]:
    result = await db.execute(select(Message.id).where(Message.is_read.is_(None)))
    return set(result.scalars().all())


# ==================== 只能存取自己的進行中配對 ====================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("viewer", "match_key"),
    [("charlie", "ab"), ("alice", "ac")],
    ids=["other-peoples-match", "unmatched"],
)
async def test_history_read_all_and_upload_require_own_active_match(
    client: AsyncClient, chat: dict, viewer: str, match_key: str
):
    """Charlie 自己有進行中的配對，仍不能存取 Alice–Bob 的；已解除的配對也不能存取"""
    match_id = chat["matches"][match_key].id
    headers = chat["headers"][viewer]

    history = await client.get(f"/api/messages/matches/{match_id}/messages", headers=headers)
    read_all = await client.post(f"/api/messages/matches/{match_id}/read-all", headers=headers)
    upload = await client.post(
        f"/api/messages/matches/{match_id}/upload-image",
        headers=headers,
        files={"file": ("a.png", b"png", "image/png")},
    )

    assert (history.status_code, history.json()["detail"]) == (404, "配對不存在或您無權查看")
    assert (read_all.status_code, read_all.json()["detail"]) == (404, "配對不存在或您無權操作")
    assert (upload.status_code, upload.json()["detail"]) == (404, "配對不存在或您無權上傳")


# ==================== 聊天記錄 ====================


@pytest.mark.asyncio
async def test_history_total_counts_only_this_match_and_not_deleted(
    client: AsyncClient, chat: dict, test_db: AsyncSession
):
    users, matches = chat["users"], chat["matches"]
    test_db.add_all(
        [
            message(matches["ab"], users["alice"], "a1", 1),
            message(matches["ab"], users["bob"], "b1", 2),
            message(matches["ab"], users["bob"], "deleted", 3, deleted_at=at(4)),
            message(matches["bc"], users["charlie"], "other match", 5),
        ]
    )
    await test_db.commit()

    response = await client.get(
        f"/api/messages/matches/{matches['ab'].id}/messages", headers=chat["headers"]["alice"]
    )

    data = response.json()
    assert [m["content"] for m in data["messages"]] == ["a1", "b1"]
    assert (data["total"], data["has_more"], data["next_cursor"]) == (2, False, None)


@pytest.mark.asyncio
async def test_cursor_pagination_with_identical_timestamps(
    client: AsyncClient, chat: dict, test_db: AsyncSession
):
    """同一時間送出的訊息以 id 排序分頁，不重複也不遺漏"""
    users, match = chat["users"], chat["matches"]["ab"]
    same_time = [message(match, users["alice"], f"same{i}", 10) for i in range(4)]
    older = message(match, users["bob"], "older", 5)
    test_db.add_all([*same_time, older])
    await test_db.commit()
    expected = ["older"] + [m.content for m in sorted(same_time, key=lambda m: m.id)]
    url = f"/api/messages/matches/{match.id}/messages"
    headers = chat["headers"]["alice"]

    pages = []
    params = {"limit": 2}
    while True:
        data = (await client.get(url, headers=headers, params=params)).json()
        pages.append([m["content"] for m in data["messages"]])
        if not data["has_more"]:
            break
        assert data["next_cursor"] == data["messages"][0]["id"]
        params = {"limit": 2, "before_id": data["next_cursor"]}

    assert pages == [expected[3:], expected[1:3], expected[:1]]


# ==================== 對話列表 ====================


@pytest.mark.asyncio
async def test_conversations(client: AsyncClient, chat: dict, test_db: AsyncSession):
    """只列出自己進行中的配對；每個對話各自的最後一則（排除已刪除）與未讀數（只算對方未讀未刪）；
    有訊息的依最後訊息時間、沒有的依配對時間，由新到舊；對方已停用的對話跳過"""
    users, matches = chat["users"], chat["matches"]
    # Bob 已解除的配對、與 Bob 無關的進行中配對，都不能出現
    frank = User(email="frank@chat.example", password_hash="x", date_of_birth=date(1995, 1, 1))
    test_db.add(frank)
    await test_db.commit()
    test_db.add(Profile(user_id=frank.id, display_name="Frank", gender="male", bio="bio"))
    test_db.add_all(
        [
            make_match(users["bob"], frank, status="UNMATCHED", matched_minutes=70),
            make_match(users["alice"], users["dave"], matched_minutes=80),
        ]
    )
    alice_photo = Photo(
        profile_id=(await profile_of(test_db, users["alice"])).id,
        url="/uploads/alice.jpg",
        thumbnail_url="/uploads/alice_thumb.jpg",
        display_order=0,
    )
    charlie_profile = await profile_of(test_db, users["charlie"])
    charlie_photos = [
        Photo(
            profile_id=charlie_profile.id,
            url="/uploads/c0.jpg",
            thumbnail_url="/uploads/c0_thumb.jpg",
            display_order=0,
        ),
        Photo(profile_id=charlie_profile.id, url="/uploads/c1.jpg", display_order=1),
    ]
    charlie_photos[1].is_profile_picture = True
    test_db.add_all([alice_photo, *charlie_photos])
    test_db.add_all(
        [
            message(matches["ab"], users["alice"], "a1", 10),
            message(matches["ab"], users["bob"], "b1", 20),
            message(matches["ab"], users["alice"], "a2 deleted", 25, deleted_at=at(26)),
            # 最後一則依 (sent_at, id) 由新到舊：c1 的 id 最大但最舊；c2、c3 同時送出時取 id 較大者
            message(matches["bc"], users["charlie"], "c1", 40, id=uuid.UUID(int=9)),
            message(matches["bc"], users["charlie"], "c2", 45, id=uuid.UUID(int=5)),
            message(
                matches["bc"], users["charlie"], "c3 read", 45, id=uuid.UUID(int=6), is_read=at(46)
            ),
            message(matches["ac"], users["charlie"], "unmatched", 60),
        ]
    )
    await test_db.commit()

    response = await client.get("/api/messages/conversations", headers=chat["headers"]["bob"])

    assert response.status_code == 200
    assert [
        (
            c["match_id"],
            c["other_user_name"],
            c["last_message"]["content"] if c["last_message"] else None,
            c["unread_count"],
            c["other_user_avatar"],
            c["other_user_avatar_thumb"],
        )
        for c in response.json()
    ] == [
        # 主頭像（第二張、無縮圖時退回原圖）優先於第一張照片
        (str(matches["bc"].id), "Charlie", "c3 read", 2, "/uploads/c1.jpg", "/uploads/c1.jpg"),
        (str(matches["bd"].id), "Dave", None, 0, None, None),
        (
            str(matches["ab"].id),
            "Alice",
            "b1",
            1,
            "/uploads/alice.jpg",
            "/uploads/alice_thumb.jpg",
        ),
    ]


async def profile_of(db: AsyncSession, user: User) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    return result.scalar_one()


# ==================== 標記已讀 ====================


@pytest.mark.asyncio
async def test_mark_read_only_requested_messages_in_own_active_matches(
    client: AsyncClient, chat: dict, test_db: AsyncSession
):
    users, matches = chat["users"], chat["matches"]
    msgs = {
        "from_alice": message(matches["ab"], users["alice"], "from alice", 1),
        "from_bob": message(matches["ab"], users["bob"], "from bob", 2),
        "not_requested": message(matches["ab"], users["alice"], "not requested", 3),
        "deleted": message(matches["ab"], users["alice"], "deleted", 4, deleted_at=at(5)),
        "unmatched": message(matches["ac"], users["charlie"], "unmatched", 6),
        "others_match": message(matches["bc"], users["charlie"], "bob-charlie", 7),
    }
    test_db.add_all(msgs.values())
    await test_db.commit()

    async def mark(viewer: str, *keys: str) -> None:
        response = await client.post(
            "/api/messages/read",
            headers=chat["headers"][viewer],
            json={"message_ids": [str(msgs[key].id) for key in keys]},
        )
        assert response.status_code == 204

    # 雙方各自標記對方的訊息（不論自己是配對的 user1 或 user2）
    await mark("bob", "from_alice", "deleted")
    await mark("alice", "from_bob", "unmatched", "others_match")

    assert await unread_ids(test_db) == {
        msgs[key].id for key in ("not_requested", "deleted", "unmatched", "others_match")
    }


@pytest.mark.asyncio
async def test_read_all_only_this_match_and_keeps_existing_read_time(
    client: AsyncClient, chat: dict, test_db: AsyncSession
):
    users, matches = chat["users"], chat["matches"]
    already_read_at = at(100)
    msgs = {
        "unread": message(matches["ab"], users["alice"], "unread", 1),
        "already_read": message(matches["ab"], users["alice"], "read", 2, is_read=already_read_at),
        "deleted": message(matches["ab"], users["alice"], "deleted", 3, deleted_at=at(4)),
        "own": message(matches["ab"], users["bob"], "own", 5),
        "other_match": message(matches["bc"], users["charlie"], "other match", 6),
    }
    test_db.add_all(msgs.values())
    await test_db.commit()

    with patch("app.api.messages.manager.send_personal_message", new_callable=AsyncMock) as send:
        response = await client.post(
            f"/api/messages/matches/{matches['ab'].id}/read-all", headers=chat["headers"]["bob"]
        )

    assert response.status_code == 204
    assert await unread_ids(test_db) == {msgs[k].id for k in ("deleted", "own", "other_match")}
    await test_db.refresh(msgs["already_read"])
    assert msgs["already_read"].is_read == already_read_at

    # 只通知對方被標記的那一則，已讀時間帶 UTC 時區
    [call] = send.await_args_list
    recipient, payload = call.args
    assert recipient == str(users["alice"].id)
    assert payload["message_id"] == str(msgs["unread"].id)
    assert payload["read_by"] == str(users["bob"].id)
    assert datetime.fromisoformat(payload["read_at"]).utcoffset() == timedelta(0)


# ==================== 刪除訊息 ====================


@pytest.mark.asyncio
async def test_delete_message_commit_failure_returns_500(
    client: AsyncClient, chat: dict, test_db: AsyncSession, monkeypatch
):
    users, match = chat["users"], chat["matches"]["ab"]
    msg = message(match, users["alice"], "to delete", 1)
    test_db.add(msg)
    await test_db.commit()
    monkeypatch.setattr(test_db, "commit", AsyncMock(side_effect=RuntimeError("db down")))

    with patch("app.api.messages.manager.send_to_match", new_callable=AsyncMock) as broadcast:
        response = await client.delete(f"/api/messages/{msg.id}", headers=chat["headers"]["alice"])

    assert (response.status_code, response.json()["detail"]) == (500, "訊息刪除失敗，請稍後再試")
    broadcast.assert_not_awaited()


# ==================== 上傳聊天圖片 ====================


@pytest.fixture
def save_chat_image():
    with patch(
        "app.api.messages.file_storage.save_chat_image",
        new_callable=AsyncMock,
        return_value=(
            str(uuid.uuid4()),
            "/uploads/chat/x.webp",
            "/uploads/chat/x_thumb.webp",
            10,
            20,
            False,
        ),
    ) as mock:
        yield mock


@pytest.mark.asyncio
async def test_upload_passes_complete_content(client: AsyncClient, chat: dict, save_chat_image):
    """分塊讀取後完整交給儲存服務（超過一個 64KB 區塊），支援 WebP"""
    content = bytes(range(256)) * 1024  # 256KB
    match = chat["matches"]["ab"]

    response = await client.post(
        f"/api/messages/matches/{match.id}/upload-image",
        headers=chat["headers"]["alice"],
        files={"file": ("photo.webp", content, "image/webp")},
    )

    assert response.status_code == 200
    assert response.json()["image_url"] == "/uploads/chat/x.webp"
    save_chat_image.assert_awaited_once_with(
        match_id=str(match.id),
        user_id=str(chat["users"]["alice"].id),
        file_content=content,
        filename="photo.webp",
        content_type="image/webp",
    )


@pytest.mark.asyncio
async def test_upload_size_limit_boundary(
    client: AsyncClient, chat: dict, save_chat_image, monkeypatch
):
    """剛好等於上限可上傳，超過 1 byte 回 413"""
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 2 * 1024 * 1024)
    url = f"/api/messages/matches/{chat['matches']['ab'].id}/upload-image"
    headers = chat["headers"]["alice"]

    at_limit = await client.post(
        url, headers=headers, files={"file": ("a.png", b"x" * (2 * 1024 * 1024), "image/png")}
    )
    over_limit = await client.post(
        url, headers=headers, files={"file": ("a.png", b"x" * (2 * 1024 * 1024 + 1), "image/png")}
    )

    assert at_limit.status_code == 200
    assert (over_limit.status_code, over_limit.json()["detail"]) == (
        413,
        "檔案過大，最大允許 2MB",
    )


@pytest.mark.asyncio
async def test_upload_storage_failure_returns_500(client: AsyncClient, chat: dict, save_chat_image):
    save_chat_image.side_effect = OSError("disk full")

    response = await client.post(
        f"/api/messages/matches/{chat['matches']['ab'].id}/upload-image",
        headers=chat["headers"]["alice"],
        files={"file": ("a.png", b"png", "image/png")},
    )

    assert (response.status_code, response.json()["detail"]) == (500, "圖片儲存失敗，請稍後再試")
