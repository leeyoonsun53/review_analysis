# -*- coding: utf-8 -*-
"""
GPT-4o-mini 기반 무신사 리뷰 분석
기존 올리브영 분석 결과에 합치기
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

api_key = os.getenv('CLASSIFICATION_REVIEW')
if not api_key:
    raise ValueError("CLASSIFICATION_REVIEW 환경변수가 설정되지 않았습니다.")

client = OpenAI(api_key=api_key)

# 분석 프롬프트
ANALYSIS_PROMPT = """화장품 리뷰 분석. JSON으로 응답.

리뷰: "{review}"
별점: {rating}점

{{
    "sentiment": "POS/NEU/NEG",
    "pain_points": ["불만점"],
    "positive_points": ["장점"],
    "benefit_tags": ["진정/보습/장벽/결/피지 중 해당"],
    "texture_tags": ["물같음/쫀쫀/끈적/흡수 중 해당"],
    "usage_tags": ["닦토/스킨팩/레이어링/바디 중 해당"],
    "value_tags": ["가성비/무난/애매/인생템 중 해당"]
}}

sentiment: 내용 기반. 별점 높아도 불만이면 NEG.
없는 항목은 빈 배열."""


def analyze_review(review_text, rating, max_retries=3):
    """단일 리뷰 GPT 분석"""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": ANALYSIS_PROMPT.format(review=review_text[:500], rating=rating)}
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
            tokens = response.usage.total_tokens

            return result, tokens, None

        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return None, 0, "json_error"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None, 0, str(e)

    return None, 0, "max_retries"


def main():
    print("=" * 70)
    print("GPT-4o-mini 무신사 리뷰 분석 시작")
    print("=" * 70)

    # 통합 데이터 로드
    print("\n데이터 로드...")
    df = pd.read_csv('data/merged_reviews_processed.csv', encoding='utf-8-sig')

    # 무신사 데이터만 필터
    musinsa_df = df[df['PLATFORM'] == '무신사'].copy()
    total = len(musinsa_df)
    print(f"무신사 리뷰: {total:,}건")
    print(f"인덱스 범위: {musinsa_df.index.min()} ~ {musinsa_df.index.max()}")

    # 결과 파일 경로
    output_path = 'output/gpt_analysis_musinsa.json'
    progress_path = 'output/gpt_musinsa_progress.json'

    # 기존 진행상황 로드
    results = []
    processed_indices = set()
    total_tokens = 0
    errors = 0

    if os.path.exists(progress_path):
        with open(progress_path, 'r', encoding='utf-8') as f:
            progress = json.load(f)
            total_tokens = progress.get('total_tokens', 0)
            errors = progress.get('errors', 0)

        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
                processed_indices = {r['idx'] for r in results}

        print(f"기존 진행상황 로드: {len(results)}건 완료")

    # 분석할 인덱스 목록
    indices_to_process = [idx for idx in musinsa_df.index if idx not in processed_indices]

    if not indices_to_process:
        print("이미 모든 분석이 완료되었습니다.")
    else:
        print(f"\n{len(indices_to_process)}건 분석 시작...")
        print(f"예상 시간: {len(indices_to_process) / 3 / 60:.0f}분")

        # 분석 실행
        save_interval = 100

        try:
            for i, idx in enumerate(tqdm(indices_to_process, desc="GPT 분석")):
                row = df.loc[idx]
                review = str(row['REVIEW_CONTENT'])
                rating = int(row['REVIEW_RATING'])
                brand = str(row['BRAND_NAME'])

                result, tokens, error = analyze_review(review, rating)
                total_tokens += tokens

                if result:
                    results.append({
                        'idx': idx,
                        'brand': brand,
                        'rating': rating,
                        'sentiment': result.get('sentiment', 'NEU'),
                        'pain_points': result.get('pain_points', []),
                        'positive_points': result.get('positive_points', []),
                        'benefit_tags': result.get('benefit_tags', []),
                        'texture_tags': result.get('texture_tags', []),
                        'usage_tags': result.get('usage_tags', []),
                        'value_tags': result.get('value_tags', [])
                    })
                else:
                    errors += 1
                    results.append({
                        'idx': idx,
                        'brand': brand,
                        'rating': rating,
                        'sentiment': 'NEU',
                        'pain_points': [],
                        'positive_points': [],
                        'benefit_tags': [],
                        'texture_tags': [],
                        'usage_tags': [],
                        'value_tags': [],
                        'error': error
                    })

                # 중간 저장
                if (i + 1) % save_interval == 0:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(results, f, ensure_ascii=False)
                    with open(progress_path, 'w', encoding='utf-8') as f:
                        json.dump({'total_tokens': total_tokens, 'errors': errors}, f)

                    cost = total_tokens * 0.15 / 1000000 + total_tokens * 0.6 / 1000000
                    tqdm.write(f"  저장: {len(results)}/{total}, 토큰: {total_tokens:,}, 비용: ${cost:.2f}, 에러: {errors}")

                # Rate limit 방지
                time.sleep(0.3)

        except KeyboardInterrupt:
            print("\n\n중단됨. 진행상황 저장 중...")

    # 최종 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    with open(progress_path, 'w', encoding='utf-8') as f:
        json.dump({'total_tokens': total_tokens, 'errors': errors}, f)

    # 결과 요약
    print("\n" + "=" * 70)
    print("무신사 분석 완료!")
    print("=" * 70)
    print(f"완료: {len(results):,}건 / {total:,}건")
    print(f"토큰: {total_tokens:,}")
    print(f"에러: {errors}건")

    cost = total_tokens * 0.15 / 1000000 + total_tokens * 0.6 / 1000000
    print(f"비용: ${cost:.2f}")

    # 감성 분포
    if results:
        sentiments = [r['sentiment'] for r in results]
        print(f"\n감성 분포:")
        for s in ['POS', 'NEU', 'NEG']:
            cnt = sentiments.count(s)
            pct = cnt / len(results) * 100
            print(f"  {s}: {cnt:,}건 ({pct:.1f}%)")

    # 올리브영 데이터와 합치기
    print("\n" + "=" * 70)
    print("올리브영 분석 결과와 합치기...")
    print("=" * 70)

    oliveyoung_path = 'output/gpt_analysis_full.json'
    if os.path.exists(oliveyoung_path):
        with open(oliveyoung_path, 'r', encoding='utf-8') as f:
            oliveyoung_results = json.load(f)

        print(f"올리브영: {len(oliveyoung_results):,}건")
        print(f"무신사: {len(results):,}건")

        # 합치기
        combined = oliveyoung_results + results
        combined_path = 'output/gpt_analysis_combined.json'

        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)

        print(f"\n통합 결과 저장: {combined_path}")
        print(f"총 {len(combined):,}건")

        # 통합 감성 분포
        sentiments = [r['sentiment'] for r in combined]
        print(f"\n통합 감성 분포:")
        for s in ['POS', 'NEU', 'NEG']:
            cnt = sentiments.count(s)
            pct = cnt / len(combined) * 100
            print(f"  {s}: {cnt:,}건 ({pct:.1f}%)")
    else:
        print(f"올리브영 분석 파일을 찾을 수 없습니다: {oliveyoung_path}")


if __name__ == "__main__":
    main()
