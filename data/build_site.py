#!/usr/bin/env python3
"""site/index.template.html に questions.json と toranomaki.json を埋め込み、
site/index.html を生成する。

実行: python3 data/build_site.py
"""
import base64
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TEMPLATE = BASE / "site" / "index.template.html"
OUT = BASE / "site" / "index.html"
VERSION_OUT = BASE / "site" / "version.txt"
QUESTIONS = BASE / "data" / "questions.json"
TORANOMAKI = BASE / "data" / "toranomaki.json"
IMAGES_DIR = BASE / "images"

# ファイル名 -> IMAGES オブジェクトのキー
IMAGE_FILES = {
    "hero": "home-header.png",
    "食文化概論": "food-culture.png",
    "公衆衛生学": "public-health.png",
    "栄養学": "nutrition.png",
    "食品学": "food-science.png",
    "食品衛生学": "food-hygiene.png",
    "調理理論": "cooking-theory.png",
}


def build_images():
    images = {}
    for key, filename in IMAGE_FILES.items():
        path = IMAGES_DIR / filename
        if not path.exists():
            continue
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        images[key] = f"data:image/png;base64,{data}"
    return images


def main():
    template = TEMPLATE.read_text(encoding="utf-8")
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))

    if TORANOMAKI.exists():
        toranomaki = json.loads(TORANOMAKI.read_text(encoding="utf-8"))
    else:
        toranomaki = []

    images = build_images()

    # <script type="application/json"> の中身なので、"</script" だけ気をつければ良い
    q_json = json.dumps(questions, ensure_ascii=False).replace("</script", "<\\/script")
    t_json = json.dumps(toranomaki, ensure_ascii=False).replace("</script", "<\\/script")
    i_json = json.dumps(images, ensure_ascii=False).replace("</script", "<\\/script")

    out = (
        template
        .replace("__QUESTIONS_JSON__", q_json)
        .replace("__TORANOMAKI_JSON__", t_json)
        .replace("__IMAGES_JSON__", i_json)
    )
    # 中身から版番号を作る。ページは version.txt と比べて、違えば読み込み直す
    version = hashlib.sha256(out.encode("utf-8")).hexdigest()[:12]
    out = out.replace("__BUILD_VERSION__", version)
    OUT.write_text(out, encoding="utf-8")
    VERSION_OUT.write_text(version + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(out)} chars, {len(questions)} questions, {len(toranomaki)} toranomaki chapters, {len(images)} images)")


if __name__ == "__main__":
    main()
