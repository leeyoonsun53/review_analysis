# -*- coding: utf-8 -*-
"""
토너 리뷰 분석 대시보드
올리브영 + 무신사 통합 버전
"""
import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import Counter
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="토너 리뷰 분석",
    page_icon="🧴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        border-bottom: 2px solid #667eea;
        padding-bottom: 0.5rem;
        margin: 1.5rem 0 1rem 0;
    }
    .platform-oliveyoung {
        background-color: #00a862;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .platform-musinsa {
        background-color: #000000;
        color: white;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ===== 데이터 로드 =====
@st.cache_data
def load_data():
    """통합 데이터 로드 및 전처리"""
    # 전처리된 통합 데이터 로드
    data_path = Path("data/merged_reviews_processed.csv")

    if not data_path.exists():
        # 기존 올리브영 데이터로 폴백
        json_path = Path("data/올영리뷰데이터_utf8.json")
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            first_key = list(data.keys())[0]
            df = pd.DataFrame(data[first_key])
            df['PLATFORM'] = '올리브영'
        else:
            st.error("데이터 파일을 찾을 수 없습니다.")
            return None
    else:
        df = pd.read_csv(data_path, encoding='utf-8-sig')

    # 날짜 파싱
    df['review_date'] = pd.to_datetime(df['REVIEW_DATE'], errors='coerce')
    df['year_month'] = df['review_date'].dt.to_period('M').astype(str)

    # 감성 분석 (v2.0 로직)
    df = analyze_sentiment_v2(df)

    # 태그 추출
    df = extract_tags(df)

    return df

# ===== v2.0 분석 로직 =====
SKIN_DISEASE_KEYWORDS = [
    "모낭염", "알러지", "알레르기", "두드러기", "습진", "아토피",
    "뾰루지", "좁쌀", "여드름", "피부염", "발진", "각질염",
    "따가움", "화끈거림", "쓰라림", "가려움", "붓기", "부어",
    "홍조", "붉어짐", "껍질", "벗겨", "진물", "딱지"
]

ADVERSATIVE_PATTERNS = [
    "했었으나", "였으나", "었으나", "지만", "는데", "했는데",
    "였는데", "었는데", "했더니", "써봤는데", "썼는데", "썼더니",
    "좋았는데", "샀는데", "했다가", "쓰다가", "쓰다보니"
]

DISCONTINUE_KEYWORDS = [
    "중단", "안써", "안쓰", "못써", "못쓰", "버렸", "버림",
    "폐기", "처분", "던져", "방치", "안바", "그만", "멈춤"
]

NEGATIVE_KEYWORDS = [
    "별로", "실망", "안맞", "후회", "싫", "최악", "안좋", "못써", "버림",
    "환불", "폐기", "실패", "트러블", "뾰루지", "돈아까", "중단", "안써",
    "그만뒀", "올라왔", "올라와", "생겼", "났어", "났네", "심해졌"
]

POSITIVE_KEYWORDS = [
    "좋아", "최고", "만족", "추천", "대박", "미쳤", "사랑", "짱", "굿", "좋음",
    "완전", "너무좋", "진짜좋", "최애", "강추", "존좋"
]

PAIN_KEYWORDS = {
    '자극/트러블': ['자극', '따가', '따끔', '트러블', '뾰루지', '올라', '붉', '화끈', '쓰라', '알러지', '예민'],
    '보습부족': ['건조', '당김', '속건조', '갈라', '각질', '푸석'],
    '끈적/무거움': ['끈적', '답답', '무거', '기름', '번들', '텁텁'],
    '효과없음': ['효과없', '모르겠', '별로', '그냥', '평범', '밍밍', '애매'],
    '향/냄새': ['향', '냄새', '냄시', '알코올'],
    '가격': ['비싸', '가격', '비쌈'],
}

BENEFIT_KEYWORDS = {
    "진정": ["어성초", "트러블", "붉은기", "진정", "쿨링", "가라앉", "자극없", "순한", "민감"],
    "보습": ["속건조", "수분", "당김", "보습", "촉촉", "건조", "수분감"],
    "장벽": ["장벽", "시카", "회복", "재생", "마데카", "피부장벽"],
    "결": ["각질", "피부결", "매끈", "결정돈", "부드러"],
    "피지": ["지성", "번들", "기름", "유분", "피지", "산뜻"]
}

def check_skin_disease(text):
    text = str(text).lower()
    found = []
    for kw in SKIN_DISEASE_KEYWORDS:
        if kw in text:
            found.append(kw)
    return found

IMPROVEMENT_PATTERNS = [
    "들어가", "들어갔", "없어", "사라", "좋아졌", "나아", "진정됐", "진정됬",
    "진정되", "가라앉", "줄었", "줄어", "완화", "개선", "호전", "깨끗",
    "맑아", "좋아요", "좋아서", "추천", "잘맞", "잘 맞", "피부에 좋"
]

def is_skin_issue_improvement(text):
    text = str(text).lower()
    for pattern in IMPROVEMENT_PATTERNS:
        if pattern in text:
            return True
    return False

def check_discontinue(text):
    text = str(text).lower()
    for kw in DISCONTINUE_KEYWORDS:
        if kw in text:
            return True
    return False

def has_adversative_negative(text):
    text = str(text).lower()
    for pattern in ADVERSATIVE_PATTERNS:
        if pattern in text:
            parts = text.split(pattern, 1)
            if len(parts) == 2:
                after = parts[1]
                for kw in DISCONTINUE_KEYWORDS + NEGATIVE_KEYWORDS:
                    if kw in after:
                        return True
    return False

def analyze_sentiment_v2(df):
    """v2.0 감성 분석"""
    def get_sentiment(row):
        text = str(row['REVIEW_CONTENT']).lower()
        rating = row['REVIEW_RATING']

        skin_issues = check_skin_disease(text)
        if skin_issues:
            if not is_skin_issue_improvement(text):
                return "NEG"

        if check_discontinue(text):
            return "NEG"
        if has_adversative_negative(text):
            return "NEG"

        neg_count = sum(1 for w in NEGATIVE_KEYWORDS if w in text)
        pos_count = sum(1 for w in POSITIVE_KEYWORDS if w in text)

        if rating >= 4:
            base = "POS"
        elif rating <= 2:
            base = "NEG"
        else:
            base = "NEU"

        if neg_count >= 2 and base == "POS":
            return "NEU"
        if neg_count > pos_count and neg_count >= 2:
            return "NEG"

        return base

    df['sentiment'] = df.apply(get_sentiment, axis=1)
    df['has_skin_issue'] = df['REVIEW_CONTENT'].apply(
        lambda x: len(check_skin_disease(str(x))) > 0 and not is_skin_issue_improvement(str(x))
    )

    return df

def extract_tags(df):
    """태그 추출"""
    def get_pain_points(text):
        text = str(text).lower()
        found = []
        for cat, keywords in PAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    found.append(cat)
                    break
        return found

    def get_benefits(text):
        text = str(text).lower()
        found = []
        for cat, keywords in BENEFIT_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    found.append(cat)
                    break
        return found

    df['pain_points'] = df['REVIEW_CONTENT'].apply(get_pain_points)
    df['benefits'] = df['REVIEW_CONTENT'].apply(get_benefits)

    return df

# ===== 메인 앱 =====
def main():
    # 헤더
    st.markdown('<p class="main-header">🧴 토너 리뷰 분석 대시보드</p>', unsafe_allow_html=True)

    # 데이터 로드
    df = load_data()

    if df is None:
        st.stop()

    # 플랫폼 정보 표시
    platforms = df['PLATFORM'].unique().tolist()
    total_reviews = len(df)
    platform_info = " | ".join([f"{p}: {len(df[df['PLATFORM']==p]):,}건" for p in platforms])
    st.markdown(f'<p style="text-align: center; color: gray;">v2.0 | {platform_info} | 총 {total_reviews:,}건</p>', unsafe_allow_html=True)

    # ===== 사이드바 필터 =====
    st.sidebar.header("🔍 필터")

    # 플랫폼 필터
    selected_platforms = st.sidebar.multiselect(
        "플랫폼 선택",
        options=platforms,
        default=platforms
    )

    if selected_platforms:
        df_filtered = df[df['PLATFORM'].isin(selected_platforms)]
    else:
        df_filtered = df

    # 날짜 범위 필터
    valid_dates = df_filtered['review_date'].dropna()
    if len(valid_dates) > 0:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        date_range = st.sidebar.date_input(
            "리뷰 날짜 범위",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if len(date_range) == 2:
            start_date, end_date = date_range
            mask = (df_filtered['review_date'].dt.date >= start_date) & (df_filtered['review_date'].dt.date <= end_date)
            df_filtered = df_filtered[mask]

    # 브랜드 필터
    all_brands = sorted(df_filtered['BRAND_NAME'].unique())
    selected_brands = st.sidebar.multiselect(
        "브랜드 선택",
        options=all_brands,
        default=all_brands
    )

    if selected_brands:
        df_filtered = df_filtered[df_filtered['BRAND_NAME'].isin(selected_brands)]

    # 필터 결과 표시
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**필터링된 리뷰: {len(df_filtered):,}건**")

    # 플랫폼별 통계
    if len(selected_platforms) > 1:
        for p in selected_platforms:
            cnt = len(df_filtered[df_filtered['PLATFORM'] == p])
            st.sidebar.markdown(f"  - {p}: {cnt:,}건")

    # ===== 주요 지표 =====
    st.markdown('<p class="section-header">📊 주요 지표</p>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("총 리뷰", f"{len(df_filtered):,}")

    with col2:
        avg_rating = df_filtered['REVIEW_RATING'].mean()
        st.metric("평균 평점", f"{avg_rating:.2f}")

    with col3:
        pos_rate = (df_filtered['sentiment'] == 'POS').mean() * 100
        st.metric("긍정 비율", f"{pos_rate:.1f}%")

    with col4:
        neg_rate = (df_filtered['sentiment'] == 'NEG').mean() * 100
        st.metric("부정 비율", f"{neg_rate:.1f}%")

    with col5:
        skin_rate = df_filtered['has_skin_issue'].mean() * 100
        st.metric("피부질병 언급", f"{skin_rate:.1f}%")

    # ===== 플랫폼 비교 (2개 이상 선택 시) =====
    if len(selected_platforms) >= 2:
        st.markdown('<p class="section-header">🏪 플랫폼 비교</p>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            # 플랫폼별 감성 비율
            platform_sentiment = df_filtered.groupby('PLATFORM')['sentiment'].value_counts(normalize=True).unstack() * 100
            platform_sentiment = platform_sentiment.fillna(0)

            fig = px.bar(platform_sentiment.reset_index(),
                         x='PLATFORM', y=['POS', 'NEU', 'NEG'],
                         title='플랫폼별 감성 분포 (%)',
                         barmode='group',
                         color_discrete_map={'POS': '#10b981', 'NEU': '#6b7280', 'NEG': '#ef4444'})
            fig.update_layout(xaxis_title='플랫폼', yaxis_title='비율 (%)', legend_title='감성')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 플랫폼별 평균 평점
            platform_rating = df_filtered.groupby('PLATFORM')['REVIEW_RATING'].mean().reset_index()
            platform_rating.columns = ['플랫폼', '평균평점']

            fig = px.bar(platform_rating, x='플랫폼', y='평균평점',
                         title='플랫폼별 평균 평점',
                         color='평균평점',
                         color_continuous_scale='Greens')
            fig.update_layout(yaxis_range=[3.5, 5])
            st.plotly_chart(fig, use_container_width=True)

        # 공통 브랜드 비교
        common_brands = df_filtered.groupby(['PLATFORM', 'BRAND_NAME']).size().unstack(fill_value=0)
        common_brands = common_brands.loc[:, (common_brands > 0).all()].columns.tolist()

        if common_brands:
            st.markdown("##### 공통 브랜드 플랫폼별 부정 비율 비교")
            common_df = df_filtered[df_filtered['BRAND_NAME'].isin(common_brands)]
            brand_platform_neg = common_df.groupby(['BRAND_NAME', 'PLATFORM']).apply(
                lambda x: (x['sentiment'] == 'NEG').mean() * 100
            ).reset_index(name='NEG비율')

            fig = px.bar(brand_platform_neg, x='BRAND_NAME', y='NEG비율', color='PLATFORM',
                         barmode='group',
                         title='공통 브랜드 플랫폼별 NEG 비율 (%)',
                         color_discrete_sequence=['#00a862', '#000000'])
            st.plotly_chart(fig, use_container_width=True)

    # ===== 브랜드별 분석 =====
    st.markdown('<p class="section-header">🏷️ 브랜드별 분석</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # 브랜드별 리뷰 수
        brand_counts = df_filtered.groupby(['BRAND_NAME', 'PLATFORM']).size().reset_index(name='리뷰수')

        fig = px.bar(brand_counts, x='BRAND_NAME', y='리뷰수', color='PLATFORM',
                     title='브랜드별 리뷰 분포',
                     color_discrete_sequence=['#00a862', '#000000'])
        fig.update_layout(xaxis_title='브랜드', yaxis_title='리뷰 수')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 브랜드별 NEG 비율
        brand_neg = df_filtered.groupby('BRAND_NAME').agg({
            'sentiment': lambda x: (x == 'NEG').mean() * 100,
            'REVIEW_RATING': 'mean'
        }).reset_index()
        brand_neg.columns = ['브랜드', 'NEG비율', '평균평점']
        brand_neg = brand_neg.sort_values('NEG비율', ascending=True)

        fig = px.bar(brand_neg, x='NEG비율', y='브랜드', orientation='h',
                     title='브랜드별 부정 리뷰 비율 (%)',
                     color='NEG비율',
                     color_continuous_scale='RdYlGn_r')
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    # 브랜드별 상세 테이블
    brand_stats = df_filtered.groupby(['BRAND_NAME', 'PLATFORM']).agg({
        'REVIEW_RATING': ['count', 'mean'],
        'sentiment': lambda x: (x == 'NEG').mean() * 100,
        'has_skin_issue': lambda x: x.mean() * 100
    }).round(2)
    brand_stats.columns = ['리뷰수', '평균평점', 'NEG비율(%)', '피부질병언급(%)']
    brand_stats = brand_stats.sort_values('리뷰수', ascending=False)

    st.dataframe(brand_stats, use_container_width=True)

    # ===== 감성 분석 =====
    st.markdown('<p class="section-header">💭 감성 분석</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        sentiment_counts = df_filtered['sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['감성', '건수']

        colors = {'POS': '#10b981', 'NEU': '#6b7280', 'NEG': '#ef4444'}
        fig = px.pie(sentiment_counts, values='건수', names='감성',
                     title='감성 분포',
                     color='감성',
                     color_discrete_map=colors)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        brand_sentiment = df_filtered.groupby(['BRAND_NAME', 'sentiment']).size().reset_index(name='count')

        fig = px.bar(brand_sentiment, x='BRAND_NAME', y='count', color='sentiment',
                     title='브랜드별 감성 분포',
                     color_discrete_map=colors,
                     barmode='group')
        fig.update_layout(xaxis_title='브랜드', yaxis_title='리뷰 수')
        st.plotly_chart(fig, use_container_width=True)

    # ===== Pain Point 분석 =====
    st.markdown('<p class="section-header">😣 Pain Point 분석 (저평점 리뷰)</p>', unsafe_allow_html=True)

    low_rating_df = df_filtered[df_filtered['REVIEW_RATING'] <= 2]

    if len(low_rating_df) > 0:
        col1, col2 = st.columns(2)

        with col1:
            all_pains = []
            for pains in low_rating_df['pain_points']:
                all_pains.extend(pains)

            if all_pains:
                pain_counts = Counter(all_pains)
                pain_df = pd.DataFrame(pain_counts.items(), columns=['Pain Point', '건수'])
                pain_df = pain_df.sort_values('건수', ascending=True)

                fig = px.bar(pain_df, x='건수', y='Pain Point', orientation='h',
                             title='Pain Point 빈도',
                             color='건수',
                             color_continuous_scale='Reds')
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            pain_matrix = []
            for brand in selected_brands:
                brand_low = low_rating_df[low_rating_df['BRAND_NAME'] == brand]
                if len(brand_low) > 0:
                    brand_pains = []
                    for pains in brand_low['pain_points']:
                        brand_pains.extend(pains)
                    pain_counts = Counter(brand_pains)
                    row = {'브랜드': brand}
                    for pain in PAIN_KEYWORDS.keys():
                        row[pain] = pain_counts.get(pain, 0)
                    pain_matrix.append(row)

            if pain_matrix:
                pain_df = pd.DataFrame(pain_matrix)
                pain_df = pain_df.set_index('브랜드')

                fig = px.imshow(pain_df,
                                title='브랜드별 Pain Point 히트맵',
                                color_continuous_scale='Reds',
                                aspect='auto')
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("선택한 기간/브랜드에 저평점 리뷰가 없습니다.")

    # ===== 월별 트렌드 =====
    st.markdown('<p class="section-header">📈 월별 트렌드</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        monthly = df_filtered.groupby(['year_month', 'PLATFORM']).size().reset_index(name='리뷰수')

        fig = px.line(monthly, x='year_month', y='리뷰수', color='PLATFORM',
                      title='월별 리뷰 수 추이',
                      markers=True,
                      color_discrete_sequence=['#00a862', '#000000'])
        fig.update_layout(xaxis_title='월', yaxis_title='리뷰 수')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        monthly_neg = df_filtered.groupby(['year_month', 'PLATFORM']).apply(
            lambda x: (x['sentiment'] == 'NEG').mean() * 100
        ).reset_index(name='NEG비율')

        fig = px.line(monthly_neg, x='year_month', y='NEG비율', color='PLATFORM',
                      title='월별 부정 비율 추이 (%)',
                      markers=True,
                      color_discrete_sequence=['#00a862', '#000000'])
        fig.update_layout(xaxis_title='월', yaxis_title='NEG 비율 (%)')
        st.plotly_chart(fig, use_container_width=True)

    # ===== 효능 분석 =====
    st.markdown('<p class="section-header">✨ 효능 키워드 분석</p>', unsafe_allow_html=True)

    benefit_matrix = []
    for brand in selected_brands:
        brand_df = df_filtered[df_filtered['BRAND_NAME'] == brand]
        if len(brand_df) > 0:
            all_benefits = []
            for benefits in brand_df['benefits']:
                all_benefits.extend(benefits)
            benefit_counts = Counter(all_benefits)
            total = len(brand_df)
            row = {'브랜드': brand}
            for benefit in BENEFIT_KEYWORDS.keys():
                row[benefit] = benefit_counts.get(benefit, 0) / total * 100
            benefit_matrix.append(row)

    if benefit_matrix:
        benefit_df = pd.DataFrame(benefit_matrix)

        fig = go.Figure()

        categories = list(BENEFIT_KEYWORDS.keys())

        for i, row in benefit_df.iterrows():
            values = [row[cat] for cat in categories]
            values.append(values[0])

            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill='toself',
                name=row['브랜드'],
                opacity=0.6
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, max(benefit_df[categories].max())])),
            title='브랜드별 효능 포지셔닝',
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

    # ===== 피부타입별 분석 (통합 데이터) =====
    if 'SKIN_TYPE' in df_filtered.columns:
        st.markdown('<p class="section-header">🧬 피부타입별 분석</p>', unsafe_allow_html=True)

        skin_data = df_filtered[df_filtered['SKIN_TYPE'].notna()]

        if len(skin_data) > 0:
            col1, col2 = st.columns(2)

            with col1:
                skin_dist = skin_data['SKIN_TYPE'].value_counts().reset_index()
                skin_dist.columns = ['피부타입', '리뷰수']

                fig = px.pie(skin_dist, values='리뷰수', names='피부타입',
                             title='피부타입 분포')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                skin_neg = skin_data.groupby('SKIN_TYPE').apply(
                    lambda x: (x['sentiment'] == 'NEG').mean() * 100
                ).reset_index(name='NEG비율')
                skin_neg.columns = ['피부타입', 'NEG비율']

                fig = px.bar(skin_neg, x='피부타입', y='NEG비율',
                             title='피부타입별 부정 비율 (%)',
                             color='NEG비율',
                             color_continuous_scale='RdYlGn_r')
                st.plotly_chart(fig, use_container_width=True)

    # ===== 무신사 평가 데이터 분석 =====
    if '무신사' in selected_platforms and 'EVAL_MOISTURE' in df_filtered.columns:
        ms_data = df_filtered[df_filtered['PLATFORM'] == '무신사']
        ms_with_eval = ms_data[ms_data['EVAL_MOISTURE'].notna()]

        if len(ms_with_eval) > 0:
            st.markdown('<p class="section-header">⚫ 무신사 평가 데이터 (보습력/흡수력/자극도)</p>', unsafe_allow_html=True)
            st.caption(f"평가 데이터가 있는 리뷰: {len(ms_with_eval):,}건 / 무신사 전체 {len(ms_data):,}건")

            col1, col2, col3 = st.columns(3)

            rating_labels = {5: '매우좋음', 4: '좋음', 3: '보통', 2: '나쁨', 1: '매우나쁨'}

            with col1:
                moisture_dist = ms_with_eval['EVAL_MOISTURE'].value_counts().sort_index(ascending=False).reset_index()
                moisture_dist.columns = ['평점', '건수']
                moisture_dist['라벨'] = moisture_dist['평점'].map(rating_labels)

                fig = px.bar(moisture_dist, x='라벨', y='건수',
                             title='보습력 평가 분포',
                             color='평점',
                             color_continuous_scale='Blues')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                absorption_dist = ms_with_eval['EVAL_ABSORPTION'].dropna().value_counts().sort_index(ascending=False).reset_index()
                absorption_dist.columns = ['평점', '건수']
                absorption_dist['라벨'] = absorption_dist['평점'].map(rating_labels)

                fig = px.bar(absorption_dist, x='라벨', y='건수',
                             title='흡수력 평가 분포',
                             color='평점',
                             color_continuous_scale='Greens')
                st.plotly_chart(fig, use_container_width=True)

            with col3:
                irritation_dist = ms_with_eval['EVAL_IRRITATION'].dropna().value_counts().sort_index(ascending=False).reset_index()
                irritation_dist.columns = ['평점', '건수']
                irritation_labels = {5: '전혀없음', 4: '거의없음', 3: '보통', 2: '조금있음', 1: '많음'}
                irritation_dist['라벨'] = irritation_dist['평점'].map(irritation_labels)

                fig = px.bar(irritation_dist, x='라벨', y='건수',
                             title='자극도 평가 분포',
                             color='평점',
                             color_continuous_scale='RdYlGn')
                st.plotly_chart(fig, use_container_width=True)

            # 브랜드별 평가 평균
            st.markdown("##### 브랜드별 평가 평균")

            brand_eval = ms_with_eval.groupby('BRAND_NAME').agg({
                'EVAL_MOISTURE': 'mean',
                'EVAL_ABSORPTION': 'mean',
                'EVAL_IRRITATION': 'mean',
                'REVIEW_RATING': 'count'
            }).round(2)
            brand_eval.columns = ['보습력', '흡수력', '자극도(높을수록 순함)', '평가수']
            brand_eval = brand_eval.sort_values('평가수', ascending=False)

            st.dataframe(brand_eval, use_container_width=True)

            # 레이더 차트로 브랜드별 비교
            col1, col2 = st.columns(2)

            with col1:
                fig = go.Figure()

                for brand in brand_eval.index:
                    row = brand_eval.loc[brand]
                    values = [row['보습력'], row['흡수력'], row['자극도(높을수록 순함)']]
                    values.append(values[0])

                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=['보습력', '흡수력', '자극도'] + ['보습력'],
                        fill='toself',
                        name=brand,
                        opacity=0.6
                    ))

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[1, 5])),
                    title='브랜드별 평가 비교 (무신사)',
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 평가 점수와 별점 상관관계
                eval_rating_corr = ms_with_eval[['EVAL_MOISTURE', 'EVAL_ABSORPTION', 'EVAL_IRRITATION', 'REVIEW_RATING']].corr()

                fig = px.imshow(eval_rating_corr,
                                title='평가 항목 간 상관관계',
                                color_continuous_scale='RdBu',
                                aspect='auto',
                                text_auto='.2f')
                st.plotly_chart(fig, use_container_width=True)

    # ===== 샘플 리뷰 =====
    st.markdown('<p class="section-header">📝 샘플 리뷰</p>', unsafe_allow_html=True)

    review_type = st.radio("리뷰 유형", ["부정 리뷰 (NEG)", "긍정 리뷰 (POS)", "피부질병 언급"], horizontal=True)

    if review_type == "부정 리뷰 (NEG)":
        sample_df = df_filtered[df_filtered['sentiment'] == 'NEG'].head(10)
    elif review_type == "긍정 리뷰 (POS)":
        sample_df = df_filtered[df_filtered['sentiment'] == 'POS'].head(10)
    else:
        sample_df = df_filtered[df_filtered['has_skin_issue']].head(10)

    for _, row in sample_df.iterrows():
        platform_badge = "🟢" if row['PLATFORM'] == '올리브영' else "⚫"
        with st.expander(f"{platform_badge} [{row['PLATFORM']}] {row['BRAND_NAME']} ⭐{row['REVIEW_RATING']} - {row['sentiment']}"):
            st.write(row['REVIEW_CONTENT'])
            if pd.notna(row.get('review_date')):
                st.caption(f"날짜: {row['review_date'].strftime('%Y-%m-%d')}")

    # ===== 푸터 =====
    st.markdown("---")
    st.markdown(
        f'<p style="text-align: center; color: gray;">토너 리뷰 분석 대시보드 v2.0 | '
        f'올리브영 + 무신사 통합 | 총 {len(df):,}건 리뷰</p>',
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
