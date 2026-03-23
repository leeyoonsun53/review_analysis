# -*- coding: utf-8 -*-
"""
GPT-4o-mini 기반 리뷰 분석
- 감성 분류 (POS/NEU/NEG)
- Pain Point 추출
- Positive Point 추출
"""
import json
import pandas as pd
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from tqdm import tqdm
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 환경 변수 로드
load_dotenv('config/.env')

# API 키 (CLASSIFICATION_REVIEW 환경변수 사용)
api_key = os.getenv('CLASSIFICATION_REVIEW')
if not api_key:
    raise ValueError("CLASSIFICATION_REVIEW 환경변수가 설정되지 않았습니다.")

client = OpenAI(api_key=api_key)

# 분석 프롬프트
ANALYSIS_PROMPT = """당신은 화장품 리뷰 분석 전문가입니다. 아래 토너 제품 리뷰를 분석해주세요.

리뷰: "{review}"
별점: {rating}점

다음 형식으로 JSON 응답해주세요:
{{
    "sentiment": "POS 또는 NEU 또는 NEG",
    "pain_points": ["pain point 1", "pain point 2", ...],
    "positive_points": ["positive point 1", "positive point 2", ...]
}}

분류 기준:
- sentiment: 리뷰 내용을 기반으로 판단. 별점이 높아도 내용이 부정적이면 NEG.
  - POS: 제품에 만족, 추천, 재구매 의사
  - NEU: 애매함, 무난함, 효과 모르겠음
  - NEG: 불만족, 부작용, 트러블, 안 맞음, 사용 중단

- pain_points: 불만/문제점 (예: "트러블 발생", "끈적임", "효과 없음", "자극", "건조함")
  - 없으면 빈 배열 []

- positive_points: 장점/만족 포인트 (예: "촉촉함", "진정 효과", "가성비", "순함", "흡수 빠름")
  - 없으면 빈 배열 []

JSON만 응답하세요."""


def analyze_review_gpt(review_text, rating):
    """단일 리뷰 GPT 분석"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": ANALYSIS_PROMPT.format(review=review_text, rating=rating)}
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
        return result, response.usage.total_tokens

    except json.JSONDecodeError as e:
        return {"sentiment": "NEU", "pain_points": [], "positive_points": [], "error": "json_parse"}, 0
    except Exception as e:
        return {"sentiment": "NEU", "pain_points": [], "positive_points": [], "error": str(e)}, 0


def analyze_reviews_batch(reviews_df, batch_size=10, delay=0.5, save_interval=100):
    """배치로 리뷰 분석"""
    results = []
    total_tokens = 0
    errors = 0

    # 기존 결과 로드 (이어서 처리)
    output_path = 'output/gpt_analysis_results.json'
    start_idx = 0

    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            results = existing.get('results', [])
            start_idx = len(results)
            total_tokens = existing.get('total_tokens', 0)
            print(f"기존 결과 {start_idx}건 로드, 이어서 분석...")

    print(f"\n총 {len(reviews_df)}건 중 {start_idx}건부터 분석 시작")
    print(f"예상 비용: ${(len(reviews_df) - start_idx) * 0.00015:.2f} (약 150토큰/리뷰)")

    for idx in tqdm(range(start_idx, len(reviews_df)), desc="GPT 분석"):
        row = reviews_df.iloc[idx]
        review_text = str(row['REVIEW_CONTENT'])
        rating = row['REVIEW_RATING']
        brand = row['BRAND_NAME']

        # 분석
        result, tokens = analyze_review_gpt(review_text, rating)
        total_tokens += tokens

        # 결과 저장
        results.append({
            'idx': idx,
            'brand': brand,
            'rating': rating,
            'review': review_text[:100],  # 미리보기
            'sentiment': result.get('sentiment', 'NEU'),
            'pain_points': result.get('pain_points', []),
            'positive_points': result.get('positive_points', []),
            'error': result.get('error')
        })

        if result.get('error'):
            errors += 1

        # 중간 저장
        if (idx + 1) % save_interval == 0:
            save_results(results, total_tokens, output_path)
            print(f"\n  {idx + 1}건 완료, 토큰: {total_tokens:,}, 에러: {errors}")

        # 딜레이
        time.sleep(delay)

    # 최종 저장
    save_results(results, total_tokens, output_path)

    return results, total_tokens, errors


def save_results(results, total_tokens, output_path):
    """결과 저장"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_tokens': total_tokens,
            'count': len(results),
            'results': results
        }, f, ensure_ascii=False, indent=2)


def merge_with_original(df, results):
    """원본 데이터프레임에 GPT 결과 병합"""
    # 결과를 데이터프레임으로 변환
    gpt_df = pd.DataFrame(results)

    # 원본에 병합
    df['gpt_sentiment'] = gpt_df['sentiment']
    df['gpt_pain_points'] = gpt_df['pain_points']
    df['gpt_positive_points'] = gpt_df['positive_points']

    return df


def main():
    print("=" * 70)
    print("GPT-4o-mini 리뷰 분석")
    print("=" * 70)

    # 데이터 로드
    print("\n데이터 로드...")
    with open('data/올영리뷰데이터_utf8.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    first_key = list(data.keys())[0]
    df = pd.DataFrame(data[first_key])
    print(f"총 리뷰: {len(df):,}건")

    # 분석 실행
    print("\nGPT 분석 시작...")
    results, total_tokens, errors = analyze_reviews_batch(
        df,
        batch_size=10,
        delay=0.3,  # 초당 약 3건
        save_interval=500
    )

    # 결과 요약
    print("\n" + "=" * 70)
    print("분석 완료!")
    print("=" * 70)
    print(f"총 분석: {len(results):,}건")
    print(f"총 토큰: {total_tokens:,}")
    print(f"에러: {errors}건")
    print(f"예상 비용: ${total_tokens * 0.00000015:.4f}")

    # 감성 분포
    sentiments = [r['sentiment'] for r in results]
    print(f"\n감성 분포:")
    for s in ['POS', 'NEU', 'NEG']:
        cnt = sentiments.count(s)
        print(f"  {s}: {cnt:,}건 ({cnt/len(results)*100:.1f}%)")

    # Pain Point 집계
    all_pains = []
    for r in results:
        all_pains.extend(r.get('pain_points', []))

    print(f"\nPain Point 상위 10개:")
    from collections import Counter
    pain_counts = Counter(all_pains)
    for pain, cnt in pain_counts.most_common(10):
        print(f"  {pain}: {cnt}건")

    # Positive Point 집계
    all_pos = []
    for r in results:
        all_pos.extend(r.get('positive_points', []))

    print(f"\nPositive Point 상위 10개:")
    pos_counts = Counter(all_pos)
    for pos, cnt in pos_counts.most_common(10):
        print(f"  {pos}: {cnt}건")

    # 원본에 병합하여 저장
    df = merge_with_original(df, results)
    df.to_csv('output/reviews_with_gpt.csv', index=False, encoding='utf-8-sig')
    print(f"\n저장: output/reviews_with_gpt.csv")


if __name__ == "__main__":
    main()
