# -*- coding: utf-8 -*-
"""
PAIN_POINTS, POSITIVE_POINTS 분석 및 카테고리화
"""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')

# GPT 분석 결과 로드
print("GPT 분석 결과 로드 중...")
with open('output/gpt_analysis_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"총 분석 건수: {len(data):,}건\n")

# ===== PAIN_POINTS 분석 =====
print("=" * 80)
print("PAIN_POINTS 분석")
print("=" * 80)

all_pain = []
for item in data:
    all_pain.extend(item.get('pain_points', []))

pain_counter = Counter(all_pain)
print(f"총 언급 수: {len(all_pain):,}건")
print(f"고유 항목 수: {len(pain_counter):,}개\n")

print("[TOP 100 Pain Points]")
print("-" * 60)
for i, (point, cnt) in enumerate(pain_counter.most_common(100), 1):
    print(f"{i:>3}. {cnt:>4}건 | {point}")

# ===== POSITIVE_POINTS 분석 =====
print("\n" + "=" * 80)
print("POSITIVE_POINTS 분석")
print("=" * 80)

all_pos = []
for item in data:
    all_pos.extend(item.get('positive_points', []))

pos_counter = Counter(all_pos)
print(f"총 언급 수: {len(all_pos):,}건")
print(f"고유 항목 수: {len(pos_counter):,}개\n")

print("[TOP 100 Positive Points]")
print("-" * 60)
for i, (point, cnt) in enumerate(pos_counter.most_common(100), 1):
    print(f"{i:>3}. {cnt:>4}건 | {point}")

# ===== 결과 저장 =====
result = {
    "pain_points": {
        "total_mentions": len(all_pain),
        "unique_count": len(pain_counter),
        "top_100": [{"point": p, "count": c} for p, c in pain_counter.most_common(100)],
        "all": [{"point": p, "count": c} for p, c in pain_counter.most_common()]
    },
    "positive_points": {
        "total_mentions": len(all_pos),
        "unique_count": len(pos_counter),
        "top_100": [{"point": p, "count": c} for p, c in pos_counter.most_common(100)],
        "all": [{"point": p, "count": c} for p, c in pos_counter.most_common()]
    }
}

with open('output/points_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n\n분석 결과 저장: output/points_analysis.json")
