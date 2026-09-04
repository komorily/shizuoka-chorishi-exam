#!/usr/bin/env python3
"""静岡県調理師試験 過去問PDF (info/) を questions.json に構造化する。

実行: python3 data/extract_questions.py
出力: data/questions.json, data/questions_review.txt（目視レビュー用）
"""
import json
import re
import sys
from pathlib import Path

import pypdf

BASE = Path(__file__).resolve().parent.parent
INFO = BASE / "info"
OUT_JSON = BASE / "data" / "questions.json"
OUT_REVIEW = BASE / "data" / "questions_review.txt"

YEARS = [
    {"year": "R5", "yearLabel": "令和5年度",
     "mondai": "r5_chourishishikennmondai (1).pdf",
     "seitou": "r5_chourishishikennseitou (1).pdf"},
    {"year": "R6", "yearLabel": "令和6年度",
     "mondai": "r6chorishishikenmondai (1).pdf",
     "seitou": "r6chorishishikenkaito (1).pdf"},
    {"year": "R7", "yearLabel": "令和7年度",
     "mondai": "r7chourishimondai (2).pdf",
     "seitou": "r7chourishikaitou (2).pdf"},
]

SUBJECT_RANGES = [
    (1, 5, "食文化概論"),
    (6, 13, "公衆衛生学"),
    (14, 21, "栄養学"),
    (22, 27, "食品学"),
    (28, 43, "食品衛生学"),
    (44, 60, "調理理論"),
]

FULLWIDTH_DIGITS = "０１２３４５６７８９"
HALFWIDTH_DIGITS = "0123456789"
DIGIT_TRANS = str.maketrans(FULLWIDTH_DIGITS, HALFWIDTH_DIGITS)

CHOICE_MARK_RE = re.compile(r"^[ 　]*([１２３４])[ 　]+(\S.*)$")
PAGE_FOOTER_RE = re.compile(r"^[ 　]*[\-－]\s*\d+\s*[\-－][ 　]*$")
QSTART_RE = re.compile(r"問\s*([0-9０-９]{1,2})\s")
BLANK_PAGE_RE = re.compile(r"^[ 　]*白\s*紙[ 　]*$")
SUBJECT_HEADER_RE = re.compile(
    r"^[ 　]*[１２３４５６]\s*(?:"
    r"食\s*文\s*化\s*概\s*論|"
    r"公\s*衆\s*衛\s*生\s*学|"
    r"栄\s*養\s*学|"
    r"食\s*品\s*学|"
    r"食\s*品\s*衛\s*生\s*学|"
    r"調\s*理\s*理\s*論"
    r")$"
)
END_MARK_RE = re.compile(r"〈\s*解\s*答\s*用\s*紙\s*の\s*記\s*入\s*例\s*〉")


def subject_of(no: int) -> str:
    for lo, hi, name in SUBJECT_RANGES:
        if lo <= no <= hi:
            return name
    raise ValueError(f"no subject range for question {no}")


def to_int(s: str) -> int:
    return int(s.translate(DIGIT_TRANS))


def collapse_spaces(s: str) -> str:
    return re.sub(r"[ 　]{2,}", " ", s).strip()


def normalize_dashes(s: str) -> str:
    return re.sub(r"[—―ー\-]{2,}", " ―― ", s)


def normalize_parens_line(line: str) -> str:
    """（ Ａ ） → (Ａ) のように括弧内の空白を除去して正規化する。"""
    def repl(m):
        inner = re.sub(r"[ 　]+", "", m.group(1))
        return f"({inner})"
    return re.sub(r"[（(]\s*([^（）()]*?)\s*[）)]", repl, line)


def is_header_line(line: str) -> bool:
    if "（" not in line and "(" not in line:
        return False
    placeholder = re.sub(r"[（(]\s*[^（）()]*?\s*[）)]", "X", line)
    placeholder = re.sub(r"[ 　]+", "", placeholder)
    return placeholder != "" and set(placeholder) == {"X"}


def extract_header_groups(line: str):
    norm = normalize_parens_line(line)
    return [collapse_spaces(g) for g in re.findall(r"\(([^()]*)\)", norm)]


def normalize_passage_blanks(text: str) -> str:
    # 「 Ａ 」のように空白に挟まれた単独の全角ラテン大文字を空欄マーカーに変換する
    text = re.sub(r"[ 　]+([ＡＢＣＤ])[ 　]+", r"【\1】", text)
    # ラベルのない素の空欄（3文字以上の連続スペース）も空欄マーカーにする
    text = re.sub(r"[ 　]{3,}", "【　】", text)
    # 残りの折り返し由来の余分なスペース(1〜2個)は詰める
    text = re.sub(r"[ 　]{1,2}", "", text)
    return text.strip()


def read_pages_text(pdf_path: Path):
    reader = pypdf.PdfReader(str(pdf_path))
    return [p.extract_text() for p in reader.pages]


def extract_mondai(pdf_path: Path):
    pages = read_pages_text(pdf_path)
    full = "\n".join(pages)
    m = END_MARK_RE.search(full)
    if m:
        full = full[: m.start()]

    matches = list(QSTART_RE.finditer(full))
    if len(matches) < 60:
        print(f"[WARN] {pdf_path.name}: only {len(matches)} question markers found", file=sys.stderr)

    questions = {}
    for i, m in enumerate(matches):
        no = to_int(m.group(1))
        if not (1 <= no <= 60):
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full)
        block = full[start:end]

        # 行頭の空白は素の空欄(ラベルなしのブランク)を表すことがあるため、
        # 行末のみ削り、行頭の空白は維持する。
        lines = [ln.rstrip() for ln in block.splitlines()]
        lines = [
            ln for ln in lines
            if ln
            and not PAGE_FOOTER_RE.match(ln)
            and not SUBJECT_HEADER_RE.match(ln)
            and not BLANK_PAGE_RE.match(ln)
        ]

        # 1) stem: 「どれか。」で終わる(連結後の)行までを積み上げる
        stem_lines = []
        idx = 0
        acc = ""
        for idx, ln in enumerate(lines):
            stem_lines.append(ln)
            acc += ln
            if acc.endswith("どれか。"):
                break
        stem_text = collapse_spaces("".join(stem_lines))
        remainder = lines[idx + 1:]

        # 2) 最初の選択肢行(全角1-4で始まる行)を探す
        choice_start = None
        for j, ln in enumerate(remainder):
            if CHOICE_MARK_RE.match(ln):
                choice_start = j
                break
        if choice_start is None:
            print(f"[WARN] {pdf_path.name} 問{no}: 選択肢が見つかりません", file=sys.stderr)
            choice_start = len(remainder)

        extra_lines = remainder[:choice_start]
        choice_lines = remainder[choice_start:]

        # 3) extra_lines を header行/passage行に分類
        header_lines = [ln for ln in extra_lines if is_header_line(ln)]
        passage_lines = [ln for ln in extra_lines if not is_header_line(ln)]

        passage = None
        if passage_lines:
            passage = normalize_passage_blanks("".join(passage_lines))

        option_header = None
        if header_lines:
            groups = []
            for hl in header_lines:
                groups.extend(extract_header_groups(hl))
            option_header = groups

        # 4) 選択肢の分割(行頭の全角数字1-4を境目にグルーピング)
        choices = []
        cur = None
        for ln in choice_lines:
            mm = CHOICE_MARK_RE.match(ln)
            if mm:
                if cur is not None:
                    choices.append(cur)
                cur = mm.group(2)
            else:
                if cur is None:
                    continue
                cur += ln
        if cur is not None:
            choices.append(cur)

        choices = [collapse_spaces(normalize_dashes(c)) for c in choices]

        if len(choices) != 4:
            print(f"[WARN] {pdf_path.name} 問{no}: 選択肢が{len(choices)}個です", file=sys.stderr)

        if option_header:
            fmt = "組合せ"
        elif passage:
            fmt = "空欄補充"
        else:
            fmt = "正誤"

        questions[no] = {
            "no": no,
            "subject": subject_of(no),
            "format": fmt,
            "stem": stem_text,
            "passage": passage,
            "optionHeader": option_header,
            "choices": choices,
        }

    return questions


def extract_seitou(pdf_path: Path):
    """正答表は「問N 問N+1 ...」という見出し行の次の行に、
    半角数字/※ が同じ個数だけ並ぶ表形式になっている。"""
    pages = read_pages_text(pdf_path)
    full = "\n".join(pages)
    lines = [ln.strip() for ln in full.splitlines() if ln.strip()]

    answers = {}
    pending_nums = None
    for ln in lines:
        nums = re.findall(r"問\s*([0-9０-９]{1,2})", ln)
        if nums:
            pending_nums = [to_int(n) for n in nums]
            continue
        if pending_nums:
            vals = re.findall(r"[1234※]", ln)
            if len(vals) == len(pending_nums):
                for no, v in zip(pending_nums, vals):
                    if v == "※":
                        answers[no] = {"answer": None, "invalidated": True}
                    else:
                        answers[no] = {"answer": int(v), "invalidated": False}
                pending_nums = None
    return answers


# 段落先頭の装飾的インデントが空欄マーカーと誤認識されるなど、
# 機械抽出だけでは直せない既知の崩れを目視レビューの上で個別に補正する。
MANUAL_FIXUPS = {
    "R5-16": {
        "passage": "アミノ酸だけでつくられている単純たんぱく質と他の物質（核酸、糖、"
                   "脂質、リン酸、色素、金属等）が結合したものを複合たんぱく質といい、"
                   "このうち【　】は、脂質とたんぱく質の結合物質である。",
    },
}


def apply_manual_fixups(item: dict) -> dict:
    fixup = MANUAL_FIXUPS.get(item["id"])
    if fixup:
        item.update(fixup)
    return item


def main():
    all_questions = []
    review_lines = []

    for spec in YEARS:
        mondai_path = INFO / spec["mondai"]
        seitou_path = INFO / spec["seitou"]
        questions = extract_mondai(mondai_path)
        answers = extract_seitou(seitou_path)

        assert len(questions) == 60, f"{spec['year']}: {len(questions)} questions parsed (expected 60)"
        assert len(answers) == 60, f"{spec['year']}: {len(answers)} answers parsed (expected 60)"

        for no in range(1, 61):
            q = questions[no]
            a = answers[no]
            assert len(q["choices"]) == 4, f"{spec['year']} 問{no}: choices != 4"
            if not a["invalidated"]:
                assert a["answer"] in (1, 2, 3, 4), f"{spec['year']} 問{no}: bad answer"

            item = {
                "id": f"{spec['year']}-{no}",
                "year": spec["year"],
                "yearLabel": spec["yearLabel"],
                "no": no,
                "subject": q["subject"],
                "format": q["format"],
                "stem": q["stem"],
                "passage": q["passage"],
                "optionHeader": q["optionHeader"],
                "choices": q["choices"],
                "answer": a["answer"],
                "invalidated": a["invalidated"],
                "theme": None,
                "explanation": None,
                "choiceNotes": None,
            }
            item = apply_manual_fixups(item)
            all_questions.append(item)

            review_lines.append(f"===== {item['id']} [{item['subject']}] format={item['format']} =====")
            review_lines.append(f"stem: {item['stem']}")
            if item["passage"]:
                review_lines.append(f"passage: {item['passage']}")
            if item["optionHeader"]:
                review_lines.append(f"header: {item['optionHeader']}")
            for i, c in enumerate(item["choices"], 1):
                mark = " <=ANSWER" if item["answer"] == i else ""
                review_lines.append(f"  {i}. {c}{mark}")
            if item["invalidated"]:
                review_lines.append("  ※全員正解")
            review_lines.append("")

        print(f"{spec['year']}: OK (60問)")

    OUT_JSON.write_text(json.dumps(all_questions, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_REVIEW.write_text("\n".join(review_lines), encoding="utf-8")
    print(f"wrote {OUT_JSON} ({len(all_questions)} questions)")
    print(f"wrote {OUT_REVIEW}")


if __name__ == "__main__":
    main()
