#!/usr/bin/env python3
"""toranomaki/*.md を data/toranomaki.json（サイト埋め込み用）に変換する。

各Markdownファイル:
  # 見出し(章タイトル)
  （章のイントロ文、任意）
  ## テーマ見出し（トピック）
  ### 小見出し
  ...
  {{practice:テーマ名}}   <- 演習へのリンクに変換される特殊記法

実行: python3 data/build_toranomaki.py
"""
import json
import re
from pathlib import Path

import markdown as md

BASE = Path(__file__).resolve().parent.parent
TK_DIR = BASE / "toranomaki"
OUT = BASE / "data" / "toranomaki.json"

PRACTICE_RE = re.compile(r"\{\{practice:([^}]+)\}\}")


def render_md(text: str) -> str:
    html = md.markdown(text.strip(), extensions=["tables", "nl2br"])
    def repl(m):
        theme = m.group(1).strip()
        return (
            f'<a href="#" class="theme-link theme-jump" data-theme="{esc(theme)}">'
            f"「{esc(theme)}」の演習に挑戦する →</a>"
        )
    return PRACTICE_RE.sub(repl, html)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def parse_file(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    title = None
    intro_lines = []
    topics = []  # list of {title, body_lines}
    cur = None
    i = 0
    # find H1
    while i < len(lines):
        if lines[i].startswith("# "):
            title = lines[i][2:].strip()
            i += 1
            break
        i += 1
    # intro until first H2
    while i < len(lines) and not lines[i].startswith("## "):
        intro_lines.append(lines[i])
        i += 1
    # topics
    while i < len(lines):
        if lines[i].startswith("## "):
            if cur is not None:
                topics.append(cur)
            cur = {"title": lines[i][3:].strip(), "body_lines": []}
            i += 1
            continue
        if cur is not None:
            cur["body_lines"].append(lines[i])
        i += 1
    if cur is not None:
        topics.append(cur)

    chapter = {
        "title": title or path.stem,
        "intro": render_md("\n".join(intro_lines)) if any(l.strip() for l in intro_lines) else "",
        "topics": [
            {"title": t["title"], "body": render_md("\n".join(t["body_lines"]))}
            for t in topics
        ],
    }
    return chapter


def main():
    files = sorted(TK_DIR.glob("*.md"))
    assert files, f"no markdown files found in {TK_DIR}"
    chapters = [parse_file(f) for f in files]
    OUT.write_text(json.dumps(chapters, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT}: {len(chapters)} chapters")
    for f, ch in zip(files, chapters):
        print(f"  {f.name}: {ch['title']} ({len(ch['topics'])} topics)")


if __name__ == "__main__":
    main()
