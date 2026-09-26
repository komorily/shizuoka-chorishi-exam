#!/usr/bin/env python3
"""data/questions.json と kaisetsu/data/part_*.json から、
年度ごとの解説付き解答 HTML (site/kaisetsu/R5.html, R6.html, R7.html) を生成する。

実行: python3 kaisetsu/build_kaisetsu.py
"""
import glob
import html
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
QUESTIONS = BASE / "data" / "questions.json"
PARTS = BASE / "kaisetsu" / "data"
OUT_DIR = BASE / "site" / "kaisetsu"

SUBJECTS = ["食文化概論", "公衆衛生学", "栄養学", "食品学", "食品衛生学", "調理理論"]
YEARS = [("R5", "令和5年度"), ("R6", "令和6年度"), ("R7", "令和7年度")]


def esc(s):
    return html.escape(s or "", quote=True)


def rich(s):
    """解説文: 全体をエスケープし、<strong> だけ許可する。"""
    t = esc(s)
    return t.replace("&lt;strong&gt;", "<strong>").replace("&lt;/strong&gt;", "</strong>")


def fix_stem(stem):
    # PDF抽出で空欄の枠が落ちた「、 の中に」を「、【　】の中に」に戻す
    return re.sub(r"、\s+の中", "、【　】の中", stem)


def render_passage(p):
    return esc(p).replace("【", '<span class="blank">').replace("】", "</span>")


def load_parts():
    by_id = {}
    for path in sorted(glob.glob(str(PARTS / "part_*.json"))):
        for item in json.loads(Path(path).read_text(encoding="utf-8")):
            assert item["id"] not in by_id, f"duplicate {item['id']} in {path}"
            assert len(item["choices"]) == 4, f"{item['id']}: choices != 4"
            by_id[item["id"]] = item
    return by_id


def render_question(q, k):
    no = q["no"]
    out = [f'<section class="q" id="q{no}">']
    out.append('<div class="q-head">'
               f'<span class="q-no">問{no}</span>'
               f'<span class="tag">{esc(k.get("tag") or q.get("theme") or "")}</span>'
               '</div>')
    out.append(f'<p class="stem">{esc(fix_stem(q["stem"]))}</p>')
    if q.get("passage"):
        out.append(f'<p class="passage">{render_passage(q["passage"])}</p>')
    if q.get("optionHeader"):
        out.append(f'<p class="opt-header">（{" ―― ".join(esc(h) for h in q["optionHeader"])}）</p>')
    out.append('<ol class="choices">')
    for i, c in enumerate(q["choices"], 1):
        out.append(f'<li><span class="c-num">{i}</span><span>{esc(c)}</span></li>')
    out.append('</ol>')

    out.append('<details class="kaisetsu"><summary>解答・解説を見る</summary><div class="k-body">')
    if q["invalidated"]:
        out.append('<p class="answer">正解：<span>全員正解（採点対象外）</span></p>')
        if k.get("invalidNote"):
            out.append(f'<p class="invalid-note">{rich(k["invalidNote"])}</p>')
    else:
        out.append(f'<p class="answer">正解：<span>{q["answer"]}</span></p>')

    for i, c in enumerate(k["choices"], 1):
        is_ans = (not q["invalidated"]) and i == q["answer"]
        ok = c["verdict"] == "正しい"
        label = c["verdict"] + ("（これが正解）" if is_ans else "")
        out.append(f'<div class="note-item{" correct" if is_ans else ""}">'
                   f'<div class="note-head">{i} <span class="verdict {"ok" if ok else "ng"}">{esc(label)}</span></div>'
                   f'<p>{rich(c["note"])}</p></div>')

    if k.get("points"):
        out.append('<div class="box"><h3>覚えるポイント</h3><ul>')
        out.extend(f'<li>{rich(p)}</li>' for p in k["points"])
        out.append('</ul></div>')
    if k.get("update"):
        out.append(f'<div class="box"><h3>最新の制度（補足）</h3><p>{rich(k["update"])}</p></div>')
    out.append('</div></details></section>')
    return "\n".join(out)


CSS = """
  :root {
    --bg: #e6e4dc; --card: #efede6; --text: #2a2b26; --muted: #66685f;
    --border: #d3d0c5; --accent: #2c4a63; --good: #2f6f49; --good-soft: #dce7dc;
    --bad: #a8382d; --note: #e4dece;
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #161816; --card: #1f221e; --text: #dfe1da; --muted: #9da397;
      --border: #333830; --accent: #9ec0dc; --good: #7fcf9d; --good-soft: #1d3025;
      --bad: #f08a7e; --note: #28281f;
      color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --bg: #161816; --card: #1f221e; --text: #dfe1da; --muted: #9da397;
    --border: #333830; --accent: #9ec0dc; --good: #7fcf9d; --good-soft: #1d3025;
    --bad: #f08a7e; --note: #28281f;
    color-scheme: dark;
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; scroll-padding-top: 64px; }
  body {
    margin: 0; -webkit-tap-highlight-color: transparent; background: var(--bg); color: var(--text);
    font-family: "Hiragino Kaku Gothic ProN", "Noto Sans JP", sans-serif;
    line-height: 1.75; font-size: 15px;
  }
  main { max-width: 760px; margin: 0 auto; padding: 24px 16px 64px; }
  header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  header h1 { font-size: 22px; line-height: 1.4; margin: 0 0 4px; text-wrap: balance; }
  .nw { display: inline-block; }
  header p { margin: 0 0 6px; color: var(--muted); font-size: 13px; }
  header p a { color: var(--accent); }
  .theme-btn {
    flex-shrink: 0; min-width: 44px; min-height: 44px; border-radius: 999px;
    border: 1px solid var(--border); background: var(--card); color: var(--text);
    font: inherit; font-size: 13px; padding: 0 14px; cursor: pointer;
  }
  nav.subj {
    position: sticky; top: 0; z-index: 5; background: var(--bg);
    display: flex; gap: 8px; overflow-x: auto; padding: 10px 0; margin-bottom: 12px;
    scrollbar-width: none;
  }
  nav.subj::-webkit-scrollbar { display: none; }
  nav.subj a {
    flex-shrink: 0; text-decoration: none; color: var(--text); font-size: 13px;
    border: 1px solid var(--border); background: var(--card); border-radius: 999px; padding: 6px 12px;
  }
  h2.subj-title { font-size: 17px; margin: 28px 0 12px; color: var(--accent); }
  h2.subj-title small { color: var(--muted); font-weight: 400; font-size: 13px; margin-left: 6px; }
  .q { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 20px; margin-bottom: 16px; }
  .q-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
  .q-no { font-weight: 800; font-size: 18px; color: var(--accent); }
  .tag { font-size: 12px; border: 1px solid var(--border); border-radius: 999px; padding: 1px 10px; color: var(--muted); }
  .stem { font-weight: 700; margin: 0 0 12px; }
  .passage { background: var(--note); border-radius: 10px; padding: 10px 12px; margin: 0 0 12px; }
  .blank { display: inline-block; min-width: 2.5em; text-align: center; border-bottom: 2px solid var(--accent); font-weight: 700; color: var(--accent); }
  .opt-header { color: var(--muted); font-size: 13px; margin: 0 0 4px; }
  ol.choices { list-style: none; padding: 0; margin: 0; }
  ol.choices li { display: flex; gap: 10px; padding: 8px 4px; border-bottom: 1px solid var(--border); }
  ol.choices li:last-child { border-bottom: 0; }
  .c-num { font-weight: 800; flex-shrink: 0; }
  details.kaisetsu { margin-top: 16px; border-top: 1px solid var(--border); }
  details.kaisetsu summary {
    cursor: pointer; list-style: none; padding: 12px 0; font-weight: 700; color: var(--accent);
    min-height: 44px; display: flex; align-items: center; justify-content: space-between;
  }
  details.kaisetsu summary::-webkit-details-marker { display: none; }
  details.kaisetsu summary::after { content: "＋"; color: var(--muted); font-weight: 400; }
  details.kaisetsu[open] summary::after { content: "－"; }
  .k-body { padding: 0 0 4px; }
  .answer { font-weight: 800; font-size: 17px; margin: 0 0 12px; }
  .answer span { color: var(--good); }
  .invalid-note { font-size: 14px; margin: -4px 0 12px; color: var(--muted); }
  .note-item { border-left: 3px solid var(--border); padding: 6px 0 6px 12px; margin-bottom: 12px; }
  .note-item.correct { border-left-color: var(--good); background: var(--good-soft); border-radius: 0 8px 8px 0; padding: 10px 12px; }
  .note-head { display: flex; gap: 8px; align-items: center; font-weight: 700; }
  .verdict { font-size: 12px; border-radius: 6px; padding: 0 8px; }
  .verdict.ok { color: var(--good); border: 1px solid var(--good); }
  .verdict.ng { color: var(--bad); border: 1px solid var(--bad); }
  .note-item p { margin: 4px 0 0; font-size: 14px; }
  .box { background: var(--note); border-radius: 10px; padding: 12px 14px; font-size: 14px; margin-top: 12px; }
  .box h3 { font-size: 14px; margin: 0 0 4px; }
  .box p, .box ul { margin: 0; }
  .box ul { padding-left: 1.2em; }
  @media (max-width: 480px) {
    body { font-size: 15.5px; }
    main { padding: 16px 12px 48px; }
    header h1 { font-size: 19px; }
    .q { padding: 16px 14px; border-radius: 12px; }
    .q-no { font-size: 17px; }
    .note-item p, .box { font-size: 14.5px; }
  }
"""

JS = """
(function () {
  var root = document.documentElement, btn = document.getElementById("theme-btn");
  function current() {
    var t = root.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function label() { btn.textContent = current() === "dark" ? "ライト" : "ダーク"; }
  try { var saved = localStorage.getItem("kaisetsu-theme"); if (saved) root.setAttribute("data-theme", saved); } catch (e) {}
  label();
  btn.onclick = function () {
    var next = current() === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("kaisetsu-theme", next); } catch (e) {}
    label();
  };
})();
"""


def render_year(year, label, questions, kaisetsu):
    qs = sorted((q for q in questions if q["year"] == year), key=lambda q: q["no"])
    others = " ／ ".join(f'<a class="nw" href="{y}.html">{l}</a>' for y, l in YEARS if y != year)
    body = []
    body.append(f"""<header>
  <div>
    <h1><span class="nw">{label}</span> <span class="nw">静岡県調理師試験</span> <span class="nw">解説付き解答</span></h1>
    <p><a class="nw" href="../">‹ 学習サイトに戻る</a></p>
    <p>全{len(qs)}問 ／ ほかの年度：{others}</p>
  </div>
  <button class="theme-btn" id="theme-btn" type="button">ダーク</button>
</header>""")
    first_no = {}
    for q in qs:
        first_no.setdefault(q["subject"], q["no"])
    body.append('<nav class="subj">' + "".join(
        f'<a href="#s{i}">{esc(s)}</a>' for i, s in enumerate(SUBJECTS) if s in first_no) + '</nav>')
    for i, s in enumerate(SUBJECTS):
        sq = [q for q in qs if q["subject"] == s]
        if not sq:
            continue
        body.append(f'<h2 class="subj-title" id="s{i}">{esc(s)}<small>問{sq[0]["no"]}〜問{sq[-1]["no"]}</small></h2>')
        for q in sq:
            body.append(render_question(q, kaisetsu[q["id"]]))
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{label} 解説付き解答</title>
<style>{CSS}</style>
</head>
<body>
<main>
{chr(10).join(body)}
</main>
<script>{JS}</script>
</body>
</html>
"""


def main():
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    kaisetsu = load_parts()
    for year, label in YEARS:
        missing = [q["id"] for q in questions if q["year"] == year and q["id"] not in kaisetsu]
        if missing:
            print(f"skip {year}: {len(missing)} questions missing ({missing[0]}...)")
            continue
        out = OUT_DIR / f"{year}.html"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out.write_text(render_year(year, label, questions, kaisetsu), encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
