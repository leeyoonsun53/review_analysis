"""
아마존 리뷰 추가 EDA (USP 발굴 / 피드백 취합용)
이미 만든 분포(별점/감성/카테고리/시계열)와 다른 각도의 지표를 산출한다.
출력 수치를 보고서(md)에 인용한다.
"""

import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ASIN = "B07B32PL1C"
reviews = {r["review_id"]: r for r in json.loads(Path(f"data/amazon_reviews_{ASIN}.json").read_text(encoding="utf-8"))}
analysis = json.loads(Path("output/amazon_analysis.json").read_text(encoding="utf-8"))
N = len(analysis)


def body_of(rid):
    return (reviews.get(rid, {}).get("body") or "")


def title_of(rid):
    return (reviews.get(rid, {}).get("title") or "")


def text_of(rid):
    return (title_of(rid) + " " + body_of(rid)).lower()


def pct(x):
    return f"{x/N*100:.1f}%"


print("=" * 60)
print(f"총 분석 리뷰: {N}")

# 1) 국가 분포 + 국가별 감성
def parse_country(dr):
    m = re.search(r"Reviewed in (.+?) on ", dr) if isinstance(dr, str) else None
    return m.group(1).strip() if m else "?"

country_cnt = Counter()
country_neg = Counter()
for r in analysis:
    c = parse_country(reviews.get(r["review_id"], {}).get("date_raw"))
    country_cnt[c] += 1
    if r["sentiment"] == "NEG":
        country_neg[c] += 1
print("\n[국가 분포 / 부정 건수]")
for c, n in country_cnt.most_common(8):
    print(f"  {c:25s}: {n:>3}건 (부정 {country_neg.get(c,0)})")

# 2) 구매인증률
verified = sum(1 for r in analysis if reviews.get(r["review_id"], {}).get("verified_purchase"))
print(f"\n[구매인증] {verified}/{N} ({pct(verified)})")

# 3) 리뷰 길이(단어 수) 분포 + 감성별 평균
def wc(rid):
    return len(re.findall(r"\w+", body_of(rid)))
lengths = {r["review_id"]: wc(r["review_id"]) for r in analysis}
import statistics
alllen = list(lengths.values())
print(f"\n[리뷰 길이(단어)] 평균 {statistics.mean(alllen):.1f} / 중앙값 {statistics.median(alllen)} / 최대 {max(alllen)}")
for s in ["POS", "NEU", "NEG"]:
    vals = [lengths[r["review_id"]] for r in analysis if r["sentiment"] == s]
    if vals:
        print(f"  {s}: 평균 {statistics.mean(vals):.1f} 단어")
short = sum(1 for v in alllen if v <= 10)
print(f"  10단어 이하 단문 리뷰: {short}건 ({pct(short)})")

# 4) 강점 동시출현 (핵심 가치 번들)
strength_pairs = Counter()
for r in analysis:
    for a, b in combinations(sorted(set(r["strengths"])), 2):
        strength_pairs[(a, b)] += 1
print("\n[강점 동시출현 TOP10]")
for (a, b), n in strength_pairs.most_common(10):
    print(f"  {a} + {b}: {n}건")

# 5) 재구매/추천 의향률, 강점 보유율
has_repurchase = sum(1 for r in analysis if "재구매/추천" in r["strengths"])
print(f"\n[재구매/추천 명시] {has_repurchase}/{N} ({pct(has_repurchase)})")

# 6) 경쟁사/대체재 언급
competitors = {
    "Laneige(라네즈)": r"laneige|cream skin",
    "i'm from/rice(라이스)": r"i'?m from|rice toner|round lab|im from",
    "Hada Labo(하다라보)": r"hada labo|gokujyun",
    "MUJI(무인양품)": r"muji",
    "COSRX": r"cosrx",
    "CeraVe": r"cerave",
    "Haruharu": r"haruharu",
    "Tirtir": r"tirtir",
    "Some By Mi": r"some by mi",
    "Kikumasamune": r"kikumasamune",
    "snail mucin(달팽이)": r"snail|mucin",
    "Illiyoon(일리윤)": r"illiyoon|illiyon",
}
print("\n[경쟁사/대체재 언급 (리뷰 수)]")
for name, pat in competitors.items():
    cnt = sum(1 for r in analysis if re.search(pat, text_of(r["review_id"])))
    if cnt:
        print(f"  {name}: {cnt}건")

# 7) 활용 사례 (USP: 다용도)
usecases = {
    "바디 사용": r"\bbody\b|whole body|on my legs|on my neck|arms",
    "스프레이/미스트": r"spray|mist",
    "DIY 마스크/시트": r"diy|cotton (round|pad).*mask|sheet mask|toner pack|toner mask",
    "메이크업 베이스/프라이머": r"makeup|primer|foundation|under make|base|tinted",
    "애프터선/번": r"sunburn|after sun|burn",
    "눈가/다크서클": r"under (the )?eye|dark circle|eye area",
    "레이어링(여러 겹)": r"layer|layers|3-4 layers|multiple layers|seven layers",
}
print("\n[활용 사례 언급 (리뷰 수)]")
for name, pat in usecases.items():
    cnt = sum(1 for r in analysis if re.search(pat, text_of(r["review_id"])))
    print(f"  {name}: {cnt}건 ({pct(cnt)})")

# 8) 핵심 USP 키워드 언급률
usp_kw = {
    "유리알/광채(glass/glow/dewy/radiant)": r"glass skin|glow|dewy|radiant|luminous",
    "대용량/오래씀(huge/big/last/forever/year)": r"huge|big bottle|large|massive|jumbo|last(s)? (a |for)|forever|lasts? (a )?year|500\s?ml|16\.9|17\s?oz",
    "가성비(value/price/bang/cheap/afford)": r"value|worth|bang for|affordable|reasonable|price|cheap|deal",
    "보습(hydrat/moistur)": r"hydrat|moistur",
    "순함/저자극(gentle/sensitive/no irritat)": r"gentle|sensitive|no irritation|non-?irritat|doesn'?t irritate",
    "세라마이드/장벽(ceramide/barrier)": r"ceramide|barrier",
    "끈적임 없음(non-sticky/not sticky)": r"non[- ]?sticky|not sticky|without.*stick|no.*stick",
    "흡수(absorb/sinks)": r"absorb|sinks in|soaks",
}
print("\n[핵심 USP 키워드 언급률]")
for name, pat in usp_kw.items():
    cnt = sum(1 for r in analysis if re.search(pat, text_of(r["review_id"])))
    print(f"  {name}: {cnt}건 ({pct(cnt)})")

# 9) 향 관련 피드백
scent_total = sum(1 for r in analysis if re.search(r"scent|smell|fragrance|perfume|citrus|lemon|fruit ?loop|fruity pebble", text_of(r["review_id"])))
fragrance_free_req = sum(1 for r in analysis if re.search(r"fragrance[- ]?free|no fragrance|without (the )?(perfume|fragrance|scent)|wish.*(no|without).*(scent|smell|fragrance|perfume)|prefer.*no.*(smell|scent)", text_of(r["review_id"])))
citrus_lemon = sum(1 for r in analysis if re.search(r"citrus|lemon|limonene|linalool|fruit ?loop|fruity pebble|earl[- ]?grey", text_of(r["review_id"])))
print(f"\n[향 피드백] 향 언급 {scent_total}건({pct(scent_total)}) / 시트러스·레몬계 묘사 {citrus_lemon}건 / 무향 옵션 요청·향 불호 {fragrance_free_req}건")

# 10) 민감성/트러블 관련 (피드백)
issues = {
    "자극/화끈/붉은기(burn/sting/irritat/red)": r"burn|sting|irritat|redness|red bumps|flare",
    "트러블/여드름 유발(breakout/acne/cyst/pustule/hives)": r"broke me out|break ?out|breakout|cyst|pustule|hives|spots|blemish",
    "주사/로사세아": r"rosacea",
    "효과없음(no difference/nothing/didn't work)": r"no (real )?(difference|change)|nothing|didn'?t (do|work)|doesn'?t do much",
    "끈적임/흡수느림(greasy/sticky/tacky)": r"greasy|sticky|tacky",
    "용기/펌프 불편": r"pump|leak|broke|broken|hole|spill",
    "유통기한/배송": r"expir|expired|return|arrived|shipping|wrong size|300\s?ml",
    "정품 의심(fake/authentic/Mocchi)": r"fake|authentic|genuine|not the original|mocchi vs|counterfeit",
}
print("\n[피드백/이슈 언급 (리뷰 수)]")
for name, pat in issues.items():
    cnt = sum(1 for r in analysis if re.search(pat, text_of(r["review_id"])))
    print(f"  {name}: {cnt}건 ({pct(cnt)})")

# 11) 스킨타입 언급
skintypes = {
    "건성/수분부족": r"dry|dehydrat",
    "지성": r"oily",
    "복합성": r"combinat",
    "민감성": r"sensitive",
    "노화/성숙": r"mature|aging|older|wrinkle|50|40'?s|60",
    "여드름성": r"acne|breakout|blemish",
    "습진/아토피": r"eczema|dermatitis",
}
print("\n[스킨타입 언급 (리뷰 수)]")
for name, pat in skintypes.items():
    cnt = sum(1 for r in analysis if re.search(pat, text_of(r["review_id"])))
    print(f"  {name}: {cnt}건 ({pct(cnt)})")

# 12) 별점-감성 교차
import collections
cross = collections.defaultdict(Counter)
for r in analysis:
    star = reviews.get(r["review_id"], {}).get("rating")
    cross[star][r["sentiment"]] += 1
print("\n[별점 x 감성]")
for star in [5.0, 4.0, 3.0, 2.0, 1.0]:
    c = cross[star]
    print(f"  ⭐{int(star)}: POS {c.get('POS',0)} / NEU {c.get('NEU',0)} / NEG {c.get('NEG',0)}")
