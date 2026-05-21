import importlib
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


EXPECTED = {
    1: {
        "vocabulary": ["你", "好", "您", "你们", "对不起", "没关系"],
        "dialogues": [
            ["你好！", "你好！"],
            ["您好！", "你们好！"],
            ["对不起！", "没关系！"],
        ],
    },
    2: {
        "vocabulary": ["谢谢", "不", "不客气", "再见"],
        "dialogues": [
            ["谢谢！", "不谢！"],
            ["谢谢你！", "不客气！"],
            ["再见！", "再见！"],
        ],
    },
    3: {
        "vocabulary": ["叫", "什么", "名字", "我", "是", "老师", "吗", "学生", "人", "李月", "中国", "美国"],
        "dialogues": [
            ["你叫什么名字？", "我叫李月。"],
            ["你是老师吗？", "我不是老师，我是学生。"],
            ["你是中国人吗？", "我不是中国人，我是美国人。"],
        ],
    },
    4: {
        "vocabulary": ["她", "谁", "的", "汉语", "哪", "国", "呢", "他", "同学", "朋友"],
        "dialogues": [
            ["她是谁？", "她是我的汉语老师，她叫李月。"],
            ["你是哪国人？", "我是美国人。你呢？", "我是中国人。"],
            ["他是谁？", "他是我同学。", "她呢？她是你同学吗？", "她不是我同学，她是我朋友。"],
        ],
    },
    5: {
        "vocabulary": ["家", "有", "口", "女儿", "几", "岁", "了", "今年", "多", "大"],
        "dialogues": [
            ["你家有几口人？", "我家有三口人。"],
            ["你女儿几岁了？", "她今年四岁了。"],
            ["李老师多大了？", "她今年50岁了。", "她女儿呢？", "她女儿今年20岁。"],
        ],
    },
}


def _lesson(order: int) -> dict:
    module = importlib.import_module(f"scripts.seed_hsk1_lesson_{order:02d}")
    return module.LESSON


def _actual_vocabulary(lesson: dict) -> list[str]:
    return [item["zh"] for item in json.loads(lesson["vocabulary_json"])]


def _actual_dialogues(lesson: dict) -> list[list[str]]:
    blocks = json.loads(lesson["dialogue_json"])
    return [
        [line["zh"] for line in block.get("dialogue", [])]
        for block in blocks
    ]


def verify() -> None:
    errors = []
    for order, expected in EXPECTED.items():
        lesson = _lesson(order)
        actual_vocabulary = _actual_vocabulary(lesson)
        actual_dialogues = _actual_dialogues(lesson)

        if actual_vocabulary != expected["vocabulary"]:
            errors.append(
                f"HSK1 lesson {order} vocabulary mismatch:\n"
                f"  expected={expected['vocabulary']}\n"
                f"  actual={actual_vocabulary}"
            )

        if actual_dialogues != expected["dialogues"]:
            errors.append(
                f"HSK1 lesson {order} dialogue mismatch:\n"
                f"  expected={expected['dialogues']}\n"
                f"  actual={actual_dialogues}"
            )

    if errors:
        raise SystemExit("\n\n".join(errors))

    print("HSK1 lessons 1-5 vocabulary/dialogues match the PDF canonical list.")


if __name__ == "__main__":
    verify()
