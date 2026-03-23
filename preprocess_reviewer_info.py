# -*- coding: utf-8 -*-
"""
리뷰어 정보 전처리 - 올리브영 전용
"""
import json
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')


RATING_MAP = {
    '매우 높음': 5, '높음': 4, '보통': 3, '낮음': 2, '매우 낮음': 1,
    '매우 좋음': 5, '좋음': 4, '나쁨': 2, '매우 나쁨': 1,
    '전혀없음': 5, '거의없음': 4, '조금있음': 2, '많음': 1,
}


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


def preprocess_data(df):
    """올리브영 데이터 전처리"""
    print("리뷰어 정보 전처리 중...")

    # 새 컬럼 초기화
    df['SKIN_TYPE'] = None
    df['SKIN_TONE'] = None
    df['SKIN_CONCERNS'] = None
    df['EVAL_IRRITATION'] = None

    # 올리브영 처리
    print("  올리브영 REVIEWER_INFO 처리...")
    oy_reviewer = df['REVIEWER_INFO'].apply(parse_oliveyoung_reviewer_info)
    df['SKIN_TYPE'] = oy_reviewer.apply(lambda x: x[0])
    df['SKIN_TONE'] = oy_reviewer.apply(lambda x: x[1])
    df['SKIN_CONCERNS'] = oy_reviewer.apply(lambda x: x[2])

    print("  올리브영 ADDITIONAL_INFO 처리...")
    if 'REVIEW_ADDITIONAL_INFO' in df.columns:
        df['EVAL_IRRITATION'] = df['REVIEW_ADDITIONAL_INFO'].apply(
            parse_oliveyoung_additional_info
        )

    return df


def main():
    print("=" * 70)
    print("리뷰어 정보 전처리 (올리브영)")
    print("=" * 70)

    # 올리브영 데이터 로드
    print("\n데이터 로드...")
    with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    first_key = list(data.keys())[0]
    df = pd.DataFrame(data[first_key])
    print(f"총 리뷰: {len(df):,}건")

    # 전처리
    df = preprocess_data(df)

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
    output_path = 'data/oliveyoung_reviews_processed.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    json_path = 'data/oliveyoung_reviews_processed.json'
    df.to_json(json_path, orient='records', force_ascii=False, indent=2)

    print(f"\n저장 완료:")
    print(f"  CSV: {output_path}")
    print(f"  JSON: {json_path}")

    # 샘플 출력
    print("\n[샘플]")
    sample_cols = ['BRAND_NAME', 'SKIN_TYPE', 'SKIN_TONE', 'SKIN_CONCERNS', 'EVAL_IRRITATION']
    print(df[sample_cols].head(5).to_string())

    return df


if __name__ == "__main__":
    main()
