# -*- coding: utf-8 -*-
"""
GPT-4o-mini 기반 리뷰 분석 → Oracle DB 직접 적재
"""
import json
import os
import sys
import time
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy import text
from tqdm import tqdm

sys.stdout.reconfigure(encoding='utf-8')

# ===== 환경 변수 로드 =====
load_dotenv('config/.env')

api_key = os.getenv('CLASSIFICATION_REVIEW')
if not api_key:
    raise ValueError("CLASSIFICATION_REVIEW 환경변수가 설정되지 않았습니다.")

client = OpenAI(api_key=api_key)

# ===== DB 연결 =====
connector_path = os.getenv('DB_CONNECTOR', r'C:\Users\USER\Pythons\reportSystem\DB_connector\DB_connector.txt')
_ns = {}
with open(connector_path, 'r', encoding='utf-8') as f:
    exec(f.read(), _ns)
engine = _ns['engine']

# ===== 분석 프롬프트 =====
ANALYSIS_PROMPT = """화장품 리뷰 분석. JSON으로 응답.

리뷰: "{review}"
별점: {rating}점

{{
    "sentiment": "POS/NEU/NEG",
    "pain_points": ["불만점"],
    "positive_points": ["장점"],
    "benefit_tags": ["진정/보습/장벽/결/피지 중 해당"],
    "texture_tags": ["물같음/쫀쫀/끈적/흡수 중 해당"],
    "usage_tags": ["닦토/스킨팩/레이어링/바디 중 해당"],
    "value_tags": ["가성비/무난/애매/인생템 중 해당"]
}}

sentiment: 내용 기반. 별점 높아도 불만이면 NEG.
없는 항목은 빈 배열."""


def analyze_review(review_text, rating, max_retries=3):
    """단일 리뷰 GPT 분석"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": ANALYSIS_PROMPT.format(review=review_text[:500], rating=rating)}
                ],
                temperature=0.1,
                max_tokens=300
            )

            content = response.choices[0].message.content.strip()

            # JSON 파싱
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]

            result = json.loads(content)
            tokens_in = response.usage.prompt_tokens
            tokens_out = response.usage.completion_tokens

            return result, tokens_in, tokens_out, None

        except json.JSONDecodeError:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return None, 0, 0, "json_error"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None, 0, 0, str(e)

    return None, 0, 0, "max_retries"


def insert_to_db(conn, review_id, rating, sentiment, tokens_in, tokens_out, result):
    """분석 결과 1건을 DB에 적재"""
    # 1) 메인 테이블
    conn.execute(text("""
        INSERT INTO TB_REVIEW_GPT_ANALYSIS (ANALYSIS_ID, REVIEW_ID, REVIEW_RATING, SENTIMENT, TOKENS_INPUT, TOKENS_OUTPUT)
        VALUES (SEQ_GPT_ANALYSIS.NEXTVAL, :review_id, :rating, :sentiment, :tokens_in, :tokens_out)
    """), {
        'review_id': review_id,
        'rating': rating,
        'sentiment': sentiment,
        'tokens_in': tokens_in,
        'tokens_out': tokens_out,
    })

    aid = conn.execute(text("SELECT SEQ_GPT_ANALYSIS.CURRVAL FROM DUAL")).scalar()

    # 2) Pain Points
    for pt in result.get('pain_points', []):
        conn.execute(text("""
            INSERT INTO TB_REVIEW_PAIN_POINTS (ID, ANALYSIS_ID, POINT_TEXT)
            VALUES (SEQ_PAIN_POINTS.NEXTVAL, :aid, :pt)
        """), {'aid': aid, 'pt': pt[:200]})

    # 3) Positive Points
    for pt in result.get('positive_points', []):
        conn.execute(text("""
            INSERT INTO TB_REVIEW_POSITIVE_POINTS (ID, ANALYSIS_ID, POINT_TEXT)
            VALUES (SEQ_POSITIVE_POINTS.NEXTVAL, :aid, :pt)
        """), {'aid': aid, 'pt': pt[:200]})

    # 4) Tags
    tag_map = {
        'BENEFIT': result.get('benefit_tags', []),
        'TEXTURE': result.get('texture_tags', []),
        'USAGE':   result.get('usage_tags', []),
        'VALUE':   result.get('value_tags', []),
    }
    for tag_type, tags in tag_map.items():
        for tag_val in tags:
            conn.execute(text("""
                INSERT INTO TB_REVIEW_TAGS (ID, ANALYSIS_ID, TAG_TYPE, TAG_VALUE)
                VALUES (SEQ_TAGS.NEXTVAL, :aid, :ttype, :tval)
            """), {'aid': aid, 'ttype': tag_type, 'tval': tag_val[:50]})

    return aid


def get_analyzed_review_ids(conn):
    """이미 분석 완료된 REVIEW_ID 목록 조회"""
    rows = conn.execute(text("SELECT REVIEW_ID FROM TB_REVIEW_GPT_ANALYSIS")).fetchall()
    return {r[0] for r in rows}


def main():
    print("=" * 70)
    print("GPT-4o-mini 리뷰 분석 → Oracle DB 직접 적재")
    print("=" * 70)

    # 분석 대상 리뷰 조회 (DB에서 직접)
    print("\n분석 대상 리뷰 조회...")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT cr.REVIEW_ID, cr.REVIEW_CONTENT, cr.REVIEW_RATING
            FROM TB_CRAWLING_REVIEW cr
            WHERE cr.REVIEW_DATE >= TO_DATE('20250101', 'YYYYMMDD')
              AND cr.PLATFORM_CODE = 'OLIVEYOUNG'
              AND cr.PRODUCT_NAME LIKE '%모찌%토너%'
              AND NOT EXISTS (SELECT 'x' FROM TB_REVIEW_GPT_ANALYSIS a WHERE a.REVIEW_ID = cr.REVIEW_ID)
            ORDER BY cr.REVIEW_ID
        """)).fetchall()

    pending = [{'review_id': r[0], 'content': r[1], 'rating': r[2]} for r in rows]
    print(f"  미분석 리뷰: {len(pending):,}건")

    if not pending:
        print("\n모든 리뷰가 이미 분석되었습니다.")
        return

    # 분석 실행
    print(f"\n{len(pending):,}건 분석 시작...")
    print(f"예상 시간: {len(pending) / 3 / 60:.0f}분")

    total_tokens = 0
    inserted = 0
    errors = 0
    commit_interval = 50

    try:
        with engine.begin() as conn:
            for i, rev in enumerate(tqdm(pending, desc="GPT 분석 + DB 적재")):
                review_text = str(rev['content']) if rev['content'] else ''
                rating = int(rev['rating']) if rev['rating'] else 3

                result, tokens_in, tokens_out, error = analyze_review(review_text, rating)
                total_tokens += tokens_in + tokens_out

                if result:
                    sentiment = result.get('sentiment', 'NEU')
                else:
                    errors += 1
                    sentiment = 'NEU'
                    result = {
                        'pain_points': [], 'positive_points': [],
                        'benefit_tags': [], 'texture_tags': [],
                        'usage_tags': [], 'value_tags': []
                    }

                insert_to_db(conn, rev['review_id'], rating, sentiment, tokens_in, tokens_out, result)
                inserted += 1

                # 진행 로그
                if (i + 1) % commit_interval == 0:
                    cost = total_tokens * 0.15 / 1_000_000 + total_tokens * 0.6 / 1_000_000
                    tqdm.write(f"  {inserted}/{len(pending)} | 토큰: {total_tokens:,} | 비용: ${cost:.2f} | 에러: {errors}")

                # Rate limit 방지
                time.sleep(0.3)

    except KeyboardInterrupt:
        print("\n\n중단됨. 트랜잭션 커밋 완료된 건까지 저장됩니다.")

    # 결과 요약
    print("\n" + "=" * 70)
    print("분석 완료!")
    print("=" * 70)
    print(f"  적재: {inserted:,}건")
    print(f"  에러: {errors}건")
    print(f"  토큰: {total_tokens:,}")

    cost = total_tokens * 0.15 / 1_000_000 + total_tokens * 0.6 / 1_000_000
    print(f"  비용: ${cost:.2f}")

    # 검증
    print("\n[검증]")
    with engine.connect() as conn:
        row = conn.execute(text("SELECT COUNT(*) FROM TB_REVIEW_GPT_ANALYSIS")).scalar()
        print(f"  TB_REVIEW_GPT_ANALYSIS: {row:,}건")

        print("\n[감성 분포]")
        rows = conn.execute(text("""
            SELECT SENTIMENT, COUNT(*) CNT,
                   ROUND(COUNT(*) * 100 / SUM(COUNT(*)) OVER (), 1) PCT
            FROM TB_REVIEW_GPT_ANALYSIS
            GROUP BY SENTIMENT ORDER BY SENTIMENT
        """)).fetchall()
        for r in rows:
            print(f"  {r[0]}: {r[1]:,}건 ({r[2]}%)")

        print("\n[토큰 사용량]")
        row = conn.execute(text("""
            SELECT SUM(TOKENS_INPUT), SUM(TOKENS_OUTPUT),
                   ROUND(AVG(TOKENS_INPUT)), ROUND(AVG(TOKENS_OUTPUT))
            FROM TB_REVIEW_GPT_ANALYSIS
            WHERE TOKENS_INPUT IS NOT NULL
        """)).fetchone()
        if row[0]:
            cost_in = row[0] * 0.15 / 1_000_000
            cost_out = row[1] * 0.60 / 1_000_000
            print(f"  Input:  {row[0]:,} (건당 {row[2]:,}) → ${cost_in:.2f}")
            print(f"  Output: {row[1]:,} (건당 {row[3]:,}) → ${cost_out:.2f}")
            print(f"  합계 비용: ${cost_in + cost_out:.2f}")


if __name__ == "__main__":
    main()
