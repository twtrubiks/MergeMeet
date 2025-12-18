# 完整範例 (Complete Examples)

## Profile API 完整實作

### 後端實作
```python
# backend/app/api/profile.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.deps import get_current_user, get_db
from ..models.user import User
from ..models.profile import Profile, Photo
from ..schemas.profile import (
    ProfileResponse,
    ProfileUpdate,
    InterestTagResponse,
    PhotoResponse
)

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """獲取個人檔案"""
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="個人檔案不存在"
        )
    return current_user.profile

@router.put("", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新個人檔案"""
    profile = current_user.profile

    # 更新欄位
    for field, value in profile_data.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile

@router.put("/interests", response_model=ProfileResponse)
async def update_interests(
    interests: List[str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新興趣標籤"""
    profile = current_user.profile

    # 清除舊的興趣
    profile.interests.clear()

    # 添加新的興趣
    from ..models.profile import InterestTag
    tags = await db.execute(
        select(InterestTag).where(InterestTag.name.in_(interests))
    )
    profile.interests.extend(tags.scalars().all())

    await db.commit()
    await db.refresh(profile)
    return profile

@router.post("/photos", status_code=status.HTTP_201_CREATED, response_model=PhotoResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上傳照片"""
    # 檢查照片數量限制
    photo_count = len(current_user.profile.photos)
    if photo_count >= 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="最多只能上傳 6 張照片"
        )

    # 儲存檔案
    file_path = await save_upload_file(file)

    # 創建照片記錄
    photo = Photo(
        profile_id=current_user.profile.id,
        file_path=file_path,
        is_primary=(photo_count == 0)  # 第一張設為主照片
    )

    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo

@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """刪除照片"""
    photo = await db.get(Photo, photo_id)

    if not photo or photo.profile_id != current_user.profile.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="照片不存在"
        )

    # 刪除檔案
    delete_file(photo.file_path)

    # 刪除記錄
    await db.delete(photo)
    await db.commit()

@router.get("/interest-tags", response_model=List[InterestTagResponse])
async def get_interest_tags(db: AsyncSession = Depends(get_db)):
    """獲取所有興趣標籤"""
    from ..models.profile import InterestTag
    result = await db.execute(select(InterestTag))
    tags = result.scalars().all()
    return tags
```

### 前端實作 (Pinia Store)
```javascript
// frontend/src/stores/profile.js
import { defineStore } from 'pinia'
import axios from 'axios'

export const useProfileStore = defineStore('profile', {
  state: () => ({
    profile: null,
    interestTags: [],
    loading: false,
    error: null
  }),

  actions: {
    async fetchProfile() {
      this.loading = true
      try {
        // ✅ 正確 - 無尾隨斜線
        const response = await axios.get('/api/profile')
        this.profile = response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    },

    async updateProfile(profileData) {
      try {
        // ✅ 正確 - 無尾隨斜線
        const response = await axios.put('/api/profile', profileData)
        this.profile = response.data
        return response.data
      } catch (error) {
        throw error
      }
    },

    async updateInterests(interests) {
      try {
        // ✅ 正確 - 無尾隨斜線
        const response = await axios.put('/api/profile/interests', { interests })
        this.profile = response.data
      } catch (error) {
        throw error
      }
    },

    async uploadPhoto(file) {
      const formData = new FormData()
      formData.append('file', file)

      try {
        // ✅ 正確 - 無尾隨斜線
        const response = await axios.post('/api/profile/photos', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        // 重新獲取檔案
        await this.fetchProfile()
        return response.data
      } catch (error) {
        throw error
      }
    },

    async deletePhoto(photoId) {
      try {
        // ✅ 正確 - 無尾隨斜線
        await axios.delete(`/api/profile/photos/${photoId}`)

        // 重新獲取檔案
        await this.fetchProfile()
      } catch (error) {
        throw error
      }
    },

    async fetchInterestTags() {
      try {
        // ✅ 正確 - 無尾隨斜線
        const response = await axios.get('/api/profile/interest-tags')
        this.interestTags = response.data
      } catch (error) {
        throw error
      }
    }
  }
})
```

### Vue 組件
```vue
<!-- frontend/src/views/Profile.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useProfileStore } from '@/stores/profile'

const profileStore = useProfileStore()
const selectedFile = ref(null)

onMounted(async () => {
  await profileStore.fetchProfile()
  await profileStore.fetchInterestTags()
})

const handleFileSelect = (event) => {
  selectedFile.value = event.target.files[0]
}

const uploadPhoto = async () => {
  if (!selectedFile.value) return

  try {
    await profileStore.uploadPhoto(selectedFile.value)
    selectedFile.value = null
    alert('照片上傳成功！')
  } catch (error) {
    alert('上傳失敗：' + error.message)
  }
}

const deletePhoto = async (photoId) => {
  if (!confirm('確定要刪除這張照片嗎？')) return

  try {
    await profileStore.deletePhoto(photoId)
    alert('照片已刪除')
  } catch (error) {
    alert('刪除失敗：' + error.message)
  }
}
</script>

<template>
  <div class="profile-page">
    <h1>個人檔案</h1>

    <div v-if="profileStore.loading">載入中...</div>

    <div v-else-if="profileStore.profile" class="profile-content">
      <h2>照片</h2>
      <div class="photos">
        <div v-for="photo in profileStore.profile.photos" :key="photo.id" class="photo-card">
          <img :src="photo.file_path" :alt="photo.is_primary ? '主照片' : '照片'" />
          <span v-if="photo.is_primary" class="primary-badge">主照片</span>
          <button @click="deletePhoto(photo.id)">刪除</button>
        </div>
      </div>

      <div class="upload-section">
        <input type="file" accept="image/*" @change="handleFileSelect" />
        <button @click="uploadPhoto" :disabled="!selectedFile">上傳照片</button>
      </div>

      <h2>興趣標籤</h2>
      <div class="interests">
        <span v-for="interest in profileStore.profile.interests" :key="interest" class="tag">
          {{ interest }}
        </span>
      </div>
    </div>
  </div>
</template>
```

---

## Discovery API 完整實作

### 後端實作
```python
# backend/app/api/discovery.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

router = APIRouter(prefix="/api/discovery", tags=["Discovery"])

@router.get("/browse", response_model=List[UserCardResponse])
async def browse_candidates(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """瀏覽候選人"""
    # 配對演算法邏輯
    candidates = await get_compatible_users(current_user, limit, db)
    return candidates

@router.post("/like/{user_id}", status_code=status.HTTP_201_CREATED)
async def like_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """喜歡用戶"""
    # 檢查目標用戶是否存在
    target_user = await db.get(User, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )

    # 創建 Like 記錄
    like = Like(liker_id=current_user.id, liked_id=user_id)
    db.add(like)

    # 檢查是否雙向喜歡（配對）
    mutual_like = await db.execute(
        select(Like).where(
            Like.liker_id == user_id,
            Like.liked_id == current_user.id
        )
    )

    if mutual_like.scalar_one_or_none():
        # 創建配對
        match = Match(user1_id=current_user.id, user2_id=user_id)
        db.add(match)
        await db.commit()
        return {"matched": True, "match_id": match.id}

    await db.commit()
    return {"matched": False}

@router.post("/pass/{user_id}", status_code=status.HTTP_200_OK)
async def pass_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """跳過用戶"""
    # 記錄到快取或資料庫（避免重複顯示）
    return {"passed": True}

@router.get("/matches", response_model=List[MatchResponse])
async def get_matches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """獲取配對列表"""
    matches = await db.execute(
        select(Match).where(
            or_(
                Match.user1_id == current_user.id,
                Match.user2_id == current_user.id
            )
        )
    )
    return matches.scalars().all()
```

### 前端實作
```javascript
// frontend/src/stores/discovery.js
import { defineStore } from 'pinia'
import axios from 'axios'

export const useDiscoveryStore = defineStore('discovery', {
  state: () => ({
    candidates: [],
    currentIndex: 0,
    matches: []
  }),

  getters: {
    currentCandidate: (state) => state.candidates[state.currentIndex]
  },

  actions: {
    async fetchCandidates() {
      const response = await axios.get('/api/discovery/browse')  // ✅ 無斜線
      this.candidates = response.data
      this.currentIndex = 0
    },

    async likeUser(userId) {
      const response = await axios.post(`/api/discovery/like/${userId}`)  // ✅ 無斜線

      if (response.data.matched) {
        alert('配對成功！')
        await this.fetchMatches()
      }

      this.nextCandidate()
    },

    async passUser(userId) {
      await axios.post(`/api/discovery/pass/${userId}`)  // ✅ 無斜線
      this.nextCandidate()
    },

    nextCandidate() {
      this.currentIndex++
      if (this.currentIndex >= this.candidates.length) {
        this.fetchCandidates()
      }
    },

    async fetchMatches() {
      const response = await axios.get('/api/discovery/matches')  // ✅ 無斜線
      this.matches = response.data
    }
  }
})
```

---

## 測試範例

### pytest 測試
```python
# backend/tests/test_profile.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_profile_success(client: AsyncClient, auth_headers):
    """測試：成功獲取個人檔案"""
    response = await client.get("/api/profile", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "bio" in data

@pytest.mark.asyncio
async def test_get_profile_with_trailing_slash(client: AsyncClient, auth_headers):
    """測試：帶尾隨斜線應該返回 404"""
    response = await client.get("/api/profile/", headers=auth_headers)

    assert response.status_code == 404  # ⚠️ 預期的錯誤

@pytest.mark.asyncio
async def test_update_interests(client: AsyncClient, auth_headers):
    """測試：更新興趣標籤"""
    interests = ["運動", "旅遊", "音樂"]

    response = await client.put(
        "/api/profile/interests",  # ✅ 無尾隨斜線
        json={"interests": interests},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data["interests"]) == set(interests)

@pytest.mark.asyncio
async def test_upload_photo(client: AsyncClient, auth_headers):
    """測試：上傳照片"""
    files = {"file": ("test.jpg", open("test.jpg", "rb"), "image/jpeg")}

    response = await client.post(
        "/api/profile/photos",  # ✅ 無尾隨斜線
        files=files,
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "file_path" in data

@pytest.mark.asyncio
async def test_delete_photo(client: AsyncClient, auth_headers, photo_id):
    """測試：刪除照片"""
    response = await client.delete(
        f"/api/profile/photos/{photo_id}",  # ✅ 無尾隨斜線
        headers=auth_headers
    )

    assert response.status_code == 204
```

---

## 查詢官方文檔

使用 context7 MCP 查詢更多範例：

```bash
# FastAPI 範例
context7: resolve-library-id "fastapi"
context7: get-library-docs "/fastapi" topic="routing examples"

# Pydantic 範例
context7: resolve-library-id "pydantic"
context7: get-library-docs "/pydantic" topic="response model"

# SQLAlchemy Async 範例
context7: resolve-library-id "sqlalchemy"
context7: get-library-docs "/sqlalchemy" topic="async orm"
```

---

**記住**：所有 URL 都不使用尾隨斜線 - 前後端保持一致！
