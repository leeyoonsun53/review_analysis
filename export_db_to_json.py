# -*- coding: utf-8 -*-
"""
DB GPT 분석 결과 → JSON 파일 내보내기
Streamlit 대시보드용 데이터 갱신
"""
import json
import re
import sys
import os
from collections import Counter, defaultdict
from dotenv import load_dotenv
from sqlalchemy import text
from tqdm import tqdm

sys.stdout.reconfigure(encoding='utf-8')


# ===== 제품명 정규화 =====
PRODUCT_NAME_MAP = {
    '토리든 다이브인 저분자 히알루론산 토너': '토리든 다이브인 토너',
    '라운드랩 독도 토너': '라운드랩 독도 토너',
    '라운드랩 독도토너': '라운드랩 독도 토너',
    '브링그린 티트리시카수딩토너': '브링그린 티트리시카 토너',
    '브링그린 티트리 시카 수딩 토너': '브링그린 티트리시카 토너',
    '브링그린 티트리시카 수딩 토너': '브링그린 티트리시카 토너',
    '에스네이처 아쿠아 오아시스 토너': '에스네이처 아쿠아 토너',
    '아누아 어성초 수딩 토너': '아누아 어성초 토너',
    '아누아 어성초 77 수딩 토너': '아누아 어성초 토너',
    '아비브 어성초 카밍 토너 스킨부스터': '아비브 어성초 토너',
    '토니모리 원더 세라마이드 모찌 토너': '토니모리 모찌 토너',
    '토니모리 원더 비건 라벨 세라마이드 모찌 토너': '토니모리 모찌 토너',
    '토니모리 원더 세라마이드 모찌 토너 마리 에디션': '토니모리 모찌 토너',
    '토니모리 원더 세라마이드 모찌 에멀전': '토니모리 모찌 에멀전',
    '토니모리 원더 세라마이드 모찌 수분 크림': '토니모리 모찌 수분크림',
    '토니모리 원더 세라마이드 모찌 마스크 시트': '토니모리 모찌 마스크시트',
    '토니모리 원더 세라마이드 모찌 팩투폼': '토니모리 모찌 팩투폼',
    '토니모리 원더 세라마이드 모찌 팩투폼 마리 에디션': '토니모리 모찌 팩투폼',
    '토니모리 원더 세라마이드 모찌 팩투 클렌징폼 마리 에디션': '토니모리 모찌 팩투폼',
}


def normalize_product_name(name):
    """제품명 정규화"""
    if not name:
        return name

    s = str(name)

    # 1) [...] 대괄호 태그 제거
    s = re.sub(r'\[.*?\]', '', s)

    # 2) (...) 괄호 정보 제거
    s = re.sub(r'\(.*?\)', '', s)

    # 3) 용량 제거: 500ml, 250mL, 20g 등
    s = re.sub(r'\d+\s*[mM][lL]', '', s)
    s = re.sub(r'\d+\s*g\b', '', s)

    # 4) 쿠팡 수량 제거: , 1개 / , 7개
    s = re.sub(r',\s*\d+개', '', s)

    # 5) 기획/단품 제거
    s = re.sub(r'기획.*', '', s)
    s = re.sub(r'단품.*', '', s)

    # 6) 숫자 잔여물 (1025, 77, 1+1 등)
    s = re.sub(r'\b1025\b', '', s)
    s = re.sub(r'\b77\b', '', s)
    s = re.sub(r'\d\+\d', '', s)

    # 7) 어워즈, 한정, 더블 등 부가 텍스트
    s = re.sub(r'어워즈.*', '', s)
    s = re.sub(r'더블.*', '', s)

    # 8) 공백 정리
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.rstrip(',').strip()

    # 9) 매핑 테이블에서 매칭
    for key, val in PRODUCT_NAME_MAP.items():
        if key in s:
            return val

    return s if s else str(name)

# ===== DB 연결 =====
load_dotenv('config/.env')
connector_path = os.getenv('DB_CONNECTOR', r'C:\Users\USER\Pythons\reportSystem\DB_connector\DB_connector.txt')
_ns = {}
with open(connector_path, 'r', encoding='utf-8') as f:
    exec(f.read(), _ns)
engine = _ns['engine']


def export_analysis():
    """DB에서 GPT 분석 결과를 JSON으로 내보내기"""
    print("=" * 60)
    print("DB → JSON 내보내기")
    print("=" * 60)

    # 1) 메인 분석 데이터 조회
    print("\n[1] GPT 분석 데이터 조회...")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT a.ANALYSIS_ID, a.REVIEW_ID, a.REVIEW_RATING, a.SENTIMENT,
                   cr.PRODUCT_NAME, cr.REVIEW_CONTENT, cr.REVIEW_DATE,
                   cr.REVIEWER_INFO, cr.ADDITIONAL_INFO, cr.TAGS,
                   cr.PLATFORM_CODE
            FROM TB_REVIEW_GPT_ANALYSIS a
            JOIN TB_CRAWLING_REVIEW cr ON a.REVIEW_ID = cr.REVIEW_ID
            ORDER BY a.ANALYSIS_ID
        """)).fetchall()

    print(f"  분석 건수: {len(rows):,}건")

    # analysis_id → index 매핑
    analysis_map = {}
    results = []
    for i, r in enumerate(rows):
        analysis_id = r[0]
        analysis_map[analysis_id] = i
        results.append({
            'idx': i,
            'analysis_id': analysis_id,
            'review_id': r[1],
            'rating': r[2],
            'sentiment': r[3],
            'product_name': r[4],
            'review_content': r[5],
            'review_date': str(r[6]) if r[6] else None,
            'reviewer_info': r[7],
            'additional_info': r[8],
            'purchase_tag': r[9],
            'platform_code': 'OLIVEYOUNG' if r[10] and 'OLIVEYOUNG' in str(r[10]).upper() else r[10],
            'pain_points': [],
            'positive_points': [],
            'benefit_tags': [],
            'texture_tags': [],
            'usage_tags': [],
            'value_tags': [],
            'pain_categories': [],
            'positive_categories': [],
        })

    # 2) Pain Points 조회
    print("[2] Pain Points 조회...")
    with engine.connect() as conn:
        pain_rows = conn.execute(text("""
            SELECT ANALYSIS_ID, POINT_TEXT, CATEGORY
            FROM TB_REVIEW_PAIN_POINTS
            ORDER BY ANALYSIS_ID
        """)).fetchall()

    for r in pain_rows:
        idx = analysis_map.get(r[0])
        if idx is not None:
            results[idx]['pain_points'].append(r[1])
            if r[2]:
                results[idx]['pain_categories'].append(r[2])

    print(f"  {len(pain_rows):,}건")

    # 3) Positive Points 조회
    print("[3] Positive Points 조회...")
    with engine.connect() as conn:
        pos_rows = conn.execute(text("""
            SELECT ANALYSIS_ID, POINT_TEXT, CATEGORY
            FROM TB_REVIEW_POSITIVE_POINTS
            ORDER BY ANALYSIS_ID
        """)).fetchall()

    for r in pos_rows:
        idx = analysis_map.get(r[0])
        if idx is not None:
            results[idx]['positive_points'].append(r[1])
            if r[2]:
                results[idx]['positive_categories'].append(r[2])

    print(f"  {len(pos_rows):,}건")

    # 4) Tags 조회
    print("[4] Tags 조회...")
    tag_type_map = {
        'BENEFIT': 'benefit_tags',
        'TEXTURE': 'texture_tags',
        'USAGE': 'usage_tags',
        'VALUE': 'value_tags',
    }
    with engine.connect() as conn:
        tag_rows = conn.execute(text("""
            SELECT ANALYSIS_ID, TAG_TYPE, TAG_VALUE
            FROM TB_REVIEW_TAGS
            ORDER BY ANALYSIS_ID
        """)).fetchall()

    for r in tag_rows:
        idx = analysis_map.get(r[0])
        if idx is not None:
            col = tag_type_map.get(r[1])
            if col:
                results[idx][col].append(r[2])

    print(f"  {len(tag_rows):,}건")

    # 5) 카테고리 채우기 (CATEGORY가 NULL인 경우 point_text를 그대로 사용)
    print("\n[5] 카테고리 보정...")
    for item in results:
        if not item['pain_categories'] and item['pain_points']:
            item['pain_categories'] = list(set(item['pain_points']))
        if not item['positive_categories'] and item['positive_points']:
            item['positive_categories'] = list(set(item['positive_points']))

    # 6) JSON 저장 (Streamlit용)
    # gpt_analysis_categorized.json - Streamlit이 읽는 메인 파일
    export_data = []
    for item in results:
        export_data.append({
            'idx': item['idx'],
            'brand': normalize_product_name(item['product_name']),
            'rating': item['rating'],
            'sentiment': item['sentiment'],
            'pain_points': item['pain_points'],
            'positive_points': item['positive_points'],
            'benefit_tags': item['benefit_tags'],
            'texture_tags': item['texture_tags'],
            'usage_tags': item['usage_tags'],
            'value_tags': item['value_tags'],
            'pain_categories': item['pain_categories'],
            'positive_categories': item['positive_categories'],
        })

    output_path = 'output/gpt_analysis_categorized.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    print(f"\n  저장: {output_path} ({len(export_data):,}건)")

    # 7) 리뷰 데이터 CSV 저장 (Streamlit이 읽는 리뷰 원본)
    print("\n[6] 리뷰 데이터 CSV 저장...")
    import pandas as pd
    review_records = []
    for item in results:
        review_records.append({
            'BRAND_NAME': normalize_product_name(item['product_name']),
            'REVIEW_CONTENT': item['review_content'],
            'REVIEW_RATING': item['rating'],
            'REVIEW_DATE': item['review_date'],
            'REVIEWER_INFO': item['reviewer_info'],
            'REVIEW_ADDITIONAL_INFO': item['additional_info'],
            'PURCHASE_TAG': item['purchase_tag'],
            'REVIEW_ID': item['review_id'],
            'PLATFORM_CODE': item['platform_code'],
        })

    df = pd.DataFrame(review_records)
    csv_path = 'data/oliveyoung_reviews_processed.csv'
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"  저장: {csv_path} ({len(df):,}건)")

    # 8) 통계 요약
    print("\n" + "=" * 60)
    print("내보내기 완료!")
    print("=" * 60)
    print(f"  총 리뷰: {len(results):,}건")

    # 감성 분포
    sent_counts = Counter(item['sentiment'] for item in results)
    print(f"\n[감성 분포]")
    for s in ['POS', 'NEU', 'NEG']:
        cnt = sent_counts.get(s, 0)
        pct = cnt / len(results) * 100
        print(f"  {s}: {cnt:,}건 ({pct:.1f}%)")

    # 브랜드 분포
    brand_counts = Counter(normalize_product_name(item['product_name']) for item in results)
    print(f"\n[브랜드별 리뷰 수]")
    for brand, cnt in brand_counts.most_common():
        print(f"  {brand}: {cnt:,}건")

    # Pain/Positive TOP 5
    pain_all = Counter()
    pos_all = Counter()
    for item in results:
        for p in item['pain_points']:
            pain_all[p] += 1
        for p in item['positive_points']:
            pos_all[p] += 1

    print(f"\n[Pain Points TOP 5]")
    for p, cnt in pain_all.most_common(5):
        print(f"  {p}: {cnt:,}건")

    print(f"\n[Positive Points TOP 5]")
    for p, cnt in pos_all.most_common(5):
        print(f"  {p}: {cnt:,}건")


if __name__ == "__main__":
    export_analysis()
