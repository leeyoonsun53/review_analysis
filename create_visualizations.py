# -*- coding: utf-8 -*-
"""
심층 분석 시각화 생성
1. Pain Point 분석
2. 재구매/이탈 분석
3. 월별 키워드 트렌드
4. 브랜드 포지셔닝 종합
"""
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from collections import Counter
from pathlib import Path
import platform
import numpy as np

# 한글 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

# 출력 디렉토리
OUTPUT_DIR = Path('output/figures')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 데이터 로드
print("데이터 로딩...")
with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

first_key = list(data.keys())[0]
df = pd.DataFrame(data[first_key])

# 날짜 파싱
df['review_date'] = pd.to_datetime(df['REVIEW_DATE'])
df['year_month'] = df['review_date'].dt.to_period('M')

# ============================================================
# 1. Pain Point 분석 시각화
# ============================================================
print("\n1. Pain Point 시각화 생성...")

PAIN_KEYWORDS = {
    '자극/트러블': ['자극', '따가', '따끔', '트러블', '뾰루지', '올라', '붉', '화끈', '쓰라', '알러지', '예민'],
    '보습부족': ['건조', '당김', '속건조', '갈라', '각질', '푸석'],
    '끈적/무거움': ['끈적', '답답', '무거', '기름', '번들', '텁텁'],
    '효과없음': ['효과없', '모르겠', '별로', '그냥', '평범', '밍밍', '애매'],
    '향/냄새': ['향', '냄새', '냄시', '알코올'],
    '용기/패키지': ['펌프', '뚜껑', '용기', '흘러', '새', '불편']
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
low_rating_df['pain_points'] = low_rating_df['REVIEW_CONTENT'].apply(extract_pain_points)

# 브랜드별 Pain Point 집계
# 실제 데이터에서 브랜드 목록 추출 (리뷰 수 기준 정렬)
brands = df['BRAND_NAME'].value_counts().index.tolist()
pain_data = []

for brand in brands:
    brand_low = low_rating_df[low_rating_df['BRAND_NAME'] == brand]
    total_low = len(brand_low)
    if total_low == 0:
        continue

    all_pains = []
    for pains in brand_low['pain_points']:
        all_pains.extend(pains)

    pain_counts = Counter(all_pains)

    for pain_cat in PAIN_KEYWORDS.keys():
        cnt = pain_counts.get(pain_cat, 0)
        pct = cnt / total_low * 100 if total_low > 0 else 0
        pain_data.append({
            'brand': brand,
            'pain': pain_cat,
            'count': cnt,
            'pct': pct
        })

pain_df = pd.DataFrame(pain_data)

# Pain Point 히트맵
fig, ax = plt.subplots(figsize=(12, 7))
pivot_df = pain_df.pivot(index='brand', columns='pain', values='pct').fillna(0)
pivot_df = pivot_df.reindex(brands)

sns.heatmap(pivot_df, annot=True, fmt='.1f', cmap='Reds', ax=ax,
            cbar_kws={'label': '저평점 리뷰 중 비율 (%)'})
ax.set_title('브랜드별 Pain Point 분포 (저평점 1-2점 리뷰)', fontsize=14, fontweight='bold')
ax.set_xlabel('Pain Point 유형', fontsize=12)
ax.set_ylabel('브랜드', fontsize=12)
plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'pain_point_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'pain_point_heatmap.png'}")

# Pain Point TOP 3 막대 그래프
fig, axes = plt.subplots(2, 4, figsize=(16, 8))
axes = axes.flatten()

for idx, brand in enumerate(brands):
    ax = axes[idx]
    brand_pain = pain_df[pain_df['brand'] == brand].sort_values('pct', ascending=True)

    colors = ['#fee2e2' if p < 20 else '#fca5a5' if p < 35 else '#ef4444'
              for p in brand_pain['pct']]

    ax.barh(brand_pain['pain'], brand_pain['pct'], color=colors, edgecolor='#991b1b')
    ax.set_title(f'{brand}', fontsize=11, fontweight='bold')
    ax.set_xlim(0, 60)

    for i, (pain, pct) in enumerate(zip(brand_pain['pain'], brand_pain['pct'])):
        if pct > 0:
            ax.text(pct + 1, i, f'{pct:.1f}%', va='center', fontsize=9)

# 마지막 빈 subplot 숨김
axes[-1].axis('off')

plt.suptitle('브랜드별 저평점 리뷰 Pain Point 비율', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'pain_point_by_brand.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'pain_point_by_brand.png'}")


# ============================================================
# 2. 재구매/이탈 분석 시각화
# ============================================================
print("\n2. 재구매/이탈 시각화 생성...")

REBUY_KEYWORDS = ['재구매', '재구', '또 사', '또사', '계속 사', '계속사', '꾸준히', 'n번째', '번째 구매', '몇통째']
LOYAL_KEYWORDS = ['인생템', '최애', '없으면 안', '필수템', '애정템', '평생', '계속 쓸']
CHURN_KEYWORDS = ['다른 거', '다른거', '바꿀', '갈아타', '안 살', '안살', '다시 안', '다시안', '바꿔야', '다른 제품']

def check_rebuy_signal(text):
    if pd.isna(text):
        return 'neutral'
    text = str(text).lower()
    for kw in LOYAL_KEYWORDS:
        if kw in text:
            return 'loyal'
    for kw in REBUY_KEYWORDS:
        if kw in text:
            return 'rebuy'
    for kw in CHURN_KEYWORDS:
        if kw in text:
            return 'churn'
    return 'neutral'

df['rebuy_signal'] = df['REVIEW_CONTENT'].apply(check_rebuy_signal)

# 브랜드별 집계
loyalty_data = []
for brand in brands:
    brand_df = df[df['BRAND_NAME'] == brand]
    total = len(brand_df)
    loyal = (brand_df['rebuy_signal'] == 'loyal').sum()
    rebuy = (brand_df['rebuy_signal'] == 'rebuy').sum()
    churn = (brand_df['rebuy_signal'] == 'churn').sum()

    loyalty_data.append({
        'brand': brand,
        'total': total,
        'loyal_pct': loyal / total * 100,
        'rebuy_pct': rebuy / total * 100,
        'churn_pct': churn / total * 100,
        'net_loyalty': (loyal + rebuy - churn) / total * 100
    })

loyalty_df = pd.DataFrame(loyalty_data)

# 순충성도 막대 그래프
fig, ax = plt.subplots(figsize=(12, 6))

x = range(len(loyalty_df))
width = 0.25

bars1 = ax.bar([i - width for i in x], loyalty_df['loyal_pct'], width,
               label='충성(Loyal)', color='#10b981', alpha=0.8)
bars2 = ax.bar(x, loyalty_df['rebuy_pct'], width,
               label='재구매(Rebuy)', color='#3b82f6', alpha=0.8)
bars3 = ax.bar([i + width for i in x], loyalty_df['churn_pct'], width,
               label='이탈(Churn)', color='#ef4444', alpha=0.8)

ax.set_xlabel('브랜드', fontsize=12)
ax.set_ylabel('비율 (%)', fontsize=12)
ax.set_title('브랜드별 재구매/충성/이탈 신호 비율', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(loyalty_df['brand'], rotation=45, ha='right')
ax.legend()

# 값 표시
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        if height > 0.3:
            ax.annotate(f'{height:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)

plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'loyalty_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'loyalty_comparison.png'}")

# 순충성도 지표
fig, ax = plt.subplots(figsize=(10, 6))

loyalty_df_sorted = loyalty_df.sort_values('net_loyalty', ascending=True)
colors = ['#10b981' if v > 10 else '#3b82f6' if v > 5 else '#f59e0b'
          for v in loyalty_df_sorted['net_loyalty']]

bars = ax.barh(loyalty_df_sorted['brand'], loyalty_df_sorted['net_loyalty'],
               color=colors, edgecolor='#1f2937')

ax.set_xlabel('순충성도 (%) = (충성 + 재구매 - 이탈) / 전체', fontsize=11)
ax.set_title('브랜드별 순충성도 지표', fontsize=14, fontweight='bold')
ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

for bar, val in zip(bars, loyalty_df_sorted['net_loyalty']):
    ax.text(val + 0.3, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}%', va='center', fontsize=10, fontweight='bold')

plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'net_loyalty.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'net_loyalty.png'}")


# ============================================================
# 3. 월별 키워드 트렌드 시각화
# ============================================================
print("\n3. 월별 키워드 트렌드 시각화 생성...")

TREND_KEYWORDS = {
    '진정': ['진정', '어성초', '시카', '트러블', '붉은기'],
    '보습': ['보습', '촉촉', '수분', '건조', '당김'],
    '각질': ['각질', '피부결', '매끈', '결정리'],
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
recent_months = months[-8:] if len(months) >= 8 else months

trend_data = []
for month in recent_months:
    month_df = df[df['year_month'] == month]
    month_cnt = len(month_df)

    if month_cnt == 0:
        continue

    row = {'month': str(month), 'count': month_cnt}
    for kw_cat, keywords in TREND_KEYWORDS.items():
        mentions = month_df['REVIEW_CONTENT'].apply(lambda x: count_keyword_category(x, keywords)).sum()
        row[kw_cat] = mentions / month_cnt * 100

    trend_data.append(row)

trend_df = pd.DataFrame(trend_data)

# 전체 트렌드 라인 차트
fig, ax = plt.subplots(figsize=(14, 7))

colors = {'진정': '#ef4444', '보습': '#3b82f6', '각질': '#f59e0b',
          '산뜻': '#10b981', '가성비': '#8b5cf6'}

for kw_cat in TREND_KEYWORDS.keys():
    ax.plot(trend_df['month'], trend_df[kw_cat], marker='o', linewidth=2.5,
            markersize=8, label=kw_cat, color=colors[kw_cat])

ax.set_xlabel('월', fontsize=12)
ax.set_ylabel('언급률 (%)', fontsize=12)
ax.set_title('월별 주요 키워드 언급률 트렌드', fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=10)
ax.grid(True, alpha=0.3)

plt.xticks(rotation=45, ha='right')
plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'monthly_trend_all.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'monthly_trend_all.png'}")

# 브랜드별 트렌드 (진정 vs 보습)
fig, axes = plt.subplots(2, 4, figsize=(18, 10))
axes = axes.flatten()

for idx, brand in enumerate(brands):
    ax = axes[idx]
    brand_df = df[df['BRAND_NAME'] == brand]

    brand_trend = []
    for month in recent_months:
        month_df = brand_df[brand_df['year_month'] == month]
        month_cnt = len(month_df)
        if month_cnt == 0:
            continue

        row = {'month': str(month)}
        for kw_cat in ['진정', '보습']:
            mentions = month_df['REVIEW_CONTENT'].apply(
                lambda x: count_keyword_category(x, TREND_KEYWORDS[kw_cat])).sum()
            row[kw_cat] = mentions / month_cnt * 100
        brand_trend.append(row)

    if brand_trend:
        bt_df = pd.DataFrame(brand_trend)
        ax.plot(bt_df['month'], bt_df['진정'], marker='o', linewidth=2,
                label='진정', color='#ef4444')
        ax.plot(bt_df['month'], bt_df['보습'], marker='s', linewidth=2,
                label='보습', color='#3b82f6')
        ax.set_title(f'{brand}', fontsize=11, fontweight='bold')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
        ax.set_ylim(0, 80)

axes[-1].axis('off')
plt.suptitle('브랜드별 진정/보습 키워드 월별 트렌드', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'monthly_trend_by_brand.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'monthly_trend_by_brand.png'}")


# ============================================================
# 4. 브랜드 포지셔닝 종합 레이더 차트
# ============================================================
print("\n4. 브랜드 포지셔닝 레이더 차트 생성...")

# REVIEW_ADDITIONAL_INFO 파싱
def parse_recommend_info(info_str):
    if pd.isna(info_str) or info_str is None:
        return '', ''
    try:
        info = json.loads(info_str)
        skin = info.get('피부타입', '')
        concern = info.get('피부고민', '')
        if '건성' in skin: skin_type = '건성'
        elif '지성' in skin: skin_type = '지성'
        elif '복합성' in skin: skin_type = '복합성'
        else: skin_type = ''
        if '보습' in concern: skin_concern = '보습'
        elif '진정' in concern: skin_concern = '진정'
        else: skin_concern = ''
        return skin_type, skin_concern
    except:
        return '', ''

parsed_rec = df['REVIEW_ADDITIONAL_INFO'].apply(parse_recommend_info)
df['recommend_type'] = [p[0] for p in parsed_rec]
df['recommend_concern'] = [p[1] for p in parsed_rec]

# 브랜드별 지표 계산
positioning_data = []
for brand in brands:
    brand_df = df[df['BRAND_NAME'] == brand]
    total = len(brand_df)

    # 추천 피부고민
    concern_valid = brand_df[brand_df['recommend_concern'] != '']
    if len(concern_valid) > 0:
        moisture_pct = (concern_valid['recommend_concern'] == '보습').mean() * 100
        calming_pct = (concern_valid['recommend_concern'] == '진정').mean() * 100
    else:
        moisture_pct, calming_pct = 50, 50

    # 저평점 비율 (역지표)
    low_rating_pct = (brand_df['REVIEW_RATING'] <= 2).mean() * 100
    satisfaction = 100 - low_rating_pct * 10  # 만족도 점수

    # 재구매 신호
    rebuy_pct = ((brand_df['rebuy_signal'] == 'loyal') |
                 (brand_df['rebuy_signal'] == 'rebuy')).mean() * 100

    positioning_data.append({
        'brand': brand,
        '보습': moisture_pct,
        '진정': calming_pct,
        '만족도': min(satisfaction, 100),
        '재구매': rebuy_pct * 5,  # 스케일 조정
        '리뷰량': min(total / 80, 100)  # 스케일 조정
    })

pos_df = pd.DataFrame(positioning_data)

# 레이더 차트
categories = ['보습', '진정', '만족도', '재구매', '리뷰량']
num_vars = len(categories)

angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
angles += angles[:1]

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

colors_radar = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']

for idx, row in pos_df.iterrows():
    values = [row[cat] for cat in categories]
    values += values[:1]
    ax.plot(angles, values, 'o-', linewidth=2, label=row['brand'], color=colors_radar[idx])
    ax.fill(angles, values, alpha=0.1, color=colors_radar[idx])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=11)
ax.set_title('브랜드 포지셔닝 종합 비교', fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'brand_positioning_radar.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'brand_positioning_radar.png'}")


# ============================================================
# 5. 고객 프로필 분포 시각화
# ============================================================
print("\n5. 고객 프로필 분포 시각화 생성...")

# 브랜드별 추천 피부타입 분포
fig, ax = plt.subplots(figsize=(12, 6))

profile_data = []
for brand in brands:
    brand_df = df[df['BRAND_NAME'] == brand]
    rec_valid = brand_df[brand_df['recommend_type'] != '']
    if len(rec_valid) > 0:
        dry = (rec_valid['recommend_type'] == '건성').mean() * 100
        oily = (rec_valid['recommend_type'] == '지성').mean() * 100
        combo = (rec_valid['recommend_type'] == '복합성').mean() * 100
    else:
        dry, oily, combo = 0, 0, 0
    profile_data.append({'brand': brand, '건성': dry, '지성': oily, '복합성': combo})

profile_df = pd.DataFrame(profile_data)

x = range(len(profile_df))
width = 0.25

bars1 = ax.bar([i - width for i in x], profile_df['건성'], width,
               label='건성', color='#fbbf24')
bars2 = ax.bar(x, profile_df['지성'], width,
               label='지성', color='#60a5fa')
bars3 = ax.bar([i + width for i in x], profile_df['복합성'], width,
               label='복합성', color='#a78bfa')

ax.set_xlabel('브랜드', fontsize=12)
ax.set_ylabel('추천 비율 (%)', fontsize=12)
ax.set_title('브랜드별 추천 피부타입 분포', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(profile_df['brand'], rotation=45, ha='right')
ax.legend()

plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'skin_type_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'skin_type_distribution.png'}")


# ============================================================
# 6. 종합 대시보드 이미지
# ============================================================
print("\n6. 종합 대시보드 생성...")

fig = plt.figure(figsize=(20, 16))

# 2x3 그리드
gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

# 1. 브랜드별 리뷰 수 (파이)
ax1 = fig.add_subplot(gs[0, 0])
brand_counts = df['BRAND_NAME'].value_counts()
brand_counts = brand_counts.dropna()  # NaN 값 제거
colors_pie = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4']
ax1.pie(brand_counts.values, labels=brand_counts.index, autopct='%1.1f%%',
        colors=colors_pie[:len(brand_counts)], startangle=90)
ax1.set_title('브랜드별 리뷰 분포', fontsize=12, fontweight='bold')

# 2. 평균 평점
ax2 = fig.add_subplot(gs[0, 1])
avg_ratings = df.groupby('BRAND_NAME')['REVIEW_RATING'].mean().reindex(brands).dropna()
bars = ax2.bar(avg_ratings.index, avg_ratings.values, color=colors_pie[:len(avg_ratings)], edgecolor='#1f2937')
ax2.set_ylim(4.7, 5.0)
ax2.set_title('브랜드별 평균 평점', fontsize=12, fontweight='bold')
ax2.tick_params(axis='x', rotation=45)
for bar, val in zip(bars, avg_ratings):
    ax2.text(bar.get_x() + bar.get_width()/2, val + 0.01, f'{val:.2f}',
             ha='center', fontsize=9)

# 3. 저평점 비율
ax3 = fig.add_subplot(gs[0, 2])
low_rates = []
for brand in brands:
    brand_df = df[df['BRAND_NAME'] == brand]
    low_rate = (brand_df['REVIEW_RATING'] <= 2).mean() * 100
    low_rates.append(low_rate)
bars = ax3.bar(brands, low_rates, color='#ef4444', alpha=0.7, edgecolor='#991b1b')
ax3.set_title('브랜드별 저평점(1-2점) 비율', fontsize=12, fontweight='bold')
ax3.tick_params(axis='x', rotation=45)
ax3.set_ylabel('%')
for bar, val in zip(bars, low_rates):
    ax3.text(bar.get_x() + bar.get_width()/2, val + 0.05, f'{val:.1f}%',
             ha='center', fontsize=9)

# 4. 보습 vs 진정 포지셔닝
ax4 = fig.add_subplot(gs[1, 0])
colors_extended = colors_pie * ((len(brands) // len(colors_pie)) + 1)  # 색상 확장
for idx, brand in enumerate(brands):
    brand_df = df[df['BRAND_NAME'] == brand]
    concern_valid = brand_df[brand_df['recommend_concern'] != '']
    if len(concern_valid) > 0:
        moisture = (concern_valid['recommend_concern'] == '보습').mean() * 100
        calming = (concern_valid['recommend_concern'] == '진정').mean() * 100
    else:
        moisture, calming = 50, 50
    ax4.scatter(moisture, calming, s=200, c=colors_extended[idx], label=brand,
                edgecolors='black', linewidth=1, alpha=0.8)
ax4.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
ax4.axvline(x=50, color='gray', linestyle='--', alpha=0.5)
ax4.set_xlabel('보습 (%)', fontsize=10)
ax4.set_ylabel('진정 (%)', fontsize=10)
ax4.set_title('보습 vs 진정 포지셔닝', fontsize=12, fontweight='bold')
ax4.legend(fontsize=8, loc='upper left')

# 5. 재구매/이탈 비교
ax5 = fig.add_subplot(gs[1, 1])
x = range(len(loyalty_df))
width = 0.35
ax5.bar([i - width/2 for i in x], loyalty_df['rebuy_pct'], width,
        label='재구매', color='#3b82f6')
ax5.bar([i + width/2 for i in x], loyalty_df['churn_pct'], width,
        label='이탈', color='#ef4444')
ax5.set_xticks(x)
ax5.set_xticklabels(loyalty_df['brand'], rotation=45, ha='right')
ax5.set_title('재구매 vs 이탈 신호', fontsize=12, fontweight='bold')
ax5.legend()
ax5.set_ylabel('%')

# 6. 월별 리뷰 트렌드
ax6 = fig.add_subplot(gs[1, 2])
monthly_counts = df.groupby('year_month').size()
recent_monthly = monthly_counts[recent_months]
ax6.plot(range(len(recent_monthly)), recent_monthly.values,
         marker='o', linewidth=2, color='#3b82f6')
ax6.fill_between(range(len(recent_monthly)), recent_monthly.values, alpha=0.3)
ax6.set_xticks(range(len(recent_monthly)))
ax6.set_xticklabels([str(m) for m in recent_monthly.index], rotation=45, ha='right')
ax6.set_title('월별 리뷰 수 추이', fontsize=12, fontweight='bold')
ax6.set_ylabel('리뷰 수')

# 7. Pain Point TOP 5 (전체)
ax7 = fig.add_subplot(gs[2, :2])
all_pains = []
for pains in low_rating_df['pain_points']:
    all_pains.extend(pains)
pain_counter = Counter(all_pains)
pain_items = pain_counter.most_common()
pains_names = [p[0] for p in pain_items]
pains_counts = [p[1] for p in pain_items]

bars = ax7.barh(pains_names[::-1], pains_counts[::-1], color='#ef4444', alpha=0.8)
ax7.set_title('전체 저평점 리뷰 Pain Point (빈도)', fontsize=12, fontweight='bold')
ax7.set_xlabel('언급 횟수')
for bar, val in zip(bars, pains_counts[::-1]):
    ax7.text(val + 1, bar.get_y() + bar.get_height()/2, str(val), va='center')

# 8. 키워드 언급률 (최근 월)
ax8 = fig.add_subplot(gs[2, 2])
if len(trend_df) > 0:
    latest = trend_df.iloc[-1]
    kw_names = list(TREND_KEYWORDS.keys())
    kw_vals = [latest[k] for k in kw_names]
    colors_kw = ['#ef4444', '#3b82f6', '#f59e0b', '#10b981', '#8b5cf6']
    bars = ax8.bar(kw_names, kw_vals, color=colors_kw)
    ax8.set_title(f'최근 월({latest["month"]}) 키워드 언급률', fontsize=12, fontweight='bold')
    ax8.set_ylabel('%')
    for bar, val in zip(bars, kw_vals):
        ax8.text(bar.get_x() + bar.get_width()/2, val + 0.5, f'{val:.1f}%',
                 ha='center', fontsize=9)

plt.suptitle('올리브영 토너 리뷰 분석 대시보드', fontsize=16, fontweight='bold', y=1.01)
plt.tight_layout()
fig.savefig(OUTPUT_DIR / 'dashboard_summary.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"  저장: {OUTPUT_DIR / 'dashboard_summary.png'}")

print("\n" + "=" * 50)
print("모든 시각화 생성 완료!")
print("=" * 50)
print(f"\n저장 위치: {OUTPUT_DIR.absolute()}")
