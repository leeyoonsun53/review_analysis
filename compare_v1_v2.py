# -*- coding: utf-8 -*-
"""
v1 vs v2 로직 비교 스크립트
실제 데이터에서 개선 효과 확인
"""
import json
import pandas as pd
import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from src.sentiment_analyzer import (
    analyze_sentiment, check_skin_disease, check_discontinue,
    split_by_adversative
)
from src.tag_extractor import (
    extract_usage_tags, extract_value_tags,
    is_negative_context, has_adversative_negative
)
from config.keywords import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS

print("=" * 90)
print("v1 vs v2 로직 비교 분석")
print("=" * 90)

# 데이터 로드
with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

first_key = list(data.keys())[0]
df = pd.DataFrame(data[first_key])

print(f"\n총 리뷰 수: {len(df):,}건")

# v1 로직 (이전 방식)
def analyze_sentiment_v1(text, rating):
    """이전 감성 분석 로직"""
    text = str(text).lower()

    if rating >= 4:
        base_sentiment = "POS"
    elif rating <= 2:
        base_sentiment = "NEG"
    else:
        base_sentiment = "NEU"

    pos_count = sum(1 for w in POSITIVE_KEYWORDS if w in text)
    neg_count = sum(1 for w in NEGATIVE_KEYWORDS[:15] if w in text)  # 이전 키워드만

    if neg_count >= 2 and base_sentiment == "POS":
        return "NEU"
    if pos_count >= 2 and base_sentiment == "NEU":
        return "POS"

    return base_sentiment

def extract_usage_tags_v1(text):
    """이전 사용법 태그 추출 (문맥 무시)"""
    from config.keywords import USAGE_KEYWORDS
    text = str(text)
    found_tags = []
    for tag, keywords in USAGE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                found_tags.append(tag)
                break
    return found_tags

def extract_value_tags_v1(text):
    """이전 가치 태그 추출 (문맥 무시)"""
    from config.keywords import VALUE_KEYWORDS
    text = str(text)
    found_tags = []
    for tag, keywords in VALUE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                found_tags.append(tag)
                break
    return found_tags

# 분석 실행
print("\n[분석 실행 중...]")

# v1, v2 결과 계산
df['sentiment_v1'] = df.apply(lambda r: analyze_sentiment_v1(r['REVIEW_CONTENT'], r['REVIEW_RATING']), axis=1)
df['sentiment_v2'] = df.apply(lambda r: analyze_sentiment(r['REVIEW_CONTENT'], r['REVIEW_RATING']), axis=1)

df['usage_v1'] = df['REVIEW_CONTENT'].apply(extract_usage_tags_v1)
df['usage_v2'] = df['REVIEW_CONTENT'].apply(extract_usage_tags)

df['value_v1'] = df['REVIEW_CONTENT'].apply(extract_value_tags_v1)
df['value_v2'] = df['REVIEW_CONTENT'].apply(extract_value_tags)

# 피부질병, 중단 플래그
df['has_skin_disease'] = df['REVIEW_CONTENT'].apply(lambda x: len(check_skin_disease(str(x))) > 0)
df['has_discontinue'] = df['REVIEW_CONTENT'].apply(lambda x: check_discontinue(str(x)))
df['has_adversative'] = df['REVIEW_CONTENT'].apply(lambda x: split_by_adversative(str(x))[2])

# ====== 결과 비교 ======
print("\n" + "=" * 90)
print("[1] 감성 분석 변화")
print("=" * 90)

# 감성 분포 비교
v1_dist = df['sentiment_v1'].value_counts()
v2_dist = df['sentiment_v2'].value_counts()

print(f"\n{'감성':<8} {'v1':>10} {'v2':>10} {'변화':>10}")
print("-" * 40)
for s in ['POS', 'NEU', 'NEG']:
    v1_cnt = v1_dist.get(s, 0)
    v2_cnt = v2_dist.get(s, 0)
    diff = v2_cnt - v1_cnt
    print(f"{s:<8} {v1_cnt:>10,} {v2_cnt:>10,} {diff:>+10,}")

# 감성이 바뀐 케이스
changed = df[df['sentiment_v1'] != df['sentiment_v2']]
print(f"\n감성 변경된 리뷰: {len(changed):,}건 ({len(changed)/len(df)*100:.1f}%)")

# POS -> NEG로 바뀐 케이스 (핵심 개선)
pos_to_neg = changed[(changed['sentiment_v1'] == 'POS') & (changed['sentiment_v2'] == 'NEG')]
print(f"  - POS → NEG: {len(pos_to_neg):,}건 (별점 높지만 실제 부정)")

# POS -> NEU로 바뀐 케이스
pos_to_neu = changed[(changed['sentiment_v1'] == 'POS') & (changed['sentiment_v2'] == 'NEU')]
print(f"  - POS → NEU: {len(pos_to_neu):,}건")

print("\n" + "=" * 90)
print("[2] 별점 5점 + NEG 판정 케이스 (핵심 개선)")
print("=" * 90)

# 별점 5점인데 v2에서 NEG로 판정된 케이스
rating_5_neg = df[(df['REVIEW_RATING'] == 5) & (df['sentiment_v2'] == 'NEG')]
print(f"\n별점 5점이지만 NEG로 판정: {len(rating_5_neg):,}건")

# 이유별 분류
with_skin = rating_5_neg[rating_5_neg['has_skin_disease']]
with_disc = rating_5_neg[rating_5_neg['has_discontinue']]
with_adv = rating_5_neg[rating_5_neg['has_adversative']]

print(f"  - 피부질병 언급: {len(with_skin):,}건")
print(f"  - 중단 키워드: {len(with_disc):,}건")
print(f"  - 역접 패턴: {len(with_adv):,}건")

# 샘플 출력
print("\n[별점5 → NEG 샘플 (상위 5건)]")
for i, row in rating_5_neg.head(5).iterrows():
    content = str(row['REVIEW_CONTENT'])[:70] + "..." if len(str(row['REVIEW_CONTENT'])) > 70 else row['REVIEW_CONTENT']
    skin = check_skin_disease(str(row['REVIEW_CONTENT']))
    print(f"  [{row['BRAND_NAME']}] \"{content}\"")
    if skin:
        print(f"       → 피부질병: {skin}")

print("\n" + "=" * 90)
print("[3] 태그 추출 변화")
print("=" * 90)

# 사용법 태그가 제거된 케이스
usage_changed = df[df['usage_v1'].apply(str) != df['usage_v2'].apply(str)]
usage_removed = df[(df['usage_v1'].apply(len) > 0) & (df['usage_v2'].apply(len) == 0)]
print(f"\n사용법 태그 변경: {len(usage_changed):,}건")
print(f"  - 태그 제거됨 (부정 문맥): {len(usage_removed):,}건")

# 가치 태그가 제거된 케이스
value_changed = df[df['value_v1'].apply(str) != df['value_v2'].apply(str)]
value_removed = df[(df['value_v1'].apply(lambda x: '인생템' in x)) & (df['value_v2'].apply(lambda x: '인생템' not in x))]
print(f"\n가치 태그 변경: {len(value_changed):,}건")
print(f"  - 인생템 태그 제거됨 (오탐 방지): {len(value_removed):,}건")

# 인생템 오탐이 수정된 샘플
print("\n[인생템 태그 제거 샘플 (상위 5건)]")
for i, row in value_removed.head(5).iterrows():
    content = str(row['REVIEW_CONTENT'])[:70] + "..." if len(str(row['REVIEW_CONTENT'])) > 70 else row['REVIEW_CONTENT']
    print(f"  [{row['BRAND_NAME']}] \"{content}\"")
    print(f"       v1 가치: {row['value_v1']} → v2 가치: {row['value_v2']}")

print("\n" + "=" * 90)
print("[4] 피부질병 탐지 통계")
print("=" * 90)

skin_reviews = df[df['has_skin_disease']]
print(f"\n피부질병 언급 리뷰: {len(skin_reviews):,}건 ({len(skin_reviews)/len(df)*100:.1f}%)")

# 브랜드별 피부질병 비율
print("\n[브랜드별 피부질병 언급률]")
for brand in df['BRAND_NAME'].unique():
    brand_df = df[df['BRAND_NAME'] == brand]
    brand_skin = brand_df[brand_df['has_skin_disease']]
    rate = len(brand_skin) / len(brand_df) * 100
    print(f"  {brand}: {len(brand_skin):,}건 ({rate:.1f}%)")

print("\n" + "=" * 90)
print("[5] 역접 패턴 탐지 통계")
print("=" * 90)

adv_reviews = df[df['has_adversative']]
print(f"\n역접 패턴 리뷰: {len(adv_reviews):,}건 ({len(adv_reviews)/len(df)*100:.1f}%)")

# 역접 + 부정 결말
adv_neg = df[df['REVIEW_CONTENT'].apply(has_adversative_negative)]
print(f"역접 + 부정 결말: {len(adv_neg):,}건 ({len(adv_neg)/len(df)*100:.1f}%)")

print("\n" + "=" * 90)
print("[6] 원본 문제 케이스 검증")
print("=" * 90)

# 원본 문제 케이스 찾기
problem_case = df[df['REVIEW_CONTENT'].str.contains('모낭염', na=False)].iloc[0] if len(df[df['REVIEW_CONTENT'].str.contains('모낭염', na=False)]) > 0 else None

if problem_case is not None:
    print(f"\n리뷰: \"{problem_case['REVIEW_CONTENT']}\"")
    print(f"브랜드: {problem_case['BRAND_NAME']}")
    print(f"별점: {problem_case['REVIEW_RATING']}")
    print(f"\n[v1] 감성: {problem_case['sentiment_v1']}, 사용법: {problem_case['usage_v1']}, 가치: {problem_case['value_v1']}")
    print(f"[v2] 감성: {problem_case['sentiment_v2']}, 사용법: {problem_case['usage_v2']}, 가치: {problem_case['value_v2']}")
else:
    print("\n원본 문제 케이스를 찾을 수 없습니다.")

print("\n" + "=" * 90)
print("비교 분석 완료!")
print("=" * 90)
