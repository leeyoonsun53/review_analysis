"""
태그 추출 모듈
키워드 딕셔너리 기반으로 리뷰에서 태그 추출

v2.0 업데이트:
- 부정 문맥 내 태그 필터링
- 과거 사용 패턴 필터링
- 역접 패턴 후 태그 무효화
"""

import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.keywords import (
    BENEFIT_KEYWORDS, TEXTURE_KEYWORDS, USAGE_KEYWORDS, VALUE_KEYWORDS,
    REASON_BUY_KEYWORDS, REASON_REBUY_KEYWORDS,
    SKIN_DISEASE_KEYWORDS, ADVERSATIVE_PATTERNS,
    DISCONTINUE_KEYWORDS, NEGATIVE_CONTEXT_KEYWORDS,
    PAST_USAGE_PATTERNS
)


def is_negative_context(text):
    """
    부정 문맥인지 판단

    Returns:
        bool: 부정 문맥 여부
    """
    text = str(text).lower()

    # 피부질병 키워드 체크
    for kw in SKIN_DISEASE_KEYWORDS:
        if kw in text:
            return True

    # 중단 키워드 체크
    for kw in DISCONTINUE_KEYWORDS:
        if kw in text:
            return True

    # 부정 문맥 키워드 2개 이상
    neg_count = sum(1 for kw in NEGATIVE_CONTEXT_KEYWORDS if kw in text)
    if neg_count >= 2:
        return True

    return False


def has_adversative_negative(text):
    """
    역접 패턴 + 부정 결말인지 판단

    Returns:
        bool: 역접 후 부정 여부
    """
    text = str(text).lower()

    for pattern in ADVERSATIVE_PATTERNS:
        if pattern in text:
            parts = text.split(pattern, 1)
            if len(parts) == 2:
                after_text = parts[1]
                # 뒷부분에 부정 키워드가 있으면
                for kw in DISCONTINUE_KEYWORDS + NEGATIVE_CONTEXT_KEYWORDS:
                    if kw in after_text:
                        return True
                # 피부질병 키워드가 있으면
                for kw in SKIN_DISEASE_KEYWORDS:
                    if kw in after_text:
                        return True

    return False


def is_past_negative_usage(text):
    """
    과거 사용 + 현재 부정 패턴인지 판단

    Returns:
        bool: 과거에 썼지만 지금은 안 쓰는 패턴 여부
    """
    text = str(text).lower()

    has_past = any(p in text for p in PAST_USAGE_PATTERNS)
    has_negative = any(kw in text for kw in DISCONTINUE_KEYWORDS + NEGATIVE_CONTEXT_KEYWORDS)

    return has_past and has_negative


def extract_tags(text, keyword_dict):
    """
    키워드 딕셔너리를 기반으로 텍스트에서 태그 추출

    Args:
        text: 리뷰 텍스트
        keyword_dict: 키워드 딕셔너리

    Returns:
        list: 추출된 태그 리스트
    """
    text = str(text)
    found_tags = []

    for tag, keywords in keyword_dict.items():
        for kw in keywords:
            if kw in text:
                found_tags.append(tag)
                break  # 한 태그당 한 번만 추가

    return found_tags


def extract_tags_with_context(text, keyword_dict, check_negative=True):
    """
    문맥을 고려한 태그 추출

    Args:
        text: 리뷰 텍스트
        keyword_dict: 키워드 딕셔너리
        check_negative: 부정 문맥 체크 여부

    Returns:
        list: 추출된 태그 리스트
    """
    text = str(text)

    # 부정 문맥 체크
    if check_negative:
        if is_negative_context(text):
            return []  # 부정 문맥에서는 태그 추출 안함
        if has_adversative_negative(text):
            return []  # 역접 + 부정에서는 태그 추출 안함
        if is_past_negative_usage(text):
            return []  # 과거 사용 + 현재 부정에서는 태그 추출 안함

    return extract_tags(text, keyword_dict)


def extract_benefit_tags(text):
    """효능/기능 태그 추출"""
    return extract_tags(text, BENEFIT_KEYWORDS)


def extract_texture_tags(text):
    """사용감/제형 태그 추출"""
    return extract_tags(text, TEXTURE_KEYWORDS)


def extract_usage_tags(text):
    """사용법/역할 태그 추출 (문맥 고려)"""
    text = str(text)

    # 과거 사용 + 부정이면 사용법 태그 추출 안함
    if is_past_negative_usage(text):
        return []

    # 역접 + 부정이면 사용법 태그 추출 안함
    if has_adversative_negative(text):
        return []

    return extract_tags(text, USAGE_KEYWORDS)


def extract_value_tags(text):
    """가치/선택 이유 태그 추출 (문맥 고려)"""
    text = str(text)

    # 부정 문맥 체크 - 인생템 오탐 방지
    if is_negative_context(text):
        # 부정 문맥에서는 인생템, 재구매 태그 제외
        tags = extract_tags(text, VALUE_KEYWORDS)
        return [t for t in tags if t not in ['인생템']]

    if has_adversative_negative(text):
        tags = extract_tags(text, VALUE_KEYWORDS)
        return [t for t in tags if t not in ['인생템']]

    if is_past_negative_usage(text):
        # 과거 좋았지만 지금은 아닌 경우 인생템 제외
        tags = extract_tags(text, VALUE_KEYWORDS)
        return [t for t in tags if t not in ['인생템']]

    return extract_tags(text, VALUE_KEYWORDS)


def extract_reason_buy(text):
    """
    구매 이유 추출 (우선순위로 1개만)

    Args:
        text: 리뷰 텍스트

    Returns:
        str: 구매 이유
    """
    text = str(text)

    # 우선순위: 가성비 > 진정 > 보습 > 대용량
    priority_order = ["가성비", "진정", "보습", "대용량"]

    for reason in priority_order:
        keywords = REASON_BUY_KEYWORDS.get(reason, [])
        if any(kw in text for kw in keywords):
            return reason

    return "기타"


def extract_reason_rebuy(text, is_rebuy):
    """
    재구매 이유 추출

    Args:
        text: 리뷰 텍스트
        is_rebuy: 재구매 여부

    Returns:
        str: 재구매 이유
    """
    if not is_rebuy:
        return ""

    text = str(text)

    # 부정 문맥이면 재구매 이유 없음
    if is_negative_context(text) or has_adversative_negative(text):
        return ""

    # 우선순위: 효능 > 안전성 > 습관 > 가성비
    priority_order = ["효능", "안전성", "습관", "가성비"]

    for reason in priority_order:
        keywords = REASON_REBUY_KEYWORDS.get(reason, [])
        if any(kw in text for kw in keywords):
            return reason

    return "기타"


def extract_all_tags(df):
    """
    전체 데이터프레임에 태그 추출 적용

    Args:
        df: 데이터프레임

    Returns:
        pd.DataFrame: 태그 컬럼들이 추가된 데이터프레임
    """
    # 효능 태그 (부정 문맥에서도 추출 - 어떤 효능이 없는지 파악 필요)
    df['benefit_tags'] = df['REVIEW_CONTENT'].apply(extract_benefit_tags)

    # 사용감 태그 (부정 문맥에서도 추출)
    df['texture_tags'] = df['REVIEW_CONTENT'].apply(extract_texture_tags)

    # 사용법 태그 (문맥 고려)
    df['usage_tags'] = df['REVIEW_CONTENT'].apply(extract_usage_tags)

    # 가치 태그 (문맥 고려 - 인생템 오탐 방지)
    df['value_tags'] = df['REVIEW_CONTENT'].apply(extract_value_tags)

    # 구매 이유
    df['reason_buy'] = df['REVIEW_CONTENT'].apply(extract_reason_buy)

    # 재구매 이유 (문맥 고려)
    df['reason_rebuy'] = df.apply(
        lambda row: extract_reason_rebuy(row['REVIEW_CONTENT'], row['is_rebuy']),
        axis=1
    )

    # 부정 문맥 플래그 (분석용)
    df['is_negative_context'] = df['REVIEW_CONTENT'].apply(is_negative_context)
    df['has_adversative_negative'] = df['REVIEW_CONTENT'].apply(has_adversative_negative)
    df['is_past_negative_usage'] = df['REVIEW_CONTENT'].apply(is_past_negative_usage)

    return df
