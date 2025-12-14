"""配對推薦服務"""
from typing import Dict, List
from datetime import datetime, timezone


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
        last_active = datetime.fromisoformat(last_active.replace('Z', '+00:00'))

    hours_ago = (datetime.now(timezone.utc) - last_active).total_seconds() / 3600

    if hours_ago < 1:
        return 20
    if hours_ago < 24:
        return 15
    if hours_ago < 72:
        return 10
    if hours_ago < 168:  # 7天
        return 5
    return 0


def _calculate_completeness_score(candidate: Dict) -> float:
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

    def calculate_match_score(
        self,
        user_profile: Dict,
        candidate: Dict
    ) -> float:
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
