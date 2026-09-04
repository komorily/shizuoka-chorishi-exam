#!/usr/bin/env python3
"""explanations_*.json (8つのエージェント出力) を questions.json にマージする。

実行: python3 data/merge_explanations.py
"""
import glob
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
QUESTIONS = BASE / "data" / "questions.json"

REQUIRED_KEYS = {"id", "theme", "explanation", "choiceNotes"}


def main():
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    by_id = {q["id"]: q for q in questions}

    seen_ids = set()
    for path in sorted(glob.glob(str(BASE / "data" / "explanations_*.json"))):
        items = json.loads(Path(path).read_text(encoding="utf-8"))
        for item in items:
            missing = REQUIRED_KEYS - set(item.keys())
            assert not missing, f"{path}: {item.get('id')} missing keys {missing}"
            qid = item["id"]
            assert qid in by_id, f"{path}: unknown id {qid}"
            assert qid not in seen_ids, f"duplicate id {qid} (in {path})"
            seen_ids.add(qid)

            choice_notes = item["choiceNotes"]
            assert isinstance(choice_notes, list) and len(choice_notes) == 4, \
                f"{qid}: choiceNotes must have 4 entries, got {choice_notes}"

            q = by_id[qid]
            q["theme"] = item["theme"]
            q["explanation"] = item["explanation"]
            q["choiceNotes"] = choice_notes

    missing_ids = set(by_id.keys()) - seen_ids
    assert not missing_ids, f"questions with no explanation: {sorted(missing_ids)}"
    assert len(seen_ids) == 180, f"expected 180 merged, got {len(seen_ids)}"

    QUESTIONS.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"merged {len(seen_ids)} explanations into {QUESTIONS}")


if __name__ == "__main__":
    main()
