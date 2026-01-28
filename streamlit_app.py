# -*- coding: utf-8 -*-
"""
토너 리뷰 분석 대시보드 v3.0
GPT 분석 기반 통합 버전
"""
import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
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
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #333;
        border-bottom: 2px solid #667eea;
        padding-bottom: 0.5rem;
        margin: 1.5rem 0 1rem 0;
    }
    .subsection-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #555;
        margin: 1rem 0 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ===== 리뷰 표시 헬퍼 함수 =====
def display_review_card(row):
    """리뷰 카드 표시 (감성, 리뷰어 정보 포함)"""
    platform_badge = "🟢" if row['PLATFORM'] == '올리브영' else "⚫"
    date_str = row['review_date'].strftime('%Y-%m-%d') if pd.notna(row['review_date']) else ''

    # 감성 뱃지
    sentiment = row.get('sentiment', 'NEU')
    sentiment_badge = {'POS': '🟢긍정', 'NEU': '⚪중립', 'NEG': '🔴부정'}.get(sentiment, '⚪중립')

    # 리뷰어 정보 구성
    reviewer_info_parts = []
    if pd.notna(row.get('SKIN_TYPE')) and row['SKIN_TYPE']:
        reviewer_info_parts.append(f"피부타입: {row['SKIN_TYPE']}")
    if pd.notna(row.get('SKIN_TONE')) and row['SKIN_TONE']:
        reviewer_info_parts.append(f"피부톤: {row['SKIN_TONE']}")
    if pd.notna(row.get('SKIN_CONCERNS')) and row['SKIN_CONCERNS']:
        concerns = row['SKIN_CONCERNS']
        if isinstance(concerns, str) and len(concerns) > 30:
            concerns = concerns[:30] + "..."
        reviewer_info_parts.append(f"고민: {concerns}")
    if pd.notna(row.get('REVIEWER_INFO')) and row['REVIEWER_INFO']:
        reviewer_info_parts.append(f"{row['REVIEWER_INFO']}")

    reviewer_info_str = " | ".join(reviewer_info_parts) if reviewer_info_parts else ""

    # 헤더 라인
    st.markdown(f"{platform_badge} **[{row['BRAND_NAME']}]** ⭐{row['REVIEW_RATING']} | {date_str} | {sentiment_badge}")

    # 리뷰어 정보
    if reviewer_info_str:
        st.caption(f"👤 {reviewer_info_str}")

    # 리뷰 내용
    content = str(row['REVIEW_CONTENT']) if pd.notna(row['REVIEW_CONTENT']) else ''
    st.markdown(f"> {content[:300]}{'...' if len(content) > 300 else ''}")
    st.markdown("---")


# ===== 데이터 로드 =====
@st.cache_data
def load_data():
    """통합 데이터 및 GPT 분석 결과 로드"""
    # 기본 리뷰 데이터 로드
    data_path = Path("data/merged_reviews_processed.csv")
    if not data_path.exists():
        st.error("데이터 파일을 찾을 수 없습니다: data/merged_reviews_processed.csv")
        return None, None

    df = pd.read_csv(data_path, encoding='utf-8-sig')

    # GPT 분석 결과 로드
    gpt_path = Path("output/gpt_analysis_categorized.json")
    if not gpt_path.exists():
        st.warning("GPT 분석 파일을 찾을 수 없습니다. 기본 분석을 사용합니다.")
        return df, None

    with open(gpt_path, 'r', encoding='utf-8') as f:
        gpt_data = json.load(f)

    # GPT 분석 데이터를 DataFrame으로 변환
    gpt_df = pd.DataFrame(gpt_data)

    # 날짜 파싱
    df['review_date'] = pd.to_datetime(df['REVIEW_DATE'], errors='coerce')
    df['year_month'] = df['review_date'].dt.to_period('M').astype(str)

    return df, gpt_df


@st.cache_data
def load_category_stats():
    """카테고리 통계 로드"""
    stats_path = Path("output/points_categorized.json")
    if stats_path.exists():
        with open(stats_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def merge_gpt_data(df, gpt_df):
    """GPT 분석 결과를 기본 데이터와 병합"""
    if gpt_df is None:
        return df

    # idx 기준으로 병합
    gpt_cols = ['idx', 'sentiment', 'pain_points', 'positive_points',
                'benefit_tags', 'texture_tags', 'usage_tags', 'value_tags',
                'pain_categories', 'positive_categories']

    gpt_subset = gpt_df[gpt_cols].copy()
    gpt_subset = gpt_subset.rename(columns={
        'sentiment': 'gpt_sentiment',
        'pain_points': 'gpt_pain_points',
        'positive_points': 'gpt_positive_points',
        'pain_categories': 'gpt_pain_categories',
        'positive_categories': 'gpt_positive_categories'
    })

    # 인덱스로 병합
    df = df.reset_index(drop=True)
    df['idx'] = df.index

    merged = df.merge(gpt_subset, on='idx', how='left')

    return merged


# ===== 메인 앱 =====
def main():
    # 헤더
    st.markdown('<p class="main-header">🧴 토너 리뷰 분석 대시보드</p>', unsafe_allow_html=True)

    # 데이터 로드
    df, gpt_df = load_data()
    category_stats = load_category_stats()

    if df is None:
        st.stop()

    # GPT 데이터 병합
    df = merge_gpt_data(df, gpt_df)

    # GPT 감성이 있으면 사용, 없으면 기본 sentiment
    if 'gpt_sentiment' in df.columns:
        df['sentiment'] = df['gpt_sentiment'].fillna('NEU')
        analysis_type = "GPT-4o-mini"
    else:
        analysis_type = "키워드 기반"

    # 플랫폼 정보
    platforms = df['PLATFORM'].unique().tolist()
    total_reviews = len(df)
    platform_info = " | ".join([f"{p}: {len(df[df['PLATFORM']==p]):,}건" for p in platforms])
    st.markdown(f'<p style="text-align: center; color: gray;">v3.0 ({analysis_type} 분석) | {platform_info} | 총 {total_reviews:,}건</p>', unsafe_allow_html=True)

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

    # 브랜드 필터 (session_state로 선택 유지)
    all_brands = sorted(df_filtered['BRAND_NAME'].unique())

    # 첫 로드시에만 전체 브랜드 선택, 이후에는 유효한 브랜드만 유지
    if 'selected_brands' not in st.session_state:
        st.session_state.selected_brands = all_brands
    else:
        # 현재 유효한 브랜드 중에서 이전 선택 유지
        st.session_state.selected_brands = [b for b in st.session_state.selected_brands if b in all_brands]
        # 선택된 브랜드가 없으면 전체 선택
        if not st.session_state.selected_brands:
            st.session_state.selected_brands = all_brands

    selected_brands = st.sidebar.multiselect(
        "브랜드 선택",
        options=all_brands,
        default=st.session_state.selected_brands,
        key="brand_multiselect"
    )

    # 선택 상태 저장
    st.session_state.selected_brands = selected_brands

    if selected_brands:
        df_filtered = df_filtered[df_filtered['BRAND_NAME'].isin(selected_brands)]

    # 감성 필터
    sentiment_options = ['전체', 'POS (긍정)', 'NEU (중립)', 'NEG (부정)']
    selected_sentiment = st.sidebar.selectbox("감성 필터", sentiment_options)

    if selected_sentiment != '전체':
        sentiment_code = selected_sentiment.split(' ')[0]
        df_filtered = df_filtered[df_filtered['sentiment'] == sentiment_code]

    # 필터 결과 표시
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**필터링된 리뷰: {len(df_filtered):,}건**")

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
        neu_rate = (df_filtered['sentiment'] == 'NEU').mean() * 100
        st.metric("중립 비율", f"{neu_rate:.1f}%")

    # ===== 감성 분석 (GPT 기반) =====
    st.markdown('<p class="section-header">💭 감성 분석 (GPT 기반)</p>', unsafe_allow_html=True)

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
        brand_sentiment = df_filtered.groupby('BRAND_NAME')['sentiment'].value_counts(normalize=True).unstack() * 100
        brand_sentiment = brand_sentiment.fillna(0)
        # 누락된 감성 컬럼 추가
        for col in ['POS', 'NEU', 'NEG']:
            if col not in brand_sentiment.columns:
                brand_sentiment[col] = 0
        brand_sentiment = brand_sentiment.reset_index()

        fig = px.bar(brand_sentiment, x='BRAND_NAME', y=['POS', 'NEU', 'NEG'],
                     title='브랜드별 감성 비율 (%)',
                     color_discrete_map=colors,
                     barmode='stack')
        fig.update_layout(xaxis_title='브랜드', yaxis_title='비율 (%)', legend_title='감성')
        st.plotly_chart(fig, use_container_width=True)

    # ===== Pain Points 분석 (GPT 카테고리) =====
    st.markdown('<p class="section-header">😣 Pain Points 분석</p>', unsafe_allow_html=True)

    if 'gpt_pain_categories' in df_filtered.columns:
        # 전체 Pain 카테고리 분포
        all_pain_cats = []
        for cats in df_filtered['gpt_pain_categories'].dropna():
            if isinstance(cats, list):
                all_pain_cats.extend([c for c in cats if c != '기타'])

        if all_pain_cats:
            col1, col2 = st.columns(2)

            with col1:
                pain_counts = Counter(all_pain_cats)
                pain_df = pd.DataFrame(pain_counts.items(), columns=['카테고리', '건수'])
                pain_df = pain_df.sort_values('건수', ascending=True)

                fig = px.bar(pain_df, x='건수', y='카테고리', orientation='h',
                             title='Pain Point 카테고리 분포',
                             color='건수',
                             color_continuous_scale='Reds')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 브랜드별 Pain 카테고리
                brand_pain_data = []
                for brand in selected_brands:
                    brand_df = df_filtered[df_filtered['BRAND_NAME'] == brand]
                    brand_pains = []
                    for cats in brand_df['gpt_pain_categories'].dropna():
                        if isinstance(cats, list):
                            brand_pains.extend([c for c in cats if c != '기타'])

                    if brand_pains:
                        pain_counts = Counter(brand_pains)
                        total = len(brand_df)
                        for cat, cnt in pain_counts.items():
                            brand_pain_data.append({
                                '브랜드': brand,
                                '카테고리': cat,
                                '비율': cnt / total * 100
                            })

                if brand_pain_data:
                    bp_df = pd.DataFrame(brand_pain_data)
                    pivot = bp_df.pivot(index='브랜드', columns='카테고리', values='비율').fillna(0)

                    fig = px.imshow(pivot,
                                    title='브랜드별 Pain Point 히트맵 (%)',
                                    color_continuous_scale='Reds',
                                    aspect='auto')
                    st.plotly_chart(fig, use_container_width=True)

            # TOP Pain Points 리스트 (클릭하면 원문 리뷰 표시)
            st.markdown('<p class="subsection-header">TOP 20 Pain Points (클릭하여 원문 보기)</p>', unsafe_allow_html=True)

            all_pains = []
            for pains in df_filtered['gpt_pain_points'].dropna():
                if isinstance(pains, list):
                    all_pains.extend(pains)

            if all_pains:
                pain_counter = Counter(all_pains)
                top_pains = pain_counter.most_common(20)

                col1, col2 = st.columns(2)
                with col1:
                    for i, (pain, cnt) in enumerate(top_pains[:10], 1):
                        with st.expander(f"**{i}.** {pain} ({cnt}건)"):
                            # 해당 키워드가 포함된 리뷰 찾기
                            mask = df_filtered['gpt_pain_points'].apply(
                                lambda x: pain in x if isinstance(x, list) else False
                            )
                            matched_reviews = df_filtered[mask].sort_values('review_date', ascending=False).head(20)
                            for _, row in matched_reviews.iterrows():
                                display_review_card(row)
                with col2:
                    for i, (pain, cnt) in enumerate(top_pains[10:20], 11):
                        with st.expander(f"**{i}.** {pain} ({cnt}건)"):
                            # 해당 키워드가 포함된 리뷰 찾기
                            mask = df_filtered['gpt_pain_points'].apply(
                                lambda x: pain in x if isinstance(x, list) else False
                            )
                            matched_reviews = df_filtered[mask].sort_values('review_date', ascending=False).head(20)
                            for _, row in matched_reviews.iterrows():
                                display_review_card(row)

    # ===== Positive Points 분석 (GPT 카테고리) =====
    st.markdown('<p class="section-header">😊 Positive Points 분석</p>', unsafe_allow_html=True)

    if 'gpt_positive_categories' in df_filtered.columns:
        # 전체 Positive 카테고리 분포
        all_pos_cats = []
        for cats in df_filtered['gpt_positive_categories'].dropna():
            if isinstance(cats, list):
                all_pos_cats.extend([c for c in cats if c != '기타'])

        if all_pos_cats:
            col1, col2 = st.columns(2)

            with col1:
                pos_counts = Counter(all_pos_cats)
                pos_df = pd.DataFrame(pos_counts.items(), columns=['카테고리', '건수'])
                pos_df = pos_df.sort_values('건수', ascending=False).head(15)

                fig = px.bar(pos_df, x='카테고리', y='건수',
                             title='Positive Point 카테고리 분포 (TOP 15)',
                             color='건수',
                             color_continuous_scale='Greens')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # 브랜드별 Positive 레이더 차트
                brand_pos_data = []
                top_cats = pos_df['카테고리'].tolist()[:8]  # 상위 8개 카테고리

                for brand in selected_brands:
                    brand_df = df_filtered[df_filtered['BRAND_NAME'] == brand]
                    brand_pos = []
                    for cats in brand_df['gpt_positive_categories'].dropna():
                        if isinstance(cats, list):
                            brand_pos.extend([c for c in cats if c != '기타'])

                    if brand_pos:
                        pos_counts = Counter(brand_pos)
                        total = len(brand_df)
                        row = {'브랜드': brand}
                        for cat in top_cats:
                            row[cat] = pos_counts.get(cat, 0) / total * 100
                        brand_pos_data.append(row)

                if brand_pos_data:
                    bp_df = pd.DataFrame(brand_pos_data)

                    fig = go.Figure()
                    for _, row in bp_df.iterrows():
                        values = [row[cat] for cat in top_cats]
                        values.append(values[0])

                        fig.add_trace(go.Scatterpolar(
                            r=values,
                            theta=top_cats + [top_cats[0]],
                            fill='toself',
                            name=row['브랜드'],
                            opacity=0.6
                        ))

                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True)),
                        title='브랜드별 강점 레이더 차트',
                        showlegend=True
                    )
                    st.plotly_chart(fig, use_container_width=True)

            # TOP Positive Points 리스트 (클릭하면 원문 리뷰 표시)
            st.markdown('<p class="subsection-header">TOP 20 Positive Points (클릭하여 원문 보기)</p>', unsafe_allow_html=True)

            all_pos = []
            for pos in df_filtered['gpt_positive_points'].dropna():
                if isinstance(pos, list):
                    all_pos.extend(pos)

            if all_pos:
                pos_counter = Counter(all_pos)
                top_pos = pos_counter.most_common(20)

                col1, col2 = st.columns(2)
                with col1:
                    for i, (p, cnt) in enumerate(top_pos[:10], 1):
                        with st.expander(f"**{i}.** {p} ({cnt}건)"):
                            # 해당 키워드가 포함된 리뷰 찾기
                            mask = df_filtered['gpt_positive_points'].apply(
                                lambda x: p in x if isinstance(x, list) else False
                            )
                            matched_reviews = df_filtered[mask].sort_values('review_date', ascending=False).head(20)
                            for _, row in matched_reviews.iterrows():
                                display_review_card(row)
                with col2:
                    for i, (p, cnt) in enumerate(top_pos[10:20], 11):
                        with st.expander(f"**{i}.** {p} ({cnt}건)"):
                            # 해당 키워드가 포함된 리뷰 찾기
                            mask = df_filtered['gpt_positive_points'].apply(
                                lambda x: p in x if isinstance(x, list) else False
                            )
                            matched_reviews = df_filtered[mask].sort_values('review_date', ascending=False).head(20)
                            for _, row in matched_reviews.iterrows():
                                display_review_card(row)

    # ===== 브랜드 포지셔닝 (태그 기반) =====
    st.markdown('<p class="section-header">🎯 브랜드 포지셔닝</p>', unsafe_allow_html=True)

    if 'benefit_tags' in df_filtered.columns:
        col1, col2 = st.columns(2)

        with col1:
            # 효능 태그 포지셔닝
            st.markdown('<p class="subsection-header">효능 태그</p>', unsafe_allow_html=True)

            benefit_data = []
            benefit_cats = ['진정', '보습', '장벽', '결', '피지']

            for brand in selected_brands:
                brand_df = df_filtered[df_filtered['BRAND_NAME'] == brand]
                all_benefits = []
                for tags in brand_df['benefit_tags'].dropna():
                    if isinstance(tags, list):
                        all_benefits.extend(tags)

                if all_benefits:
                    tag_counts = Counter(all_benefits)
                    total = len(brand_df)
                    row = {'브랜드': brand}
                    for cat in benefit_cats:
                        row[cat] = tag_counts.get(cat, 0) / total * 100
                    benefit_data.append(row)

            if benefit_data:
                b_df = pd.DataFrame(benefit_data)

                fig = go.Figure()
                for _, row in b_df.iterrows():
                    values = [row[cat] for cat in benefit_cats]
                    values.append(values[0])

                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=benefit_cats + [benefit_cats[0]],
                        fill='toself',
                        name=row['브랜드'],
                        opacity=0.6
                    ))

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    title='효능 포지셔닝',
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 사용감 태그 포지셔닝
            st.markdown('<p class="subsection-header">사용감 태그</p>', unsafe_allow_html=True)

            texture_data = []
            texture_cats = ['물같음', '쫀쫀', '끈적', '흡수']

            for brand in selected_brands:
                brand_df = df_filtered[df_filtered['BRAND_NAME'] == brand]
                all_textures = []
                for tags in brand_df['texture_tags'].dropna():
                    if isinstance(tags, list):
                        all_textures.extend(tags)

                if all_textures:
                    tag_counts = Counter(all_textures)
                    total = len(brand_df)
                    row = {'브랜드': brand}
                    for cat in texture_cats:
                        row[cat] = tag_counts.get(cat, 0) / total * 100
                    texture_data.append(row)

            if texture_data:
                t_df = pd.DataFrame(texture_data)

                fig = go.Figure()
                for _, row in t_df.iterrows():
                    values = [row[cat] for cat in texture_cats]
                    values.append(values[0])

                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=texture_cats + [texture_cats[0]],
                        fill='toself',
                        name=row['브랜드'],
                        opacity=0.6
                    ))

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    title='사용감 포지셔닝',
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)

        # 가치 태그 분석
        st.markdown('<p class="subsection-header">가치 태그 분포</p>', unsafe_allow_html=True)

        value_data = []
        value_cats = ['가성비', '무난', '인생템', '애매']

        for brand in selected_brands:
            brand_df = df_filtered[df_filtered['BRAND_NAME'] == brand]
            all_values = []
            for tags in brand_df['value_tags'].dropna():
                if isinstance(tags, list):
                    all_values.extend(tags)

            if all_values:
                tag_counts = Counter(all_values)
                total = len(brand_df)
                for cat in value_cats:
                    value_data.append({
                        '브랜드': brand,
                        '태그': cat,
                        '비율': tag_counts.get(cat, 0) / total * 100
                    })

        if value_data:
            v_df = pd.DataFrame(value_data)

            fig = px.bar(v_df, x='브랜드', y='비율', color='태그',
                         title='브랜드별 가치 태그 비율 (%)',
                         barmode='group',
                         color_discrete_sequence=['#10b981', '#6b7280', '#f59e0b', '#ef4444'])
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
        'sentiment': lambda x: (x == 'NEG').mean() * 100
    }).round(2)
    brand_stats.columns = ['리뷰수', '평균평점', 'NEG비율(%)']
    brand_stats = brand_stats.sort_values('리뷰수', ascending=False)

    st.dataframe(brand_stats, use_container_width=True)

    # ===== 플랫폼 비교 =====
    if len(selected_platforms) >= 2:
        st.markdown('<p class="section-header">🏪 플랫폼 비교</p>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            platform_sentiment = df_filtered.groupby('PLATFORM')['sentiment'].value_counts(normalize=True).unstack() * 100
            platform_sentiment = platform_sentiment.fillna(0)
            # 누락된 감성 컬럼 추가
            for col in ['POS', 'NEU', 'NEG']:
                if col not in platform_sentiment.columns:
                    platform_sentiment[col] = 0

            fig = px.bar(platform_sentiment.reset_index(),
                         x='PLATFORM', y=['POS', 'NEU', 'NEG'],
                         title='플랫폼별 감성 분포 (%)',
                         barmode='group',
                         color_discrete_map={'POS': '#10b981', 'NEU': '#6b7280', 'NEG': '#ef4444'})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            platform_rating = df_filtered.groupby('PLATFORM')['REVIEW_RATING'].mean().reset_index()
            platform_rating.columns = ['플랫폼', '평균평점']

            fig = px.bar(platform_rating, x='플랫폼', y='평균평점',
                         title='플랫폼별 평균 평점',
                         color='평균평점',
                         color_continuous_scale='Greens')
            fig.update_layout(yaxis_range=[3.5, 5])
            st.plotly_chart(fig, use_container_width=True)

    # ===== 월별 트렌드 =====
    st.markdown('<p class="section-header">📈 월별 트렌드</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        monthly = df_filtered.groupby(['year_month', 'PLATFORM']).size().reset_index(name='리뷰수')

        fig = px.line(monthly, x='year_month', y='리뷰수', color='PLATFORM',
                      title='월별 리뷰 수 추이',
                      markers=True,
                      color_discrete_sequence=['#00a862', '#000000'])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        monthly_neg = df_filtered.groupby(['year_month', 'PLATFORM']).apply(
            lambda x: (x['sentiment'] == 'NEG').mean() * 100
        ).reset_index(name='NEG비율')

        fig = px.line(monthly_neg, x='year_month', y='NEG비율', color='PLATFORM',
                      title='월별 부정 비율 추이 (%)',
                      markers=True,
                      color_discrete_sequence=['#00a862', '#000000'])
        st.plotly_chart(fig, use_container_width=True)

    # ===== 피부타입별 분석 =====
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

    # ===== 무신사 평가 데이터 =====
    if '무신사' in selected_platforms and 'EVAL_MOISTURE' in df_filtered.columns:
        ms_data = df_filtered[df_filtered['PLATFORM'] == '무신사']
        ms_with_eval = ms_data[ms_data['EVAL_MOISTURE'].notna()]

        if len(ms_with_eval) > 0:
            st.markdown('<p class="section-header">⚫ 무신사 평가 데이터</p>', unsafe_allow_html=True)
            st.caption(f"평가 데이터가 있는 리뷰: {len(ms_with_eval):,}건")

            col1, col2 = st.columns(2)

            with col1:
                brand_eval = ms_with_eval.groupby('BRAND_NAME').agg({
                    'EVAL_MOISTURE': 'mean',
                    'EVAL_ABSORPTION': 'mean',
                    'EVAL_IRRITATION': 'mean'
                }).round(2)
                brand_eval.columns = ['보습력', '흡수력', '자극도(높을수록 순함)']

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
                    title='브랜드별 평가 비교',
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.dataframe(brand_eval, use_container_width=True)

    # ===== 샘플 리뷰 =====
    st.markdown('<p class="section-header">📝 샘플 리뷰</p>', unsafe_allow_html=True)

    review_type = st.radio("리뷰 유형", ["부정 리뷰 (NEG)", "긍정 리뷰 (POS)", "중립 리뷰 (NEU)"], horizontal=True)

    sentiment_map = {"부정 리뷰 (NEG)": "NEG", "긍정 리뷰 (POS)": "POS", "중립 리뷰 (NEU)": "NEU"}
    selected_sent = sentiment_map[review_type]
    sample_df = df_filtered[df_filtered['sentiment'] == selected_sent].head(10)

    for _, row in sample_df.iterrows():
        platform_badge = "🟢" if row['PLATFORM'] == '올리브영' else "⚫"
        with st.expander(f"{platform_badge} [{row['PLATFORM']}] {row['BRAND_NAME']} ⭐{row['REVIEW_RATING']} - {row['sentiment']}"):
            st.write(row['REVIEW_CONTENT'])

            # GPT 분석 결과 표시
            if 'gpt_pain_points' in row and isinstance(row['gpt_pain_points'], list) and row['gpt_pain_points']:
                st.markdown(f"**Pain Points:** {', '.join(row['gpt_pain_points'])}")
            if 'gpt_positive_points' in row and isinstance(row['gpt_positive_points'], list) and row['gpt_positive_points']:
                st.markdown(f"**Positive Points:** {', '.join(row['gpt_positive_points'])}")

    # ===== 푸터 =====
    st.markdown("---")
    st.markdown(
        f'<p style="text-align: center; color: gray;">토너 리뷰 분석 대시보드 v3.0 (GPT-4o-mini 분석) | '
        f'총 {len(df):,}건 리뷰</p>',
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
