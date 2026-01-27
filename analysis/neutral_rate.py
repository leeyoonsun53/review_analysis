"""
3-A: 무난/애매 점유율 분석 모듈
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform

# 한글 폰트 설정
if platform.system() == 'Windows':
    plt.rcParams['font.family'] = 'Malgun Gothic'
elif platform.system() == 'Darwin':
    plt.rcParams['font.family'] = 'AppleGothic'
else:
    plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

# 무난/애매 키워드 정의
NEUTRAL_KEYWORDS = ["무난", "그냥", "평범", "무탈", "데일리", "무조건", "무색무취", "기본"]
AMBIGUOUS_KEYWORDS = ["애매", "모르겠", "효과없", "잘모르", "느낌없", "밍밍", "별로", "글쎄"]


def calculate_neutral_rates(df):
    """
    브랜드별 무난/애매 키워드 점유율 계산

    Args:
        df: 데이터프레임

    Returns:
        pd.DataFrame: 브랜드별 점유율 결과
    """
    results = []

    for brand in df['BRAND_NAME'].unique():
        brand_df = df[df['BRAND_NAME'] == brand]
        total = len(brand_df)

        # 무난 키워드 포함 리뷰 수
        neutral_count = brand_df['REVIEW_CONTENT'].apply(
            lambda x: any(kw in str(x) for kw in NEUTRAL_KEYWORDS)
        ).sum()

        # 애매 키워드 포함 리뷰 수
        ambiguous_count = brand_df['REVIEW_CONTENT'].apply(
            lambda x: any(kw in str(x) for kw in AMBIGUOUS_KEYWORDS)
        ).sum()

        results.append({
            'brand': brand,
            'total_reviews': total,
            'neutral_count': neutral_count,
            'ambiguous_count': ambiguous_count,
            'neutral_rate': neutral_count / total * 100 if total > 0 else 0,
            'ambiguous_rate': ambiguous_count / total * 100 if total > 0 else 0,
            'total_neutral_rate': (neutral_count + ambiguous_count) / total * 100 if total > 0 else 0
        })

    return pd.DataFrame(results).sort_values('total_neutral_rate', ascending=False)


def plot_neutral_rate_comparison(neutral_df, save_path=None):
    """
    무난/애매 점유율 비교 막대 그래프

    Args:
        neutral_df: 점유율 데이터프레임
        save_path: 저장 경로 (optional)

    Returns:
        matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(neutral_df))
    width = 0.35

    bars1 = ax.bar([i - width/2 for i in x], neutral_df['neutral_rate'],
                   width, label='무난', color='#3498db', alpha=0.8)
    bars2 = ax.bar([i + width/2 for i in x], neutral_df['ambiguous_rate'],
                   width, label='애매', color='#e74c3c', alpha=0.8)

    ax.set_xlabel('브랜드', fontsize=12)
    ax.set_ylabel('점유율 (%)', fontsize=12)
    ax.set_title('브랜드별 무난/애매 키워드 점유율', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(neutral_df['brand'], rotation=45, ha='right')
    ax.legend()

    # 값 표시
    for bar in bars1:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8)

    for bar in bars2:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def get_neutral_insights(neutral_df):
    """
    무난/애매 분석 인사이트 생성

    Args:
        neutral_df: 점유율 데이터프레임

    Returns:
        dict: 인사이트 딕셔너리
    """
    insights = {}

    # 무난 점유율 최고/최저 브랜드
    max_neutral = neutral_df.loc[neutral_df['neutral_rate'].idxmax()]
    min_neutral = neutral_df.loc[neutral_df['neutral_rate'].idxmin()]

    insights['highest_neutral'] = {
        'brand': max_neutral['brand'],
        'rate': max_neutral['neutral_rate'],
        'interpretation': f"{max_neutral['brand']}: 무난↑ → 차별성 약화 가능성"
    }

    insights['lowest_neutral'] = {
        'brand': min_neutral['brand'],
        'rate': min_neutral['neutral_rate'],
        'interpretation': f"{min_neutral['brand']}: 무난↓ → 뚜렷한 특성 보유"
    }

    # 애매 점유율 최고 브랜드
    max_ambiguous = neutral_df.loc[neutral_df['ambiguous_rate'].idxmax()]
    insights['highest_ambiguous'] = {
        'brand': max_ambiguous['brand'],
        'rate': max_ambiguous['ambiguous_rate'],
        'interpretation': f"{max_ambiguous['brand']}: 애매↑ → 효능 인지 부족"
    }

    return insights
