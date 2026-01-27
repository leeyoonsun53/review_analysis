"""
3-E: 고객 전환 시나리오 분석 모듈
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# 한글 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False


def build_switch_matrix(df):
    """
    브랜드 간 전환 매트릭스 생성

    Args:
        df: 데이터프레임

    Returns:
        pd.DataFrame: 전환 매트릭스
    """
    # 전환 신호가 있는 리뷰만 필터
    switch_df = df[(df['switch_signal'] == 1) & (df['switch_to_brand'] != '')].copy()

    if len(switch_df) == 0:
        return pd.DataFrame()

    # 전환 방향 집계
    matrix = pd.crosstab(
        switch_df['BRAND_NAME'],  # From
        switch_df['switch_to_brand'],  # To
        margins=True
    )

    return matrix


def analyze_switch_reasons(df):
    """
    전환 이유 분석

    Args:
        df: 데이터프레임

    Returns:
        dict: 브랜드별 전환 이유 분석
    """
    switch_df = df[df['switch_signal'] == 1].copy()

    results = {}

    for brand in switch_df['BRAND_NAME'].unique():
        brand_switch = switch_df[switch_df['BRAND_NAME'] == brand]

        # 전환 리뷰에서의 value_tags 분석 (무난/애매가 많으면 효능 부족으로 이탈)
        value_tags = []
        for tags in brand_switch['value_tags']:
            if isinstance(tags, list):
                value_tags.extend(tags)

        from collections import Counter
        tag_counts = Counter(value_tags)

        results[brand] = {
            'switch_count': len(brand_switch),
            'main_switch_reasons': dict(tag_counts.most_common(3))
        }

    return results


def plot_switch_heatmap(matrix_df, save_path=None):
    """
    전환 매트릭스 히트맵

    Args:
        matrix_df: 전환 매트릭스 데이터프레임
        save_path: 저장 경로 (optional)

    Returns:
        matplotlib.figure.Figure
    """
    if matrix_df.empty:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, '전환 데이터가 없습니다', ha='center', va='center', fontsize=14)
        ax.set_title('브랜드 간 고객 전환 매트릭스', fontsize=14, fontweight='bold')
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
        return fig

    # All 행/열 제외
    plot_df = matrix_df.drop('All', axis=0, errors='ignore').drop('All', axis=1, errors='ignore')

    fig, ax = plt.subplots(figsize=(12, 10))

    sns.heatmap(
        plot_df,
        annot=True,
        fmt='d',
        cmap='YlOrRd',
        ax=ax,
        cbar_kws={'label': '전환 리뷰 수'}
    )

    ax.set_xlabel('전환 대상 브랜드 (To)', fontsize=12)
    ax.set_ylabel('원래 브랜드 (From)', fontsize=12)
    ax.set_title('브랜드 간 고객 전환 매트릭스', fontsize=14, fontweight='bold')

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def generate_switch_narrative(from_brand, to_brand, from_tags, to_tags):
    """
    전환 시나리오 문장 생성

    Args:
        from_brand: 출발 브랜드
        to_brand: 도착 브랜드
        from_tags: 출발 브랜드 특성
        to_tags: 도착 브랜드 특성

    Returns:
        str: 전환 시나리오 문장
    """
    from_desc = '/'.join(from_tags[:2]) if from_tags else '일반'
    to_desc = '/'.join(to_tags[:2]) if to_tags else '일반'

    return f"{from_brand}({from_desc}) → {to_brand}({to_desc})"


def get_switch_insights(df, switch_matrix):
    """
    전환 분석 인사이트 생성

    Args:
        df: 전체 데이터프레임
        switch_matrix: 전환 매트릭스

    Returns:
        dict: 인사이트 딕셔너리
    """
    insights = {
        'total_switch_signals': df['switch_signal'].sum(),
        'switch_rate': df['switch_signal'].mean() * 100,
        'narratives': []
    }

    if switch_matrix.empty:
        insights['message'] = "전환 신호가 감지된 리뷰가 없습니다."
        return insights

    # 전환이 많은 패턴 찾기
    switch_df = df[(df['switch_signal'] == 1) & (df['switch_to_brand'] != '')].copy()

    if len(switch_df) > 0:
        # 가장 많은 전환 패턴
        patterns = switch_df.groupby(['BRAND_NAME', 'switch_to_brand']).size()
        if len(patterns) > 0:
            top_patterns = patterns.nlargest(3)

            for (from_brand, to_brand), count in top_patterns.items():
                narrative = f"{from_brand} → {to_brand} ({count}건)"
                insights['narratives'].append(narrative)

    return insights


def print_switch_analysis(insights):
    """
    전환 분석 결과 출력

    Args:
        insights: 인사이트 딕셔너리
    """
    print("\n" + "=" * 60)
    print("고객 전환 시나리오 분석")
    print("=" * 60)

    print(f"\n전환 신호 감지 리뷰: {insights['total_switch_signals']}건")
    print(f"전체 대비 비율: {insights['switch_rate']:.2f}%")

    if insights['narratives']:
        print("\n주요 전환 패턴:")
        for narrative in insights['narratives']:
            print(f"  - {narrative}")
    else:
        print("\n" + insights.get('message', '전환 패턴이 없습니다.'))

    print("\n" + "=" * 60)
