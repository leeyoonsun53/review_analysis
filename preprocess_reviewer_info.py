# -*- coding: utf-8 -*-
"""
리뷰어 정보 전처리 - 플랫폼별 형식 통합 (최적화 버전)
"""
import json
import pandas as pd
import re
import sys
from tqdm import tqdm

sys.stdout.reconfigure(encoding='utf-8')


# ===== 무신사 → 한글 매핑 =====

SKIN_TYPE_MAP = {
    'oily': '지성',
    'dry': '건성',
    'combination': '복합성',
    'sensitive': '민감성',
    'normal': '중성',
}

SKIN_TONE_MAP = {
    'spring_warm': '봄웜톤',
    'summer_cool': '여름쿨톤',
    'fall_warm': '가을웜톤',
    'winter_cool': '겨울쿨톤',
}

SKIN_CONCERN_MAP = {
    'nutrition': '영양',
    'soothing': '진정',
    'acne': '트러블',
    'pores': '모공',
    'moisture_control': '유수분',
    'brightening': '미백',
    'elasticity': '탄력',
    'wrinkles': '주름',
    'dark_circles': '다크서클',
    'redness': '홍조',
    'sebum': '피지',
}

RATING_MAP = {
    '매우 높음': 5, '높음': 4, '보통': 3, '낮음': 2, '매우 낮음': 1,
    '매우 좋음': 5, '좋음': 4, '나쁨': 2, '매우 나쁨': 1,
    '전혀없음': 5, '거의없음': 4, '조금있음': 2, '많음': 1,
}


def parse_musinsa_reviewer_info(info):
    """무신사 REVIEWER_INFO 파싱: oily / spring_warm / acne,soothing"""
    if pd.isna(info) or not info:
        return None, None, None

    parts = str(info).split(' / ')
    skin_type = SKIN_TYPE_MAP.get(parts[0].strip(), None) if len(parts) >= 1 else None
    skin_tone = SKIN_TONE_MAP.get(parts[1].strip(), None) if len(parts) >= 2 else None

    concerns = None
    if len(parts) >= 3:
        concern_list = [SKIN_CONCERN_MAP.get(c.strip(), c.strip()) for c in parts[2].split(',') if c.strip()]
        concerns = ','.join(concern_list) if concern_list else None

    return skin_type, skin_tone, concerns


def parse_oliveyoung_reviewer_info(info):
    """올리브영 REVIEWER_INFO 파싱: 지성, 가을웜톤, 각질, 다크서클"""
    if pd.isna(info) or not info:
        return None, None, None

    parts = [p.strip() for p in str(info).split(',')]

    skin_types = ['지성', '건성', '복합성', '민감성', '중성']
    skin_tones = ['봄웜톤', '여름쿨톤', '가을웜톤', '겨울쿨톤']

    skin_type = None
    skin_tone = None
    concerns = []

    for part in parts:
        if part in skin_types:
            skin_type = part
        elif part in skin_tones:
            skin_tone = part
        elif part:
            concerns.append(part)

    return skin_type, skin_tone, ','.join(concerns) if concerns else None


def parse_musinsa_additional_info(info):
    """무신사 REVIEW_ADDITIONAL_INFO에서 보습력/흡수력/자극 추출"""
    if pd.isna(info) or not info:
        return None, None, None

    info_str = str(info)

    moisture = None
    absorption = None
    irritation = None

    # 보습력
    m = re.search(r"보습력.*?'answerShortText':\s*'([^']+)'", info_str)
    if m:
        moisture = RATING_MAP.get(m.group(1))

    # 흡수력
    m = re.search(r"흡수력.*?'answerShortText':\s*'([^']+)'", info_str)
    if m:
        absorption = RATING_MAP.get(m.group(1))

    # 자극여부
    m = re.search(r"자극여부.*?'answerShortText':\s*'([^']+)'", info_str)
    if m:
        irritation = RATING_MAP.get(m.group(1))

    return moisture, absorption, irritation


def parse_oliveyoung_additional_info(info):
    """올리브영 REVIEW_ADDITIONAL_INFO에서 자극도 추출"""
    if pd.isna(info) or not info:
        return None

    try:
        data = json.loads(str(info))
        if '자극도' in data:
            text = data['자극도']
            if '순해요' in text or '없' in text:
                return 5
            elif '보통' in text:
                return 3
            else:
                return 2
    except:
        pass

    return None


def preprocess_merged_data(df):
    """병합된 데이터 전처리 (벡터화)"""
    print("리뷰어 정보 전처리 중...")

    # 무신사 마스크
    ms_mask = df['PLATFORM'] == '무신사'
    oy_mask = df['PLATFORM'] == '올리브영'

    # 새 컬럼 초기화
    df['SKIN_TYPE'] = None
    df['SKIN_TONE'] = None
    df['SKIN_CONCERNS'] = None
    df['EVAL_MOISTURE'] = None
    df['EVAL_ABSORPTION'] = None
    df['EVAL_IRRITATION'] = None

    # 무신사 처리
    print("  무신사 REVIEWER_INFO 처리...")
    ms_reviewer = df.loc[ms_mask, 'REVIEWER_INFO'].apply(parse_musinsa_reviewer_info)
    df.loc[ms_mask, 'SKIN_TYPE'] = ms_reviewer.apply(lambda x: x[0])
    df.loc[ms_mask, 'SKIN_TONE'] = ms_reviewer.apply(lambda x: x[1])
    df.loc[ms_mask, 'SKIN_CONCERNS'] = ms_reviewer.apply(lambda x: x[2])

    print("  무신사 ADDITIONAL_INFO 처리...")
    if 'REVIEW_ADDITIONAL_INFO' in df.columns:
        ms_additional = df.loc[ms_mask, 'REVIEW_ADDITIONAL_INFO'].apply(parse_musinsa_additional_info)
        df.loc[ms_mask, 'EVAL_MOISTURE'] = ms_additional.apply(lambda x: x[0])
        df.loc[ms_mask, 'EVAL_ABSORPTION'] = ms_additional.apply(lambda x: x[1])
        df.loc[ms_mask, 'EVAL_IRRITATION'] = ms_additional.apply(lambda x: x[2])

    # 올리브영 처리
    print("  올리브영 REVIEWER_INFO 처리...")
    oy_reviewer = df.loc[oy_mask, 'REVIEWER_INFO'].apply(parse_oliveyoung_reviewer_info)
    df.loc[oy_mask, 'SKIN_TYPE'] = oy_reviewer.apply(lambda x: x[0])
    df.loc[oy_mask, 'SKIN_TONE'] = oy_reviewer.apply(lambda x: x[1])
    df.loc[oy_mask, 'SKIN_CONCERNS'] = oy_reviewer.apply(lambda x: x[2])

    print("  올리브영 ADDITIONAL_INFO 처리...")
    if 'REVIEW_ADDITIONAL_INFO' in df.columns:
        df.loc[oy_mask, 'EVAL_IRRITATION'] = df.loc[oy_mask, 'REVIEW_ADDITIONAL_INFO'].apply(
            parse_oliveyoung_additional_info
        )

    return df


def main():
    print("=" * 70)
    print("리뷰어 정보 전처리")
    print("=" * 70)

    # 병합 데이터 로드
    print("\n병합 데이터 로드...")
    df = pd.read_csv('data/merged_reviews.csv', encoding='utf-8-sig')
    print(f"총 리뷰: {len(df):,}건")

    # 전처리
    df = preprocess_merged_data(df)

    # 통계 출력
    print("\n" + "=" * 70)
    print("전처리 결과")
    print("=" * 70)

    print("\n[피부타입 분포]")
    for val, cnt in df['SKIN_TYPE'].value_counts(dropna=False).head(10).items():
        label = val if val else 'N/A'
        print(f"  {label}: {cnt:,}건")

    print("\n[피부톤 분포]")
    for val, cnt in df['SKIN_TONE'].value_counts(dropna=False).head(10).items():
        label = val if val else 'N/A'
        print(f"  {label}: {cnt:,}건")

    print("\n[피부고민 TOP 10]")
    all_concerns = df['SKIN_CONCERNS'].dropna().str.split(',').explode()
    for concern, cnt in all_concerns.value_counts().head(10).items():
        print(f"  {concern}: {cnt:,}건")

    print("\n[자극도 평가 분포]")
    for val, cnt in df['EVAL_IRRITATION'].value_counts(dropna=False).items():
        if pd.isna(val):
            label = 'N/A'
        else:
            label = {5: '순함(5)', 4: '거의없음(4)', 3: '보통(3)', 2: '약간(2)', 1: '자극(1)'}.get(int(val), val)
        print(f"  {label}: {cnt:,}건")

    # 저장
    output_path = 'data/merged_reviews_processed.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    json_path = 'data/merged_reviews_processed.json'
    df.to_json(json_path, orient='records', force_ascii=False, indent=2)

    print(f"\n저장 완료:")
    print(f"  CSV: {output_path}")
    print(f"  JSON: {json_path}")

    # 샘플 출력
    print("\n[샘플 - 무신사]")
    sample_cols = ['PLATFORM', 'BRAND_NAME', 'SKIN_TYPE', 'SKIN_TONE', 'SKIN_CONCERNS', 'EVAL_IRRITATION']
    print(df[df['PLATFORM'] == '무신사'][sample_cols].head(5).to_string())

    print("\n[샘플 - 올리브영]")
    print(df[df['PLATFORM'] == '올리브영'][sample_cols].head(5).to_string())

    return df


if __name__ == "__main__":
    main()
