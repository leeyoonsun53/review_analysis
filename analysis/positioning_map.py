"""
3-B: 키워드 포지셔닝 맵 모듈
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


def calculate_positioning_scores(df):
    """
    브랜드별 키워드 언급률 계산

    Args:
        df: 데이터프레임

    Returns:
        pd.DataFrame: 브랜드별 언급률 데이터
    """
    positions = []

    for brand in df['BRAND_NAME'].unique():
        brand_df = df[df['BRAND_NAME'] == brand]
        total = len(brand_df)

        # 효능 축 언급률
        def has_tag(tags, target):
            if isinstance(tags, list):
                return target in tags
            return False

        진정_rate = brand_df['benefit_tags'].apply(lambda x: has_tag(x, '진정')).mean() * 100
        보습_rate = brand_df['benefit_tags'].apply(lambda x: has_tag(x, '보습')).mean() * 100
        장벽_rate = brand_df['benefit_tags'].apply(lambda x: has_tag(x, '장벽')).mean() * 100
        결_rate = brand_df['benefit_tags'].apply(lambda x: has_tag(x, '결')).mean() * 100
        피지_rate = brand_df['benefit_tags'].apply(lambda x: has_tag(x, '피지')).mean() * 100

        # 사용감 축 언급률
        물같음_rate = brand_df['texture_tags'].apply(lambda x: has_tag(x, '물같음')).mean() * 100
        쫀쫀_rate = brand_df['texture_tags'].apply(lambda x: has_tag(x, '쫀쫀')).mean() * 100
        끈적_rate = brand_df['texture_tags'].apply(lambda x: has_tag(x, '끈적')).mean() * 100
        흡수_rate = brand_df['texture_tags'].apply(lambda x: has_tag(x, '흡수')).mean() * 100

        # 사용법 축 언급률
        닦토_rate = brand_df['usage_tags'].apply(lambda x: has_tag(x, '닦토')).mean() * 100
        스킨팩_rate = brand_df['usage_tags'].apply(lambda x: has_tag(x, '스킨팩')).mean() * 100
        레이어링_rate = brand_df['usage_tags'].apply(lambda x: has_tag(x, '레이어링')).mean() * 100

        positions.append({
            'brand': brand,
            'total_reviews': total,
            # 효능
            '진정': 진정_rate,
            '보습': 보습_rate,
            '장벽': 장벽_rate,
            '결': 결_rate,
            '피지': 피지_rate,
            # 사용감
            '물같음': 물같음_rate,
            '쫀쫀': 쫀쫀_rate,
            '끈적': 끈적_rate,
            '흡수': 흡수_rate,
            # 사용법
            '닦토': 닦토_rate,
            '스킨팩': 스킨팩_rate,
            '레이어링': 레이어링_rate
        })

    return pd.DataFrame(positions)


def plot_positioning_map(positions_df, x_col, y_col, title, save_path=None):
    """
    2D 포지셔닝 맵 생성

    Args:
        positions_df: 포지셔닝 데이터프레임
        x_col: X축 컬럼명
        y_col: Y축 컬럼명
        title: 차트 제목
        save_path: 저장 경로 (optional)

    Returns:
        matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    # 색상 팔레트
    colors = plt.cm.Set2(range(len(positions_df)))

    # 산점도
    for idx, row in positions_df.iterrows():
        ax.scatter(row[x_col], row[y_col], s=300, c=[colors[idx]], alpha=0.7, edgecolors='black', linewidth=1)
        ax.annotate(row['brand'],
                    (row[x_col], row[y_col]),
                    fontsize=11,
                    ha='center',
                    va='bottom',
                    xytext=(0, 10),
                    textcoords='offset points',
                    fontweight='bold')

    # 평균선 (사분면 구분)
    x_mean = positions_df[x_col].mean()
    y_mean = positions_df[y_col].mean()

    ax.axhline(y=y_mean, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.axvline(x=x_mean, color='gray', linestyle='--', alpha=0.5, linewidth=1)

    # 사분면 라벨
    ax.text(positions_df[x_col].max() * 0.9, positions_df[y_col].max() * 0.9,
            f'{x_col}↑ {y_col}↑', fontsize=9, alpha=0.7, ha='right')
    ax.text(positions_df[x_col].min() * 1.1, positions_df[y_col].max() * 0.9,
            f'{x_col}↓ {y_col}↑', fontsize=9, alpha=0.7, ha='left')
    ax.text(positions_df[x_col].max() * 0.9, positions_df[y_col].min() * 1.1,
            f'{x_col}↑ {y_col}↓', fontsize=9, alpha=0.7, ha='right')
    ax.text(positions_df[x_col].min() * 1.1, positions_df[y_col].min() * 1.1,
            f'{x_col}↓ {y_col}↓', fontsize=9, alpha=0.7, ha='left')

    ax.set_xlabel(f'{x_col} 언급률 (%)', fontsize=12)
    ax.set_ylabel(f'{y_col} 언급률 (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')

    # 축 범위 여유 추가
    x_range = positions_df[x_col].max() - positions_df[x_col].min()
    y_range = positions_df[y_col].max() - positions_df[y_col].min()
    ax.set_xlim(positions_df[x_col].min() - x_range * 0.1, positions_df[x_col].max() + x_range * 0.1)
    ax.set_ylim(positions_df[y_col].min() - y_range * 0.1, positions_df[y_col].max() + y_range * 0.1)

    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def get_positioning_insights(positions_df):
    """
    포지셔닝 맵 인사이트 생성

    Args:
        positions_df: 포지셔닝 데이터프레임

    Returns:
        dict: 인사이트 딕셔너리
    """
    insights = {}

    # 효능 축 대표 브랜드
    insights['진정_leader'] = positions_df.loc[positions_df['진정'].idxmax(), 'brand']
    insights['보습_leader'] = positions_df.loc[positions_df['보습'].idxmax(), 'brand']

    # 사용감 축 대표 브랜드
    insights['물같음_leader'] = positions_df.loc[positions_df['물같음'].idxmax(), 'brand']
    insights['쫀쫀_leader'] = positions_df.loc[positions_df['쫀쫀'].idxmax(), 'brand']

    # 사용법 축 대표 브랜드
    insights['닦토_leader'] = positions_df.loc[positions_df['닦토'].idxmax(), 'brand']

    return insights
