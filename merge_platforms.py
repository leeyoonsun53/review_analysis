# -*- coding: utf-8 -*-
"""
플랫폼 데이터 병합 스크립트
- 올리브영 + 무신사 리뷰 데이터 통합
- PLATFORM 컬럼으로 구분
"""
import json
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')


def load_oliveyoung():
    """올리브영 데이터 로드"""
    with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    first_key = list(data.keys())[0]
    df = pd.DataFrame(data[first_key])
    df['PLATFORM'] = '올리브영'

    print(f"올리브영 리뷰: {len(df):,}건")
    print(f"  컬럼: {list(df.columns)}")
    print(f"  브랜드: {df['BRAND_NAME'].unique().tolist()}")

    return df


def load_musinsa():
    """무신사 데이터 로드"""
    df = pd.read_csv('data/무신사리뷰.csv', encoding='utf-8')
    df['PLATFORM'] = '무신사'

    # 컬럼명 통일 (대문자로)
    df.columns = [col.upper() for col in df.columns]

    print(f"\n무신사 리뷰: {len(df):,}건")
    print(f"  컬럼: {list(df.columns)}")
    print(f"  브랜드: {df['BRAND_NAME'].unique().tolist()}")

    return df


def clean_brand_name(name):
    """브랜드명 정규화"""
    name = str(name).strip()
    # 브랜드명 통일
    brand_mapping = {
        '에스네이처 ': '에스네이처',
        '에스네이쳐': '에스네이처',
    }
    return brand_mapping.get(name, name)


def merge_data(df_oy, df_ms):
    """두 데이터 병합"""
    # 브랜드명 정규화
    df_oy['BRAND_NAME'] = df_oy['BRAND_NAME'].apply(clean_brand_name)
    df_ms['BRAND_NAME'] = df_ms['BRAND_NAME'].apply(clean_brand_name)

    # 공통 컬럼 정의
    common_cols = ['PLATFORM', 'BRAND_NAME', 'REVIEW_CONTENT', 'REVIEW_RATING',
                   'REVIEW_DATE', 'REVIEWER_INFO', 'REVIEW_ADDITIONAL_INFO']

    # 올리브영에서 필요한 컬럼만 선택
    oy_cols = [c for c in common_cols if c in df_oy.columns]
    if 'REVIEW_ID' in df_oy.columns:
        oy_cols.append('REVIEW_ID')
    df_oy_subset = df_oy[oy_cols].copy()

    # 무신사에서 필요한 컬럼만 선택
    ms_cols = [c for c in common_cols if c in df_ms.columns]
    # 무신사 추가 컬럼
    extra_ms_cols = ['USER_ID', 'GOODS_NAME', 'PRODUCT_NAME', 'REVIEW_LIKES']
    for col in extra_ms_cols:
        if col in df_ms.columns:
            ms_cols.append(col)
    df_ms_subset = df_ms[ms_cols].copy()

    # 병합
    df_merged = pd.concat([df_oy_subset, df_ms_subset], ignore_index=True)

    # REVIEW_DATE 정규화
    df_merged['REVIEW_DATE'] = pd.to_datetime(df_merged['REVIEW_DATE'], errors='coerce')

    print(f"\n병합 완료: {len(df_merged):,}건")
    print(f"  컬럼: {list(df_merged.columns)}")

    return df_merged


def main():
    print("=" * 70)
    print("플랫폼 데이터 병합")
    print("=" * 70)

    # 데이터 로드
    df_oy = load_oliveyoung()
    df_ms = load_musinsa()

    # 병합
    df_merged = merge_data(df_oy, df_ms)

    # 통계
    print("\n" + "=" * 70)
    print("병합 데이터 통계")
    print("=" * 70)

    print("\n플랫폼별 리뷰 수:")
    platform_counts = df_merged['PLATFORM'].value_counts()
    for platform, count in platform_counts.items():
        print(f"  {platform}: {count:,}건")

    print("\n브랜드별 리뷰 수:")
    brand_counts = df_merged.groupby(['PLATFORM', 'BRAND_NAME']).size().reset_index(name='count')
    for _, row in brand_counts.iterrows():
        print(f"  [{row['PLATFORM']}] {row['BRAND_NAME']}: {row['count']:,}건")

    print("\n별점 분포:")
    rating_dist = df_merged['REVIEW_RATING'].value_counts().sort_index()
    for rating, count in rating_dist.items():
        pct = count / len(df_merged) * 100
        print(f"  {rating}점: {count:,}건 ({pct:.1f}%)")

    # 저장
    output_path = 'data/merged_reviews.json'

    # JSON으로 저장 (날짜를 문자열로 변환)
    df_merged['REVIEW_DATE'] = df_merged['REVIEW_DATE'].astype(str)
    df_merged.to_json(output_path, orient='records', force_ascii=False, indent=2)

    # CSV로도 저장
    csv_path = 'data/merged_reviews.csv'
    df_merged.to_csv(csv_path, index=False, encoding='utf-8-sig')

    print(f"\n저장 완료:")
    print(f"  JSON: {output_path}")
    print(f"  CSV: {csv_path}")

    return df_merged


if __name__ == "__main__":
    main()
