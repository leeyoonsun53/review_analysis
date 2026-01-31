# -*- coding: utf-8 -*-
"""
Usage Tags 재분류 - 유사한 표현 통합
"""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

# Usage Tags 매핑 (유사 표현 → 대표 표현)
USAGE_MAPPING = {
    # === 닦토 ===
    '닦토': '닦토',
    '닥토': '닦토',
    '닦아내는 토너': '닦토',

    # === 흡토/찹토 ===
    '흡토': '흡토(패팅)',
    '팩토': '흡토(패팅)',
    '챱토': '흡토(패팅)',
    '찹토': '흡토(패팅)',
    '패팅': '흡토(패팅)',
    '손토너': '흡토(패팅)',
    '바르기': '흡토(패팅)',
    '바름': '흡토(패팅)',
    '바르는 토너': '흡토(패팅)',
    '바르는 용도': '흡토(패팅)',
    '손으로 챱챱': '흡토(패팅)',

    # === 레이어링 ===
    '레이어링': '레이어링',
    '겹바름': '레이어링',
    '덧바름': '레이어링',
    '7스킨': '레이어링',
    '7토너': '레이어링',

    # === 스킨팩/토너팩 ===
    '스킨팩': '스킨팩/토너팩',
    '토너팩': '스킨팩/토너팩',
    '팩': '스킨팩/토너팩',
    '마스크팩': '스킨팩/토너팩',
    '모델링팩': '스킨팩/토너팩',
    '시트팩': '스킨팩/토너팩',
    '크림팩': '스킨팩/토너팩',
    '석고팩': '스킨팩/토너팩',

    # === 바디 ===
    '바디': '바디 사용',
    '바디용': '바디 사용',

    # === 미스트 ===
    '미스트': '미스트/스프레이',
    '스프레이': '미스트/스프레이',
    '뿌토': '미스트/스프레이',
    '안개분사': '미스트/스프레이',

    # === 데일리 ===
    '데일리': '데일리 사용',
    '데일리 사용': '데일리 사용',
    '데일리템': '데일리 사용',
    '일상 사용': '데일리 사용',
    '일상용품': '데일리 사용',
    '일상사용': '데일리 사용',
    '매일 사용': '데일리 사용',
    '기본템': '데일리 사용',

    # === 기타 ===
    '스킨': '기타',
    '토너': '기타',
    '무난': '기타',
    '그냥': '기타',
    '기초': '기타',
    '기초 화장': '기타',
    '기초 단계에 사용': '기타',
    '첫 단계로 사용': '기타',
}


def recategorize_usage():
    print("Usage Tags 재분류 시작...")

    # 데이터 로드
    with open('output/gpt_analysis_categorized.json', 'r', encoding='utf-8') as f:
        cat_data = json.load(f)

    print(f"총 {len(cat_data):,}건 분석 데이터")

    # 재분류 전 통계
    before_usage = Counter()
    for r in cat_data:
        for u in r.get('usage_tags', []):
            before_usage[u] += 1
    print(f"재분류 전 고유 Usage Tags: {len(before_usage)}개")

    # 재분류 적용
    mapped_count = 0
    for r in cat_data:
        new_usage_tags = []
        for u in r.get('usage_tags', []):
            if u in USAGE_MAPPING:
                mapped = USAGE_MAPPING[u]
                if mapped != '기타':  # 기타는 제외
                    new_usage_tags.append(mapped)
                mapped_count += 1
            else:
                new_usage_tags.append(u)
        # 중복 제거
        r['usage_tags'] = list(dict.fromkeys(new_usage_tags))

    print(f"매핑 적용: {mapped_count}건")

    # 재분류 후 통계
    after_usage = Counter()
    for r in cat_data:
        for u in r.get('usage_tags', []):
            after_usage[u] += 1
    print(f"재분류 후 고유 Usage Tags: {len(after_usage)}개")

    # 저장
    with open('output/gpt_analysis_categorized.json', 'w', encoding='utf-8') as f:
        json.dump(cat_data, f, ensure_ascii=False, indent=2)

    print("\n=== 재분류 후 TOP 10 Usage Tags ===")
    for i, (u, c) in enumerate(after_usage.most_common(10), 1):
        print(f"{i}. {u}: {c}건")

    return after_usage


if __name__ == "__main__":
    recategorize_usage()
