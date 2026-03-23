# -*- coding: utf-8 -*-
"""
GPT-4o-mini 기반 리뷰 분석 (샘플 테스트)
옵션 2: 전체 항목 GPT 분석
"""
import json
import pandas as pd
import os
from openai import OpenAI
from dotenv import load_dotenv
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 환경 변수 로드
load_dotenv('config/.env')

api_key = os.getenv('CLASSIFICATION_REVIEW')
if not api_key:
    raise ValueError("CLASSIFICATION_REVIEW 환경변수가 설정되지 않았습니다.")

client = OpenAI(api_key=api_key)

# 분석 프롬프트 (옵션 2: 전체 항목)
ANALYSIS_PROMPT = """당신은 화장품 리뷰 분석 전문가입니다. 아래 토너 제품 리뷰를 분석해주세요.

리뷰: "{review}"
별점: {rating}점

다음 JSON 형식으로 응답해주세요:
{{
    "sentiment": "POS 또는 NEU 또는 NEG",
    "pain_points": ["불만/문제점 리스트"],
    "positive_points": ["장점/만족 포인트 리스트"],
    "benefit_tags": ["효능/기능 태그"],
    "texture_tags": ["사용감/제형 태그"],
    "usage_tags": ["사용법/역할 태그"],
    "value_tags": ["가치/선택이유 태그"]
}}

분류 기준:

1. sentiment (감성): 리뷰 내용 기반 판단. 별점이 높아도 내용이 부정적이면 NEG.
   - POS: 만족, 추천, 재구매 의사
   - NEU: 애매함, 무난함, 효과 모르겠음
   - NEG: 불만족, 부작용, 트러블, 안 맞음, 사용 중단

2. pain_points: 불만/문제점 (없으면 빈 배열)
   예: "트러블 발생", "끈적임", "효과 없음", "자극", "건조함", "향이 강함"

3. positive_points: 장점/만족 포인트 (없으면 빈 배열)
   예: "촉촉함", "진정 효과", "가성비 좋음", "순함", "흡수 빠름"

4. benefit_tags: 효능/기능 (해당되는 것만)
   - 진정: 트러블 진정, 붉은기 완화, 자극 없음
   - 보습: 촉촉함, 수분감, 건조함 해결
   - 장벽: 피부장벽 강화, 시카, 재생
   - 결: 피부결 개선, 각질 제거, 매끈함
   - 피지: 유분 조절, 산뜻함, 번들거림 감소

5. texture_tags: 사용감/제형 (해당되는 것만)
   - 물같음: 묽은 제형, 가벼움
   - 쫀쫀: 점성 있음, 꾸덕함
   - 끈적: 끈적거림, 답답함
   - 흡수: 흡수 빠름, 스며듦

6. usage_tags: 사용법/역할 (해당되는 것만)
   - 닦토: 닦아내는 토너, 화장솜 사용
   - 스킨팩: 토너팩, 패드팩
   - 레이어링: 여러 번 덧바름
   - 바디: 몸에도 사용

7. value_tags: 가치/선택이유 (해당되는 것만)
   - 가성비: 가격 대비 좋음, 저렴함
   - 무난: 무난함, 기본템
   - 애매: 효과 모르겠음, 별로
   - 인생템: 최애, 재구매 의사 강함

JSON만 응답하세요. 해당 없는 항목은 빈 배열 []로."""


def analyze_review(review_text, rating):
    """단일 리뷰 GPT 분석"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": ANALYSIS_PROMPT.format(review=review_text, rating=rating)}
        ],
        temperature=0.1,
        max_tokens=500
    )

    content = response.choices[0].message.content.strip()

    # JSON 파싱
    if content.startswith('```'):
        content = content.split('```')[1]
        if content.startswith('json'):
            content = content[4:]

    result = json.loads(content)
    tokens = response.usage.total_tokens

    return result, tokens


def main():
    print("=" * 80)
    print("GPT-4o-mini 리뷰 분석 (옵션 2: 전체 항목) - 샘플 10건")
    print("=" * 80)

    # 데이터 로드
    with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    first_key = list(data.keys())[0]
    df = pd.DataFrame(data[first_key])

    # 다양한 케이스 샘플 선택
    samples = []

    # 1. 일반 긍정 (별점 5)
    samples.append(df[df['REVIEW_RATING'] == 5].iloc[0])

    # 2. 일반 부정 (별점 1-2)
    low_rating = df[df['REVIEW_RATING'] <= 2]
    if len(low_rating) > 0:
        samples.append(low_rating.iloc[0])

    # 3. 피부질병 언급 케이스
    skin_case = df[df['REVIEW_CONTENT'].str.contains('여드름|트러블|뾰루지', na=False)]
    if len(skin_case) > 0:
        samples.append(skin_case.iloc[0])
        samples.append(skin_case.iloc[1])

    # 4. 진정 효과 언급
    calming = df[df['REVIEW_CONTENT'].str.contains('진정', na=False)]
    if len(calming) > 0:
        samples.append(calming.iloc[0])

    # 5. 보습 언급
    moisture = df[df['REVIEW_CONTENT'].str.contains('촉촉|보습', na=False)]
    if len(moisture) > 0:
        samples.append(moisture.iloc[0])

    # 6. 역접 패턴
    adversative = df[df['REVIEW_CONTENT'].str.contains('했는데|지만|었으나', na=False)]
    if len(adversative) > 0:
        samples.append(adversative.iloc[0])

    # 7. 가성비 언급
    value = df[df['REVIEW_CONTENT'].str.contains('가성비|저렴', na=False)]
    if len(value) > 0:
        samples.append(value.iloc[0])

    # 8-10. 랜덤 추가
    remaining = 10 - len(samples)
    if remaining > 0:
        random_samples = df.sample(n=remaining, random_state=42)
        for _, row in random_samples.iterrows():
            samples.append(row)

    samples = samples[:10]  # 최대 10개

    print(f"\n샘플 {len(samples)}건 분석 시작...\n")

    total_tokens = 0
    results = []

    for i, row in enumerate(samples, 1):
        review = row['REVIEW_CONTENT']
        rating = row['REVIEW_RATING']
        brand = row['BRAND_NAME']

        print(f"[{i}/10] {brand} | 별점 {rating}")
        print(f"리뷰: {review[:60]}..." if len(review) > 60 else f"리뷰: {review}")

        try:
            result, tokens = analyze_review(review, rating)
            total_tokens += tokens

            print(f"  → 감성: {result['sentiment']}")
            print(f"  → Pain: {result.get('pain_points', [])}")
            print(f"  → Positive: {result.get('positive_points', [])}")
            print(f"  → 효능: {result.get('benefit_tags', [])}")
            print(f"  → 사용감: {result.get('texture_tags', [])}")
            print(f"  → 사용법: {result.get('usage_tags', [])}")
            print(f"  → 가치: {result.get('value_tags', [])}")
            print(f"  → 토큰: {tokens}")

            results.append({
                'brand': brand,
                'rating': rating,
                'review': review,
                **result,
                'tokens': tokens
            })

        except Exception as e:
            print(f"  → 에러: {e}")

        print()

    # 결과 요약
    print("=" * 80)
    print("샘플 분석 완료")
    print("=" * 80)
    print(f"총 토큰: {total_tokens}")
    print(f"평균 토큰/건: {total_tokens / len(results):.0f}")
    print(f"예상 전체 비용 (27,745건): ${total_tokens / len(results) * 27745 * 0.00000015 + total_tokens / len(results) * 27745 * 0.0000006:.2f}")

    # 결과 저장
    with open('output/gpt_sample_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: output/gpt_sample_results.json")


if __name__ == "__main__":
    main()
