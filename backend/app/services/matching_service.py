"""配對推薦服務"""
from typing import Dict, List
from datetime import datetime, timezone


class MatchingService:
    """配對推薦服務"""

    def calculate_match_score(
        self,
        user_profile: Dict,
        candidate: Dict
    ) -> float:
        """
        計算配對分數

        評分因素:
        - 興趣匹配: 50 分 (每個共同興趣 10 分)
        - 距離: 20 分
        - 活躍度: 20 分
        - 檔案完整度: 10 分

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

        # 每個共同興趣 10 分，最多 5 個共同興趣
        score += min(len(common_interests) * 10, 50)

        # 2. 距離因素（最高 20 分）
        distance_km = candidate.get("distance_km", 999)

        if distance_km < 5:
            score += 20
        elif distance_km < 10:
            score += 15
        elif distance_km < 25:
            score += 10
        elif distance_km < 50:
            score += 5

        # 3. 活躍度（最高 20 分）
        last_active = candidate.get("last_active")
        if last_active:
            if isinstance(last_active, str):
                last_active = datetime.fromisoformat(last_active.replace('Z', '+00:00'))

            # 統一使用 UTC 時區進行比較
            hours_ago = (datetime.now(timezone.utc) - last_active).total_seconds() / 3600

            if hours_ago < 1:
                score += 20
            elif hours_ago < 24:
                score += 15
            elif hours_ago < 72:
                score += 10
            elif hours_ago < 168:  # 7天
                score += 5

        # 4. 檔案完整度（最高 10 分）
        photo_count = candidate.get("photo_count", 0)
        has_bio = bool(candidate.get("bio"))

        # 照片：每張 1 分，最多 6 分
        score += min(photo_count, 6)

        # 自我介紹：4 分
        score += 4 if has_bio else 0

        return min(score, 100)

    def rank_candidates(
        self,
        user_profile: Dict,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        對候選人進行排序

        Args:
            user_profile: 當前用戶的檔案資料
            candidates: 候選人列表

        Returns:
            排序後的候選人列表（包含分數）
        """
        # 計算每個候選人的分數
        scored_candidates = []
        for candidate in candidates:
            score = self.calculate_match_score(user_profile, candidate)
            candidate_with_score = {
                **candidate,
                "match_score": score
            }
            scored_candidates.append(candidate_with_score)

        # 依分數排序（高到低）
        scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)

        return scored_candidates

    def filter_by_preferences(
        self,
        user_profile: Dict,
        candidate: Dict
    ) -> bool:
        """
        根據用戶偏好篩選候選人

        Args:
            user_profile: 當前用戶的檔案資料
            candidate: 候選人資料

        Returns:
            是否符合偏好
        """
        # 檢查年齡偏好
        min_age = user_profile.get("min_age_preference", 18)
        max_age = user_profile.get("max_age_preference", 99)
        candidate_age = candidate.get("age", 0)

        if not (min_age <= candidate_age <= max_age):
            return False

        # 檢查距離偏好
        max_distance_km = user_profile.get("max_distance_km", 50)
        distance_km = candidate.get("distance_km", 999)

        if distance_km > max_distance_km:
            return False

        # 檢查性別偏好
        gender_preference = user_profile.get("gender_preference")
        if gender_preference and gender_preference != "all":
            candidate_gender = candidate.get("gender")
            if gender_preference == "both":
                # "both" 表示 male 或 female，不包含 non_binary
                if candidate_gender not in ["male", "female"]:
                    return False
            elif gender_preference != candidate_gender:
                return False

        return True


# 單例模式
matching_service = MatchingService()
