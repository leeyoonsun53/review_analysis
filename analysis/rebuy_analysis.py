"""
3-D: 재구매 이유 분석 모듈
"""

import pandas as pd
import matplotlib.pyplot as plt
import platform

# 한글 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False


def analyze_rebuy_reasons(df):
    """
    브랜드별 재구매 이유 집계

    Args:
        df: 데이터프레임

    Returns:
        dict: 브랜드별 재구매 이유 카운트
    """
    # 재구매 리뷰만 필터
    rebuy_df = df[df['is_rebuy'] == True].copy()

    results = {}

    for brand in rebuy_df['BRAND_NAME'].unique():
        brand_df = rebuy_df[rebuy_df['BRAND_NAME'] == brand]

        # 재구매 이유 집계 (빈 문자열 제외)
        reason_counts = brand_df[brand_df['reason_rebuy'] != '']['reason_rebuy'].value_counts()

        if len(reason_counts) > 0:
            results[brand] = reason_counts.to_dict()

    return results


def analyze_strong_rebuy(df):
    """
    STRONG 감성 리뷰에서의 재구매 이유 분석 (진짜 팬덤)

    Args:
        df: 데이터프레임

    Returns:
        pd.DataFrame: STRONG 재구매 이유 분석 결과
    """
    strong_rebuy = df[(df['strength'] == 'STRONG') & (df['is_rebuy'] == True)].copy()

    if len(strong_rebuy) == 0:
        return pd.DataFrame()

    result = strong_rebuy.groupby('BRAND_NAME')['reason_rebuy'].value_counts().unstack(fill_value=0)

    return result


def plot_rebuy_pie(rebuy_data, brand, save_path=None):
    """
    재구매 이유 파이차트

    Args:
        rebuy_data: 재구매 이유 딕셔너리
        brand: 브랜드명
        save_path: 저장 경로 (optional)

    Returns:
        matplotlib.figure.Figure
    """
    if not rebuy_data:
        return None

    fig, ax = plt.subplots(figsize=(8, 8))

    labels = list(rebuy_data.keys())
    sizes = list(rebuy_data.values())
    colors = ['#3498db', '#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6']

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors[:len(labels)],
        autopct='%1.1f%%',
        startangle=90,
        pctdistance=0.75
    )

    # 텍스트 스타일
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')

    ax.set_title(f'{brand} 재구매 이유 분포', fontsize=14, fontweight='bold')

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def plot_rebuy_comparison(rebuy_results, save_path=None):
    """
    브랜드별 재구매 이유 비교 막대 그래프

    Args:
        rebuy_results: 브랜드별 재구매 이유 딕셔너리
        save_path: 저장 경로 (optional)

    Returns:
        matplotlib.figure.Figure
    """
    # 데이터 정리
    all_reasons = set()
    for reasons in rebuy_results.values():
        all_reasons.update(reasons.keys())

    df_data = []
    for brand, reasons in rebuy_results.items():
        row = {'brand': brand}
        for reason in all_reasons:
            row[reason] = reasons.get(reason, 0)
        df_data.append(row)

    df = pd.DataFrame(df_data)

    if len(df) == 0:
        return None

    # 그래프 생성
    fig, ax = plt.subplots(figsize=(12, 6))

    reasons_cols = [col for col in df.columns if col != 'brand']
    x = range(len(df))
    width = 0.15

    colors = ['#3498db', '#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6']

    for i, reason in enumerate(reasons_cols):
        offset = (i - len(reasons_cols)/2 + 0.5) * width
        ax.bar([xi + offset for xi in x], df[reason], width, label=reason, color=colors[i % len(colors)])

    ax.set_xlabel('브랜드', fontsize=12)
    ax.set_ylabel('리뷰 수', fontsize=12)
    ax.set_title('브랜드별 재구매 이유 비교', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(df['brand'], rotation=45, ha='right')
    ax.legend()

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def get_rebuy_insights(rebuy_results, df):
    """
    재구매 분석 인사이트 생성

    Args:
        rebuy_results: 재구매 이유 분석 결과
        df: 전체 데이터프레임

    Returns:
        dict: 인사이트 딕셔너리
    """
    insights = {}

    for brand, reasons in rebuy_results.items():
        total = sum(reasons.values())
        if total == 0:
            continue

        # 주요 재구매 이유
        top_reason = max(reasons, key=reasons.get)
        top_rate = reasons[top_reason] / total * 100

        # 해석
        if top_reason in ['습관', '가성비']:
            interpretation = "성장 정체 가능성 (습관적 구매)"
        elif top_reason in ['효능', '안전성']:
            interpretation = "팬덤/확장 가능 (효능 체감 구매)"
        else:
            interpretation = "다양한 이유로 재구매"

        insights[brand] = {
            'top_reason': top_reason,
            'top_rate': top_rate,
            'interpretation': interpretation
        }

    return insights
