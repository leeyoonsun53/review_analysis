"""
아마존 리뷰 감성·강점/약점 분류 하네스 (Claude 인라인 분류용, 재개 가능)

분류 주체는 Claude(나)다. 이 스크립트는 입출력만 담당한다.

서브커맨드:
  python analyze_amazon.py next [N]      아직 분류 안 된 리뷰 N(기본 10)개 출력
  python analyze_amazon.py merge <path>  배치 결과 JSON을 누적 저장(review_id dedup)
  python analyze_amazon.py stats         진행률 + 강점/약점 카테고리 분포

산출물: output/amazon_analysis.json  (리뷰별 {review_id, sentiment, strengths, weaknesses, evidence})
"""

import json
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ASIN = "B07B32PL1C"
REVIEWS = Path("data") / f"amazon_reviews_{ASIN}.json"
OUT = Path("output") / "amazon_analysis.json"

VALID_SENTIMENT = {"POS", "NEU", "NEG"}
STRENGTH_CATS = [
    "보습/촉촉", "순함/저자극", "대용량/오래씀", "가성비/가격만족", "흡수력",
    "광채/윤기", "진정/장벽케어", "제형/텍스처", "향 만족", "산뜻함",
    "재구매/추천", "용기/디자인", "기타",
]
WEAKNESS_CATS = [
    "트러블/뾰루지", "효과없음", "제형불호", "향 불호", "자극/따가움", "끈적임",
    "가격부담", "용기불편", "흡수느림", "건조함", "배송/포장", "기타",
]


def load_reviews():
    return json.loads(REVIEWS.read_text(encoding="utf-8"))


def load_out():
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return []


def save_out(records):
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_next(n=10):
    reviews = load_reviews()
    done = {r["review_id"] for r in load_out()}
    todo = [r for r in reviews if r["review_id"] not in done]
    print(f"# 남은 미분류: {len(todo)} / 전체 {len(reviews)}  (이번 출력 {min(n, len(todo))}개)")
    print("# 아래를 분류해 output/_batch.json 으로 저장 후 `merge` 실행")
    print("-" * 70)
    for r in todo[:n]:
        body = (r.get("body") or "").replace("\n", " ").strip()
        title = (r.get("title") or "").replace("\n", " ").strip()
        print(f"[{r['review_id']}] ⭐{r['rating']} ({r['star_filter']})")
        print(f"  TITLE: {title}")
        print(f"  BODY : {body}")
        print()


def cmd_merge(path):
    batch = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(batch, dict):
        batch = [batch]
    records = load_out()
    idx = {r["review_id"]: i for i, r in enumerate(records)}

    valid_ids = {r["review_id"] for r in load_reviews()}
    added, updated, warnings = 0, 0, []
    for b in batch:
        rid = b.get("review_id")
        if rid not in valid_ids:
            warnings.append(f"알 수 없는 review_id: {rid}")
            continue
        rec = {
            "review_id": rid,
            "sentiment": b.get("sentiment", "NEU"),
            "strengths": b.get("strengths", []) or [],
            "weaknesses": b.get("weaknesses", []) or [],
            "evidence": b.get("evidence", ""),
        }
        if rec["sentiment"] not in VALID_SENTIMENT:
            warnings.append(f"{rid}: 잘못된 sentiment '{rec['sentiment']}' -> NEU")
            rec["sentiment"] = "NEU"
        for c in rec["strengths"]:
            if c not in STRENGTH_CATS:
                warnings.append(f"{rid}: 미정의 강점 '{c}'")
        for c in rec["weaknesses"]:
            if c not in WEAKNESS_CATS:
                warnings.append(f"{rid}: 미정의 약점 '{c}'")
        if rid in idx:
            records[idx[rid]] = rec
            updated += 1
        else:
            records.append(rec)
            idx[rid] = len(records) - 1
            added += 1

    save_out(records)
    print(f"머지 완료: 신규 {added}, 갱신 {updated}, 누적 {len(records)}")
    if warnings:
        print("⚠️ 경고:")
        for w in warnings[:30]:
            print("  -", w)


def cmd_stats():
    reviews = load_reviews()
    records = load_out()
    print(f"진행률: {len(records)} / {len(reviews)}")
    if not records:
        return
    sent = Counter(r["sentiment"] for r in records)
    print("\n[감성]")
    for s in ["POS", "NEU", "NEG"]:
        c = sent.get(s, 0)
        print(f"  {s}: {c:>4}건 ({c/len(records)*100:5.1f}%)")

    sc = Counter()
    for r in records:
        sc.update(r["strengths"])
    print("\n[강점 카테고리]")
    for cat, c in sc.most_common():
        print(f"  {cat:14s}: {c:>4}건")

    wc = Counter()
    for r in records:
        wc.update(r["weaknesses"])
    print("\n[약점 카테고리]")
    for cat, c in wc.most_common():
        print(f"  {cat:14s}: {c:>4}건")

    # 무결성
    ids = {r["review_id"] for r in records}
    valid = {r["review_id"] for r in reviews}
    missing = valid - ids
    print(f"\n미분류 {len(missing)}건, 중복 {len(records)-len(ids)}건")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "next":
        cmd_next(int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif cmd == "merge":
        cmd_merge(sys.argv[2])
    elif cmd == "stats":
        cmd_stats()
    else:
        print("사용법: next [N] | merge <path> | stats")
