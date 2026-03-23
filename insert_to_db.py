# -*- coding: utf-8 -*-
"""
GPT 분석 결과를 Oracle DB에 적재
"""
import json
import sys
from os import getenv
from dotenv import load_dotenv
from sqlalchemy import text
from tqdm import tqdm

sys.stdout.reconfigure(encoding='utf-8')

# ===== DB 연결 (config/DB_connector.txt 사용) =====
load_dotenv('config/.env')
connector_path = getenv('DB_CONNECTOR', r'C:\Users\USER\Pythons\reportSystem\DB_connector\DB_connector.txt')

_ns = {}
with open(connector_path, 'r', encoding='utf-8') as f:
    exec(f.read(), _ns)
engine = _ns['engine']

# ===== DDL (시퀀스 + 테이블) =====
DROP_STATEMENTS = [
    "DROP TABLE TB_REVIEW_TAGS CASCADE CONSTRAINTS",
    "DROP TABLE TB_REVIEW_POSITIVE_POINTS CASCADE CONSTRAINTS",
    "DROP TABLE TB_REVIEW_PAIN_POINTS CASCADE CONSTRAINTS",
    "DROP TABLE TB_REVIEW_GPT_ANALYSIS CASCADE CONSTRAINTS",
    "DROP SEQUENCE SEQ_GPT_ANALYSIS",
    "DROP SEQUENCE SEQ_PAIN_POINTS",
    "DROP SEQUENCE SEQ_POSITIVE_POINTS",
    "DROP SEQUENCE SEQ_TAGS",
]

CREATE_STATEMENTS = [
    "CREATE SEQUENCE SEQ_GPT_ANALYSIS START WITH 1 INCREMENT BY 1",
    "CREATE SEQUENCE SEQ_PAIN_POINTS START WITH 1 INCREMENT BY 1",
    "CREATE SEQUENCE SEQ_POSITIVE_POINTS START WITH 1 INCREMENT BY 1",
    "CREATE SEQUENCE SEQ_TAGS START WITH 1 INCREMENT BY 1",
    """
    CREATE TABLE TB_REVIEW_GPT_ANALYSIS (
        ANALYSIS_ID   NUMBER        PRIMARY KEY,
        REVIEW_ID     NUMBER        NOT NULL,
        REVIEW_RATING NUMBER(1)     NOT NULL,
        SENTIMENT     VARCHAR2(3)   NOT NULL,
        TOKENS_INPUT  NUMBER,
        TOKENS_OUTPUT NUMBER,
        ANALYZED_AT   TIMESTAMP     DEFAULT SYSTIMESTAMP,
        CONSTRAINT FK_REVIEW FOREIGN KEY (REVIEW_ID)
            REFERENCES TB_CRAWLING_REVIEW(REVIEW_ID),
        CONSTRAINT CK_SENTIMENT CHECK (SENTIMENT IN ('POS', 'NEU', 'NEG'))
    )
    """,
    """
    CREATE TABLE TB_REVIEW_PAIN_POINTS (
        ID          NUMBER        PRIMARY KEY,
        ANALYSIS_ID NUMBER        NOT NULL,
        POINT_TEXT  VARCHAR2(400) NOT NULL,
        CATEGORY    VARCHAR2(200),
        CONSTRAINT FK_PAIN_ANALYSIS FOREIGN KEY (ANALYSIS_ID)
            REFERENCES TB_REVIEW_GPT_ANALYSIS(ANALYSIS_ID)
    )
    """,
    """
    CREATE TABLE TB_REVIEW_POSITIVE_POINTS (
        ID          NUMBER        PRIMARY KEY,
        ANALYSIS_ID NUMBER        NOT NULL,
        POINT_TEXT  VARCHAR2(400) NOT NULL,
        CATEGORY    VARCHAR2(200),
        CONSTRAINT FK_POS_ANALYSIS FOREIGN KEY (ANALYSIS_ID)
            REFERENCES TB_REVIEW_GPT_ANALYSIS(ANALYSIS_ID)
    )
    """,
    """
    CREATE TABLE TB_REVIEW_TAGS (
        ID          NUMBER        PRIMARY KEY,
        ANALYSIS_ID NUMBER        NOT NULL,
        TAG_TYPE    VARCHAR2(20)  NOT NULL,
        TAG_VALUE   VARCHAR2(100) NOT NULL,
        CONSTRAINT FK_TAG_ANALYSIS FOREIGN KEY (ANALYSIS_ID)
            REFERENCES TB_REVIEW_GPT_ANALYSIS(ANALYSIS_ID),
        CONSTRAINT CK_TAG_TYPE CHECK (TAG_TYPE IN ('BENEFIT', 'TEXTURE', 'USAGE', 'VALUE'))
    )
    """,
]

INDEX_STATEMENTS = [
    "CREATE INDEX IDX_GPT_REVIEW_ID ON TB_REVIEW_GPT_ANALYSIS(REVIEW_ID)",
    "CREATE INDEX IDX_GPT_SENTIMENT ON TB_REVIEW_GPT_ANALYSIS(SENTIMENT)",
    "CREATE INDEX IDX_PAIN_ANALYSIS ON TB_REVIEW_PAIN_POINTS(ANALYSIS_ID)",
    "CREATE INDEX IDX_PAIN_CATEGORY ON TB_REVIEW_PAIN_POINTS(CATEGORY)",
    "CREATE INDEX IDX_POS_ANALYSIS  ON TB_REVIEW_POSITIVE_POINTS(ANALYSIS_ID)",
    "CREATE INDEX IDX_POS_CATEGORY  ON TB_REVIEW_POSITIVE_POINTS(CATEGORY)",
    "CREATE INDEX IDX_TAG_ANALYSIS  ON TB_REVIEW_TAGS(ANALYSIS_ID)",
    "CREATE INDEX IDX_TAG_TYPE      ON TB_REVIEW_TAGS(TAG_TYPE, TAG_VALUE)",
]


def create_tables():
    """기존 테이블 DROP 후 재생성"""
    print("기존 테이블 삭제 중...")
    with engine.begin() as conn:
        for stmt in DROP_STATEMENTS:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass  # 없으면 무시

    print("테이블 생성 중...")
    with engine.begin() as conn:
        for stmt in CREATE_STATEMENTS:
            conn.execute(text(stmt))
        for stmt in INDEX_STATEMENTS:
            conn.execute(text(stmt))
    print("  완료")


def load_review_id_map():
    """원본 JSON에서 idx → REVIEW_ID 매핑 생성"""
    print("\nREVIEW_ID 매핑 로드...")
    with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    first_key = list(data.keys())[0]
    reviews = data[first_key]

    id_map = {}
    for i, review in enumerate(reviews):
        review_id = review.get('REVIEW_ID')
        if review_id:
            id_map[i] = int(review_id)

    print(f"  매핑 완료: {len(id_map):,}건")
    return id_map


def insert_analysis_data(gpt_data, id_map):
    """GPT 분석 결과 DB 적재"""
    print(f"\nDB 적재 시작: {len(gpt_data):,}건")

    skipped = 0
    inserted = 0

    with engine.begin() as conn:
        for item in tqdm(gpt_data, desc="DB 적재"):
            idx = item['idx']
            review_id = id_map.get(idx)

            if review_id is None:
                skipped += 1
                continue

            # 1) 메인 테이블 INSERT (시퀀스로 PK 생성)
            conn.execute(text("""
                INSERT INTO TB_REVIEW_GPT_ANALYSIS (ANALYSIS_ID, REVIEW_ID, REVIEW_RATING, SENTIMENT, TOKENS_INPUT, TOKENS_OUTPUT)
                VALUES (SEQ_GPT_ANALYSIS.NEXTVAL, :review_id, :rating, :sentiment, :tokens_in, :tokens_out)
            """), {
                'review_id': review_id,
                'rating': item['rating'],
                'sentiment': item.get('sentiment', 'NEU'),
                'tokens_in': item.get('tokens_input'),
                'tokens_out': item.get('tokens_output'),
            })

            result = conn.execute(text("SELECT SEQ_GPT_ANALYSIS.CURRVAL FROM DUAL"))
            analysis_id = result.scalar()

            # 2) Pain Points
            pain_points = item.get('pain_points', [])
            pain_categories = item.get('pain_categories', [])
            for i, pt in enumerate(pain_points):
                cat = pain_categories[i] if i < len(pain_categories) else None
                conn.execute(text("""
                    INSERT INTO TB_REVIEW_PAIN_POINTS (ID, ANALYSIS_ID, POINT_TEXT, CATEGORY)
                    VALUES (SEQ_PAIN_POINTS.NEXTVAL, :aid, :pt, :cat)
                """), {'aid': analysis_id, 'pt': pt[:200], 'cat': cat})

            # 3) Positive Points
            pos_points = item.get('positive_points', [])
            pos_categories = item.get('positive_categories', [])
            for i, pt in enumerate(pos_points):
                cat = pos_categories[i] if i < len(pos_categories) else None
                conn.execute(text("""
                    INSERT INTO TB_REVIEW_POSITIVE_POINTS (ID, ANALYSIS_ID, POINT_TEXT, CATEGORY)
                    VALUES (SEQ_POSITIVE_POINTS.NEXTVAL, :aid, :pt, :cat)
                """), {'aid': analysis_id, 'pt': pt[:200], 'cat': cat})

            # 4) Tags
            tag_map = {
                'BENEFIT': item.get('benefit_tags', []),
                'TEXTURE': item.get('texture_tags', []),
                'USAGE':   item.get('usage_tags', []),
                'VALUE':   item.get('value_tags', []),
            }
            for tag_type, tags in tag_map.items():
                for tag_val in tags:
                    conn.execute(text("""
                        INSERT INTO TB_REVIEW_TAGS (ID, ANALYSIS_ID, TAG_TYPE, TAG_VALUE)
                        VALUES (SEQ_TAGS.NEXTVAL, :aid, :ttype, :tval)
                    """), {'aid': analysis_id, 'ttype': tag_type, 'tval': tag_val[:50]})

            inserted += 1

    return inserted, skipped


def main():
    print("=" * 60)
    print("GPT 분석 결과 → Oracle DB 적재")
    print("=" * 60)

    # 1. 테이블 생성
    create_tables()

    # 2. REVIEW_ID 매핑
    id_map = load_review_id_map()

    # 3. GPT 분석 결과 로드
    gpt_path = 'output/gpt_analysis_categorized.json'
    print(f"\nGPT 분석 결과 로드: {gpt_path}")
    with open(gpt_path, 'r', encoding='utf-8') as f:
        gpt_data = json.load(f)
    print(f"  {len(gpt_data):,}건")

    # 4. DB 적재
    inserted, skipped = insert_analysis_data(gpt_data, id_map)

    # 5. 결과 요약
    print("\n" + "=" * 60)
    print("적재 완료!")
    print("=" * 60)
    print(f"  적재: {inserted:,}건")
    print(f"  스킵 (REVIEW_ID 없음): {skipped:,}건")

    # 6. 검증 쿼리
    print("\n[검증]")
    with engine.connect() as conn:
        row = conn.execute(text("SELECT COUNT(*) FROM TB_REVIEW_GPT_ANALYSIS")).scalar()
        print(f"  TB_REVIEW_GPT_ANALYSIS: {row:,}건")

        row = conn.execute(text("SELECT COUNT(*) FROM TB_REVIEW_PAIN_POINTS")).scalar()
        print(f"  TB_REVIEW_PAIN_POINTS: {row:,}건")

        row = conn.execute(text("SELECT COUNT(*) FROM TB_REVIEW_POSITIVE_POINTS")).scalar()
        print(f"  TB_REVIEW_POSITIVE_POINTS: {row:,}건")

        row = conn.execute(text("SELECT COUNT(*) FROM TB_REVIEW_TAGS")).scalar()
        print(f"  TB_REVIEW_TAGS: {row:,}건")

        print("\n[감성 분포]")
        rows = conn.execute(text("""
            SELECT SENTIMENT, COUNT(*) CNT,
                   ROUND(COUNT(*) * 100 / SUM(COUNT(*)) OVER (), 1) PCT
            FROM TB_REVIEW_GPT_ANALYSIS
            GROUP BY SENTIMENT ORDER BY SENTIMENT
        """)).fetchall()
        for r in rows:
            print(f"  {r[0]}: {r[1]:,}건 ({r[2]}%)")


if __name__ == "__main__":
    main()
