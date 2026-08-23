"""配對推薦服務"""

import uuid
from datetime import UTC, datetime, timedelta

from dateutil.relativedelta import relativedelta
from geoalchemy2.functions import ST_DWithin
from sqlalchemy import Select, and_, case, exists, func, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.match import BlockedUser, Like, Match, Pass
from app.models.profile import Profile
from app.models.user import User
from app.schemas.discovery import ExpandSuggestion, ProfileCard

# 配對分數最低門檻（低於此分數的用戶不會出現在探索列表）
MIN_MATCH_SCORE = 15.0

# browse_candidates 分批撈取的批次上限（避免極端情況下掃描整個候選池）
MAX_BROWSE_BATCHES = 10

# 「已喜歡我」的候選人排序加權（只影響排序，不寫進回傳的 match_score）
# 把註定會成的配對推前，但採保守加分而非強制置頂，避免低品質暗戀者洗版整個卡堆
LIKED_ME_SORT_BONUS = 15.0

# 空池放寬建議的邊界（與 schemas/profile.py 的偏好驗證範圍一致）
MAX_DISTANCE_KM = 500
MIN_AGE = 18
MAX_AGE = 99
AGE_EXPAND_STEP = 5


def _common_interests(viewer_interests: list[str], candidate_interests: list[str]) -> list[str]:
    """取出雙方共同興趣，依候選人興趣順序輸出（去重）

    與 calculate_match_score 內的交集邏輯一致，但獨立成純函式
    以免更動既有評分函式簽名；回傳 list 而非 set 是為了輸出順序穩定。
    """
    viewer_set = set(viewer_interests)
    seen: set[str] = set()
    common: list[str] = []
    for name in candidate_interests:
        if name in viewer_set and name not in seen:
            seen.add(name)
            common.append(name)
    return common


def _calculate_distance_score(distance_km: float) -> float:
    """計算距離分數（最高 20 分）

    Args:
        distance_km: 距離（公里）

    Returns:
        距離分數
    """
    if distance_km < 5:
        return 20
    if distance_km < 10:
        return 15
    if distance_km < 25:
        return 10
    if distance_km < 50:
        return 5
    return 0


def _calculate_activity_score(last_active) -> float:
    """計算活躍度分數（最高 20 分）

    Args:
        last_active: 最後活躍時間

    Returns:
        活躍度分數
    """
    if not last_active:
        return 0

    if isinstance(last_active, str):
        last_active = datetime.fromisoformat(last_active.replace("Z", "+00:00"))

    hours_ago = (datetime.now(UTC) - last_active).total_seconds() / 3600

    if hours_ago < 1:
        return 20
    if hours_ago < 24:
        return 15
    if hours_ago < 72:
        return 10
    if hours_ago < 168:  # 7天
        return 5
    return 0


def _calculate_completeness_score(candidate: dict) -> float:
    """計算檔案完整度分數（最高 5 分）

    權重調整：原 10 分改為 5 分，騰出 5 分給信任分數

    Args:
        candidate: 候選人資料

    Returns:
        完整度分數
    """
    score = 0.0
    # 照片：每張 0.5 分，最多 3 分
    photo_count = candidate.get("photo_count", 0)
    score += min(photo_count * 0.5, 3)
    # 自我介紹：2 分
    if candidate.get("bio"):
        score += 2
    return score


def _calculate_trust_score_weight(trust_score: int) -> float:
    """計算信任分數權重（最高 5 分）

    信任分數映射：
    - trust_score >= 70: 5 分（高度信任）
    - trust_score >= 50: 4 分（正常）
    - trust_score >= 30: 2.5 分（需關注）
    - trust_score >= 20: 1 分（受限）
    - trust_score < 20: 0 分（高度可疑）

    Args:
        trust_score: 用戶信任分數 (0-100)

    Returns:
        信任權重分數
    """
    if trust_score >= 70:
        return 5.0
    if trust_score >= 50:
        return 4.0
    if trust_score >= 30:
        return 2.5
    if trust_score >= 20:
        return 1.0
    return 0.0


class MatchingService:
    """配對推薦服務"""

    def calculate_match_score(self, user_profile: dict, candidate: dict) -> float:
        """
        計算配對分數

        評分因素（總分 100 分）:
        - 興趣匹配: 50 分 (每個共同興趣 10 分)
        - 距離: 20 分
        - 活躍度: 20 分
        - 檔案完整度: 5 分（原 10 分）
        - 信任分數: 5 分（新增）

        Args:
            user_profile: 當前用戶的檔案資料
            candidate: 候選人的檔案資料

        Returns:
            配對分數 (0-100)
        """
        score = 0.0

        # 1. 興趣匹配（最高 50 分）
        user_interests = set(user_profile.get("interests", []))
        candidate_interests = set(candidate.get("interests", []))
        common_interests = user_interests & candidate_interests
        score += min(len(common_interests) * 10, 50)

        # 2. 距離因素（最高 20 分）
        score += _calculate_distance_score(candidate.get("distance_km", 999))

        # 3. 活躍度（最高 20 分）
        score += _calculate_activity_score(candidate.get("last_active"))

        # 4. 檔案完整度（最高 5 分）
        score += _calculate_completeness_score(candidate)

        # 5. 信任分數（最高 5 分）
        trust_score = candidate.get("trust_score", 50)  # 預設 50 分
        score += _calculate_trust_score_weight(trust_score)

        return min(score, 100)

    def _candidate_query(
        self,
        viewer_id: uuid.UUID,
        my_profile: Profile,
        *,
        min_age: int,
        max_age: int,
        max_distance_km: int,
    ) -> Select:
        """建立候選人篩選查詢（browse 與空池放寬建議共用，確保條件不漂移）

        條件：可見、完整、啟用、年齡區間、距離內、性別偏好，
        並排除已喜歡、已配對、已封鎖（雙向）、24h 內跳過的用戶。

        回傳 ``select(Profile)``，呼叫端可再 ``add_columns`` / ``options`` / ``order_by``，
        或包成 subquery 做 count。
        """
        today = datetime.today().date()
        max_birth_date = today - relativedelta(years=min_age)
        min_birth_date = today - relativedelta(years=max_age + 1)

        query = (
            select(Profile)
            .join(User, Profile.user_id == User.id)
            .where(
                and_(
                    Profile.user_id != viewer_id,
                    Profile.is_visible.is_(True),
                    Profile.is_complete.is_(True),
                    User.is_active.is_(True),
                    # 年齡篩選
                    User.date_of_birth >= min_birth_date,
                    User.date_of_birth <= max_birth_date,
                    # 距離篩選 (PostGIS)
                    ST_DWithin(
                        Profile.location,
                        my_profile.location,
                        max_distance_km * 1000,  # 轉換為公尺
                        True,  # use_spheroid=True，使用球面計算
                    ),
                )
            )
        )

        # 性別篩選
        gender_preference = my_profile.gender_preference
        if gender_preference and gender_preference != "all":
            if gender_preference == "both":
                query = query.where(Profile.gender.in_(["male", "female"]))
            else:
                query = query.where(Profile.gender == gender_preference)

        # 排除用戶：已喜歡、已配對、已封鎖（雙向）、24h 內跳過
        # 合併成一個 UNION 子查詢，只做一次 anti-join
        pass_cutoff = datetime.now(UTC) - timedelta(hours=24)
        excluded_users = union_all(
            # 已喜歡的用戶
            select(Like.to_user_id.label("user_id")).where(Like.from_user_id == viewer_id),
            # 已配對的用戶
            select(
                case((Match.user1_id == viewer_id, Match.user2_id), else_=Match.user1_id).label(
                    "user_id"
                )
            ).where(
                or_(Match.user1_id == viewer_id, Match.user2_id == viewer_id),
                Match.status == "ACTIVE",
            ),
            # 我封鎖的用戶
            select(BlockedUser.blocked_id.label("user_id")).where(
                BlockedUser.blocker_id == viewer_id
            ),
            # 封鎖我的用戶
            select(BlockedUser.blocker_id.label("user_id")).where(
                BlockedUser.blocked_id == viewer_id
            ),
            # 24h 內跳過的用戶
            select(Pass.to_user_id.label("user_id")).where(
                Pass.from_user_id == viewer_id,
                Pass.passed_at > pass_cutoff,
            ),
        ).subquery("excluded")
        return query.where(Profile.user_id.notin_(select(excluded_users.c.user_id)))

    async def browse_candidates(
        self,
        db: AsyncSession,
        viewer_id: uuid.UUID,
        my_profile: Profile,
        limit: int,
    ) -> list[ProfileCard]:
        """瀏覽可配對候選人

        依偏好設定（年齡、距離、性別）過濾，排除已喜歡、已配對、已封鎖（雙向）、
        24h 內跳過的用戶，計算配對分數後過濾低分者並依分數排序。

        「已喜歡我」的候選人優先曝光：DB 掃描順序排前（確保會被撈到）、
        豁免 MIN_MATCH_SCORE 門檻、排序加 LIKED_ME_SORT_BONUS。
        此訊號只用於排序，**不可**透過 ProfileCard 洩漏給前端。

        空池放寬：合格池（>= MIN_MATCH_SCORE）耗盡時，改回傳掃描到的低分候選人，
        避免用戶撞上「沒有更多候選人」死路。門檻是內部實作細節，用戶無感，
        故不回報放寬狀態；距離／年齡等用戶自訂偏好則由 expand_suggestions 另行建議。

        分批撈取：每批 limit*3 筆，過濾低分者後不足 limit 筆就再撈下一批，
        直到湊滿、掃完候選池或達 MAX_BROWSE_BATCHES 上限。

        Args:
            db: 資料庫 session
            viewer_id: 瀏覽者的 user_id
            my_profile: 瀏覽者的 Profile（需預先加載 interests）
            limit: 返回數量上限

        Returns:
            依配對分數排序（高到低）的 ProfileCard 列表
        """
        min_age = my_profile.min_age_preference or 18
        max_age = my_profile.max_age_preference or 99
        max_distance_km = my_profile.max_distance_km or 50
        today = datetime.today().date()

        # 計算距離作為標籤，避免 N+1 查詢
        distance_label = (
            func.ST_Distance(
                Profile.location,
                my_profile.location,
                True,  # use_spheroid=True
            )
            / 1000  # 轉換為公里
        ).label("distance_km")

        # 已喜歡我的候選人先掃（否則湊滿 limit 就停，排在後面批次的永遠撈不到）
        liked_me = exists(
            select(Like.id).where(
                Like.from_user_id == Profile.user_id, Like.to_user_id == viewer_id
            )
        )
        query = (
            self._candidate_query(
                viewer_id,
                my_profile,
                min_age=min_age,
                max_age=max_age,
                max_distance_km=max_distance_km,
            )
            .add_columns(distance_label)
            .options(
                selectinload(Profile.user),
                selectinload(Profile.photos),
                selectinload(Profile.interests),
            )
            # 固定排序（喜歡我的優先，其餘依 user_id），確保 offset 分頁不重複、不遺漏
            .order_by(case((liked_me, 0), else_=1), Profile.user_id)
        )

        # 瀏覽者偏好資料（每批共用）
        user_data = {
            "interests": [interest.name for interest in my_profile.interests],
            "min_age_preference": min_age,
            "max_age_preference": max_age,
            "max_distance_km": max_distance_km,
            "gender_preference": my_profile.gender_preference,
        }

        liked_me_ids: set[uuid.UUID] = set(
            (
                await db.execute(select(Like.from_user_id).where(Like.to_user_id == viewer_id))
            ).scalars()
        )

        batch_size = limit * 3
        # (排序分數, 卡片)：排序分數含 liked_me 加權，卡片的 match_score 維持真實分數
        scored_cards: list[tuple[float, ProfileCard]] = []
        # 低於門檻者另存，只在合格池為空時作為放寬結果回傳
        below_threshold: list[tuple[float, ProfileCard]] = []

        for batch_index in range(MAX_BROWSE_BATCHES):
            result = await db.execute(query.offset(batch_index * batch_size).limit(batch_size))
            rows = result.all()

            for profile, distance_km in rows:
                # 計算年齡
                age = relativedelta(today, profile.user.date_of_birth).years

                # 取得興趣標籤與照片（僅公開可見照片，排除審核駁回）
                interests = [interest.name for interest in profile.interests]
                photos = [photo.url for photo in profile.public_photos]

                # 計算配對分數
                match_score = self.calculate_match_score(
                    user_data,
                    {
                        "interests": interests,
                        "distance_km": distance_km,
                        "last_active": profile.last_active,
                        "photo_count": len(photos),
                        "bio": profile.bio,
                        "age": age,
                        "trust_score": profile.user.trust_score,
                    },
                )

                is_liked_me = profile.user_id in liked_me_ids
                sort_score = match_score + (LIKED_ME_SORT_BONUS if is_liked_me else 0)
                card = ProfileCard(
                    user_id=profile.user_id,
                    display_name=profile.display_name,
                    age=age,
                    gender=profile.gender,
                    bio=profile.bio,
                    location_name=profile.location_name,
                    distance_km=round(distance_km, 1) if distance_km else None,
                    interests=interests,
                    common_interests=_common_interests(user_data["interests"], interests),
                    photos=photos,
                    match_score=round(match_score, 1),
                )

                # 低於門檻者先擱置（已喜歡我的豁免：配對必成，不該被門檻擋掉）
                if match_score < MIN_MATCH_SCORE and not is_liked_me:
                    below_threshold.append((sort_score, card))
                else:
                    scored_cards.append((sort_score, card))

            # 已湊滿或候選池已掃完
            if len(scored_cards) >= limit or len(rows) < batch_size:
                break

        # 合格池耗盡 → 放寬門檻，回傳低分候選人
        if not scored_cards:
            scored_cards = below_threshold

        # 依排序分數（含 liked_me 加權）高到低排序並限制返回數量
        scored_cards.sort(key=lambda item: item[0], reverse=True)
        return [card for _, card in scored_cards[:limit]]

    async def expand_suggestions(
        self,
        db: AsyncSession,
        viewer_id: uuid.UUID,
        my_profile: Profile,
    ) -> list[ExpandSuggestion]:
        """空池時的偏好放寬建議

        分別試算「距離 ×2（上限 MAX_DISTANCE_KM）」與「年齡 ±AGE_EXPAND_STEP（18–99）」
        能多看到幾位候選人，只回傳有增加的建議。不自動修改偏好——
        放寬是用戶的決定，由前端一鍵套用。

        計數不套用 MIN_MATCH_SCORE（browse 已會在合格池空時放寬門檻）。
        """
        min_age = my_profile.min_age_preference or 18
        max_age = my_profile.max_age_preference or 99
        max_distance_km = my_profile.max_distance_km or 50

        async def _count(**prefs: int) -> int:
            subquery = self._candidate_query(viewer_id, my_profile, **prefs).subquery()
            return (await db.execute(select(func.count()).select_from(subquery))).scalar_one()

        current = await _count(min_age=min_age, max_age=max_age, max_distance_km=max_distance_km)
        suggestions: list[ExpandSuggestion] = []

        suggested_distance = min(max_distance_km * 2, MAX_DISTANCE_KM)
        if suggested_distance > max_distance_km:
            additional = (
                await _count(min_age=min_age, max_age=max_age, max_distance_km=suggested_distance)
                - current
            )
            if additional > 0:
                suggestions.append(
                    ExpandSuggestion(
                        type="distance",
                        current_max_distance_km=max_distance_km,
                        suggested_max_distance_km=suggested_distance,
                        additional_candidates=additional,
                    )
                )

        suggested_min_age = max(min_age - AGE_EXPAND_STEP, MIN_AGE)
        suggested_max_age = min(max_age + AGE_EXPAND_STEP, MAX_AGE)
        if (suggested_min_age, suggested_max_age) != (min_age, max_age):
            additional = (
                await _count(
                    min_age=suggested_min_age,
                    max_age=suggested_max_age,
                    max_distance_km=max_distance_km,
                )
                - current
            )
            if additional > 0:
                suggestions.append(
                    ExpandSuggestion(
                        type="age",
                        current_min_age=min_age,
                        current_max_age=max_age,
                        suggested_min_age=suggested_min_age,
                        suggested_max_age=suggested_max_age,
                        additional_candidates=additional,
                    )
                )

        return suggestions


# 單例模式
matching_service = MatchingService()
