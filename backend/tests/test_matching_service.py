"""配對評分演算法單元測試

純函數測試，不依賴 DB / mock。目標：
1. 固定各評分因素的分層邊界（< vs >= 的方向重構時最容易改壞）
2. 驗證各因素上限封頂與權重總和 = 100
3. 把 MIN_MATCH_SCORE 門檻的實際效果寫成可執行規格
4. 固定髒資料 fallback 路徑（None / ISO 字串 / 缺欄位預設值）
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.services.matching_service import (
    MIN_MATCH_SCORE,
    MatchingService,
    _calculate_activity_score,
    _calculate_completeness_score,
    _calculate_distance_score,
    _calculate_trust_score_weight,
)

matching = MatchingService()


# ---------------------------------------------------------------------------
# 距離分數（最高 20 分）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("distance_km", "expected"),
    [
        (0, 20),
        (4.9, 20),
        (5, 15),  # 邊界：剛好 5km 落入下一層
        (9.9, 15),
        (10, 10),  # 邊界
        (24.9, 10),
        (25, 5),  # 邊界
        (49.9, 5),
        (50, 0),  # 邊界
        (999, 0),
    ],
)
def test_distance_score_tiers(distance_km, expected):
    """距離分層邊界：5 / 10 / 25 / 50 km，邊界值落入較低分層"""
    assert _calculate_distance_score(distance_km) == expected


# ---------------------------------------------------------------------------
# 活躍度分數（最高 20 分）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hours_ago", "expected"),
    [
        (0.5, 20),
        (1, 15),  # 邊界：剛好 1 小時落入下一層
        (23, 15),
        (24, 10),  # 邊界
        (71, 10),
        (72, 5),  # 邊界
        (167, 5),
        (168, 0),  # 邊界：剛好 7 天 = 不活躍
        (500, 0),
    ],
)
def test_activity_score_tiers(hours_ago, expected):
    """活躍度分層邊界：1h / 24h / 72h / 168h，邊界值落入較低分層"""
    last_active = datetime.now(UTC) - timedelta(hours=hours_ago)
    assert _calculate_activity_score(last_active) == expected


def test_activity_score_none_returns_zero():
    """從未上線（last_active 為 None）→ 0 分，不應拋錯"""
    assert _calculate_activity_score(None) == 0


def test_activity_score_accepts_iso_string_with_z_suffix():
    """接受帶 Z 後綴的 ISO 字串（Redis / JSON 來源的序列化格式）"""
    last_active = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    last_active = last_active.replace("+00:00", "Z")
    assert _calculate_activity_score(last_active) == 20


# ---------------------------------------------------------------------------
# 檔案完整度分數（最高 5 分）
# ---------------------------------------------------------------------------


def test_completeness_empty_profile_is_zero():
    assert _calculate_completeness_score({}) == 0


def test_completeness_photo_score_caps_at_three():
    """照片每張 0.5 分，超過 6 張仍封頂 3 分"""
    assert _calculate_completeness_score({"photo_count": 10}) == 3


def test_completeness_bio_adds_two():
    assert _calculate_completeness_score({"bio": "哈囉"}) == 2


def test_completeness_empty_bio_does_not_count():
    """空字串 bio 不算有自我介紹"""
    assert _calculate_completeness_score({"bio": ""}) == 0


def test_completeness_max_is_five():
    assert _calculate_completeness_score({"photo_count": 6, "bio": "哈囉"}) == 5


# ---------------------------------------------------------------------------
# 信任分數權重（最高 5 分）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("trust_score", "expected"),
    [
        (100, 5.0),
        (70, 5.0),  # 邊界：>= 70 高度信任
        (69, 4.0),
        (50, 4.0),  # 邊界：>= 50 正常
        (49, 2.5),
        (30, 2.5),  # 邊界：>= 30 需關注
        (29, 1.0),
        (20, 1.0),  # 邊界：>= 20 受限
        (19, 0.0),
        (0, 0.0),
    ],
)
def test_trust_score_weight_tiers(trust_score, expected):
    """信任分數分層邊界：70 / 50 / 30 / 20，邊界值落入較高分層（>=）"""
    assert _calculate_trust_score_weight(trust_score) == expected


# ---------------------------------------------------------------------------
# 總分計算（calculate_match_score）
# ---------------------------------------------------------------------------


def test_perfect_candidate_scores_exactly_100():
    """滿分候選人 = 100 分，驗證權重總和 50+20+20+5+5 = 100

    未來調整任一因素權重而未重新配平時，此測試會失敗。
    """
    user = {"interests": ["旅遊", "美食", "音樂", "電影", "運動"]}
    candidate = {
        "interests": ["旅遊", "美食", "音樂", "電影", "運動"],
        "distance_km": 1,
        "last_active": datetime.now(UTC),
        "photo_count": 6,
        "bio": "自我介紹",
        "trust_score": 70,
    }
    assert matching.calculate_match_score(user, candidate) == 100


def test_common_interests_cap_at_50():
    """超過 5 個共同興趣仍封頂 50 分"""
    interests = ["a", "b", "c", "d", "e", "f", "g"]
    score_7_common = matching.calculate_match_score(
        {"interests": interests}, {"interests": interests}
    )
    score_5_common = matching.calculate_match_score(
        {"interests": interests[:5]}, {"interests": interests[:5]}
    )
    assert score_7_common == score_5_common


def test_duplicate_interests_not_double_counted():
    """重複的興趣標籤只算一次（set 語意）"""
    score = matching.calculate_match_score({"interests": ["旅遊", "旅遊"]}, {"interests": ["旅遊"]})
    score_single = matching.calculate_match_score({"interests": ["旅遊"]}, {"interests": ["旅遊"]})
    assert score == score_single


def test_missing_fields_fall_back_to_defaults():
    """缺欄位時的預設值：距離 999→0 分、無活躍紀錄→0 分、
    無照片無 bio→0 分、信任分數預設 50→4 分。總分 = 4。
    """
    assert matching.calculate_match_score({}, {}) == 4.0


def test_low_affinity_candidate_hidden_by_threshold():
    """可執行規格：零共同興趣 + 20km + 一週未上線 + 空檔案 + 預設信任分
    → 10 + 0 + 0 + 0 + 4 = 14 分，低於門檻，會從探索列表消失。
    """
    user = {"interests": ["旅遊", "美食"]}
    candidate = {
        "interests": ["運動", "遊戲"],
        "distance_km": 20,
        "last_active": datetime.now(UTC) - timedelta(days=8),
        "photo_count": 0,
        "bio": None,
    }
    score = matching.calculate_match_score(user, candidate)
    assert score == 14.0
    assert score < MIN_MATCH_SCORE


def test_one_common_interest_lifts_above_threshold():
    """同上情境加 1 個共同興趣 → 24 分，超過門檻可見"""
    user = {"interests": ["旅遊", "美食"]}
    candidate = {
        "interests": ["旅遊", "遊戲"],
        "distance_km": 20,
        "last_active": datetime.now(UTC) - timedelta(days=8),
        "photo_count": 0,
        "bio": None,
    }
    score = matching.calculate_match_score(user, candidate)
    assert score == 24.0
    assert score >= MIN_MATCH_SCORE
