# -*- coding: utf-8 -*-
import sys, os
from dotenv import load_dotenv
from sqlalchemy import text
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('config/.env')
_ns = {}
with open(os.getenv('DB_CONNECTOR'), 'r', encoding='utf-8') as f:
    exec(f.read(), _ns)
engine = _ns['engine']

with engine.begin() as conn:
    # 리뷰 컨텐츠가 없는 분석 건 찾기
    rows = conn.execute(text("""
        SELECT a.ANALYSIS_ID, a.REVIEW_ID
        FROM TB_REVIEW_GPT_ANALYSIS a
        JOIN TB_CRAWLING_REVIEW cr ON a.REVIEW_ID = cr.REVIEW_ID
        WHERE cr.REVIEW_CONTENT IS NULL OR TRIM(cr.REVIEW_CONTENT) IS NULL
    """)).fetchall()
    print(f"삭제 대상: {len(rows)}건")

    if rows:
        aids = [r[0] for r in rows]
        for aid in aids:
            conn.execute(text("DELETE FROM TB_REVIEW_TAGS WHERE ANALYSIS_ID = :aid"), {'aid': aid})
            conn.execute(text("DELETE FROM TB_REVIEW_POSITIVE_POINTS WHERE ANALYSIS_ID = :aid"), {'aid': aid})
            conn.execute(text("DELETE FROM TB_REVIEW_PAIN_POINTS WHERE ANALYSIS_ID = :aid"), {'aid': aid})
            conn.execute(text("DELETE FROM TB_REVIEW_GPT_ANALYSIS WHERE ANALYSIS_ID = :aid"), {'aid': aid})
        print(f"삭제 완료: {len(aids)}건")

    cnt = conn.execute(text("SELECT COUNT(*) FROM TB_REVIEW_GPT_ANALYSIS")).scalar()
    print(f"남은 분석 건수: {cnt:,}건")
