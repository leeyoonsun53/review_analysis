"""
전환 신호 탐지 모듈
리뷰에서 브랜드 전환 신호 및 타겟 브랜드 추출
"""

import pandas as pd
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.keywords import SWITCH_KEYWORDS, COMPETITOR_BRANDS


def detect_switch_signal(text):
    """
    전환 신호 탐지

    Args:
        text: 리뷰 텍스트

    Returns:
        int: 1 if switch signal detected, 0 otherwise
    """
    text = str(text)

    has_signal = any(kw in text for kw in SWITCH_KEYWORDS)

    return 1 if has_signal else 0


def extract_switch_brand(text):
    """
    전환 대상 브랜드 추출

    Args:
        text: 리뷰 텍스트

    Returns:
        str: 타겟 브랜드명 또는 빈 문자열
    """
    text = str(text)

    for brand in COMPETITOR_BRANDS:
        if brand in text:
            return brand

    return ""


def detect_all_switches(df):
    """
    전체 데이터프레임에 전환 신호 탐지 적용

    Args:
        df: 데이터프레임

    Returns:
        pd.DataFrame: switch_signal, switch_to_brand 컬럼이 추가된 데이터프레임
    """
    # 전환 신호
    df['switch_signal'] = df['REVIEW_CONTENT'].apply(detect_switch_signal)

    # 전환 대상 브랜드
    df['switch_to_brand'] = df['REVIEW_CONTENT'].apply(extract_switch_brand)

    return df
