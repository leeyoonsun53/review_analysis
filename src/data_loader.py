"""
데이터 로딩 및 전처리 모듈
"""

import pandas as pd
import json
from pathlib import Path


def load_and_preprocess(file_path):
    """
    CSV 또는 JSON 데이터 로딩 및 전처리

    Args:
        file_path: CSV 또는 JSON 파일 경로

    Returns:
        pd.DataFrame: 전처리된 데이터프레임
    """
    file_path = Path(file_path)

    # 파일 확장자에 따라 로딩 방식 결정
    if file_path.suffix.lower() == '.json':
        # JSON 파일 로딩
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # JSON 구조 처리: {SQL쿼리: [데이터리스트]} 형태
        if isinstance(data, dict):
            # 첫 번째 키의 값이 리스트인 경우 (SQL 쿼리 결과 형태)
            first_key = list(data.keys())[0]
            if isinstance(data[first_key], list):
                df = pd.DataFrame(data[first_key])
            else:
                df = pd.DataFrame([data])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            raise ValueError("지원하지 않는 JSON 구조입니다.")
    else:
        # CSV 로딩 (파싱 오류 처리)
        df = pd.read_csv(
            file_path,
            encoding='utf-8',
            engine='python',
            on_bad_lines='skip'
        )

    # REVIEW_ADDITIONAL_INFO JSON 파싱
    def parse_additional_info(x):
        try:
            if pd.notna(x) and x.strip():
                return json.loads(x)
            return {}
        except (json.JSONDecodeError, AttributeError):
            return {}

    df['additional_info_parsed'] = df['REVIEW_ADDITIONAL_INFO'].apply(parse_additional_info)

    # 피부타입, 피부고민, 자극도 컬럼 추출
    df['피부타입'] = df['additional_info_parsed'].apply(lambda x: x.get('피부타입', ''))
    df['피부고민'] = df['additional_info_parsed'].apply(lambda x: x.get('피부고민', ''))
    df['자극도'] = df['additional_info_parsed'].apply(lambda x: x.get('자극도', ''))

    # 텍스트 정제
    df['REVIEW_CONTENT'] = df['REVIEW_CONTENT'].fillna('').astype(str).str.strip()

    # 날짜 파싱
    df['REVIEW_DATE'] = pd.to_datetime(df['REVIEW_DATE'], errors='coerce')

    # PURCHASE_TAG 정제
    df['PURCHASE_TAG'] = df['PURCHASE_TAG'].fillna('')

    # 재구매 여부 플래그
    df['is_rebuy'] = df['PURCHASE_TAG'].str.contains('재구매', na=False)

    return df


def get_brand_summary(df):
    """
    브랜드별 요약 통계

    Args:
        df: 데이터프레임

    Returns:
        pd.DataFrame: 브랜드별 요약
    """
    summary = df.groupby('BRAND_NAME').agg({
        'REVIEW_ID': 'count',
        'REVIEW_RATING': 'mean',
        'is_rebuy': 'sum'
    }).rename(columns={
        'REVIEW_ID': 'review_count',
        'REVIEW_RATING': 'avg_rating',
        'is_rebuy': 'rebuy_count'
    })

    summary['rebuy_rate'] = summary['rebuy_count'] / summary['review_count'] * 100

    return summary.sort_values('review_count', ascending=False)
