# -*- coding: utf-8 -*-
"""
토너 리뷰 분석 대시보드 v4.0
GPT 분석 기반 통합 버전 (탭 구조)
"""
import streamlit as st
import pandas as pd
import json
import re
import html
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="모찌토너 리뷰 분석",
    page_icon="🧴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header { font-size: 3.4rem; font-weight: bold; color: #667eea; text-align: center; margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 56px; padding: 0 24px; }
    .stTabs [data-baseweb="tab"] p { font-size: 1.35rem; font-weight: 600; }
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



# ===== 탭 3: 카테고리 시계열 =====
def _explode_categories(df_filtered, col):
    """리뷰별 카테고리 리스트를 (year_month, category) 행으로 펼친다."""
    if col not in df_filtered.columns:
        return pd.DataFrame(columns=['year_month', 'category', 'BRAND_NAME', 'idx'])
    sub = df_filtered[['year_month', 'BRAND_NAME', col]].copy()
    sub = sub[sub[col].apply(lambda x: isinstance(x, list) and len(x) > 0)]
    sub = sub.explode(col).rename(columns={col: 'category'})
    sub = sub[sub['category'].notna() & (sub['category'].astype(str).str.strip() != '')]
    return sub


def tab_category_timeseries(df_filtered):
    st.markdown('<p class="section-header">📈 카테고리 시계열 분석</p>', unsafe_allow_html=True)
    st.caption("월별로 어떤 카테고리의 불만/만족 포인트가 많이 나타나는지 시계열로 확인합니다. (사이드바 필터 적용)")

    if len(df_filtered) == 0 or 'gpt_pain_categories' not in df_filtered.columns:
        st.info("데이터가 없거나 카테고리 정보가 없습니다.")
        return

    # 컨트롤
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.2])
    with c1:
        point_type = st.radio("포인트 유형", ["😣 Pain", "😊 Positive"], horizontal=True, key="cts_type")
    with c2:
        top_n = st.slider("상위 카테고리 N", 3, 15, 8, key="cts_topn")
    with c3:
        metric_mode = st.radio("지표", ["건수", "월별 비중(%)"], horizontal=True, key="cts_metric")
    with c4:
        smooth = st.checkbox("3개월 이동평균", value=False, key="cts_smooth",
                             help="시계열 변동을 부드럽게 보고 싶을 때 사용")

    is_pain = point_type.startswith("😣")
    cat_col = 'gpt_pain_categories' if is_pain else 'gpt_positive_categories'
    color_scale = 'Reds' if is_pain else 'Greens'  # 히트맵용 단색 그라데이션
    color_seq = px.colors.qualitative.Bold        # 라인/누적 영역용 정성 팔레트

    exploded = _explode_categories(df_filtered, cat_col)
    if len(exploded) == 0:
        st.info("선택된 필터 범위에 카테고리 데이터가 없습니다.")
        return

    # 상위 N 카테고리
    top_cats = exploded['category'].value_counts().head(top_n).index.tolist()
    exp_top = exploded[exploded['category'].isin(top_cats)]

    # 월별 × 카테고리 집계
    monthly_total_reviews = df_filtered.groupby('year_month').size().rename('total_reviews')
    pivot_cnt = (exp_top.groupby(['year_month', 'category']).size()
                 .unstack(fill_value=0)
                 .sort_index())
    if len(pivot_cnt) == 0:
        st.info("월별 집계 결과가 비어 있습니다.")
        return

    # 월별 비중(%): 해당 월의 전체 리뷰 수 대비 카테고리 언급 비율
    pivot_pct = pivot_cnt.div(monthly_total_reviews.reindex(pivot_cnt.index), axis=0) * 100
    pivot_pct = pivot_pct.fillna(0)

    pivot_view = pivot_pct if metric_mode.startswith("월별") else pivot_cnt
    value_label = '월별 비중(%)' if metric_mode.startswith("월별") else '건수'

    if smooth:
        pivot_view = pivot_view.rolling(window=3, min_periods=1).mean()

    # 카테고리는 전체 합계 큰 순으로 정렬
    cat_order = pivot_cnt.sum(axis=0).sort_values(ascending=False).index.tolist()
    pivot_view = pivot_view[cat_order]

    # ----- 1) 라인 차트 (월별 추세) -----
    st.markdown("### 1️⃣ 월별 카테고리 추세")
    line_df = pivot_view.reset_index().melt(id_vars='year_month', var_name='카테고리', value_name=value_label)
    fig_line = px.line(
        line_df, x='year_month', y=value_label, color='카테고리',
        markers=True, color_discrete_sequence=color_seq,
        category_orders={'카테고리': cat_order}
    )
    fig_line.update_traces(line=dict(width=2.5), marker=dict(size=8))
    fig_line.update_layout(
        height=420, xaxis_title='월', yaxis_title=value_label,
        legend=dict(orientation='v', yanchor='top', y=1, xanchor='left', x=1.02),
        plot_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#eee'),
        yaxis=dict(showgrid=True, gridcolor='#eee'),
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # ----- 2) 히트맵 (카테고리 × 월) -----
    st.markdown("### 2️⃣ 카테고리 × 월 히트맵")
    heat_z = pivot_view[cat_order].T  # 행: 카테고리, 열: 월
    fig_heat = go.Figure(data=go.Heatmap(
        z=heat_z.values,
        x=heat_z.columns.tolist(),
        y=heat_z.index.tolist(),
        colorscale=color_scale,
        colorbar=dict(title=value_label),
        hovertemplate='월=%{x}<br>카테고리=%{y}<br>' + value_label + '=%{z:.2f}<extra></extra>'
    ))
    fig_heat.update_layout(height=max(320, 40 * len(cat_order)),
                           xaxis_title='월', yaxis_title='카테고리',
                           yaxis=dict(autorange='reversed'))
    st.plotly_chart(fig_heat, use_container_width=True)

    # ----- 3) 누적 영역 차트 (구성 변화) -----
    st.markdown("### 3️⃣ 월별 카테고리 구성 (누적)")
    stack_mode = st.radio("누적 방식", ["절대 건수", "100% 비중"], horizontal=True, key="cts_stack")
    if stack_mode == "100% 비중":
        denom = pivot_cnt.sum(axis=1).replace(0, pd.NA)
        stack_df = (pivot_cnt.div(denom, axis=0) * 100).fillna(0)
        stack_label = '구성비(%)'
    else:
        stack_df = pivot_cnt
        stack_label = '건수'
    stack_long = stack_df[cat_order].reset_index().melt(id_vars='year_month', var_name='카테고리', value_name=stack_label)
    fig_area = px.area(
        stack_long, x='year_month', y=stack_label, color='카테고리',
        color_discrete_sequence=color_seq,
        category_orders={'카테고리': cat_order}
    )
    fig_area.update_layout(height=400, xaxis_title='월', yaxis_title=stack_label)
    st.plotly_chart(fig_area, use_container_width=True)

    # ----- 4) 카테고리 드릴다운 -----
    st.markdown("### 4️⃣ 카테고리 드릴다운 (월별 리뷰 확인)")
    sel_cat = st.selectbox("카테고리 선택", cat_order, key="cts_drill_cat")

    cat_monthly = exploded[exploded['category'] == sel_cat].groupby('year_month').size().rename('건수').reset_index()
    if len(cat_monthly) > 0:
        peak_month = cat_monthly.loc[cat_monthly['건수'].idxmax(), 'year_month']
        peak_cnt = int(cat_monthly['건수'].max())
        total_cnt = int(cat_monthly['건수'].sum())
        m1, m2, m3 = st.columns(3)
        m1.metric("총 언급", f"{total_cnt:,}건")
        m2.metric("최다 월", f"{peak_month}")
        m3.metric("최다 월 건수", f"{peak_cnt:,}건")

        bar_color = '#ef4444' if is_pain else '#10b981'
        fig_bar = px.bar(cat_monthly, x='year_month', y='건수', color_discrete_sequence=[bar_color])
        fig_bar.update_layout(height=300, xaxis_title='월', yaxis_title='언급 건수',
                              title=f"'{sel_cat}' 월별 언급 추이")
        st.plotly_chart(fig_bar, use_container_width=True)

        # 월 선택 → 해당 월의 리뷰 표시
        months_with_data = cat_monthly['year_month'].tolist()
        sel_month = st.selectbox("월 선택", ['(전체 기간)'] + months_with_data, key="cts_drill_month")

        mask = df_filtered[cat_col].apply(lambda x: isinstance(x, list) and sel_cat in x)
        target_df = df_filtered[mask]
        if sel_month != '(전체 기간)':
            target_df = target_df[target_df['year_month'] == sel_month]

        st.markdown(f"**대상 리뷰: {len(target_df):,}건** (최신순 최대 15건 표시)")
        for _, row in target_df.sort_values('review_date', ascending=False).head(15).iterrows():
            display_review_card(row)
    else:
        st.info("선택한 카테고리에 해당하는 데이터가 없습니다.")


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


# ===== 아마존 분석 =====
AMAZON_STRENGTHS = [
    "보습/촉촉", "순함/저자극", "대용량/오래씀", "가성비/가격만족", "흡수력",
    "광채/윤기", "진정/장벽케어", "제형/텍스처", "향 만족", "산뜻함",
    "재구매/추천", "용기/디자인", "기타",
]
AMAZON_WEAKNESSES = [
    "트러블/뾰루지", "효과없음", "제형불호", "향 불호", "자극/따가움", "끈적임",
    "가격부담", "용기불편", "흡수느림", "건조함", "배송/포장", "기타",
]


def _parse_amazon_date_country(date_raw):
    """'Reviewed in the United Kingdom on 23 May 2026' -> ('United Kingdom', Timestamp)"""
    if not isinstance(date_raw, str):
        return None, pd.NaT
    m = re.search(r"Reviewed in (.+?) on (.+)$", date_raw)
    if not m:
        return None, pd.NaT
    country = m.group(1).strip()
    date = pd.to_datetime(m.group(2).strip(), format="%d %B %Y", errors="coerce")
    if pd.isna(date):
        date = pd.to_datetime(m.group(2).strip(), errors="coerce")
    return country, date


@st.cache_data(ttl=600)
def load_amazon_data():
    rev_path = Path("data/amazon_reviews_B07B32PL1C.json")
    ana_path = Path("output/amazon_analysis.json")
    if not rev_path.exists() or not ana_path.exists():
        return None
    reviews = json.loads(rev_path.read_text(encoding="utf-8"))
    analysis = {a["review_id"]: a for a in json.loads(ana_path.read_text(encoding="utf-8"))}
    rows = []
    for r in reviews:
        a = analysis.get(r["review_id"], {})
        country, date = _parse_amazon_date_country(r.get("date_raw"))
        rows.append({
            "review_id": r["review_id"],
            "rating": r.get("rating"),
            "title": r.get("title", ""),
            "body": r.get("body", ""),
            "author": r.get("author", ""),
            "date_raw": r.get("date_raw", ""),
            "verified_purchase": r.get("verified_purchase", False),
            "helpful": r.get("helpful", ""),
            "sentiment": a.get("sentiment", "NEU"),
            "strengths": a.get("strengths", []) or [],
            "weaknesses": a.get("weaknesses", []) or [],
            "evidence": a.get("evidence", ""),
            "translation_ko": a.get("translation_ko", ""),
            "country": country,
            "review_date": date,
        })
    return pd.DataFrame(rows)


def _amazon_point_counts(df_am, col):
    c = Counter()
    for lst in df_am[col]:
        if isinstance(lst, list):
            c.update(lst)
    return c


def display_amazon_review_card(row):
    if pd.notna(row.get("review_date")):
        date_str = row["review_date"].strftime("%Y-%m-%d")
    else:
        date_str = row.get("date_raw", "") or ""
    sentiment = row.get("sentiment", "NEU")
    badge = {"POS": "🟢긍정", "NEU": "⚪중립", "NEG": "🔴부정"}.get(sentiment, "⚪중립")
    verified = " | ✅구매인증" if row.get("verified_purchase") else ""
    country = f" | 🌍{row['country']}" if row.get("country") else ""
    st.markdown(f"**⭐{row.get('rating', '')} | {badge} | {date_str}{country}{verified}**")
    if row.get("title"):
        st.markdown(f"**{row['title']}**")
    strengths = row.get("strengths") or []
    weaknesses = row.get("weaknesses") or []
    tag_parts = [f"`💪 {s}`" for s in strengths] + [f"`⚠️ {w}`" for w in weaknesses]
    if tag_parts:
        st.markdown(" ".join(tag_parts))
    # 본문은 마크다운으로 해석되지 않도록 HTML escape 후 div로 렌더 (원문 전체, 줄바꿈 보존)
    body = html.escape(str(row.get("body", "") or ""))
    st.markdown(
        f'<div style="border-left:3px solid #d9d9e3; padding:6px 14px; margin:4px 0 6px;'
        f' color:#3a3a3a; white-space:pre-wrap; line-height:1.55;">{body}</div>',
        unsafe_allow_html=True,
    )
    # 한글 번역 (있을 때만)
    trans = str(row.get("translation_ko", "") or "").strip()
    if trans:
        st.markdown(
            f'<div style="border-left:3px solid #c7d2fe; background:#f5f7ff; padding:6px 14px;'
            f' margin:0 0 12px; color:#3730a3; white-space:pre-wrap; line-height:1.55;">'
            f'🇰🇷 {html.escape(trans)}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("---")


def tab_amazon(df_am):
    st.markdown('<p class="section-header">🛒 아마존 토너 분석</p>', unsafe_allow_html=True)
    st.caption("TONYMOLY Wonder Ceramide Mochi Toner (아마존 UK · ASIN B07B32PL1C)")
    if df_am is None or len(df_am) == 0:
        st.warning("아마존 분석 데이터가 없습니다. `python analyze_amazon.py` 로 분류를 먼저 실행하세요.")
        return

    n = len(df_am)
    pos_pct = (df_am['sentiment'] == 'POS').mean() * 100
    neu_pct = (df_am['sentiment'] == 'NEU').mean() * 100
    neg_pct = (df_am['sentiment'] == 'NEG').mean() * 100
    pos_n = int((df_am['sentiment'] == 'POS').sum())
    neu_n = int((df_am['sentiment'] == 'NEU').sum())
    neg_n = int((df_am['sentiment'] == 'NEG').sum())

    # ===== 종합 감성 배너 =====
    if pos_pct >= 85:
        verdict, banner = "🟢 전반적으로 매우 긍정적", "success"
    elif pos_pct >= 65:
        verdict, banner = "🟢 전반적으로 긍정적", "success"
    elif pos_pct >= 50:
        verdict, banner = "🙂 대체로 긍정적", "info"
    elif neg_pct > pos_pct:
        verdict, banner = "🔴 전반적으로 부정적", "error"
    else:
        verdict, banner = "⚪ 긍정·부정 혼재", "warning"
    msg = f"**{verdict}** &nbsp;|&nbsp; 긍정 {pos_pct:.1f}% ({pos_n}) · 중립 {neu_pct:.1f}% ({neu_n}) · 부정 {neg_pct:.1f}% ({neg_n})"
    {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}[banner](msg)

    # ===== KPI =====
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("총 리뷰", f"{n:,}건")
    c2.metric("평균 별점", f"{df_am['rating'].mean():.2f} ⭐")
    c3.metric("긍정", f"{pos_pct:.1f}%")
    c4.metric("중립", f"{neu_pct:.1f}%")
    c5.metric("부정", f"{neg_pct:.1f}%")

    # ===== 별점 분포 + 감성 분포 =====
    dist_l, dist_r = st.columns(2)
    with dist_l:
        star_counts = df_am['rating'].value_counts().reindex([5.0, 4.0, 3.0, 2.0, 1.0], fill_value=0)
        fig_star = px.bar(
            x=[f"⭐{int(s)}" for s in star_counts.index], y=star_counts.values,
            labels={"x": "별점", "y": "리뷰 수"}, text=star_counts.values,
        )
        fig_star.update_traces(marker_color="#667eea", textposition="outside", cliponaxis=False)
        fig_star.update_layout(height=300, margin=dict(t=50, b=10), title="별점 분포")
        fig_star.update_yaxes(range=[0, float(star_counts.max()) * 1.18])
        st.plotly_chart(fig_star, use_container_width=True)
    with dist_r:
        fig_sent = go.Figure(data=[go.Pie(
            labels=["긍정", "중립", "부정"], values=[pos_n, neu_n, neg_n], hole=0.55,
            marker=dict(colors=["#2ca02c", "#bbbbbb", "#d62728"]),
            sort=False, textinfo="label+percent",
        )])
        fig_sent.update_layout(height=300, margin=dict(t=40, b=10), title="감성 분포",
                               annotations=[dict(text=f"긍정<br>{pos_pct:.0f}%", x=0.5, y=0.5,
                                                 font_size=18, showarrow=False)])
        st.plotly_chart(fig_sent, use_container_width=True)

    # ===== 강점 / 약점 포인트 (막대 클릭 → 아래에 해당 카테고리 리뷰) =====
    st.markdown('<p class="subsection-header">💪 강점 포인트 vs ⚠️ 약점 포인트</p>', unsafe_allow_html=True)
    st.caption("👉 막대를 클릭하면 아래에 해당 카테고리의 리뷰가 표시됩니다.")
    colL, colR = st.columns(2)
    sel_s = sel_w = None
    with colL:
        sc = _amazon_point_counts(df_am, "strengths")
        if sc:
            s_df = pd.DataFrame(sc.most_common(), columns=["카테고리", "건수"]).iloc[::-1]
            fig_s = px.bar(s_df, x="건수", y="카테고리", orientation="h", text="건수")
            fig_s.update_traces(marker_color="#2ca02c", textposition="outside")
            fig_s.update_layout(height=420, margin=dict(t=30, l=10), title="강점 포인트 (언급 수)")
            sel_s = st.plotly_chart(fig_s, use_container_width=True, on_select="rerun",
                                    selection_mode="points", key="am_chart_s")
    with colR:
        wc = _amazon_point_counts(df_am, "weaknesses")
        if wc:
            w_df = pd.DataFrame(wc.most_common(), columns=["카테고리", "건수"]).iloc[::-1]
            fig_w = px.bar(w_df, x="건수", y="카테고리", orientation="h", text="건수")
            fig_w.update_traces(marker_color="#d62728", textposition="outside")
            fig_w.update_layout(height=420, margin=dict(t=30, l=10), title="약점 포인트 (언급 수)")
            sel_w = st.plotly_chart(fig_w, use_container_width=True, on_select="rerun",
                                    selection_mode="points", key="am_chart_w")

    # 클릭된 막대 추출 (가장 최근에 바뀐 쪽을 선택으로 간주)
    def _picked_cat(sel):
        try:
            pts = sel["selection"]["points"]
        except (TypeError, KeyError, AttributeError):
            pts = []
        return pts[0].get("y") if pts else None

    s_pick, w_pick = _picked_cat(sel_s), _picked_cat(sel_w)
    if s_pick and s_pick != st.session_state.get("_am_prev_s"):
        st.session_state["_am_chosen"] = ("strengths", s_pick)
    elif w_pick and w_pick != st.session_state.get("_am_prev_w"):
        st.session_state["_am_chosen"] = ("weaknesses", w_pick)
    st.session_state["_am_prev_s"], st.session_state["_am_prev_w"] = s_pick, w_pick

    # ===== 리뷰 보기 (필터 + 목록; 카테고리 막대 클릭 시 해당 카테고리로 좁힘) =====
    st.markdown('<p class="subsection-header">📝 리뷰 보기</p>', unsafe_allow_html=True)

    chosen = st.session_state.get("_am_chosen")
    if chosen:
        col_c, cat_c = chosen
        emoji = "💪" if col_c == "strengths" else "⚠️"
        cc1, cc2 = st.columns([4, 1])
        cc1.markdown(f"선택된 카테고리: **{emoji} {cat_c}** &nbsp;(다른 막대를 클릭하면 변경)")
        if cc2.button("✕ 카테고리 해제"):
            st.session_state["_am_chosen"] = None
            chosen = None

    fc1, fc2, fc3 = st.columns([1, 1, 2])
    with fc1:
        sent_f = st.selectbox("감성", ["전체", "POS (긍정)", "NEU (중립)", "NEG (부정)"], key="am_sent")
    with fc2:
        star_f = st.selectbox("별점", ["전체", 5, 4, 3, 2, 1], key="am_starf")
    with fc3:
        kw = st.text_input("키워드 검색 (제목·본문)", key="am_kw", placeholder="예: hydrating, scent, glass...")

    view = df_am.copy()
    if chosen:
        col_c, cat_c = chosen
        view = view[view[col_c].apply(lambda l: isinstance(l, list) and cat_c in l)]
    if sent_f != "전체":
        view = view[view["sentiment"] == sent_f.split(" ")[0]]
    if star_f != "전체":
        view = view[view["rating"] == float(star_f)]
    if kw:
        mask = view["body"].str.contains(kw, case=False, na=False) | view["title"].str.contains(kw, case=False, na=False)
        view = view[mask]
    view = view.sort_values("review_date", ascending=False, na_position="last")

    scope = (f"{'💪' if chosen[0] == 'strengths' else '⚠️'} {chosen[1]} 카테고리") if chosen else "전체"
    st.markdown(f"**{scope} · 표시 중 {len(view)}건** (전체 {n}건)")
    for _, row in view.iterrows():
        display_amazon_review_card(row)


def _explode_amazon(df_am, col):
    """아마존 리뷰별 카테고리 리스트를 (year_month, category) 행으로 펼친다."""
    sub = df_am[["year_month", col]].copy()
    sub = sub[sub[col].apply(lambda x: isinstance(x, list) and len(x) > 0)]
    sub = sub.explode(col).rename(columns={col: "category"})
    return sub[sub["category"].notna() & (sub["category"].astype(str).str.strip() != "")]


def tab_amazon_timeseries(df_am):
    st.markdown('<p class="section-header">📈 아마존 카테고리 시계열</p>', unsafe_allow_html=True)
    st.caption("리뷰 작성일(월) 기준으로 강점/약점 카테고리가 어떻게 변해왔는지 봅니다.")
    if df_am is None or len(df_am) == 0:
        st.warning("아마존 분석 데이터가 없습니다.")
        return

    df = df_am.dropna(subset=["review_date"]).copy()
    df["year_month"] = df["review_date"].dt.to_period("M").astype(str)
    if len(df) == 0:
        st.info("작성일이 파싱된 리뷰가 없습니다.")
        return

    all_months = sorted(df["year_month"].unique())
    # 기본 시작월: 마지막 달로부터 약 18개월 전 (희박한 오래된 구간 제외)
    default_start_idx = max(0, len(all_months) - 18)

    c1, c2, c3, c4 = st.columns([1.2, 1.4, 1, 1])
    with c1:
        ptype = st.radio("포인트 유형", ["💪 강점", "⚠️ 약점"], horizontal=True, key="amts_type")
    with c2:
        start_month = st.selectbox("시작월", all_months, index=default_start_idx, key="amts_start")
    with c3:
        top_n = st.slider("상위 카테고리 N", 3, 12, 7, key="amts_topn")
    with c4:
        metric_mode = st.radio("지표", ["건수", "월별 비중(%)"], horizontal=True, key="amts_metric")

    is_strength = ptype.startswith("💪")
    cat_col = "strengths" if is_strength else "weaknesses"
    color_scale = "Greens" if is_strength else "Reds"
    color_seq = px.colors.qualitative.Bold

    df = df[df["year_month"] >= start_month]
    exploded = _explode_amazon(df, cat_col)
    if len(exploded) == 0:
        st.info("선택한 기간에 카테고리 데이터가 없습니다.")
        return

    top_cats = exploded["category"].value_counts().head(top_n).index.tolist()
    exp_top = exploded[exploded["category"].isin(top_cats)]

    monthly_total = df.groupby("year_month").size().rename("total_reviews")
    pivot_cnt = (exp_top.groupby(["year_month", "category"]).size()
                 .unstack(fill_value=0).sort_index())
    # 데이터 없는 달도 0으로 채워 연속 축 유지
    full_idx = [m for m in all_months if m >= start_month]
    pivot_cnt = pivot_cnt.reindex(full_idx, fill_value=0)

    pivot_pct = (pivot_cnt.div(monthly_total.reindex(pivot_cnt.index), axis=0) * 100).fillna(0)
    pivot_view = pivot_pct if metric_mode.startswith("월별") else pivot_cnt
    value_label = "월별 비중(%)" if metric_mode.startswith("월별") else "건수"

    cat_order = pivot_cnt.sum(axis=0).sort_values(ascending=False).index.tolist()
    pivot_view = pivot_view[cat_order]

    # ----- 1) 라인 차트 -----
    st.markdown("### 1️⃣ 월별 카테고리 추세")
    line_df = pivot_view.reset_index().rename(columns={"index": "year_month"}).melt(
        id_vars="year_month", var_name="카테고리", value_name=value_label)
    fig_line = px.line(line_df, x="year_month", y=value_label, color="카테고리",
                       markers=True, color_discrete_sequence=color_seq,
                       category_orders={"카테고리": cat_order})
    fig_line.update_traces(line=dict(width=2.5), marker=dict(size=7))
    fig_line.update_layout(height=420, xaxis_title="월", yaxis_title=value_label,
                           legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
                           plot_bgcolor="white",
                           xaxis=dict(showgrid=True, gridcolor="#eee"),
                           yaxis=dict(showgrid=True, gridcolor="#eee"))
    st.plotly_chart(fig_line, use_container_width=True)

    # ----- 2) 히트맵 -----
    st.markdown("### 2️⃣ 카테고리 × 월 히트맵")
    heat_z = pivot_view[cat_order].T
    fig_heat = go.Figure(data=go.Heatmap(
        z=heat_z.values, x=heat_z.columns.tolist(), y=heat_z.index.tolist(),
        colorscale=color_scale, colorbar=dict(title=value_label),
        hovertemplate="월=%{x}<br>카테고리=%{y}<br>" + value_label + "=%{z:.2f}<extra></extra>"))
    fig_heat.update_layout(height=max(320, 40 * len(cat_order)), xaxis_title="월",
                           yaxis_title="카테고리", yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_heat, use_container_width=True)

    # ----- 3) 카테고리 드릴다운 -----
    st.markdown("### 3️⃣ 카테고리 드릴다운")
    sel_cat = st.selectbox("카테고리 선택", cat_order, key="amts_drill_cat")
    cat_monthly = (exploded[exploded["category"] == sel_cat]
                   .groupby("year_month").size().rename("건수").reset_index())
    if len(cat_monthly) > 0:
        m1, m2, m3 = st.columns(3)
        m1.metric("총 언급", f"{int(cat_monthly['건수'].sum()):,}건")
        m2.metric("최다 월", f"{cat_monthly.loc[cat_monthly['건수'].idxmax(), 'year_month']}")
        m3.metric("최다 월 건수", f"{int(cat_monthly['건수'].max()):,}건")
        bar_color = "#10b981" if is_strength else "#ef4444"
        fig_bar = px.bar(cat_monthly, x="year_month", y="건수", color_discrete_sequence=[bar_color])
        fig_bar.update_layout(height=300, xaxis_title="월", yaxis_title="언급 건수",
                              title=f"'{sel_cat}' 월별 언급 추이")
        st.plotly_chart(fig_bar, use_container_width=True)

        months_with_data = cat_monthly["year_month"].tolist()
        sel_month = st.selectbox("월 선택", ["(전체 기간)"] + months_with_data, key="amts_drill_month")
        mask = df[cat_col].apply(lambda x: isinstance(x, list) and sel_cat in x)
        target = df[mask]
        if sel_month != "(전체 기간)":
            target = target[target["year_month"] == sel_month]
        st.markdown(f"**대상 리뷰: {len(target):,}건** (최신순)")
        for _, row in target.sort_values("review_date", ascending=False).iterrows():
            display_amazon_review_card(row)
    else:
        st.info("선택한 카테고리에 해당하는 데이터가 없습니다.")


# ===== 아마존 워드클라우드(고객이 실제로 쓴 단어) =====
# 영어 기능어 + 리뷰에서 의미 없는 일반어
_WC_STOP = set("""
a an the and or but if then so than that this these those there here
i me my we our you your he she it its they them their his her him
is am are was were be been being do does did doing have has had having
will would shall should can could may might must
of to in on at by for with from into onto about as up down out off over under again
not no nor too very just only also even still yet more most much many few less least
i'm i've it's don't didn't doesn't isn't wasn't aren't weren't can't won't couldn't
im ive its dont didnt doesnt isnt wasnt arent werent cant wont couldnt
get got getting go going goes went come comes came use used using uses
one two three really quite bit lot lots way ways thing things stuff
all any some each every both either neither other another such own same
what which who whom whose when where why how
because while during before after above below between through against
s t re ve ll d m o y amp nbsp br
review reviewed amazon product item order ordered buy bought purchase purchased
""".split())


def _wc_tokenize(text):
    return re.findall(r"[a-z][a-z']+", str(text).lower())


@st.cache_data
def _amazon_word_freq(texts):
    """리뷰 본문 리스트 → (단어 빈도 Counter, 리뷰수 Counter, bigram Counter)"""
    word_c, doc_c, bi_c = Counter(), Counter(), Counter()
    for doc in texts:
        toks = [w for w in _wc_tokenize(doc) if w not in _WC_STOP and len(w) > 2]
        word_c.update(toks)
        doc_c.update(set(toks))
        for a, b in zip(toks, toks[1:]):
            bi_c[f"{a} {b}"] += 1
    return word_c, doc_c, bi_c


@st.cache_data
def _amazon_wordcloud_png(freq):
    """빈도 dict → 워드클라우드 PNG 바이트"""
    from wordcloud import WordCloud
    import io
    wc = WordCloud(
        width=1600, height=900, background_color="white", max_words=120,
        colormap="viridis", prefer_horizontal=0.9, collocations=False,
        relative_scaling=0.5, min_font_size=10,
    ).generate_from_frequencies(freq)
    buf = io.BytesIO()
    wc.to_image().save(buf, format="PNG")
    return buf.getvalue()


def tab_amazon_wordcloud(df_am):
    st.markdown('<p class="section-header">☁️ 고객이 실제로 쓴 단어</p>', unsafe_allow_html=True)
    st.caption("아마존 리뷰 원문(영어)에서 추출한 빈출 단어 — 기능어/일반어 제외")
    if df_am is None or len(df_am) == 0:
        st.warning("아마존 분석 데이터가 없습니다.")
        return

    texts = [f"{t} {b}" for t, b in zip(df_am["title"].fillna(""), df_am["body"].fillna(""))]
    n = len(texts)
    word_c, doc_c, bi_c = _amazon_word_freq(texts)
    if not word_c:
        st.info("추출된 단어가 없습니다.")
        return

    st.markdown(f"리뷰 **{n:,}건**에서 고유 단어 **{len(word_c):,}개** 추출")

    # ===== 워드클라우드 (wordcloud 패키지 없으면 아래 차트로 대체) =====
    try:
        st.image(_amazon_wordcloud_png(dict(word_c)), use_container_width=True)
    except ModuleNotFoundError:
        st.info(
            "ℹ️ 워드클라우드 이미지를 그리려면 `wordcloud` 패키지가 필요합니다 "
            "(`pip install wordcloud`). 패키지가 없어 이미지는 생략하고, "
            "아래 **빈출 단어 차트와 순위표**로 동일한 내용을 보여드립니다."
        )
    except Exception as e:
        st.warning(f"워드클라우드 렌더 실패: {e} — 아래 차트/표로 대체합니다.")

    st.markdown("---")
    left, right = st.columns(2)

    # ===== 단어 빈도 TOP 30 (가로 막대) =====
    with left:
        st.markdown("**🔤 빈출 단어 TOP 30**")
        top = word_c.most_common(30)
        words = [w for w, _ in top][::-1]
        counts = [c for _, c in top][::-1]
        fig = px.bar(
            x=counts, y=words, orientation="h",
            labels={"x": "언급 횟수", "y": ""}, text=counts,
        )
        fig.update_traces(textposition="outside", marker_color="#667eea", cliponaxis=False)
        fig.update_layout(height=720, margin=dict(l=10, r=40, t=10, b=10), yaxis=dict(tickfont=dict(size=13)))
        st.plotly_chart(fig, use_container_width=True)

    # ===== 연어(2-gram) TOP 20 =====
    with right:
        st.markdown("**🔗 자주 함께 쓴 표현 (2-gram) TOP 20**")
        top_bi = bi_c.most_common(20)
        bg = [b for b, _ in top_bi][::-1]
        bc = [c for _, c in top_bi][::-1]
        fig2 = px.bar(
            x=bc, y=bg, orientation="h",
            labels={"x": "언급 횟수", "y": ""}, text=bc,
        )
        fig2.update_traces(textposition="outside", marker_color="#f59e0b", cliponaxis=False)
        fig2.update_layout(height=720, margin=dict(l=10, r=40, t=10, b=10), yaxis=dict(tickfont=dict(size=13)))
        st.plotly_chart(fig2, use_container_width=True)

    # ===== 상세 순위 표 =====
    st.markdown("---")
    st.markdown("**📋 단어 빈도 상세 순위 (TOP 50)**")
    rows = []
    for i, (w, c) in enumerate(word_c.most_common(50), 1):
        dc = doc_c[w]
        rows.append({"순위": i, "단어": w, "언급 횟수": c, "리뷰 수": dc, "리뷰 비율": f"{dc / n * 100:.1f}%"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=420)
    st.caption("※ 리뷰 비율 = 해당 단어가 등장한 리뷰의 비중. 같은 리뷰에서 여러 번 써도 1건으로 집계.")


# 아마존 전용 보기: True면 사이드바 필터와 기존 3개 탭을 숨기고 아마존 탭만 표시
# (원래 대시보드로 되돌리려면 False 로 변경)
AMAZON_ONLY = True


# ===== 메인 앱 =====
def main():
    st.markdown('<p class="main-header">🧴 모찌토너 리뷰 분석 대시보드</p>', unsafe_allow_html=True)

    # 아마존 전용 모드: 사이드바 필터와 기존 3개 탭 숨김
    if AMAZON_ONLY:
        # 맨 위 앵커 + 우하단 고정 '맨 위로' 버튼
        st.markdown(
            """
            <div id="amz-top"></div>
            <a href="#amz-top" class="scroll-top-btn" title="맨 위로">▲</a>
            <style>
            .scroll-top-btn {
                position: fixed; bottom: 42px; right: 34px; z-index: 9999;
                width: 48px; height: 48px; border-radius: 50%;
                background: #667eea; color: #fff !important;
                display: flex; align-items: center; justify-content: center;
                font-size: 20px; text-decoration: none;
                box-shadow: 0 2px 10px rgba(0,0,0,0.28); opacity: 0.85;
            }
            .scroll-top-btn:hover { background: #4f5fd0; opacity: 1; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        df_am = load_amazon_data()
        amz_tab1, amz_tab2, amz_tab3 = st.tabs([
            "🛒 아마존 토너 분석", "📈 아마존 카테고리 시계열", "☁️ 고객 단어/워드클라우드"
        ])
        with amz_tab1:
            tab_amazon(df_am)
        with amz_tab2:
            tab_amazon_timeseries(df_am)
        with amz_tab3:
            tab_amazon_wordcloud(df_am)
        st.markdown("---")
        n_am = 0 if df_am is None else len(df_am)
        st.markdown(
            f'<p style="text-align: center; color: gray;">아마존 토너 리뷰 분석 | 총 {n_am:,}건</p>',
            unsafe_allow_html=True,
        )
        return

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
    st.sidebar.caption("※ 필터는 [전체 리뷰 분석] / [카테고리 시계열] 탭에 적용됩니다.")

    # ===== 탭 =====
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🥛 모찌토너 인사이트", "📊 전체 리뷰 분석", "📈 카테고리 시계열",
        "🛒 아마존 토너 분석", "☁️ 아마존 고객 단어"
    ])

    with tab1:
        tab_mochi_insight(df)

    with tab2:
        tab_dashboard(df, df_filtered, selected_brands)

    with tab3:
        tab_category_timeseries(df_filtered)

    with tab4:
        tab_amazon(load_amazon_data())

    with tab5:
        tab_amazon_wordcloud(load_amazon_data())

    # 푸터
    st.markdown("---")
    st.markdown(f'<p style="text-align: center; color: gray;">토너 리뷰 분석 대시보드 v4.0 | 총 {len(df):,}건</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
