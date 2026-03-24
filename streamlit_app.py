# -*- coding: utf-8 -*-
"""
토너 리뷰 분석 대시보드 v4.0
GPT 분석 기반 통합 버전 (탭 구조)
"""
import streamlit as st
import pandas as pd
import json
import re
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
    .main-header { font-size: 2.5rem; font-weight: bold; color: #667eea; text-align: center; margin-bottom: 1rem; }
    .section-header { font-size: 1.5rem; font-weight: bold; color: #333; border-bottom: 2px solid #667eea; padding-bottom: 0.5rem; margin: 1.5rem 0 1rem 0; }
    .subsection-header { font-size: 1.2rem; font-weight: bold; color: #555; margin: 1rem 0 0.5rem 0; }
    .insight-box { background: #f0f4ff; border-left: 4px solid #667eea; padding: 1rem; margin: 0.5rem 0; border-radius: 4px; }
    .metric-highlight { font-size: 2rem; font-weight: bold; color: #667eea; }
</style>
""", unsafe_allow_html=True)


# ===== 리뷰 표시 헬퍼 함수 =====
def display_review_card(row):
    date_str = row['review_date'].strftime('%Y-%m-%d') if pd.notna(row['review_date']) else ''
    sentiment = row.get('sentiment', 'NEU')
    sentiment_badge = {'POS': '🟢긍정', 'NEU': '⚪중립', 'NEG': '🔴부정'}.get(sentiment, '⚪중립')
    skin_type = row.get('SKIN_TYPE', '')
    skin_badge = ""
    if pd.notna(skin_type) and skin_type:
        skin_emoji = {'민감성': '🔴', '건성': '🟠', '지성': '🟡', '복합성': '🟢', '중성': '⚪'}.get(skin_type, '⚪')
        skin_badge = f" | {skin_emoji}{skin_type}"
    reviewer_info_parts = []
    if pd.notna(row.get('SKIN_TONE')) and row['SKIN_TONE']:
        reviewer_info_parts.append(f"피부톤: {row['SKIN_TONE']}")
    if pd.notna(row.get('SKIN_CONCERNS')) and row['SKIN_CONCERNS']:
        concerns = str(row['SKIN_CONCERNS'])
        if not re.search(r'[A-Z]\d+', concerns):
            reviewer_info_parts.append(f"고민: {concerns[:30]}")
    if pd.notna(row.get('REVIEWER_INFO')) and row['REVIEWER_INFO']:
        reviewer_info_parts.append(f"{row['REVIEWER_INFO']}")
    st.markdown(f"**[{row['BRAND_NAME']}]** ⭐{row['REVIEW_RATING']} | {date_str} | {sentiment_badge}{skin_badge}")
    if reviewer_info_parts:
        st.caption(f"👤 {' | '.join(reviewer_info_parts)}")
    content = str(row['REVIEW_CONTENT']) if pd.notna(row['REVIEW_CONTENT']) else ''
    st.markdown(f"> {content[:300]}{'...' if len(content) > 300 else ''}")
    st.markdown("---")


# ===== 데이터 로드 =====
@st.cache_data(ttl=600)
def load_data():
    data_path = Path("data/oliveyoung_reviews_processed.csv")
    if not data_path.exists():
        json_path = Path("data/올영리뷰데이터_utf8.json")
        if not json_path.exists():
            st.error("데이터 파일을 찾을 수 없습니다.")
            return None, None
        import json as json_mod
        with open(json_path, 'r', encoding='utf-8') as f:
            raw = json_mod.load(f)
        first_key = list(raw.keys())[0]
        df = pd.DataFrame(raw[first_key])
    else:
        df = pd.read_csv(data_path, encoding='utf-8-sig')

    gpt_path = Path("output/gpt_analysis_categorized.json")
    if not gpt_path.exists():
        return df, None
    with open(gpt_path, 'r', encoding='utf-8') as f:
        gpt_data = json.load(f)
    gpt_df = pd.DataFrame(gpt_data)
    df['review_date'] = pd.to_datetime(df['REVIEW_DATE'], errors='coerce')
    df['year_month'] = df['review_date'].dt.to_period('M').astype(str)
    return df, gpt_df


def merge_gpt_data(df, gpt_df):
    if gpt_df is None:
        return df
    gpt_cols = ['idx', 'sentiment', 'pain_points', 'positive_points',
                'benefit_tags', 'texture_tags', 'usage_tags', 'value_tags',
                'pain_categories', 'positive_categories']
    gpt_subset = gpt_df[gpt_cols].copy()
    gpt_subset = gpt_subset.rename(columns={
        'sentiment': 'gpt_sentiment', 'pain_points': 'gpt_pain_points',
        'positive_points': 'gpt_positive_points',
        'pain_categories': 'gpt_pain_categories', 'positive_categories': 'gpt_positive_categories'
    })
    df = df.reset_index(drop=True)
    df['idx'] = df.index
    return df.merge(gpt_subset, on='idx', how='left')


# ===== 탭 1: 모찌토너 인사이트 =====
def tab_mochi_insight(df):
    st.markdown('<p class="section-header">🥛 모찌토너 리뷰 인사이트</p>', unsafe_allow_html=True)

    mochi = df[df['BRAND_NAME'] == '토니모리 모찌 토너']
    if len(mochi) == 0:
        st.warning("토니모리 모찌 토너 데이터가 없습니다.")
        return

    # 핵심 인사이트
    st.markdown("""
> **"보습·가성비·대용량 삼박자로 긍정률 92.5%를 기록한 고충성 제품. 치명적 불만 없이 부정률 2.3%로, 향 호불호와 지성 피부 끈적임만 보완하면 완성도가 더 높아질 수 있음."**
""")

    # 주요 지표
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("총 리뷰", f"{len(mochi):,}건")
    with col2:
        st.metric("평균 별점", f"{mochi['REVIEW_RATING'].mean():.2f}점")
    with col3:
        pos_rate = (mochi['sentiment'] == 'POS').mean() * 100
        st.metric("긍정률", f"{pos_rate:.1f}%")
    with col4:
        neg_rate = (mochi['sentiment'] == 'NEG').mean() * 100
        st.metric("부정률", f"{neg_rate:.1f}%")

    st.markdown("---")

    # 강점 & 페인포인트
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 💪 핵심 강점")
        all_pos = []
        for pts in mochi['gpt_positive_points'].dropna():
            if isinstance(pts, list):
                all_pos.extend(pts)
        if all_pos:
            pos_counter = Counter(all_pos)
            top_pos = pos_counter.most_common(10)
            total = len(mochi)
            for i, (p, cnt) in enumerate(top_pos, 1):
                pct = cnt / total * 100
                st.markdown(f"**{i}.** {p} — {cnt}건 ({pct:.1f}%)")

    with col_right:
        st.markdown("### 😣 페인포인트")
        all_pain = []
        for pts in mochi['gpt_pain_points'].dropna():
            if isinstance(pts, list):
                all_pain.extend(pts)
        if all_pain:
            pain_counter = Counter(all_pain)
            top_pain = pain_counter.most_common(10)
            total = len(mochi)
            for i, (p, cnt) in enumerate(top_pain, 1):
                pct = cnt / total * 100
                st.markdown(f"**{i}.** {p} — {cnt}건 ({pct:.1f}%)")
        else:
            st.info("페인포인트가 거의 없습니다. (부정률 2.3%)")

    st.markdown("---")

    # 태그 분석
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏷️ 효능 태그")
        benefit_counts = Counter()
        for tags in mochi['benefit_tags'].dropna():
            if isinstance(tags, list):
                benefit_counts.update(tags)
        if benefit_counts:
            b_df = pd.DataFrame(benefit_counts.most_common(5), columns=['태그', '건수'])
            fig = px.bar(b_df, x='태그', y='건수', color='건수',
                         color_continuous_scale='Greens')
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🧴 사용법 태그")
        usage_counts = Counter()
        for tags in mochi['usage_tags'].dropna():
            if isinstance(tags, list):
                usage_counts.update(tags)
        if usage_counts:
            u_df = pd.DataFrame(usage_counts.most_common(5), columns=['사용법', '건수'])
            fig = px.bar(u_df, x='사용법', y='건수', color='건수',
                         color_continuous_scale='Blues')
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

    # 사용감 & 가치 태그
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 💧 사용감 태그")
        texture_counts = Counter()
        for tags in mochi['texture_tags'].dropna():
            if isinstance(tags, list):
                texture_counts.update(tags)
        if texture_counts:
            t_df = pd.DataFrame(texture_counts.most_common(5), columns=['사용감', '건수'])
            fig = px.pie(t_df, values='건수', names='사용감', hole=0.4)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 💎 가치 태그")
        value_counts = Counter()
        for tags in mochi['value_tags'].dropna():
            if isinstance(tags, list):
                value_counts.update(tags)
        if value_counts:
            v_df = pd.DataFrame(value_counts.most_common(5), columns=['가치', '건수'])
            fig = px.pie(v_df, values='건수', names='가치', hole=0.4)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # 월별 트렌드
    st.markdown("### 📈 월별 리뷰 추이")
    monthly = mochi.groupby('year_month').agg(
        리뷰수=('sentiment', 'count'),
        긍정률=('sentiment', lambda x: (x == 'POS').mean() * 100)
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly['year_month'], y=monthly['리뷰수'], name='리뷰 수', marker_color='#667eea', opacity=0.6))
    fig.add_trace(go.Scatter(x=monthly['year_month'], y=monthly['긍정률'], name='긍정률 (%)', yaxis='y2',
                             line=dict(color='#10b981', width=3), mode='lines+markers'))
    fig.update_layout(
        yaxis=dict(title='리뷰 수'), yaxis2=dict(title='긍정률 (%)', overlaying='y', side='right', range=[80, 100]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02), height=350
    )
    st.plotly_chart(fig, use_container_width=True)



# ===== 탭 2: 전체 대시보드 (기존) =====
def tab_dashboard(df, df_filtered, selected_brands):
    # 주요 지표
    st.markdown('<p class="section-header">📊 주요 지표</p>', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("총 리뷰", f"{len(df_filtered):,}")
    with col2:
        st.metric("평균 평점", f"{df_filtered['REVIEW_RATING'].mean():.2f}")
    with col3:
        st.metric("긍정 비율", f"{(df_filtered['sentiment'] == 'POS').mean() * 100:.1f}%")
    with col4:
        st.metric("부정 비율", f"{(df_filtered['sentiment'] == 'NEG').mean() * 100:.1f}%")
    with col5:
        st.metric("중립 비율", f"{(df_filtered['sentiment'] == 'NEU').mean() * 100:.1f}%")

    # 감성 분석
    st.markdown('<p class="section-header">💭 감성 분석</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    colors = {'긍정': '#10b981', '중립': '#6b7280', '부정': '#ef4444'}
    with col1:
        sentiment_counts = df_filtered['sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['감성', '건수']
        sentiment_counts['감성'] = sentiment_counts['감성'].map({'POS': '긍정', 'NEU': '중립', 'NEG': '부정'})
        fig = px.pie(sentiment_counts, values='건수', names='감성', title='감성 분포', color='감성', color_discrete_map=colors)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        brand_sentiment = df_filtered.groupby('BRAND_NAME')['sentiment'].value_counts(normalize=True).unstack() * 100
        brand_sentiment = brand_sentiment.fillna(0)
        for col in ['POS', 'NEU', 'NEG']:
            if col not in brand_sentiment.columns:
                brand_sentiment[col] = 0
        brand_sentiment = brand_sentiment.rename(columns={'POS': '긍정', 'NEU': '중립', 'NEG': '부정'}).reset_index()
        fig = px.bar(brand_sentiment, x='BRAND_NAME', y=['긍정', '중립', '부정'], title='제품별 감성 비율 (%)',
                     color_discrete_map=colors, barmode='stack')
        fig.update_layout(xaxis_title='제품', yaxis_title='비율 (%)', legend_title='감성')
        st.plotly_chart(fig, use_container_width=True)

    # Pain Points
    st.markdown('<p class="section-header">😣 Pain Points</p>', unsafe_allow_html=True)
    if 'gpt_pain_points' in df_filtered.columns:
        all_pains = []
        for pains in df_filtered['gpt_pain_points'].dropna():
            if isinstance(pains, list):
                all_pains.extend(pains)
        if all_pains:
            pain_counter = Counter(all_pains)
            top_pains = pain_counter.most_common(20)
            total_filtered = len(df_filtered)
            col1, col2 = st.columns(2)
            with col1:
                for i, (pain, cnt) in enumerate(top_pains[:10], 1):
                    pct = cnt / total_filtered * 100
                    with st.expander(f"**{i}.** {pain} ({cnt}건, {pct:.2f}%)"):
                        mask = df_filtered['gpt_pain_points'].apply(lambda x: pain in x if isinstance(x, list) else False)
                        for _, row in df_filtered[mask].sort_values('review_date', ascending=False).head(10).iterrows():
                            display_review_card(row)
            with col2:
                for i, (pain, cnt) in enumerate(top_pains[10:20], 11):
                    pct = cnt / total_filtered * 100
                    with st.expander(f"**{i}.** {pain} ({cnt}건, {pct:.2f}%)"):
                        mask = df_filtered['gpt_pain_points'].apply(lambda x: pain in x if isinstance(x, list) else False)
                        for _, row in df_filtered[mask].sort_values('review_date', ascending=False).head(10).iterrows():
                            display_review_card(row)

    # Positive Points
    st.markdown('<p class="section-header">😊 Positive Points</p>', unsafe_allow_html=True)
    if 'gpt_positive_points' in df_filtered.columns:
        all_pos = []
        for pos in df_filtered['gpt_positive_points'].dropna():
            if isinstance(pos, list):
                all_pos.extend(pos)
        if all_pos:
            pos_counter = Counter(all_pos)
            top_pos = pos_counter.most_common(20)
            total_filtered = len(df_filtered)
            col1, col2 = st.columns(2)
            with col1:
                for i, (p, cnt) in enumerate(top_pos[:10], 1):
                    pct = cnt / total_filtered * 100
                    with st.expander(f"**{i}.** {p} ({cnt}건, {pct:.2f}%)"):
                        mask = df_filtered['gpt_positive_points'].apply(lambda x: p in x if isinstance(x, list) else False)
                        for _, row in df_filtered[mask].sort_values('review_date', ascending=False).head(10).iterrows():
                            display_review_card(row)
            with col2:
                for i, (p, cnt) in enumerate(top_pos[10:20], 11):
                    pct = cnt / total_filtered * 100
                    with st.expander(f"**{i}.** {p} ({cnt}건, {pct:.2f}%)"):
                        mask = df_filtered['gpt_positive_points'].apply(lambda x: p in x if isinstance(x, list) else False)
                        for _, row in df_filtered[mask].sort_values('review_date', ascending=False).head(10).iterrows():
                            display_review_card(row)

    # 포지셔닝
    st.markdown('<p class="section-header">🎯 제품 포지셔닝</p>', unsafe_allow_html=True)
    if 'benefit_tags' in df_filtered.columns:
        col1, col2 = st.columns(2)
        for col_widget, tag_field, cats, title in [
            (col1, 'benefit_tags', ['진정', '보습', '장벽', '결', '피지'], '효능 포지셔닝'),
            (col2, 'texture_tags', ['물같음', '쫀쫀', '끈적', '흡수'], '사용감 포지셔닝')
        ]:
            with col_widget:
                data = []
                for brand in selected_brands:
                    brand_df = df_filtered[df_filtered['BRAND_NAME'] == brand]
                    all_tags = []
                    for tags in brand_df[tag_field].dropna():
                        if isinstance(tags, list):
                            all_tags.extend(tags)
                    if all_tags:
                        tag_counts = Counter(all_tags)
                        total = len(brand_df)
                        row = {'브랜드': brand}
                        for cat in cats:
                            row[cat] = tag_counts.get(cat, 0) / total * 100
                        data.append(row)
                if data:
                    fig = go.Figure()
                    for _, row in pd.DataFrame(data).iterrows():
                        values = [row[cat] for cat in cats] + [row[cats[0]]]
                        fig.add_trace(go.Scatterpolar(r=values, theta=cats + [cats[0]], fill='toself', name=row['브랜드'], opacity=0.6))
                    fig.update_layout(polar=dict(radialaxis=dict(visible=True)), title=title, showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)

    # 월별 트렌드
    st.markdown('<p class="section-header">📈 월별 트렌드</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        monthly = df_filtered.groupby('year_month').size().reset_index(name='리뷰수')
        fig = px.line(monthly, x='year_month', y='리뷰수', title='월별 리뷰 수 추이', markers=True, color_discrete_sequence=['#00a862'])
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        monthly_neg = df_filtered.groupby('year_month').apply(lambda x: (x['sentiment'] == 'NEG').mean() * 100).reset_index(name='NEG비율')
        fig = px.line(monthly_neg, x='year_month', y='NEG비율', title='월별 부정 비율 추이 (%)', markers=True, color_discrete_sequence=['#00a862'])
        st.plotly_chart(fig, use_container_width=True)

    # 샘플 리뷰
    st.markdown('<p class="section-header">📝 샘플 리뷰</p>', unsafe_allow_html=True)
    review_type = st.radio("리뷰 유형", ["부정 리뷰 (NEG)", "긍정 리뷰 (POS)", "중립 리뷰 (NEU)"], horizontal=True)
    selected_sent = review_type.split(' ')[0].replace("부정", "NEG").replace("긍정", "POS").replace("중립", "NEU")
    sentiment_map = {"부정 리뷰 (NEG)": "NEG", "긍정 리뷰 (POS)": "POS", "중립 리뷰 (NEU)": "NEU"}
    selected_sent = sentiment_map[review_type]
    for _, row in df_filtered[df_filtered['sentiment'] == selected_sent].head(10).iterrows():
        with st.expander(f"{row['BRAND_NAME']} ⭐{row['REVIEW_RATING']} - {row['sentiment']}"):
            st.write(row['REVIEW_CONTENT'])
            if 'gpt_pain_points' in row and isinstance(row['gpt_pain_points'], list) and row['gpt_pain_points']:
                st.markdown(f"**Pain Points:** {', '.join(row['gpt_pain_points'])}")
            if 'gpt_positive_points' in row and isinstance(row['gpt_positive_points'], list) and row['gpt_positive_points']:
                st.markdown(f"**Positive Points:** {', '.join(row['gpt_positive_points'])}")


# ===== 메인 앱 =====
def main():
    st.markdown('<p class="main-header">🧴 토너 리뷰 분석 대시보드</p>', unsafe_allow_html=True)

    df, gpt_df = load_data()
    if df is None:
        st.stop()

    df = merge_gpt_data(df, gpt_df)
    if 'gpt_sentiment' in df.columns:
        df['sentiment'] = df['gpt_sentiment'].fillna('NEU')

    total_reviews = len(df)
    # ===== 사이드바 필터 =====
    st.sidebar.header("🔍 필터")

    if 'PLATFORM_CODE' in df.columns:
        platform_map = {'OLIVEYOUNG': '올리브영', 'COUPANG': '쿠팡'}
        df['PLATFORM'] = df['PLATFORM_CODE'].map(platform_map).fillna(df['PLATFORM_CODE'])
        platforms = sorted(df['PLATFORM'].unique())
        selected_platforms = st.sidebar.multiselect("플랫폼 선택", options=platforms, default=platforms)
        df_filtered = df[df['PLATFORM'].isin(selected_platforms)] if selected_platforms else df
    else:
        df_filtered = df

    valid_dates = df_filtered['review_date'].dropna()
    if len(valid_dates) > 0:
        min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
        date_filter_type = st.sidebar.radio("날짜 선택 방식", ["월별", "일별"], horizontal=True)
        if date_filter_type == "월별":
            all_months = sorted(df_filtered['year_month'].dropna().unique())
            if all_months:
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    start_month = st.selectbox("시작월", options=all_months, index=0)
                with col2:
                    end_month = st.selectbox("종료월", options=all_months, index=len(all_months) - 1)
                df_filtered = df_filtered[(df_filtered['year_month'] >= start_month) & (df_filtered['year_month'] <= end_month)]
        else:
            date_range = st.sidebar.date_input("리뷰 날짜 범위", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            if len(date_range) == 2:
                df_filtered = df_filtered[(df_filtered['review_date'].dt.date >= date_range[0]) & (df_filtered['review_date'].dt.date <= date_range[1])]

    all_brands = sorted(df_filtered['BRAND_NAME'].unique())
    if 'selected_brands' not in st.session_state:
        default_brand = [b for b in all_brands if b == '토니모리 모찌 토너']
        st.session_state.selected_brands = default_brand if default_brand else all_brands
    else:
        st.session_state.selected_brands = [b for b in st.session_state.selected_brands if b in all_brands]
        if not st.session_state.selected_brands:
            st.session_state.selected_brands = all_brands

    selected_brands = st.sidebar.multiselect("제품 선택", options=all_brands, default=st.session_state.selected_brands, key="brand_multiselect")
    st.session_state.selected_brands = selected_brands
    if selected_brands:
        df_filtered = df_filtered[df_filtered['BRAND_NAME'].isin(selected_brands)]

    sentiment_options = ['전체', 'POS (긍정)', 'NEU (중립)', 'NEG (부정)']
    selected_sentiment = st.sidebar.selectbox("감성 필터", sentiment_options)
    if selected_sentiment != '전체':
        df_filtered = df_filtered[df_filtered['sentiment'] == selected_sentiment.split(' ')[0]]

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**필터링된 리뷰: {len(df_filtered):,}건**")
    st.sidebar.caption("※ 필터는 [전체 리뷰 분석] 탭에만 적용됩니다.")

    # ===== 탭 =====
    tab1, tab2 = st.tabs(["🥛 모찌토너 인사이트", "📊 전체 리뷰 분석"])

    with tab1:
        tab_mochi_insight(df)

    with tab2:
        tab_dashboard(df, df_filtered, selected_brands)

    # 푸터
    st.markdown("---")
    st.markdown(f'<p style="text-align: center; color: gray;">토너 리뷰 분석 대시보드 v4.0 | 총 {len(df):,}건</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
