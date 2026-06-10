# backend/micro_assessment/test_engine.py
from .engine import calculate_assessment

def test_normal_case():
    answers = [
        {"dimension": "pressure", "score": 2},
        {"dimension": "avoidance", "score": 2},
        {"dimension": "self_efficacy", "score": 4},
        {"dimension": "coping", "score": 4}
    ]
    result = calculate_assessment(answers)
    assert result.comprehensive_risk["index"] < 40
    assert result.comprehensive_risk["level"] == "low"
    print("test_normal_case passed")

def test_high_risk():
    answers = [
        {"dimension": "pressure", "score": 5},
        {"dimension": "avoidance", "score": 5},
        {"dimension": "self_efficacy", "score": 1},
        {"dimension": "coping", "score": 1}
    ]
    result = calculate_assessment(answers)
    assert result.comprehensive_risk["index"] >= 70
    assert result.comprehensive_risk["level"] == "high"
    print("test_high_risk passed")

def test_missing_dimension():
    answers = [
        {"dimension": "pressure", "score": 2},
        {"dimension": "avoidance", "score": 2},
        {"dimension": "self_efficacy", "score": 4}
    ]
    try:
        calculate_assessment(answers)
        assert False, "应该抛出异常"
    except ValueError:
        print("test_missing_dimension passed")

if __name__ == "__main__":
    test_normal_case()
    test_high_risk()
    test_missing_dimension()
    print("所有测试通过！")