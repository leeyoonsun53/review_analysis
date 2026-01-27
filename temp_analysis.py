# -*- coding: utf-8 -*-
import json
import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

first_key = list(data.keys())[0]
df = pd.DataFrame(data[first_key])

# REVIEWER_INFO 파싱 (리뷰어 본인)
def parse_reviewer_info(info_str):
    if pd.isna(info_str) or info_str is None:
        return ''
    parts = [p.strip() for p in str(info_str).split(',')]
    for part in parts:
        if '건성' in part: return '건성'
        if '지성' in part: return '지성'
        if '복합성' in part: return '복합성'
        if '중성' in part: return '중성'
    return ''

# REVIEW_ADDITIONAL_INFO 파싱 (제품 추천 대상)
def parse_recommend_info(info_str):
    if pd.isna(info_str) or info_str is None:
        return '', ''
    try:
        info = json.loads(info_str)
        skin = info.get('피부타입', '')
        concern = info.get('피부고민', '')
        # 피부타입 추출
        if '건성' in skin: skin_type = '건성'
        elif '지성' in skin: skin_type = '지성'
        elif '복합성' in skin: skin_type = '복합성'
        else: skin_type = ''
        # 피부고민 추출
        if '보습' in concern: skin_concern = '보습'
        elif '진정' in concern: skin_concern = '진정'
        else: skin_concern = ''
        return skin_type, skin_concern
    except:
        return '', ''

df['reviewer_type'] = df['REVIEWER_INFO'].apply(parse_reviewer_info)
parsed_rec = df['REVIEW_ADDITIONAL_INFO'].apply(parse_recommend_info)
df['recommend_type'] = [p[0] for p in parsed_rec]
df['recommend_concern'] = [p[1] for p in parsed_rec]

print('=' * 90)
print('브랜드별 [실제 구매자] vs [추천 대상] 비교 분석')
print('=' * 90)

brands = df['BRAND_NAME'].unique()
results = []

for brand in sorted(brands):
    brand_df = df[df['BRAND_NAME'] == brand]
    total = len(brand_df)

    # 실제 구매자 (REVIEWER_INFO)
    buyer_valid = brand_df[brand_df['reviewer_type'] != '']
    if len(buyer_valid) > 0:
        buyer_dry = (buyer_valid['reviewer_type'] == '건성').mean() * 100
        buyer_oily = (buyer_valid['reviewer_type'] == '지성').mean() * 100
        buyer_combo = (buyer_valid['reviewer_type'] == '복합성').mean() * 100
    else:
        buyer_dry, buyer_oily, buyer_combo = 0, 0, 0

    # 추천 대상 (REVIEW_ADDITIONAL_INFO)
    rec_valid = brand_df[brand_df['recommend_type'] != '']
    if len(rec_valid) > 0:
        rec_dry = (rec_valid['recommend_type'] == '건성').mean() * 100
        rec_oily = (rec_valid['recommend_type'] == '지성').mean() * 100
        rec_combo = (rec_valid['recommend_type'] == '복합성').mean() * 100
    else:
        rec_dry, rec_oily, rec_combo = 0, 0, 0

    # 추천 피부고민
    concern_valid = brand_df[brand_df['recommend_concern'] != '']
    if len(concern_valid) > 0:
        rec_moisture = (concern_valid['recommend_concern'] == '보습').mean() * 100
        rec_calming = (concern_valid['recommend_concern'] == '진정').mean() * 100
    else:
        rec_moisture, rec_calming = 0, 0

    results.append({
        'brand': brand, 'total': total,
        'buyer_dry': buyer_dry, 'buyer_oily': buyer_oily, 'buyer_combo': buyer_combo,
        'rec_dry': rec_dry, 'rec_oily': rec_oily, 'rec_combo': rec_combo,
        'rec_moisture': rec_moisture, 'rec_calming': rec_calming
    })

results = sorted(results, key=lambda x: x['total'], reverse=True)

print()
print('[피부타입 비교: 실제 구매자 vs 추천 대상]')
print()
print(f"{'브랜드':<12} {'리뷰':>6} | {'--실제 구매자--':^18} | {'--제품 추천 대상--':^18} | {'주요 고민':^12}")
print(f"{'':12} {'':>6} | {'건성':>6} {'지성':>6} {'복합':>6} | {'건성':>6} {'지성':>6} {'복합':>6} | {'보습':>6} {'진정':>6}")
print('-' * 95)

for r in results:
    print(f"{r['brand']:<12} {r['total']:>5,} | {r['buyer_dry']:>5.1f}% {r['buyer_oily']:>5.1f}% {r['buyer_combo']:>5.1f}% | {r['rec_dry']:>5.1f}% {r['rec_oily']:>5.1f}% {r['rec_combo']:>5.1f}% | {r['rec_moisture']:>5.1f}% {r['rec_calming']:>5.1f}%")

print()
print('=' * 90)
print('브랜드별 포지셔닝 요약')
print('=' * 90)

for r in results:
    print(f"\n[{r['brand']}] (리뷰 {r['total']:,}건)")

    # 주요 구매자
    buyer_main = max([('건성', r['buyer_dry']), ('지성', r['buyer_oily']), ('복합성', r['buyer_combo'])], key=lambda x: x[1])
    print(f"  - 주요 구매자: {buyer_main[0]} ({buyer_main[1]:.1f}%)")

    # 추천 피부타입
    rec_main = max([('건성', r['rec_dry']), ('지성', r['rec_oily']), ('복합성', r['rec_combo'])], key=lambda x: x[1])
    print(f"  - 추천 피부타입: {rec_main[0]} ({rec_main[1]:.1f}%)")

    # 주요 고민
    concern_main = '보습' if r['rec_moisture'] > r['rec_calming'] else '진정'
    concern_pct = max(r['rec_moisture'], r['rec_calming'])
    print(f"  - 주요 고민 해결: {concern_main} ({concern_pct:.1f}%)")

    # 특징 분석
    if r['buyer_oily'] > 25 and r['rec_calming'] > 60:
        print(f"  >>> 지성+트러블 케어 포지션")
    elif r['buyer_dry'] > 30 and r['rec_moisture'] > 60:
        print(f"  >>> 건성+보습 케어 포지션")
    elif r['rec_calming'] > 70:
        print(f"  >>> 진정 전문 포지션")
    elif r['rec_moisture'] > 70:
        print(f"  >>> 보습 전문 포지션")
