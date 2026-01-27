# -*- coding: utf-8 -*-
"""
v2.0 로직 테스트 스크립트
문제 케이스들이 올바르게 처리되는지 확인
"""
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from src.sentiment_analyzer import (
    analyze_sentiment, analyze_sentiment_detail, analyze_strength,
    check_skin_disease, check_discontinue, split_by_adversative
)
from src.tag_extractor import (
    extract_usage_tags, extract_value_tags,
    is_negative_context, has_adversative_negative, is_past_negative_usage
)

print("=" * 80)
print("v2.0 로직 테스트")
print("=" * 80)

# 테스트 케이스들
test_cases = [
    {
        "name": "원본 문제 케이스",
        "text": "예전에 닦토로 잘써서 재구매했었으나 모낭염이 올라와서 중단했네여요",
        "rating": 5,
        "expected_sentiment": "NEG",
        "expected_usage": [],
        "expected_value": []
    },
    {
        "name": "역접 + 부정",
        "text": "처음에는 좋았는데 쓰다보니 트러블이 올라왔어요",
        "rating": 4,
        "expected_sentiment": "NEG",
        "expected_usage": [],
        "expected_value": []
    },
    {
        "name": "피부질병 언급",
        "text": "알러지 반응이 생겨서 사용 중단했습니다",
        "rating": 3,
        "expected_sentiment": "NEG",
        "expected_usage": [],
        "expected_value": []
    },
    {
        "name": "과거 좋았지만 현재 부정",
        "text": "예전에 인생템이라고 생각했는데 피부에 안맞아서 버렸어요",
        "rating": 5,
        "expected_sentiment": "NEG",
        "expected_usage": [],
        "expected_value": []  # 인생템 제외되어야 함
    },
    {
        "name": "순수 긍정 케이스",
        "text": "정말 촉촉하고 좋아요! 닦토로 쓰니까 각질도 잘 정리되네요",
        "rating": 5,
        "expected_sentiment": "POS",
        "expected_usage": ["닦토"],
        "expected_value": []
    },
    {
        "name": "재구매 의사 있는 긍정",
        "text": "인생템이에요! 계속 재구매하고 있어요 촉촉하고 순해서 좋아요",
        "rating": 5,
        "expected_sentiment": "POS",
        "expected_usage": [],
        "expected_value": ["인생템"]
    },
    {
        "name": "중단 키워드",
        "text": "피부가 너무 따가워서 중단했어요",
        "rating": 4,
        "expected_sentiment": "NEG",
        "expected_usage": [],
        "expected_value": []
    },
    {
        "name": "두드러기",
        "text": "사용 후 두드러기가 올라왔어요",
        "rating": 2,
        "expected_sentiment": "NEG",
        "expected_usage": [],
        "expected_value": []
    }
]

print("\n[테스트 결과]")
print("-" * 80)

passed = 0
failed = 0

for i, case in enumerate(test_cases, 1):
    text = case["text"]
    rating = case["rating"]

    # 분석 실행
    sentiment = analyze_sentiment(text, rating)
    detail = analyze_sentiment_detail(text, rating)
    usage_tags = extract_usage_tags(text)
    value_tags = extract_value_tags(text)

    # 결과 확인
    sentiment_ok = sentiment == case["expected_sentiment"]
    usage_ok = usage_tags == case["expected_usage"]
    value_ok = value_tags == case["expected_value"]

    all_ok = sentiment_ok and usage_ok and value_ok

    if all_ok:
        status = "✓ PASS"
        passed += 1
    else:
        status = "✗ FAIL"
        failed += 1

    print(f"\n[{i}] {case['name']} - {status}")
    print(f"    텍스트: \"{text[:50]}...\"" if len(text) > 50 else f"    텍스트: \"{text}\"")
    print(f"    별점: {rating}")

    if not sentiment_ok:
        print(f"    감성: {sentiment} (기대: {case['expected_sentiment']}) ← 불일치!")
    else:
        print(f"    감성: {sentiment} ✓")

    if not usage_ok:
        print(f"    사용법: {usage_tags} (기대: {case['expected_usage']}) ← 불일치!")
    else:
        print(f"    사용법: {usage_tags} ✓")

    if not value_ok:
        print(f"    가치: {value_tags} (기대: {case['expected_value']}) ← 불일치!")
    else:
        print(f"    가치: {value_tags} ✓")

    # 상세 분석 정보
    print(f"    [상세] 피부질병: {detail['skin_issues']}, 중단: {detail['is_discontinue']}, 역접: {detail['has_adversative']}")

print("\n" + "=" * 80)
print(f"테스트 결과: {passed}/{passed + failed} 통과")
print("=" * 80)

# 원본 문제 케이스 상세 분석
print("\n\n[원본 문제 케이스 상세 분석]")
print("-" * 80)
problem_text = "예전에 닦토로 잘써서 재구매했었으나 모낭염이 올라와서 중단했네여요"
print(f"텍스트: {problem_text}")
print(f"별점: 5")

print(f"\n1. 역접 패턴 분리:")
before, after, has_adv = split_by_adversative(problem_text)
print(f"   역접 발견: {has_adv}")
print(f"   앞부분: \"{before}\"")
print(f"   뒷부분: \"{after}\"")

print(f"\n2. 피부질병 탐지:")
diseases = check_skin_disease(problem_text)
print(f"   발견된 질병: {diseases}")

print(f"\n3. 중단 키워드 탐지:")
is_disc = check_discontinue(problem_text)
print(f"   중단 여부: {is_disc}")

print(f"\n4. 부정 문맥 판단:")
print(f"   is_negative_context: {is_negative_context(problem_text)}")
print(f"   has_adversative_negative: {has_adversative_negative(problem_text)}")
print(f"   is_past_negative_usage: {is_past_negative_usage(problem_text)}")

print(f"\n5. 최종 분석 결과:")
final_sentiment = analyze_sentiment(problem_text, 5)
final_usage = extract_usage_tags(problem_text)
final_value = extract_value_tags(problem_text)
print(f"   감성: {final_sentiment} (이전: POS)")
print(f"   사용법: {final_usage} (이전: ['닦토'])")
print(f"   가치: {final_value} (이전: ['인생템'])")

print("\n개선 완료!")
