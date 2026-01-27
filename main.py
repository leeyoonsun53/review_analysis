"""
리뷰 분석 프로젝트 메인 실행 스크립트

올리브영 토너 리뷰 데이터를 분석하여 PM 인사이트 도출

실행 방법:
    python main.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# 모듈 임포트
from src.data_loader import load_and_preprocess, get_brand_summary
from src.sentiment_analyzer import analyze_all_sentiments
from src.tag_extractor import extract_all_tags
from src.switch_detector import detect_all_switches
from src.ai_enhancer import enhance_with_ai

from analysis.neutral_rate import (
    calculate_neutral_rates,
    plot_neutral_rate_comparison,
    get_neutral_insights
)
from analysis.positioning_map import (
    calculate_positioning_scores,
    plot_positioning_map,
    get_positioning_insights
)
from analysis.positioning_sentence import (
    generate_all_sentences,
    print_positioning_sentences
)
from analysis.rebuy_analysis import (
    analyze_rebuy_reasons,
    analyze_strong_rebuy,
    plot_rebuy_pie,
    plot_rebuy_comparison,
    get_rebuy_insights
)
from analysis.switch_matrix import (
    build_switch_matrix,
    plot_switch_heatmap,
    get_switch_insights,
    print_switch_analysis
)


def main():
    """메인 실행 함수"""

    # ===== 0. 설정 =====
    # JSON 파일 우선, 없으면 CSV 사용
    DATA_PATH = PROJECT_ROOT / "data" / "올영리뷰데이터_utf8.json"
    if not DATA_PATH.exists():
        DATA_PATH = PROJECT_ROOT / "data" / "올영리뷰데이터_utf8.csv"
    OUTPUT_DIR = PROJECT_ROOT / "output"
    FIGURES_DIR = OUTPUT_DIR / "figures"

    # 출력 디렉토리 생성
    OUTPUT_DIR.mkdir(exist_ok=True)
    FIGURES_DIR.mkdir(exist_ok=True)

    print("=" * 60)
    print("    리뷰 분석 프로젝트")
    print("    올리브영 토너 리뷰 데이터 분석")
    print("=" * 60)

    # ===== 1. 데이터 로딩 =====
    print("\n[Step 1] 데이터 로딩 및 전처리...")

    if not DATA_PATH.exists():
        print(f"오류: 데이터 파일을 찾을 수 없습니다: {DATA_PATH}")
        return

    df = load_and_preprocess(DATA_PATH)
    print(f"  - 로딩 완료: {len(df):,}개 리뷰")

    # 브랜드 요약
    brand_summary = get_brand_summary(df)
    print("\n  브랜드별 리뷰 수:")
    for brand, row in brand_summary.iterrows():
        print(f"    - {brand}: {int(row['review_count']):,}개 (평균 {row['avg_rating']:.1f}점)")

    # ===== 2. 변수 추출 (Step 2) =====
    print("\n[Step 2] 리뷰별 변수 추출...")

    # 2-1. 감성/강도 분석
    print("  - 감성/강도 분석 중...")
    df = analyze_all_sentiments(df)

    sentiment_dist = df['sentiment'].value_counts()
    print(f"    감성 분포: POS={sentiment_dist.get('POS', 0)}, NEU={sentiment_dist.get('NEU', 0)}, NEG={sentiment_dist.get('NEG', 0)}")

    # 2-2. 태그 추출
    print("  - 태그 추출 중 (benefit, texture, usage, value)...")
    df = extract_all_tags(df)

    # 태그 추출 통계
    benefit_count = df['benefit_tags'].apply(lambda x: len(x) if isinstance(x, list) else 0).sum()
    texture_count = df['texture_tags'].apply(lambda x: len(x) if isinstance(x, list) else 0).sum()
    usage_count = df['usage_tags'].apply(lambda x: len(x) if isinstance(x, list) else 0).sum()
    print(f"    추출된 태그: 효능={benefit_count}, 사용감={texture_count}, 사용법={usage_count}")

    # 2-3. 전환 신호 탐지
    print("  - 전환 신호 탐지 중...")
    df = detect_all_switches(df)

    switch_count = df['switch_signal'].sum()
    print(f"    전환 신호 감지: {switch_count}건 ({switch_count/len(df)*100:.1f}%)")

    # 2-4. AI 보정 (선택적)
    USE_AI_ENHANCEMENT = True  # AI 보정 사용 여부

    if USE_AI_ENHANCEMENT:
        print("\n  - AI 보정 (GPT-4o-mini) 시작...")
        df = enhance_with_ai(df, OUTPUT_DIR, batch_size=50, delay=0.3, max_samples=50)  # 테스트용 50건

        # AI 보정 후 감성 분포 재출력
        sentiment_dist_after = df['sentiment'].value_counts()
        print(f"\n    [AI 보정 후] 감성 분포: POS={sentiment_dist_after.get('POS', 0)}, NEU={sentiment_dist_after.get('NEU', 0)}, NEG={sentiment_dist_after.get('NEG', 0)}")

    # 처리된 데이터 저장
    output_csv = OUTPUT_DIR / "processed_reviews.csv"
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n  - 처리된 데이터 저장: {output_csv}")

    # ===== 3. 산출물 생성 (Step 3) =====
    print("\n[Step 3] 산출물 생성...")

    # ----- 3-A: 무난/애매 점유율 -----
    print("\n  [3-A] 무난/애매 점유율 분석...")
    neutral_df = calculate_neutral_rates(df)

    print("\n  브랜드별 무난/애매 점유율:")
    print(neutral_df[['brand', 'neutral_rate', 'ambiguous_rate', 'total_neutral_rate']].to_string(index=False))

    # 시각화
    fig_neutral = plot_neutral_rate_comparison(neutral_df, FIGURES_DIR / "3A_neutral_rate.png")
    print(f"  - 그래프 저장: {FIGURES_DIR / '3A_neutral_rate.png'}")

    # 인사이트
    neutral_insights = get_neutral_insights(neutral_df)
    print(f"\n  인사이트:")
    print(f"    - {neutral_insights['highest_neutral']['interpretation']}")
    print(f"    - {neutral_insights['highest_ambiguous']['interpretation']}")

    # ----- 3-B: 포지셔닝 맵 -----
    print("\n  [3-B] 키워드 포지셔닝 맵 생성...")
    positions_df = calculate_positioning_scores(df)

    # 맵1: 진정 vs 보습 (효능 축)
    fig_map1 = plot_positioning_map(
        positions_df, '진정', '보습',
        '효능 포지셔닝 맵 (진정 vs 보습)',
        FIGURES_DIR / "3B_positioning_benefit.png"
    )
    print(f"  - 효능 맵 저장: {FIGURES_DIR / '3B_positioning_benefit.png'}")

    # 맵2: 물같음 vs 쫀쫀 (사용감 축)
    fig_map2 = plot_positioning_map(
        positions_df, '물같음', '쫀쫀',
        '사용감 포지셔닝 맵 (물같음 vs 쫀쫀)',
        FIGURES_DIR / "3B_positioning_texture.png"
    )
    print(f"  - 사용감 맵 저장: {FIGURES_DIR / '3B_positioning_texture.png'}")

    # 인사이트
    pos_insights = get_positioning_insights(positions_df)
    print(f"\n  포지셔닝 리더:")
    print(f"    - 진정 대표: {pos_insights['진정_leader']}")
    print(f"    - 보습 대표: {pos_insights['보습_leader']}")
    print(f"    - 물같음 대표: {pos_insights['물같음_leader']}")
    print(f"    - 쫀쫀 대표: {pos_insights['쫀쫀_leader']}")

    # ----- 3-C: 포지셔닝 문장 -----
    print("\n  [3-C] 포지셔닝 문장 생성...")
    sentences = generate_all_sentences(df)
    print_positioning_sentences(sentences)

    # ----- 3-D: 재구매 이유 분석 -----
    print("\n  [3-D] 재구매 이유 분석...")
    rebuy_results = analyze_rebuy_reasons(df)

    if rebuy_results:
        # 비교 그래프
        fig_rebuy = plot_rebuy_comparison(rebuy_results, FIGURES_DIR / "3D_rebuy_comparison.png")
        print(f"  - 비교 그래프 저장: {FIGURES_DIR / '3D_rebuy_comparison.png'}")

        # 브랜드별 파이차트
        for brand, reasons in rebuy_results.items():
            safe_brand = brand.replace('/', '_')
            fig_pie = plot_rebuy_pie(reasons, brand, FIGURES_DIR / f"3D_rebuy_{safe_brand}.png")

        # 인사이트
        rebuy_insights = get_rebuy_insights(rebuy_results, df)
        print(f"\n  재구매 인사이트:")
        for brand, insight in rebuy_insights.items():
            print(f"    - {brand}: {insight['top_reason']} ({insight['top_rate']:.1f}%) - {insight['interpretation']}")
    else:
        print("  재구매 데이터가 없습니다.")

    # STRONG 재구매 분석
    strong_rebuy = analyze_strong_rebuy(df)
    if not strong_rebuy.empty:
        print(f"\n  STRONG 감성 재구매 분석 (진짜 팬덤):")
        print(strong_rebuy.to_string())

    # ----- 3-E: 전환 매트릭스 -----
    print("\n  [3-E] 고객 전환 시나리오 분석...")
    switch_matrix = build_switch_matrix(df)

    # 히트맵
    fig_switch = plot_switch_heatmap(switch_matrix, FIGURES_DIR / "3E_switch_matrix.png")
    print(f"  - 전환 매트릭스 저장: {FIGURES_DIR / '3E_switch_matrix.png'}")

    # 인사이트
    switch_insights = get_switch_insights(df, switch_matrix)
    print_switch_analysis(switch_insights)

    # ===== 완료 =====
    print("\n" + "=" * 60)
    print("    분석 완료!")
    print("=" * 60)
    print(f"\n결과 저장 위치:")
    print(f"  - 처리된 데이터: {OUTPUT_DIR / 'processed_reviews.csv'}")
    print(f"  - 시각화 그래프: {FIGURES_DIR}/")
    print(f"\n생성된 파일 목록:")

    for f in FIGURES_DIR.glob("*.png"):
        print(f"    - {f.name}")

    print("\n" + "=" * 60)

    # matplotlib 창 닫기
    import matplotlib.pyplot as plt
    plt.close('all')


if __name__ == "__main__":
    main()
