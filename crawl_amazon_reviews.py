"""
Amazon UK 리뷰 크롤러 (디버그 포트 attach 방식)

사용 전 준비 (사용자가 직접):
  1) 열려있는 Chrome 전부 종료
  2) 아래 명령으로 Chrome 재시작 (PowerShell):
       & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" `
         --remote-debugging-port=9222 `
         --user-data-dir="C:\\Users\\USER\\chrome-debug-profile"
     (user-data-dir 는 본인 평소 프로필을 써도 되지만, 전용 프로필 권장)
  3) 그 Chrome 창에서 amazon.co.uk 에 로그인하고, 리뷰 페이지가 정상으로 보이는지 확인
     (CAPTCHA / "확인" 페이지가 뜨면 직접 통과)
  4) 그 상태에서 이 스크립트 실행:  python crawl_amazon_reviews.py

스크립트는 새 창을 띄우지 않고, 이미 로그인된 그 Chrome 세션에 attach 해서 크롤링한다.
"""

import json
import re
import sys
import time
from pathlib import Path

# Windows 콘솔(cp949)에서 이모지/유니코드 출력 시 크래시 방지
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
)

# ----------------------------- 설정 -----------------------------
ASIN = "B07B32PL1C"
DOMAIN = "https://www.amazon.co.uk"
DEBUGGER_ADDRESS = "127.0.0.1:9222"
STAR_FILTERS = ["five_star", "four_star", "three_star", "two_star", "one_star"]
SORT_BY = "recent"  # recent | helpful

OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)
OUT_CSV = OUT_DIR / f"amazon_reviews_{ASIN}.csv"
OUT_JSON = OUT_DIR / f"amazon_reviews_{ASIN}.json"

# "Show N more reviews" 클릭 사이 대기 / 최대 클릭 횟수 (안전장치)
CLICK_PAUSE = 2.0
MAX_CLICKS_PER_FILTER = 500
PAGE_LOAD_TIMEOUT = 25


# ----------------------------- 드라이버 -----------------------------
def attach_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_experimental_option("debuggerAddress", DEBUGGER_ADDRESS)
    # Selenium Manager 가 설치된 Chrome 버전에 맞는 chromedriver 자동 다운로드
    driver = webdriver.Chrome(options=opts)
    return driver


def build_url(star: str, page: int = 1) -> str:
    # 사용자가 본 "Show N more reviews" 버튼이 있는 새 포털 화면
    return (
        f"{DOMAIN}/portal/customer-reviews/{ASIN}/"
        f"?reviewerType=all_reviews&sortBy={SORT_BY}"
        f"&filterByStar={star}&pageNumber={page}#reviews-filter-bar"
    )


# ----------------------------- 파싱 -----------------------------
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


def parse_reviews_on_page(driver, star: str) -> list[dict]:
    cards = driver.find_elements(By.CSS_SELECTOR, '[data-hook="review"]')
    out = []
    for c in cards:
        try:
            rid = c.get_attribute("id") or ""

            # 별점: "5.0 out of 5 stars" -> 5.0
            rating_raw = (
                _attr(c, '[data-hook="review-star-rating"] .a-icon-alt', "textContent")
                or _text(c, '[data-hook="review-star-rating"]')
                or _text(c, '[data-hook="cmps-review-star-rating"]')
            )
            m = re.search(r"([0-9.]+)\s*out of", rating_raw or "")
            # 파싱 실패 시 star_filter 로 보정 (five_star=5.0 ...)
            star_map = {"five_star": 5.0, "four_star": 4.0, "three_star": 3.0,
                        "two_star": 2.0, "one_star": 1.0}
            rating = float(m.group(1)) if m else star_map.get(star)

            title = _text(c, '[data-hook="review-title"]')
            # 새 레이아웃에서 title 안에 별점 span 텍스트가 섞이는 경우 정리
            title = re.sub(r"^\s*[0-9.]+\s*out of\s*5\s*stars\s*", "", title).strip()

            body = (
                _text(c, '[data-hook="review-body"]')
                or _text(c, '[data-hook="review-collapsed"]')
            )
            author = _text(c, ".a-profile-name")
            date_raw = _text(c, '[data-hook="review-date"]')

            verified = bool(
                c.find_elements(By.CSS_SELECTOR, '[data-hook="avp-badge"]')
            )
            helpful = _text(c, '[data-hook="helpful-vote-statement"]')

            out.append(
                {
                    "review_id": rid,
                    "star_filter": star,
                    "rating": rating,
                    "title": title,
                    "body": body,
                    "author": author,
                    "date_raw": date_raw,
                    "verified_purchase": verified,
                    "helpful": helpful,
                }
            )
        except StaleElementReferenceException:
            continue
    return out


def click_show_more(driver) -> bool:
    """'Show N more reviews' 버튼이 있으면 클릭하고 True, 없으면 False."""
    candidates = driver.find_elements(
        By.XPATH,
        "//*[self::a or self::button or self::span]"
        "[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
        "'abcdefghijklmnopqrstuvwxyz'), 'more review')]",
    )
    for el in candidates:
        try:
            if el.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.4)
                try:
                    el.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", el)
                return True
        except StaleElementReferenceException:
            continue
    return False


def crawl_filter(driver, star: str, seen: set) -> list[dict]:
    url = build_url(star)
    print(f"\n[{star}] {url}")
    driver.get(url)

    try:
        WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-hook="review"]'))
        )
    except TimeoutException:
        # 봇 차단 / 로그인 페이지 가능성
        if "captcha" in driver.page_source.lower() or "robot" in driver.page_source.lower():
            print(f"  ⚠️  CAPTCHA/봇 차단 감지. Chrome 창에서 직접 통과 후 Enter...")
            input("  통과했으면 Enter > ")
        else:
            print(f"  ⚠️  리뷰 요소를 못 찾음 (리뷰 0개이거나 레이아웃 변경). 스킵.")
            return []

    results = []
    clicks = 0
    while True:
        page_reviews = parse_reviews_on_page(driver, star)
        new = [r for r in page_reviews if r["review_id"] not in seen]
        for r in new:
            seen.add(r["review_id"])
        results.extend(new)
        print(f"  누적 {len(results)}개 (이번 화면 신규 {len(new)}개)")

        if not click_show_more(driver):
            print(f"  '더보기' 버튼 없음 -> [{star}] 종료")
            break
        clicks += 1
        if clicks >= MAX_CLICKS_PER_FILTER:
            print(f"  ⚠️  최대 클릭 {MAX_CLICKS_PER_FILTER}회 도달 -> 중단")
            break
        time.sleep(CLICK_PAUSE)

    return results


# ----------------------------- 저장 -----------------------------
def save(all_reviews: list[dict]):
    OUT_JSON.write_text(
        json.dumps(all_reviews, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # CSV (pandas 사용)
    try:
        import pandas as pd

        pd.DataFrame(all_reviews).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"CSV 저장 실패(JSON은 저장됨): {e}")
    print(f"\n✅ 총 {len(all_reviews)}개 저장")
    print(f"   {OUT_JSON}")
    print(f"   {OUT_CSV}")


# ----------------------------- 메인 -----------------------------
def main():
    try:
        driver = attach_driver()
    except Exception as e:
        print("❌ Chrome 디버그 세션에 attach 실패.")
        print("   Chrome을 --remote-debugging-port=9222 로 켰는지 확인하세요.")
        print(f"   에러: {e}")
        return

    seen: set = set()
    all_reviews: list[dict] = []
    try:
        for star in STAR_FILTERS:
            all_reviews.extend(crawl_filter(driver, star, seen))
            save(all_reviews)  # 필터마다 중간 저장 (중단 대비)
    finally:
        save(all_reviews)
        # attach 모드이므로 driver.quit() 하지 않음 (사용자 브라우저 유지)
        print("완료. (브라우저는 닫지 않음)")


if __name__ == "__main__":
    main()
