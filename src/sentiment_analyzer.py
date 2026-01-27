"""
감성 분석 및 강도 분석 모듈

v2.0 업데이트:
- 역접 패턴 처리 (뒤 문장 가중치)
- 피부질병 키워드 탐지
- 중단/사용중지 키워드 탐지
- 별점-내용 불일치 보정 강화
"""

import pandas as pd
import re
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.keywords import (
    POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS,
    STRONG_MARKERS, WEAK_MARKERS,
    SKIN_DISEASE_KEYWORDS, ADVERSATIVE_PATTERNS,
    DISCONTINUE_KEYWORDS, NEGATIVE_CONTEXT_KEYWORDS,
    PAST_USAGE_PATTERNS
)


def split_by_adversative(text):
    """
    역접 패턴으로 문장 분리

    Returns:
        tuple: (앞부분, 뒷부분, 역접패턴 발견여부)
    """
    text = str(text)

    for pattern in ADVERSATIVE_PATTERNS:
        if pattern in text:
            parts = text.split(pattern, 1)
            if len(parts) == 2:
                return parts[0], parts[1], True

    return text, "", False


def check_skin_disease(text):
    """피부질병/부작용 키워드 체크"""
    text = str(text).lower()
    found = []
    for kw in SKIN_DISEASE_KEYWORDS:
        if kw in text:
            found.append(kw)
    return found


def check_discontinue(text):
    """중단/사용중지 키워드 체크"""
    text = str(text).lower()
    for kw in DISCONTINUE_KEYWORDS:
        if kw in text:
            return True
    return False


def check_negative_context(text):
    """부정 문맥 키워드 체크"""
    text = str(text).lower()
    count = 0
    for kw in NEGATIVE_CONTEXT_KEYWORDS:
        if kw in text:
            count += 1
    return count


def check_past_usage(text):
    """과거 사용 패턴 체크"""
    text = str(text).lower()
    for pattern in PAST_USAGE_PATTERNS:
        if pattern in text:
            return True
    return False


def analyze_sentiment(text, rating):
    """
    감성 분석 (별점 + 키워드 기반 + 문맥 분석)

    Args:
        text: 리뷰 텍스트
        rating: 별점 (1-5)

    Returns:
        str: POS/NEU/NEG
    """
    text = str(text).lower()

    # 1. 역접 패턴 분석 - 뒤 문장에 가중치
    before_text, after_text, has_adversative = split_by_adversative(text)

    # 역접 패턴이 있으면 뒤 문장을 주로 분석
    main_text = after_text if has_adversative and after_text else text

    # 2. 피부질병 체크 (가장 강력한 부정 신호)
    skin_issues = check_skin_disease(text)
    if skin_issues:
        # 피부질병 언급이 있으면 무조건 NEG
        return "NEG"

    # 3. 중단/사용중지 체크
    if check_discontinue(text):
        return "NEG"

    # 4. 부정 문맥 강도 체크
    neg_context_count = check_negative_context(main_text)

    # 5. 과거 사용 + 현재 부정 패턴 체크
    if check_past_usage(text) and neg_context_count >= 1:
        return "NEG"

    # 6. 키워드 기반 분석
    pos_count = sum(1 for w in POSITIVE_KEYWORDS if w in main_text)
    neg_count = sum(1 for w in NEGATIVE_KEYWORDS if w in main_text)

    # 역접 뒤에 부정 키워드가 있으면 부정으로 판정
    if has_adversative:
        after_neg = sum(1 for w in NEGATIVE_KEYWORDS if w in after_text)
        if after_neg >= 1:
            return "NEG"

    # 7. 별점 기반 1차 판정
    if rating >= 4:
        base_sentiment = "POS"
    elif rating <= 2:
        base_sentiment = "NEG"
    else:
        base_sentiment = "NEU"

    # 8. 별점-내용 불일치 보정 (강화)
    # 부정 키워드가 긍정보다 많으면 별점과 관계없이 보정
    if neg_count > pos_count and neg_count >= 2:
        if base_sentiment == "POS":
            return "NEG"  # 강한 부정은 NEG로
        return "NEU"

    # 부정 문맥이 강하면 보정
    if neg_context_count >= 2 and base_sentiment == "POS":
        return "NEU"

    # 강한 부정 키워드가 있으면 보정
    if neg_count >= 2 and base_sentiment == "POS":
        return "NEU"

    # 별점 3점이지만 긍정 키워드가 많으면 보정
    if pos_count >= 2 and neg_count == 0 and base_sentiment == "NEU":
        return "POS"

    return base_sentiment


def analyze_sentiment_detail(text, rating):
    """
    상세 감성 분석 (디버깅/분석용)

    Returns:
        dict: 분석 상세 결과
    """
    text = str(text).lower()

    before_text, after_text, has_adversative = split_by_adversative(text)
    skin_issues = check_skin_disease(text)
    is_discontinue = check_discontinue(text)
    neg_context_count = check_negative_context(text)
    is_past_usage = check_past_usage(text)

    pos_count = sum(1 for w in POSITIVE_KEYWORDS if w in text)
    neg_count = sum(1 for w in NEGATIVE_KEYWORDS if w in text)

    sentiment = analyze_sentiment(text, rating)

    return {
        'sentiment': sentiment,
        'rating': rating,
        'has_adversative': has_adversative,
        'skin_issues': skin_issues,
        'is_discontinue': is_discontinue,
        'neg_context_count': neg_context_count,
        'is_past_usage': is_past_usage,
        'pos_keyword_count': pos_count,
        'neg_keyword_count': neg_count
    }


def analyze_strength(text):
    """
    감성 강도 분석

    Args:
        text: 리뷰 텍스트

    Returns:
        str: STRONG/MID/WEAK
    """
    text = str(text)

    # STRONG 마커 체크
    strong_count = sum(1 for m in STRONG_MARKERS if m in text)

    # WEAK 마커 체크
    weak_count = sum(1 for m in WEAK_MARKERS if m in text)

    # 부정 문맥에서는 STRONG 판정 제외
    neg_context = check_negative_context(text.lower())
    is_discontinue = check_discontinue(text.lower())

    if neg_context >= 1 or is_discontinue:
        # 부정 문맥에서 인생템 등이 나와도 STRONG 아님
        if weak_count >= 1:
            return "WEAK"
        return "MID"

    # 강한 표현이 2개 이상이거나 특정 키워드 포함
    if strong_count >= 2 or any(m in text for m in ["인생템", "미쳤", "레전드"]):
        return "STRONG"

    # 약한 표현이 있으면
    if weak_count >= 1:
        return "WEAK"

    return "MID"


def analyze_all_sentiments(df):
    """
    전체 데이터프레임에 감성/강도 분석 적용

    Args:
        df: 데이터프레임

    Returns:
        pd.DataFrame: sentiment, strength 컬럼이 추가된 데이터프레임
    """
    # 감성 분석
    df['sentiment'] = df.apply(
        lambda row: analyze_sentiment(row['REVIEW_CONTENT'], row['REVIEW_RATING']),
        axis=1
    )

    # 강도 분석
    df['strength'] = df['REVIEW_CONTENT'].apply(analyze_strength)

    # 피부질병 발견 여부 (분석용)
    df['has_skin_issue'] = df['REVIEW_CONTENT'].apply(
        lambda x: len(check_skin_disease(str(x))) > 0
    )

    # 역접 패턴 발견 여부 (분석용)
    df['has_adversative'] = df['REVIEW_CONTENT'].apply(
        lambda x: split_by_adversative(str(x))[2]
    )

    return df
