# -*- coding: utf-8 -*-
"""
PAIN_POINTS, POSITIVE_POINTS 카테고리화 (패턴 확장 버전)
"""
import json
import re
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# ===== 카테고리 정의 (확장) =====

# PAIN_POINTS 카테고리
PAIN_CATEGORIES = {
    "건조/보습부족": [
        "건조", "보습.*부족", "수분.*부족", "촉촉.*부족", "촉촉.*않", "속건조",
        "당김", "땡김", "겨울.*건조", "보습력.*부족", "보습감.*부족", "수분감.*부족",
        "건성.*비추", "건성.*추천.*않", "수분.*충전.*부족", "보습.*효과.*부족",
        "겨울철.*보습", "속보습.*부족", "수분충전.*부족", "촉촉.*느낌.*부족",
        "수분.*없", "보습이.*부족", "보습력이.*부족", "보습력이.*약", "수분.*안",
        "속수분.*부족", "보습.*좋지.*않", "수분고정력.*부족", "보습.*오래.*않",
        "보습.*지속.*않", "수분.*날아"
    ],
    "자극/트러블": [
        "자극", "따가", "따끔", "트러블", "여드름", "뾰루지", "좁쌀", "뒤집",
        "붉어", "홍조", "가려", "간지", "알레르기", "피부.*맞지", "안.*맞",
        "화끈", "화한", "시림", "시려", "빨개", "발적", "모낭염", "피부.*민감",
        "아토피", "각질.*부각", "벗겨", "뿌득", "민감.*피부.*자극", "얼굴.*자극",
        "피부.*상태.*악화", "피부.*악화", "티트리.*민감", "성분.*민감"
    ],
    "가격": [
        "비싸", "비쌈", "가격.*상승", "가격.*인상", "가격$", "비싼.*느낌",
        "가격.*불만", "가성비.*부족", "가격.*대비", "가격.*오르", "돈.*낭비",
        "가격.*착한.*않"
    ],
    "효과부족": [
        "효과.*부족", "효과.*없", "효과.*미비", "효과.*불확", "기대.*이하",
        "기대.*미치", "진정.*부족", "드라마틱.*부족", "진정효과.*부족",
        "진정.*효과.*미비", "트러블.*효과.*없", "여드름.*효과.*없", "큰.*효과.*없",
        "효능.*부족", "효과.*감소", "특별.*효과.*부족", "기능.*부족",
        "각질.*제거.*효과.*부족", "쿨링.*효과.*부족", "피지.*감소.*효과",
        "개선.*효과.*부족", "완화.*효과.*부족", "토너.*효과.*부족",
        "효과.*의문", "효과.*미미", "변화.*없", "딱히.*효과", "특별.*기능.*없",
        "효과.*모르겠", "쿨링감.*부족", "쿨링감.*약", "효과.*느끼지.*못",
        "보습이.*약", "피지.*정리.*부족"
    ],
    "사용감불편": [
        "끈적", "기름", "유분", "무거", "답답", "미끌", "겉돌", "흡수.*안",
        "흡수.*느", "흡수.*문제", "흡수력.*부족", "번들", "기름진", "흘러내림",
        "점도", "묽", "물.*같", "워터리", "흡수.*잘.*안", "발림성",
        "미끄덩", "바르기.*불편", "흡수.*속도"
    ],
    "향/냄새": [
        "냄새", "향.*강함", "향.*별로", "알코올.*냄새", "알콜.*냄새", "향.*호불호",
        "향.*세다", "향.*거슬", "향.*아쉽", "냄새.*이상", "냄새.*불쾌", "향$",
        "향.*인공"
    ],
    "용량/포장": [
        "용량.*부족", "용량.*적", "양.*적", "대용량.*부족", "펌프", "뚜껑",
        "용기.*불편", "포장.*불량", "내용물.*유출", "사이즈.*작", "휴대.*불편",
        "용량.*작", "빨리.*소모", "빠른.*소모"
    ],
    "재구매부정": [
        "재구매.*없", "재구매.*불확", "재구매.*고민", "재구매.*낮", "구매.*후회",
        "사용.*중단", "손.*안.*감"
    ],
    "눈자극": [
        "눈.*따가", "눈.*들어가", "눈시림", "눈.*아픔", "눈.*시려", "눈이.*따"
    ],
    "배송/서비스": [
        "배송.*문제", "배송.*느림", "배송.*지연", "증정품.*미제공", "증정품.*소진",
        "교환.*대기", "리뷰.*등록.*오류", "품절", "일시품절", "재고.*부족"
    ],
    "피부타입불일치": [
        "지성.*적합.*않", "건성.*적합.*않", "복합.*비추", "민감.*부적합",
        "피부.*타입.*맞지", "지성.*맞지", "건성.*맞지", "수부지.*과한",
        "피부.*불일치"
    ],
    "애매함": [
        "애매", "밍밍", "특징.*없", "그냥.*그", "별로"
    ],
}

# POSITIVE_POINTS 카테고리
POSITIVE_CATEGORIES = {
    "보습/수분": [
        "촉촉", "수분", "보습", "속건조.*개선", "당김.*없", "건조.*없", "건조.*않",
        "수분.*충전", "수분.*공급", "속보습", "수분충전", "보습감", "보습력",
        "촉촉하다", "수분감.*좋", "보습.*잘", "수분.*채", "촉촉해", "수분.*잡",
        "속건조.*잡", "수분.*가득", "촉촉.*유지"
    ],
    "순함/저자극": [
        "순함", "순하다", "순해", "자극.*없", "저자극", "민감.*적합", "민감.*좋",
        "순한.*제품", "순한.*사용", "순한.*느낌", "순한.*토너", "자극적.*않",
        "자극없이", "무자극", "순하게", "자극이.*없", "순한.*성분", "순한.*제형",
        "예민.*피부.*적합", "자극이.*적", "자극.*적음"
    ],
    "진정효과": [
        "진정", "트러블.*없", "트러블.*감소", "트러블.*완화", "붉은기.*완화",
        "여드름.*완화", "피부.*안정", "진정효과", "피부.*진정", "트러블.*케어",
        "피부.*가라앉", "홍조.*완화", "열감.*완화", "여드름.*개선", "트러블.*개선",
        "좁쌀.*개선", "여드름.*감소", "트러블이.*나지.*않", "열감.*감소"
    ],
    "피부결개선": [
        "피부결.*개선", "피부결.*정돈", "피부결.*정리", "결.*좋", "각질.*제거",
        "매끈", "부드러", "피부결이.*좋", "각질.*케어", "결.*정리", "결.*개선",
        "피부.*좋아", "피부.*개선", "피부.*쫀쫀"
    ],
    "사용감좋음": [
        "산뜻", "가벼", "흡수.*잘", "흡수.*빠", "끈적.*없", "답답.*없",
        "시원", "쿨링", "청량", "상쾌", "개운", "흡수력.*좋", "스며",
        "빠른.*흡수", "흡수가.*잘", "가볍게", "산뜻하게", "끈적이지.*않",
        "좋은.*사용감", "사용감$", "깔끔", "흡수력$", "물같은.*제형",
        "무겁지.*않", "잘.*흡수", "기름지지.*않", "유분기.*없", "쫀쫀",
        "텍스처", "부담.*없이.*사용", "산뜻한.*느낌"
    ],
    "가성비": [
        "가성비", "저렴", "싸다", "싼", "가격.*좋", "혜자", "가격이.*저렴",
        "가격.*착", "가격.*괜찮", "가격$"
    ],
    "대용량": [
        "대용량", "용량.*많", "용량.*큼", "양.*많", "넉넉", "용량이.*많",
        "양이.*많", "푸짐", "용량$", "용량이.*크"
    ],
    "향좋음": [
        "향.*좋", "무향", "향.*없", "향.*은은", "향기.*좋", "향.*거의.*없",
        "은은한.*향", "향$"
    ],
    "재구매/추천": [
        "재구매", "추천", "강추", "인생템", "꾸준히", "계속.*쓸", "또.*살",
        "재구매템", "추천합니다", "추천해요", "리피트", "꾸준.*사용",
        "정착템", "믿고.*쓰", "잘.*쓰고.*있", "정착$", "잘.*사용하고.*있",
        "인생.*토너", "구매.*의사"
    ],
    "무난함": [
        "무난", "데일리", "기본", "평범", "무난하게", "무난템", "무난한.*사용",
        "매일.*사용", "부담없이.*사용"
    ],
    "화장잘받음": [
        "화장.*잘", "화장.*먹", "메이크업", "베이스", "화장이.*잘"
    ],
    "피부타입적합": [
        "지성.*적합", "건성.*적합", "복합.*적합", "피부.*맞", "잘.*맞",
        "피부.*잘.*맞", "지성피부.*적합", "건성피부.*적합", "복합성.*적합",
        "여름.*적합", "모든.*피부.*타입", "피지.*조절"
    ],
    "효과좋음": [
        "효과.*좋", "효과적", "효과.*있", "효과가.*좋", "효과.*뛰어",
        "좋은.*효과", "효과$"
    ],
    "사용편리": [
        "편리", "편함", "사용.*좋", "사용.*쉬", "사용하기.*좋", "편하게",
        "사용.*편리", "사계절.*사용", "여름.*사용.*좋", "겨울.*사용.*좋"
    ],
    "만족/좋음": [
        "좋음", "좋아요", "좋다", "만족", "최고", "굿", "좋습니다",
        "너무.*좋", "정말.*좋", "완전.*좋", "아주.*좋", "매우.*좋",
        "만족스러", "만족해", "마음에.*들", "대만족", "좋은.*제품",
        "좋은.*사용.*경험"
    ],
    "사계절사용": [
        "사계절", "올시즌", "계절.*상관.*없", "언제.*사용"
    ],
    "오래사용": [
        "오래.*사용", "몇.*년째", "몇년째", "꾸준히.*사용", "오랜.*시간",
        "계속.*사용", "애용", "몇.*통째", "오랜.*사용.*경험"
    ],
    "유명/인기": [
        "유명", "인기", "베스트셀러", "스테디셀러", "핫한"
    ],
    "배송좋음": [
        "빠른.*배송", "배송.*빠", "배송.*좋"
    ],
    "레이어링": [
        "레이어링", "겹쳐.*바", "덧바", "여러.*겹"
    ],
}


def categorize_point(point, categories):
    """포인트를 카테고리에 매핑"""
    point_lower = point.lower()
    matched = []

    for category, patterns in categories.items():
        for pattern in patterns:
            if re.search(pattern, point_lower):
                matched.append(category)
                break

    return matched if matched else ["기타"]


def main():
    # GPT 분석 결과 로드
    print("GPT 분석 결과 로드 중...")
    with open('output/gpt_analysis_full.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"총 분석 건수: {len(data):,}건\n")

    # ===== PAIN_POINTS 카테고리화 =====
    print("=" * 80)
    print("PAIN_POINTS 카테고리화")
    print("=" * 80)

    pain_by_category = defaultdict(list)
    pain_category_counts = Counter()

    for item in data:
        for pain in item.get('pain_points', []):
            categories = categorize_point(pain, PAIN_CATEGORIES)
            for cat in categories:
                pain_by_category[cat].append(pain)
                pain_category_counts[cat] += 1

    print("\n[카테고리별 분포]")
    total_pain = sum(pain_category_counts.values())
    for cat, cnt in pain_category_counts.most_common():
        pct = cnt / total_pain * 100
        print(f"  {cat:15s}: {cnt:>5}건 ({pct:>5.1f}%)")

    print("\n[카테고리별 TOP 항목]")
    for cat in pain_category_counts.keys():
        items = pain_by_category[cat]
        item_counts = Counter(items).most_common(5)
        print(f"\n  [{cat}]")
        for item, cnt in item_counts:
            print(f"    - {item} ({cnt}건)")

    # ===== POSITIVE_POINTS 카테고리화 =====
    print("\n" + "=" * 80)
    print("POSITIVE_POINTS 카테고리화")
    print("=" * 80)

    pos_by_category = defaultdict(list)
    pos_category_counts = Counter()

    for item in data:
        for pos in item.get('positive_points', []):
            categories = categorize_point(pos, POSITIVE_CATEGORIES)
            for cat in categories:
                pos_by_category[cat].append(pos)
                pos_category_counts[cat] += 1

    print("\n[카테고리별 분포]")
    total_pos = sum(pos_category_counts.values())
    for cat, cnt in pos_category_counts.most_common():
        pct = cnt / total_pos * 100
        print(f"  {cat:15s}: {cnt:>5}건 ({pct:>5.1f}%)")

    print("\n[카테고리별 TOP 항목]")
    for cat in pos_category_counts.keys():
        items = pos_by_category[cat]
        item_counts = Counter(items).most_common(5)
        print(f"\n  [{cat}]")
        for item, cnt in item_counts:
            print(f"    - {item} ({cnt}건)")

    # ===== 결과 저장 =====
    result = {
        "pain_points": {
            "total": total_pain,
            "category_counts": dict(pain_category_counts),
            "by_category": {k: Counter(v).most_common(20) for k, v in pain_by_category.items()}
        },
        "positive_points": {
            "total": total_pos,
            "category_counts": dict(pos_category_counts),
            "by_category": {k: Counter(v).most_common(20) for k, v in pos_by_category.items()}
        }
    }

    with open('output/points_categorized.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n\n카테고리 결과 저장: output/points_categorized.json")

    # ===== 리뷰 데이터에 카테고리 추가 =====
    print("\n리뷰 데이터에 카테고리 추가 중...")

    for item in data:
        # Pain categories
        pain_cats = set()
        for pain in item.get('pain_points', []):
            cats = categorize_point(pain, PAIN_CATEGORIES)
            pain_cats.update(cats)
        item['pain_categories'] = list(pain_cats)

        # Positive categories
        pos_cats = set()
        for pos in item.get('positive_points', []):
            cats = categorize_point(pos, POSITIVE_CATEGORIES)
            pos_cats.update(cats)
        item['positive_categories'] = list(pos_cats)

    with open('output/gpt_analysis_categorized.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"카테고리 추가된 분석 결과 저장: output/gpt_analysis_categorized.json")

    # ===== 기타 항목 분석 =====
    print("\n" + "=" * 80)
    print("'기타' 항목 TOP 30")
    print("=" * 80)

    pain_others = pain_by_category.get("기타", [])
    pos_others = pos_by_category.get("기타", [])

    print("\n[PAIN - 기타 TOP 30]")
    for item, cnt in Counter(pain_others).most_common(30):
        print(f"  {cnt:>3}건 | {item}")

    print("\n[POSITIVE - 기타 TOP 30]")
    for item, cnt in Counter(pos_others).most_common(30):
        print(f"  {cnt:>3}건 | {item}")


if __name__ == "__main__":
    main()
