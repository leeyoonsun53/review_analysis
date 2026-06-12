# -*- coding: utf-8 -*-
"""
아마존 리뷰 '진짜 고객이 쓴 단어' 빈도 순위 + 워드클라우드.

입력: data/amazon_reviews_B07B32PL1C.json (원문 영어 본문 409건)
출력:
  - output/amazon_wordfreq.csv         단어 빈도 순위(전체)
  - output/amazon_wordfreq_top50.txt   상위 50 순위 표(콘솔/보고서용)
  - output/amazon_bigrams_top30.csv    상위 30 연어(2-gram)
  - output/amazon_wordcloud.png        워드클라우드 이미지
"""
import sys, json, re
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path("data/amazon_reviews_B07B32PL1C.json")
OUT = Path("output")
OUT.mkdir(exist_ok=True)

# --- 불용어: 영어 기능어 + 리뷰에서 의미 없는 일반어 ---
STOP = set("""
a an the and or but if then so than that this these those there here
i me my we our you your he she it its they them their his her him
is am are was were be been being do does did doing have has had having
will would shall should can could may might must
of to in on at by for with from into onto about as up down out off over under again
not no nor too very just only also even still yet more most much many few less least
i'm i've it's don't didn't doesn't isn't wasn't aren't weren't can't won't couldn't
im ive its dont didnt doesnt isnt wasnt arent werent cant wont couldnt
get got getting go going goes went come comes came use used using uses
one two three really quite bit lot lots way ways thing things stuff
all any some each every both either neither other another such own same
what which who whom whose when where why how
because while during before after above below between through against
s t re ve ll d m o y amp nbsp br
review reviewed amazon product item order ordered buy bought purchase purchased
""".split())


def tokenize(text: str):
    text = text.lower()
    # 영문 단어만 (아포스트로피 포함), 숫자/특수문자 제거
    return re.findall(r"[a-z][a-z']+", text)


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    docs = []
    for r in data:
        body = (r.get("body") or "").strip()
        title = (r.get("title") or "").strip()
        if body or title:
            docs.append(f"{title} {body}")

    # --- 단일 단어 빈도 ---
    word_counter = Counter()
    # 단어가 등장한 '리뷰 수'(document frequency)도 같이 — 더 신뢰도 높은 순위
    doc_counter = Counter()
    bigram_counter = Counter()

    for doc in docs:
        toks = [w for w in tokenize(doc) if w not in STOP and len(w) > 2]
        word_counter.update(toks)
        doc_counter.update(set(toks))
        for a, b in zip(toks, toks[1:]):
            bigram_counter[f"{a} {b}"] += 1

    total_reviews = len(docs)

    # --- CSV 저장 (빈도 순위 전체) ---
    csv_path = OUT / "amazon_wordfreq.csv"
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("rank,word,count,review_count,review_pct\n")
        for i, (w, c) in enumerate(word_counter.most_common(), 1):
            dc = doc_counter[w]
            f.write(f"{i},{w},{c},{dc},{dc/total_reviews*100:.1f}\n")

    # --- 상위 50 텍스트 표 ---
    top_path = OUT / "amazon_wordfreq_top50.txt"
    with open(top_path, "w", encoding="utf-8") as f:
        f.write(f"아마존 리뷰 고객 단어 빈도 TOP 50  (총 {total_reviews}개 리뷰)\n")
        f.write("=" * 56 + "\n")
        f.write(f"{'순위':>4} {'단어':<18}{'언급횟수':>8}{'리뷰수':>7}{'비율':>8}\n")
        f.write("-" * 56 + "\n")
        for i, (w, c) in enumerate(word_counter.most_common(50), 1):
            dc = doc_counter[w]
            f.write(f"{i:>4} {w:<18}{c:>8}{dc:>7}{dc/total_reviews*100:>7.1f}%\n")

    # --- 상위 30 연어(bigram) ---
    bi_path = OUT / "amazon_bigrams_top30.csv"
    with open(bi_path, "w", encoding="utf-8-sig") as f:
        f.write("rank,bigram,count\n")
        for i, (bg, c) in enumerate(bigram_counter.most_common(30), 1):
            f.write(f"{i},{bg},{c}\n")

    # --- 워드클라우드 ---
    from wordcloud import WordCloud
    import matplotlib.pyplot as plt

    wc = WordCloud(
        width=1600, height=900,
        background_color="white",
        max_words=120,
        colormap="viridis",
        prefer_horizontal=0.9,
        collocations=False,  # 우리가 직접 빈도를 주므로 자동 연어 결합 끔
        relative_scaling=0.5,
        min_font_size=10,
    ).generate_from_frequencies(dict(word_counter))

    png_path = OUT / "amazon_wordcloud.png"
    plt.figure(figsize=(16, 9))
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close()

    # --- 콘솔 요약 ---
    print(f"리뷰 {total_reviews}개에서 고유 단어 {len(word_counter)}개 추출\n")
    print("TOP 25 고객 단어:")
    for i, (w, c) in enumerate(word_counter.most_common(25), 1):
        dc = doc_counter[w]
        print(f"  {i:>2}. {w:<16} {c:>4}회  ({dc}개 리뷰, {dc/total_reviews*100:.0f}%)")
    print("\nTOP 10 연어:")
    for i, (bg, c) in enumerate(bigram_counter.most_common(10), 1):
        print(f"  {i:>2}. {bg:<22} {c}회")
    print(f"\n저장: {csv_path}\n      {top_path}\n      {bi_path}\n      {png_path}")


if __name__ == "__main__":
    main()
