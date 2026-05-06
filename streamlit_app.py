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
    st.sidebar.caption("※ 필터는 [전체 리뷰 분석] / [카테고리 시계열] 탭에 적용됩니다.")

    # ===== 탭 =====
    tab1, tab2, tab3 = st.tabs(["🥛 모찌토너 인사이트", "📊 전체 리뷰 분석", "📈 카테고리 시계열"])

    with tab1:
        tab_mochi_insight(df)

    with tab2:
        tab_dashboard(df, df_filtered, selected_brands)

    with tab3:
        tab_category_timeseries(df_filtered)

    # 푸터
    st.markdown("---")
    st.markdown(f'<p style="text-align: center; color: gray;">토너 리뷰 분석 대시보드 v4.0 | 총 {len(df):,}건</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
