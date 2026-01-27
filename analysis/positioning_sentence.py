"""
3-C: 포지셔닝 문장 자동 생성 모듈
"""

import pandas as pd
from collections import Counter


def get_top_tags(tag_series, n=2):
    """
    태그 리스트에서 가장 많이 등장한 태그 추출

    Args:
        tag_series: 태그 리스트의 Series
        n: 추출할 태그 수

    Returns:
        list: 상위 n개 태그
    """
    all_tags = []
    for tags in tag_series:
        if isinstance(tags, list):
            all_tags.extend(tags)

    if not all_tags:
        return []

    counter = Counter(all_tags)
    return [tag for tag, _ in counter.most_common(n)]


def get_top_skin_type(brand_df):
    """
    브랜드 리뷰에서 가장 많이 언급된 피부타입 추출

    Args:
        brand_df: 브랜드별 데이터프레임

    Returns:
        str: 대표 피부타입
    """
    skin_types = brand_df['피부타입'].value_counts()

    if len(skin_types) == 0 or skin_types.index[0] == '':
        return "모든피부"

    # 첫 번째 결과에서 핵심 단어 추출
    top_skin = skin_types.index[0]

    # "~에 좋아요" 패턴 정리
    if '좋아요' in top_skin:
        top_skin = top_skin.replace('에 좋아요', '').strip()

    return top_skin if top_skin else "모든피부"


def generate_positioning_sentence(brand, brand_df):
    """
    브랜드별 포지셔닝 문장 생성

    템플릿: "{타겟피부/상황}이 {핵심효능}을 위해 쓰는 {사용역할} 토너"

    Args:
        brand: 브랜드명
        brand_df: 브랜드별 데이터프레임

    Returns:
        str: 포지셔닝 문장
    """
    # 타겟 피부
    target_skin = get_top_skin_type(brand_df)

    # 핵심 효능 (benefit_tags Top 2)
    top_benefits = get_top_tags(brand_df['benefit_tags'], n=2)
    if top_benefits:
        핵심효능 = '/'.join(top_benefits)
    else:
        핵심효능 = "보습"

    # 사용 역할 (usage_tags Top 1)
    top_usage = get_top_tags(brand_df['usage_tags'], n=1)
    if top_usage:
        사용역할 = top_usage[0]
    else:
        사용역할 = "데일리"

    # 문장 생성
    sentence = f"{target_skin}이 {핵심효능}을 위해 쓰는 {사용역할} 토너"

    return sentence


def generate_all_sentences(df):
    """
    전체 브랜드에 대한 포지셔닝 문장 생성

    Args:
        df: 전체 데이터프레임

    Returns:
        dict: 브랜드별 포지셔닝 문장
    """
    sentences = {}

    for brand in df['BRAND_NAME'].unique():
        brand_df = df[df['BRAND_NAME'] == brand]
        sentence = generate_positioning_sentence(brand, brand_df)
        sentences[brand] = sentence

    return sentences


def print_positioning_sentences(sentences):
    """
    포지셔닝 문장 출력

    Args:
        sentences: 브랜드별 문장 딕셔너리
    """
    print("\n" + "=" * 60)
    print("브랜드별 포지셔닝 문장")
    print("=" * 60)

    for brand, sentence in sentences.items():
        print(f"\n{brand}:")
        print(f"  \"{sentence}\"")

    print("\n" + "=" * 60)
