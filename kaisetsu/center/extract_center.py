#!/usr/bin/env python3
"""調理技術技能センターの過去問 PDF (center/) を kaisetsu/center/questions.json に変換する。

実行: python3 kaisetsu/center/extract_center.py
出力: kaisetsu/center/questions.json（180問）と kaisetsu/center/questions_review.txt（目視確認用）
"""
import glob
import json
import re
import unicodedata
from pathlib import Path

import pypdf

BASE = Path(__file__).resolve().parent.parent.parent
SRC = BASE / "center"
OUT = BASE / "kaisetsu" / "center" / "questions.json"
REVIEW = BASE / "kaisetsu" / "center" / "questions_review.txt"

YEARS = [("R5", "令和5年度", "R05"), ("R6", "令和6年度", "R6"), ("R7", "令和7年度", "R7")]
# センターの出題順（静岡とは科目の順番が違う）
SUBJECT_RANGES = [
    ("公衆衛生学", 1, 10), ("食品学", 11, 16), ("栄養学", 17, 25),
    ("食品衛生学", 26, 40), ("調理理論", 41, 56), ("食文化概論", 57, 60),
]
HEADINGS = {"公衆衛生学", "食品学", "栄養学", "食品衛生学", "調理理論", "食文化概論"}
# 汎用的に直せない抽出の崩れを問題ごとに直す
MANUAL_FIXUPS = {
    "CR5-49": {"stem": "糖類の甘味度の強い順として、正しいものを一つ選びなさい。（甘味度が強い＞甘味度が弱い）"},
}
WRAP_WIDTH = 70  # これ以上の表示幅の行は、PDF上で折り返されている


def width(s):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def join(a, b):
    # 折り返しの継ぎ目。日本語どうしなら空白なしで連結
    a, b = a.rstrip(), b.strip()
    if a and b and a[-1].isascii() and b[0].isascii() and a[-1].isalnum() and b[0].isalnum():
        return a + " " + b
    return a + b


def norm(s):
    s = re.sub(r"\s+", " ", s).strip()
    # 全角文字の間の余計な空白を詰める（「21（第二次） 」→「21（第二次）」など）
    s = re.sub(r"(?<=[^\x00-\x7f]) (?=[^\x00-\x7f])", "", s)
    s = re.sub(r"(?<=[^\x00-\x7f]) (?=[）」』、。])", "", s)
    return s


# ふりがな（ルビ）は PDF から単独の行として出てくる。読みを残す語だけここに書く
KEEP_RUBY = {"冬菇", "卓袱", "更科", "antipasto"}


def split_passage(q):
    """穴埋め問題: 『…』を本文に分け、空欄を【A】【　】の形にする。"""
    m = re.match(r"^(.*?)『(.*)』(.*)$", q["stem"])
    if not m:
        return None
    stem, passage, tail = m.groups()
    stem = re.sub(r"、\s{2,}に入る", "、【＿】に入る", stem)
    passage = re.sub(r"(^|\s)[A-C](?=\s|$)", lambda x: f"【{x.group(0).strip()}】", passage)
    passage = re.sub(r"\s*([Ａ-Ｃ])\s*", lambda x: f"【{unicodedata.normalize('NFKC', x.group(1))}】", passage)
    passage = re.sub(r"\s{2,}", "【＿】", passage.rstrip())
    q["stem"] = stem
    letters = re.findall(r"[A-CＡ-Ｃ]", tail)
    if letters and not q["optionHeader"]:
        q["optionHeader"] = [unicodedata.normalize("NFKC", c) for c in letters]
    return passage


def lines_of(pdf):
    text = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(pdf).pages)
    out = []
    merge_next = False
    started = False
    for raw in text.split("\n"):
        ln = unicodedata.normalize("NFKC", raw).rstrip() if re.match(r"\s*[１-４]", raw) else raw.rstrip()
        s = ln.strip()
        if not s:
            continue
        if re.fullmatch(r"-\s*\d+\s*-", s):
            started = True
            continue
        if not started:
            continue  # 表紙（注意事項・記入例）を飛ばす
        if re.fullmatch(r"[0-9０-９ ]+", s):
            continue  # 枠で囲まれた問題番号（PDFでは問題の後ろにまとめて出る）
        if s.replace(" ", "") in HEADINGS:
            continue
        if re.fullmatch(r"[ぁ-んァ-ヶー ]{1,12}", s) and out:
            # ルビの行: 前の行の続きが次の行に来るので、次の行を前の行につなぐ
            # （ただし選択肢4の末尾のルビの次は、新しい問題の文）
            reading = s.replace(" ", "")
            if any(out[-1].rstrip().endswith(w) for w in KEEP_RUBY):
                out[-1] = out[-1].rstrip() + f"（{reading}）"
            merge_next = True
            continue
        if merge_next:
            merge_next = False
            if not (re.match(r"\s*[1-4]\s", out[-1]) and re.search(r"選び|一つ", s)):
                out[-1] = join(out[-1], s)
                continue
        out.append(ln)
    return out


def parse(lines):
    qs = []
    q = None
    state = "stem"
    expect = 1
    prev = ""
    for ln in lines:
        s = ln.strip()
        m = re.match(r"^([1-4])\s*(.*)$", s)
        if state == "stem":
            if m and int(m.group(1)) == 1 and q and q["stem"]:
                state = "choice"
                q["choices"].append(m.group(2))
                expect = 2
            elif s.startswith("《"):
                q["optionHeader"] = re.findall(r"《([^》]+)》", s)
            elif q is None or q["choices"]:
                q = {"stem": s, "choices": [], "optionHeader": None}
                qs.append(q)
            else:
                q["stem"] = join(q["stem"], s)
        else:  # choice
            if m and int(m.group(1)) == expect:
                q["choices"].append(m.group(2))
                expect += 1
            elif expect <= 4 or (width(prev) >= WRAP_WIDTH and (
                    not prev.endswith("。") or (s.endswith("。") and "なさい" not in s))):
                q["choices"][-1] = join(q["choices"][-1], s)
            elif expect == 5:
                state = "stem"
                q = {"stem": s, "choices": [], "optionHeader": None}
                qs.append(q)
            else:
                raise ValueError(f"unexpected line: {s!r} (after {prev!r})")
        prev = s
    return qs


def parse_answers(pdf):
    text = "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(pdf).pages)
    nos, vals = [], []
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith("問"):
            nos += [int(n) for n in re.findall(r"問\s*(\d+)", s)]
        elif re.fullmatch(r"[1-4※ ]+", s):
            vals += s.split()
    assert len(nos) == len(vals) == 60, (len(nos), len(vals))
    return {n: (None if v == "※" else int(v)) for n, v in zip(nos, vals)}


def subject_of(no):
    for name, lo, hi in SUBJECT_RANGES:
        if lo <= no <= hi:
            return name
    raise ValueError(no)


def main():
    allq = []
    for year, label, tag in YEARS:
        qpdf = glob.glob(str(SRC / f"【{tag}】調理師試験問題*.pdf"))[0]
        apdf = glob.glob(str(SRC / f"【{tag}】解答番号一覧*.pdf"))[0]
        qs = parse(lines_of(qpdf))
        ans = parse_answers(apdf)
        assert len(qs) == 60, f"{year}: {len(qs)} questions"
        for no, q in enumerate(qs, 1):
            assert len(q["choices"]) == 4, f"{year}-{no}: {q}"
            passage = split_passage(q)
            allq.append({
                "id": f"C{year}-{no}", "year": year, "yearLabel": label, "no": no,
                "subject": subject_of(no),
                "format": "組合せ" if q["optionHeader"] else ("空欄補充" if passage else "正誤"),
                "stem": norm(q["stem"]).replace("＿", "　"),
                "passage": norm(passage).replace("＿", "　") if passage else None,
                "optionHeader": q["optionHeader"],
                "choices": [norm(re.sub(r"\s*[―—]{2,}\s*", " ―― ", c)) for c in q["choices"]],
                "answer": ans[no], "invalidated": ans[no] is None,
            })
    for q in allq:
        q.update(MANUAL_FIXUPS.get(q["id"], {}))
    OUT.write_text(json.dumps(allq, ensure_ascii=False, indent=1), encoding="utf-8")
    with REVIEW.open("w", encoding="utf-8") as f:
        for q in allq:
            f.write(f"[{q['id']}] {q['subject']} 正解={q['answer']}\n{q['stem']}\n")
            if q["optionHeader"]:
                f.write("  《" + "》《".join(q["optionHeader"]) + "》\n")
            for i, c in enumerate(q["choices"], 1):
                f.write(f"  {i} {c}\n")
            f.write("\n")
    print(f"wrote {OUT} ({len(allq)} questions)")


if __name__ == "__main__":
    main()
