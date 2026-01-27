"""
AI 기반 감성 분석 보정 모듈
GPT-4o-mini를 사용하여 애매한 리뷰를 재분석
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# OpenAI 라이브러리
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai 라이브러리가 설치되지 않았습니다. pip install openai")


# .env 파일 로드
ENV_PATH = Path(__file__).parent.parent / "config" / ".env"
load_dotenv(ENV_PATH)


def get_openai_client():
    """OpenAI 클라이언트 생성"""
    api_key = os.getenv("CLASSIFICATION_REVIEW")
    if not api_key:
        raise ValueError("API 키가 설정되지 않았습니다. config/.env 파일에 CLASSIFICATION_REVIEW를 설정하세요.")
    return OpenAI(api_key=api_key)


def select_ambiguous_reviews(df, max_samples=3000):
    """
    AI 분석이 필요한 애매한 리뷰 선별

    선별 기준 (우선순위 순):
    1. NEU (중립) 판정된 리뷰 - 가장 애매함
    2. 별점-내용 불일치 (5점인데 WEAK, 1-2점인데 긍정)
    3. 긴 리뷰인데 태그 미추출 (30자 이상인데 태그 없음)

    Args:
        df: 데이터프레임
        max_samples: 최대 샘플 수 (비용 제한)

    Returns:
        DataFrame: 샘플링된 리뷰
    """
    # 우선순위별 점수 부여
    df = df.copy()
    df['_ambiguity_score'] = 0

    # 1. NEU (중립) 판정 - 최우선 (점수 3점)
    cond_neu = df['sentiment'] == 'NEU'
    df.loc[cond_neu, '_ambiguity_score'] += 3

    # 2. 별점-내용 불일치 (점수 2점)
    cond_mismatch_high = (df['REVIEW_RATING'] == 5) & (df['strength'] == 'WEAK')
    cond_mismatch_low = (df['REVIEW_RATING'] <= 2) & (df['strength'] == 'STRONG')
    df.loc[cond_mismatch_high | cond_mismatch_low, '_ambiguity_score'] += 2

    # 3. 긴 리뷰인데 태그 미추출 (점수 1점) - 30자 이상만
    def no_tags_long(row):
        if len(str(row['REVIEW_CONTENT'])) < 30:
            return False
        benefit = row['benefit_tags'] if isinstance(row['benefit_tags'], list) else []
        texture = row['texture_tags'] if isinstance(row['texture_tags'], list) else []
        return len(benefit) == 0 and len(texture) == 0

    cond_no_tags_long = df.apply(no_tags_long, axis=1)
    df.loc[cond_no_tags_long, '_ambiguity_score'] += 1

    # 점수가 1점 이상인 리뷰만 선택
    sampled_df = df[df['_ambiguity_score'] >= 1].copy()

    # 우선순위 정렬 후 상한 적용
    sampled_df = sampled_df.sort_values('_ambiguity_score', ascending=False)

    print(f"\n  [AI 샘플링] 선별 결과:")
    print(f"    - NEU 판정: {cond_neu.sum():,}건")
    print(f"    - 별점-내용 불일치: {(cond_mismatch_high | cond_mismatch_low).sum():,}건")
    print(f"    - 긴 리뷰+태그 미추출: {cond_no_tags_long.sum():,}건")
    print(f"    - 총 후보 (중복 제거): {len(sampled_df):,}건")

    # 상한 적용
    if len(sampled_df) > max_samples:
        print(f"    - 상한 적용: {len(sampled_df):,} → {max_samples:,}건")
        sampled_df = sampled_df.head(max_samples)

    # 임시 컬럼 제거
    sampled_df = sampled_df.drop(columns=['_ambiguity_score'])
    df.drop(columns=['_ambiguity_score'], inplace=True)

    return sampled_df


def create_prompt(review_text):
    """GPT에게 보낼 프롬프트 생성"""
    prompt = f"""다음 화장품(토너) 리뷰를 분석해주세요.

리뷰: "{review_text}"

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
    "sentiment": "POS 또는 NEU 또는 NEG",
    "strength": "STRONG 또는 MID 또는 WEAK",
    "benefit_tags": ["진정", "보습", "장벽", "결", "피지"] 중 해당하는 것만 배열로,
    "texture_tags": ["물같음", "쫀쫀", "끈적", "흡수"] 중 해당하는 것만 배열로,
    "usage_tags": ["닦토", "스킨팩", "레이어링", "바디"] 중 해당하는 것만 배열로,
    "reason_buy": "가성비 또는 진정 또는 보습 또는 대용량 또는 기타"
}}

판단 기준:
- sentiment: 전반적 만족도 (POS=만족, NEU=보통/애매, NEG=불만족)
- strength: 감정 강도 (STRONG=매우 강함, MID=보통, WEAK=약함/무난)
- benefit_tags: 언급된 효능 (없으면 빈 배열)
- texture_tags: 언급된 사용감 (없으면 빈 배열)
- usage_tags: 언급된 사용법 (없으면 빈 배열)
- reason_buy: 구매 이유 추정 (명확하지 않으면 "기타")"""

    return prompt


def call_gpt_api(client, review_text, review_id, token_log):
    """
    GPT-4o-mini API 호출

    Args:
        client: OpenAI 클라이언트
        review_text: 리뷰 텍스트
        review_id: 리뷰 ID
        token_log: 토큰 사용량 로그 리스트

    Returns:
        dict: 분석 결과
    """
    prompt = create_prompt(review_text)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a Korean cosmetics review analyzer. Always respond in valid JSON format only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )

        # 토큰 사용량 기록
        usage = response.usage
        token_log.append({
            "review_id": int(review_id),
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "timestamp": datetime.now().isoformat()
        })

        # 응답 파싱
        content = response.choices[0].message.content.strip()

        # JSON 파싱 시도
        # 가끔 ```json ... ``` 형태로 올 수 있음
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        result = json.loads(content)
        return result

    except json.JSONDecodeError as e:
        print(f"    JSON 파싱 오류 (review_id={review_id}): {e}")
        return None
    except Exception as e:
        print(f"    API 호출 오류 (review_id={review_id}): {e}")
        return None


def enhance_with_ai(df, output_dir, batch_size=50, delay=0.5, max_samples=3000):
    """
    AI를 사용하여 애매한 리뷰 분석 보정

    Args:
        df: 전체 데이터프레임 (이미 1차 분석 완료)
        output_dir: 출력 디렉토리
        batch_size: 배치 크기 (진행상황 출력용)
        delay: API 호출 간 딜레이 (초)

    Returns:
        DataFrame: AI 분석이 반영된 데이터프레임
    """
    if not OPENAI_AVAILABLE:
        print("  [AI 보정] openai 라이브러리가 없어 건너뜁니다.")
        return df

    try:
        client = get_openai_client()
    except ValueError as e:
        print(f"  [AI 보정] {e}")
        return df

    # 샘플링
    sampled_df = select_ambiguous_reviews(df, max_samples=max_samples)

    if len(sampled_df) == 0:
        print("  [AI 보정] 샘플링된 리뷰가 없습니다.")
        return df

    print(f"\n  [AI 보정] GPT-4o-mini 분석 시작 ({len(sampled_df):,}건)...")

    # 토큰 로그
    token_log = []

    # AI 분석 결과 저장
    ai_results = {}

    # 진행 상황
    total = len(sampled_df)
    processed = 0
    errors = 0

    for idx, row in sampled_df.iterrows():
        review_id = row['REVIEW_ID']
        review_text = row['REVIEW_CONTENT']

        # API 호출
        result = call_gpt_api(client, review_text, review_id, token_log)

        if result:
            ai_results[idx] = result
        else:
            errors += 1

        processed += 1

        # 진행 상황 출력
        if processed % batch_size == 0 or processed == total:
            print(f"    진행: {processed:,}/{total:,} ({processed/total*100:.1f}%) - 오류: {errors}건")

        # Rate limiting
        if delay > 0:
            time.sleep(delay)

    # 결과 반영
    print(f"\n  [AI 보정] 결과 반영 중...")

    for idx, result in ai_results.items():
        if 'sentiment' in result:
            df.at[idx, 'sentiment'] = result['sentiment']
        if 'strength' in result:
            df.at[idx, 'strength'] = result['strength']
        if 'benefit_tags' in result:
            df.at[idx, 'benefit_tags'] = result['benefit_tags']
        if 'texture_tags' in result:
            df.at[idx, 'texture_tags'] = result['texture_tags']
        if 'usage_tags' in result:
            df.at[idx, 'usage_tags'] = result['usage_tags']
        if 'reason_buy' in result:
            df.at[idx, 'reason_buy'] = result['reason_buy']

    # 토큰 로그 저장
    output_dir = Path(output_dir)
    token_log_path = output_dir / "ai_token_usage.json"

    # 총합 계산
    total_input = sum(t['input_tokens'] for t in token_log)
    total_output = sum(t['output_tokens'] for t in token_log)
    total_tokens = sum(t['total_tokens'] for t in token_log)

    log_data = {
        "summary": {
            "total_reviews_processed": len(token_log),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(total_tokens * 0.00000015, 4),  # gpt-4o-mini 가격
            "created_at": datetime.now().isoformat()
        },
        "details": token_log
    }

    with open(token_log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    print(f"\n  [AI 보정] 완료!")
    print(f"    - 처리: {len(ai_results):,}건")
    print(f"    - 오류: {errors}건")
    print(f"    - 총 토큰: {total_tokens:,} (입력: {total_input:,}, 출력: {total_output:,})")
    print(f"    - 예상 비용: ${log_data['summary']['estimated_cost_usd']:.4f}")
    print(f"    - 토큰 로그: {token_log_path}")

    return df
