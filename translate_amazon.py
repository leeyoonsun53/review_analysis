"""
아마존 리뷰 한글 번역 하네스 (Claude 인라인 번역용, 재개 가능)

번역 주체는 Claude(나)다. 이 스크립트는 입출력만 담당한다.
번역 결과는 output/amazon_analysis.json 의 각 레코드에 translation_ko 필드로 누적된다.

  python translate_amazon.py next [N]      아직 번역 안 된 리뷰 N(기본 20)개 출력
  python translate_amazon.py merge <path>  번역 배치 JSON([{review_id, translation_ko}, ...]) 머지
  python translate_amazon.py stats         번역 진행률
"""

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ASIN = "B07B32PL1C"
REVIEWS = Path("data") / f"amazon_reviews_{ASIN}.json"
OUT = Path("output") / "amazon_analysis.json"


def load_reviews():
    return {r["review_id"]: r for r in json.loads(REVIEWS.read_text(encoding="utf-8"))}


def load_out():
    return json.loads(OUT.read_text(encoding="utf-8"))


def save_out(recs):
    OUT.write_text(json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_next(n=20):
    reviews = load_reviews()
    recs = load_out()
    todo = [r for r in recs if not r.get("translation_ko")]
    print(f"# 미번역 {len(todo)} / 전체 {len(recs)}  (이번 출력 {min(n, len(todo))}개)")
    print("# 번역 결과를 output/_tbatch.json 으로 저장 후 merge 실행")
    print("-" * 70)
    for r in todo[:n]:
        rid = r["review_id"]
        rv = reviews.get(rid, {})
        title = (rv.get("title") or "").replace("\n", " ").strip()
        body = (rv.get("body") or "").replace("\n", " ").strip()
        print(f"[{rid}] (제목) {title}")
        print(f"  (본문) {body}")
        print()


def cmd_merge(path):
    batch = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(batch, dict):
        batch = [batch]
    recs = load_out()
    idx = {r["review_id"]: i for i, r in enumerate(recs)}
    added, warn = 0, []
    for b in batch:
        rid = b.get("review_id")
        tr = (b.get("translation_ko") or "").strip()
        if rid not in idx:
            warn.append(f"알 수 없는 review_id: {rid}")
            continue
        if not tr:
            warn.append(f"빈 번역: {rid}")
            continue
        recs[idx[rid]]["translation_ko"] = tr
        added += 1
    save_out(recs)
    done = sum(1 for r in recs if r.get("translation_ko"))
    print(f"머지: {added}건, 누적 번역 {done}/{len(recs)}")
    for w in warn[:30]:
        print("  ⚠️", w)


def cmd_stats():
    recs = load_out()
    done = sum(1 for r in recs if r.get("translation_ko"))
    print(f"번역 완료: {done}/{len(recs)}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "next":
        cmd_next(int(sys.argv[2]) if len(sys.argv) > 2 else 20)
    elif cmd == "merge":
        cmd_merge(sys.argv[2])
    else:
        cmd_stats()
