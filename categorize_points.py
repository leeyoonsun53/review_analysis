# -*- coding: utf-8 -*-
"""
PAIN_POINTS, POSITIVE_POINTS 카테고리화
- 이미 재분류된 pain_points/positive_points를 그대로 카테고리로 사용
"""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')


def main():
    print("GPT 분석 결과 로드 중...")

    with open('output/gpt_analysis_categorized.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"총 분석 건수: {len(data):,}건\n")

    # ===== PAIN_POINTS 카테고리화 =====
    print("=" * 70)
    print("PAIN_POINTS 카테고리 분포")
    print("=" * 70)

    pain_counts = Counter()
    for item in data:
        for pain in item.get('pain_points', []):
            pain_counts[pain] += 1

    print("\n[카테고리별 분포]")
    total_pain = sum(pain_counts.values())
    for cat, cnt in pain_counts.most_common(15):
        pct = cnt / total_pain * 100 if total_pain > 0 else 0
        print(f"  {cat:20s}: {cnt:>5}건 ({pct:>5.1f}%)")

    # ===== POSITIVE_POINTS 카테고리화 =====
    print("\n" + "=" * 70)
    print("POSITIVE_POINTS 카테고리 분포")
    print("=" * 70)

    pos_counts = Counter()
    for item in data:
        for pos in item.get('positive_points', []):
            pos_counts[pos] += 1

    print("\n[카테고리별 분포]")
    total_pos = sum(pos_counts.values())
    for cat, cnt in pos_counts.most_common(15):
        pct = cnt / total_pos * 100 if total_pos > 0 else 0
        print(f"  {cat:20s}: {cnt:>5}건 ({pct:>5.1f}%)")

    # ===== 리뷰 데이터에 카테고리 추가 =====
    print("\n리뷰 데이터에 카테고리 동기화 중...")

    # 주요 카테고리 정의 (TOP 카테고리만 유지, 나머지는 기타)
    main_pain_categories = [cat for cat, _ in pain_counts.most_common(14)]
    main_pos_categories = [cat for cat, _ in pos_counts.most_common(18)]

    for item in data:
        # Pain categories - pain_points를 그대로 사용 (주요 카테고리만)
        pain_cats = []
        for pain in item.get('pain_points', []):
            if pain in main_pain_categories:
                pain_cats.append(pain)
            elif pain:  # 기타로 분류하지 않고 그대로 유지
                pain_cats.append(pain)
        item['pain_categories'] = list(set(pain_cats))  # 중복 제거

        # Positive categories - positive_points를 그대로 사용
        pos_cats = []
        for pos in item.get('positive_points', []):
            if pos in main_pos_categories:
                pos_cats.append(pos)
            elif pos:
                pos_cats.append(pos)
        item['positive_categories'] = list(set(pos_cats))  # 중복 제거

    # 저장
    with open('output/gpt_analysis_categorized.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"카테고리 동기화 완료: output/gpt_analysis_categorized.json")

    # 결과 확인
    print("\n" + "=" * 70)
    print("카테고리 동기화 결과 확인")
    print("=" * 70)

    # pain_categories 집계
    pain_cat_counts = Counter()
    for item in data:
        for cat in item.get('pain_categories', []):
            pain_cat_counts[cat] += 1

    print("\n[Pain Categories TOP 10]")
    for cat, cnt in pain_cat_counts.most_common(10):
        print(f"  {cat}: {cnt}건")

    # positive_categories 집계
    pos_cat_counts = Counter()
    for item in data:
        for cat in item.get('positive_categories', []):
            pos_cat_counts[cat] += 1

    print("\n[Positive Categories TOP 10]")
    for cat, cnt in pos_cat_counts.most_common(10):
        print(f"  {cat}: {cnt}건")


if __name__ == "__main__":
    main()
