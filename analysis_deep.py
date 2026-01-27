# -*- coding: utf-8 -*-
"""
심층 분석: 1) Pain Point, 2) 재구매/이탈, 3) 월별 키워드 트렌드
"""
import json
import pandas as pd
import re
from collections import Counter
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 데이터 로드
with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

first_key = list(data.keys())[0]
df = pd.DataFrame(data[first_key])

# 날짜 파싱
df['review_date'] = pd.to_datetime(df['REVIEW_DATE'])
df['year_month'] = df['review_date'].dt.to_period('M')

print('=' * 90)
print('1. 저평점 리뷰 Pain Point 분석 (1-2점)')
print('=' * 90)

# Pain Point 키워드
PAIN_KEYWORDS = {
    '자극/트러블': ['자극', '따가', '따끔', '트러블', '뾰루지', '올라', '붉', '화끈', '쓰라', '알러지', '예민'],
    '보습부족': ['건조', '당김', '속건조', '갈라', '각질', '푸석'],
    '끈적/무거움': ['끈적', '답답', '무거', '기름', '번들', '텁텁'],
    '효과없음': ['효과없', '모르겠', '별로', '그냥', '평범', '밍밍', '애매'],
    '향/냄새': ['향', '냄새', '냄시', '알코올'],
    '가격': ['비싸', '가격', '비쌈'],
    '용기/패키지': ['펌프', '뚜껑', '용기', '흘러', '새', '불편'],
    '흡수불량': ['흡수', '겉돌', '안스며', '뜨']
}

def extract_pain_points(text):
    if pd.isna(text):
        return []
    text = str(text).lower()
    found = []
    for category, keywords in PAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                found.append(category)
                break
    return found

# 저평점 리뷰 필터
low_rating_df = df[df['REVIEW_RATING'] <= 2].copy()
print(f"\n전체 저평점 리뷰: {len(low_rating_df)}건 (전체의 {len(low_rating_df)/len(df)*100:.2f}%)")

low_rating_df['pain_points'] = low_rating_df['REVIEW_CONTENT'].apply(extract_pain_points)

# 브랜드별 Pain Point 분석
print("\n[브랜드별 저평점 리뷰 Pain Point 분포]")
print("-" * 90)

brands = df['BRAND_NAME'].unique()
brand_pains = {}

for brand in sorted(brands, key=lambda x: len(df[df['BRAND_NAME']==x]), reverse=True):
    brand_low = low_rating_df[low_rating_df['BRAND_NAME'] == brand]
    total_low = len(brand_low)
    total_all = len(df[df['BRAND_NAME'] == brand])

    if total_low == 0:
        continue

    # Pain point 집계
    all_pains = []
    for pains in brand_low['pain_points']:
        all_pains.extend(pains)

    pain_counts = Counter(all_pains)
    brand_pains[brand] = pain_counts

    print(f"\n[{brand}] 저평점 {total_low}건 (전체 {total_all}건 중 {total_low/total_all*100:.1f}%)")

    if pain_counts:
        for pain, cnt in pain_counts.most_common(5):
            print(f"  - {pain}: {cnt}건 ({cnt/total_low*100:.1f}%)")
    else:
        print("  - Pain point 키워드 없음")

    # 대표 불만 리뷰 출력
    if total_low > 0:
        sample = brand_low.iloc[0]['REVIEW_CONTENT']
        if len(str(sample)) > 80:
            sample = str(sample)[:80] + "..."
        print(f"  예시: \"{sample}\"")

# Pain Point 비교 테이블
print("\n" + "=" * 90)
print("[브랜드별 Pain Point 비교 (저평점 리뷰 중 비율)]")
print("=" * 90)

pain_categories = list(PAIN_KEYWORDS.keys())
print(f"\n{'브랜드':<12}", end="")
for cat in pain_categories:
    print(f"{cat[:6]:>8}", end="")
print()
print("-" * 80)

for brand in sorted(brands, key=lambda x: len(df[df['BRAND_NAME']==x]), reverse=True):
    brand_low = low_rating_df[low_rating_df['BRAND_NAME'] == brand]
    total_low = len(brand_low)
    if total_low == 0:
        continue

    print(f"{brand:<12}", end="")
    for cat in pain_categories:
        cnt = brand_pains.get(brand, {}).get(cat, 0)
        pct = cnt / total_low * 100 if total_low > 0 else 0
        print(f"{pct:>7.1f}%", end="")
    print()


# ============================================================
# 2. 재구매 vs 이탈 분석
# ============================================================
print("\n\n" + "=" * 90)
print("2. 재구매 vs 이탈 요인 분석")
print("=" * 90)

# 재구매 관련 키워드
REBUY_KEYWORDS = ['재구매', '재구', '또 사', '또사', '계속 사', '계속사', '꾸준히', 'n번째', '번째 구매', '몇통째']
LOYAL_KEYWORDS = ['인생템', '최애', '없으면 안', '필수템', '애정템', '평생', '계속 쓸']

# 이탈 관련 키워드
CHURN_KEYWORDS = ['다른 거', '다른거', '바꿀', '갈아타', '안 살', '안살', '다시 안', '다시안', '바꿔야', '다른 제품']

def check_rebuy_signal(text):
    if pd.isna(text):
        return 'unknown'
    text = str(text).lower()

    # 강한 충성
    for kw in LOYAL_KEYWORDS:
        if kw in text:
            return 'loyal'

    # 재구매 언급
    for kw in REBUY_KEYWORDS:
        if kw in text:
            return 'rebuy'

    # 이탈 신호
    for kw in CHURN_KEYWORDS:
        if kw in text:
            return 'churn'

    return 'neutral'

df['rebuy_signal'] = df['REVIEW_CONTENT'].apply(check_rebuy_signal)

# PURCHASE_TAG 분석 (재구매 태그)
def check_purchase_tag(tag):
    if pd.isna(tag):
        return False
    return '재구매' in str(tag)

df['is_repurchase'] = df['PURCHASE_TAG'].apply(check_purchase_tag)

print("\n[전체 재구매 신호 분포]")
signal_dist = df['rebuy_signal'].value_counts()
for signal, cnt in signal_dist.items():
    print(f"  {signal}: {cnt:,}건 ({cnt/len(df)*100:.1f}%)")

print(f"\n[PURCHASE_TAG 기준 재구매]")
repurchase_cnt = df['is_repurchase'].sum()
print(f"  재구매 태그 있음: {repurchase_cnt:,}건 ({repurchase_cnt/len(df)*100:.1f}%)")

# 브랜드별 재구매/이탈 분석
print("\n" + "-" * 90)
print("[브랜드별 재구매/충성/이탈 비율]")
print("-" * 90)

print(f"\n{'브랜드':<12} {'리뷰수':>7} {'재구매태그':>10} {'충성(loyal)':>12} {'재구매언급':>12} {'이탈신호':>10}")
print("-" * 75)

brand_loyalty = {}
for brand in sorted(brands, key=lambda x: len(df[df['BRAND_NAME']==x]), reverse=True):
    brand_df = df[df['BRAND_NAME'] == brand]
    total = len(brand_df)

    repurchase_tag = brand_df['is_repurchase'].sum()
    loyal = (brand_df['rebuy_signal'] == 'loyal').sum()
    rebuy = (brand_df['rebuy_signal'] == 'rebuy').sum()
    churn = (brand_df['rebuy_signal'] == 'churn').sum()

    brand_loyalty[brand] = {
        'total': total,
        'repurchase_tag': repurchase_tag,
        'loyal': loyal,
        'rebuy': rebuy,
        'churn': churn
    }

    print(f"{brand:<12} {total:>6,} {repurchase_tag/total*100:>9.1f}% {loyal/total*100:>11.1f}% {rebuy/total*100:>11.1f}% {churn/total*100:>9.1f}%")

# 충성 고객 vs 이탈 고객 특성 비교
print("\n" + "-" * 90)
print("[충성 고객 vs 이탈 신호 고객 특성 비교]")
print("-" * 90)

loyal_df = df[df['rebuy_signal'] == 'loyal']
churn_df = df[df['rebuy_signal'] == 'churn']

print(f"\n충성 고객 (loyal) 리뷰 수: {len(loyal_df):,}건")
print(f"이탈 신호 (churn) 리뷰 수: {len(churn_df):,}건")

# 평점 비교
print(f"\n[평균 평점]")
print(f"  충성 고객: {loyal_df['REVIEW_RATING'].mean():.2f}점")
print(f"  이탈 신호: {churn_df['REVIEW_RATING'].mean():.2f}점")

# 브랜드 분포
print(f"\n[충성 고객 브랜드 분포 TOP 5]")
loyal_brands = loyal_df['BRAND_NAME'].value_counts()
for brand, cnt in loyal_brands.head(5).items():
    brand_total = len(df[df['BRAND_NAME'] == brand])
    print(f"  {brand}: {cnt}건 (해당 브랜드의 {cnt/brand_total*100:.1f}%)")

print(f"\n[이탈 신호 브랜드 분포 TOP 5]")
churn_brands = churn_df['BRAND_NAME'].value_counts()
for brand, cnt in churn_brands.head(5).items():
    brand_total = len(df[df['BRAND_NAME'] == brand])
    print(f"  {brand}: {cnt}건 (해당 브랜드의 {cnt/brand_total*100:.1f}%)")

# 충성 고객 대표 리뷰
print(f"\n[충성 고객 대표 리뷰 예시]")
for i, row in loyal_df.head(3).iterrows():
    content = str(row['REVIEW_CONTENT'])[:100] + "..." if len(str(row['REVIEW_CONTENT'])) > 100 else row['REVIEW_CONTENT']
    print(f"  [{row['BRAND_NAME']}] \"{content}\"")

# 이탈 신호 대표 리뷰
print(f"\n[이탈 신호 대표 리뷰 예시]")
for i, row in churn_df.head(3).iterrows():
    content = str(row['REVIEW_CONTENT'])[:100] + "..." if len(str(row['REVIEW_CONTENT'])) > 100 else row['REVIEW_CONTENT']
    print(f"  [{row['BRAND_NAME']}] \"{content}\"")


# ============================================================
# 3. 월별 키워드 트렌드
# ============================================================
print("\n\n" + "=" * 90)
print("3. 브랜드별 월별 키워드 트렌드")
print("=" * 90)

# 주요 추적 키워드
TREND_KEYWORDS = {
    '진정': ['진정', '어성초', '시카', '트러블', '붉은기'],
    '보습': ['보습', '촉촉', '수분', '건조', '당김'],
    '각질': ['각질', '피부결', '매끈', '결정리'],
    '끈적': ['끈적', '답답', '무거'],
    '산뜻': ['산뜻', '가벼', '물같', '흡수'],
    '가성비': ['가성비', '저렴', '싸', '혜자', '대용량']
}

def count_keyword_category(text, keywords):
    if pd.isna(text):
        return 0
    text = str(text).lower()
    for kw in keywords:
        if kw in text:
            return 1
    return 0

# 월별 집계
months = sorted(df['year_month'].unique())
print(f"\n데이터 기간: {months[0]} ~ {months[-1]} ({len(months)}개월)")

# 브랜드별 월별 키워드 트렌드
print("\n[브랜드별 월별 주요 키워드 언급률 변화]")

for brand in sorted(brands, key=lambda x: len(df[df['BRAND_NAME']==x]), reverse=True)[:4]:  # 상위 4개 브랜드
    brand_df = df[df['BRAND_NAME'] == brand].copy()

    print(f"\n{'=' * 70}")
    print(f"[{brand}] 월별 키워드 트렌드")
    print(f"{'=' * 70}")

    # 헤더
    print(f"\n{'월':>10}", end="")
    for kw_cat in TREND_KEYWORDS.keys():
        print(f"{kw_cat:>8}", end="")
    print(f"{'리뷰수':>8}")
    print("-" * 70)

    # 최근 6개월만
    recent_months = months[-6:] if len(months) >= 6 else months

    for month in recent_months:
        month_df = brand_df[brand_df['year_month'] == month]
        month_cnt = len(month_df)

        if month_cnt == 0:
            continue

        print(f"{str(month):>10}", end="")

        for kw_cat, keywords in TREND_KEYWORDS.items():
            mentions = month_df['REVIEW_CONTENT'].apply(lambda x: count_keyword_category(x, keywords)).sum()
            pct = mentions / month_cnt * 100
            print(f"{pct:>7.1f}%", end="")

        print(f"{month_cnt:>8}")

# 전체 트렌드 요약
print("\n\n" + "=" * 90)
print("[전체 월별 키워드 트렌드 요약]")
print("=" * 90)

print(f"\n{'월':>10}", end="")
for kw_cat in TREND_KEYWORDS.keys():
    print(f"{kw_cat:>8}", end="")
print(f"{'총리뷰':>8}")
print("-" * 70)

recent_months = months[-6:] if len(months) >= 6 else months

for month in recent_months:
    month_df = df[df['year_month'] == month]
    month_cnt = len(month_df)

    if month_cnt == 0:
        continue

    print(f"{str(month):>10}", end="")

    for kw_cat, keywords in TREND_KEYWORDS.items():
        mentions = month_df['REVIEW_CONTENT'].apply(lambda x: count_keyword_category(x, keywords)).sum()
        pct = mentions / month_cnt * 100
        print(f"{pct:>7.1f}%", end="")

    print(f"{month_cnt:>8}")

print("\n분석 완료!")
