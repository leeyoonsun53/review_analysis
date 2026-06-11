"""
5점 리뷰 100개 캡 우회 수집 (키워드 스윕 방식)

포털은 한 화면당 리뷰 열람을 100개로 제한한다(토큰/정렬 우회 모두 한계).
대신 filterByKeyword 로 키워드별 ≤100개 세트를 받아 합집합하면 캡을 넘길 수 있다.
데이터에서 뽑은 빈출 단어들로 five_star 를 훑어 거의 전부 수집한 뒤,
기존 amazon_reviews_B07B32PL1C.json 의 5점을 더 완전한 세트로 교체/머지한다.

사전 조건: Chrome 이 --remote-debugging-port=9222 로 떠 있고 amazon.co.uk 로그인 상태.
실행:  python crawl_five_star_full.py
"""

import json
import re
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)

ASIN = "B07B32PL1C"
DOMAIN = "https://www.amazon.co.uk"
DEBUGGER_ADDRESS = "127.0.0.1:9222"
OUT_JSON = Path("data") / f"amazon_reviews_{ASIN}.json"
OUT_CSV = Path("data") / f"amazon_reviews_{ASIN}.csv"

# 데이터에서 추출한 빈출 단어 (recall 극대화용 일반어 일부 포함)
KEYWORDS = [
    "hydrating", "skin", "good", "dry", "love", "toner", "price",
    "great", "like", "sensitive", "bottle", "face", "nice", "feel",
    "definitely", "milky", "best", "feeling", "amazing", "smells",
    "soft", "mochi", "leaves", "glass", "tonymoly", "texture",
    "products", "cream", "smell", "recommend", "use", "oily",
    "moisturiser", "absorb", "gentle", "scent", "morning", "night",
]
# 조기 종료: 연속 N개 키워드가 새 리뷰를 거의 안 주면 포화로 보고 중단
SATURATION_PATIENCE = 4
SATURATION_MIN_NEW = 2
CLICK_PAUSE = 1.0
MAX_CLICKS = 200


def attach_driver():
    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUGGER_ADDRESS)
    return webdriver.Chrome(options=opts)


def _text(el, css):
    try:
        return el.find_element(By.CSS_SELECTOR, css).text.strip()
    except NoSuchElementException:
        return ""


def _attr(el, css, attr):
    try:
        return el.find_element(By.CSS_SELECTOR, css).get_attribute(attr)
    except NoSuchElementException:
        return ""


def parse_card(c):
    rid = c.get_attribute("id") or ""
    rating_raw = (
        _attr(c, '[data-hook="review-star-rating"] .a-icon-alt', "textContent")
        or _text(c, '[data-hook="review-star-rating"]')
    )
    m = re.search(r"([0-9.]+)\s*out of", rating_raw or "")
    rating = float(m.group(1)) if m else 5.0  # five_star 필터이므로 파싱 실패 시 5.0
    title = _text(c, '[data-hook="review-title"]')
    title = re.sub(r"^\s*[0-9.]+\s*out of\s*5\s*stars\s*", "", title).strip()
    body = _text(c, '[data-hook="review-body"]') or _text(c, '[data-hook="review-collapsed"]')
    return {
        "review_id": rid,
        "star_filter": "five_star",
        "rating": rating,
        "title": title,
        "body": body,
        "author": _text(c, ".a-profile-name"),
        "date_raw": _text(c, '[data-hook="review-date"]'),
        "verified_purchase": bool(c.find_elements(By.CSS_SELECTOR, '[data-hook="avp-badge"]')),
        "helpful": _text(c, '[data-hook="helpful-vote-statement"]'),
    }


def load_keyword(driver, kw, collected: dict) -> int:
    url = (
        f"{DOMAIN}/portal/customer-reviews/{ASIN}/"
        f"?reviewerType=all_reviews&sortBy=recent&filterByStar=five_star"
        f"&filterByKeyword={kw}#reviews-filter-bar"
    )
    driver.get(url)
    time.sleep(2.5)
    before = len(collected)
    clicks = 0
    while True:
        for c in driver.find_elements(By.CSS_SELECTOR, '[data-hook="review"]'):
            try:
                rid = c.get_attribute("id")
                if rid and rid not in collected:
                    collected[rid] = parse_card(c)
            except StaleElementReferenceException:
                continue
        # show more
        btns = driver.find_elements(
            By.XPATH,
            "//*[self::a or self::button or self::span][contains(translate(., "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'more review')]",
        )
        clicked = False
        for b in btns:
            try:
                if b.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", b)
                    time.sleep(0.3)
                    try:
                        b.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", b)
                    clicked = True
                    break
            except StaleElementReferenceException:
                continue
        if not clicked:
            break
        clicks += 1
        if clicks >= MAX_CLICKS:
            break
        time.sleep(CLICK_PAUSE)
    return len(collected) - before


def main():
    try:
        driver = attach_driver()
    except Exception as e:
        print(f"❌ Chrome attach 실패. 디버그 포트 9222 확인. {e}")
        return

    collected: dict = {}
    dry_streak = 0
    for i, kw in enumerate(KEYWORDS, 1):
        new = load_keyword(driver, kw, collected)
        print(f"  [{i}/{len(KEYWORDS)}] kw='{kw}': 신규 {new}개, 누적 {len(collected)}개")
        if new < SATURATION_MIN_NEW:
            dry_streak += 1
        else:
            dry_streak = 0
        if dry_streak >= SATURATION_PATIENCE:
            print(f"  포화 도달(연속 {SATURATION_PATIENCE}개 키워드 신규<{SATURATION_MIN_NEW}) -> 중단")
            break

    five = list(collected.values())
    print(f"\n5점 키워드 스윕 수집: {len(five)}개")

    # 기존 데이터와 머지 (기존 5점 제거 후 새 세트로 교체)
    existing = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else []
    others = [r for r in existing if r.get("star_filter") != "five_star"]
    merged = others + five
    # 전체 review_id 기준 최종 중복 제거 (다른 별점과 겹칠 일은 없지만 안전)
    seen, dedup = set(), []
    for r in merged:
        rid = r.get("review_id")
        if rid and rid in seen:
            continue
        seen.add(rid)
        dedup.append(r)

    OUT_JSON.write_text(json.dumps(dedup, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import pandas as pd
        pd.DataFrame(dedup).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"CSV 저장 실패(JSON은 됨): {e}")

    from collections import Counter
    dist = Counter(r["star_filter"] for r in dedup)
    print(f"\n최종 머지: {len(dedup)}개")
    for k in ["five_star", "four_star", "three_star", "two_star", "one_star"]:
        print(f"  {k}: {dist.get(k,0)}")
    print(f"저장: {OUT_JSON} / {OUT_CSV}")
    print("완료. (브라우저는 닫지 않음)")


if __name__ == "__main__":
    main()
