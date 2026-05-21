import importlib
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


EXPECTED = {
    1: {
        "vocabulary": [
            "周末",
            "打算",
            "啊",
            "跟",
            "一直",
            "游戏",
            "作业",
            "着急",
            "复习",
            "南方",
            "北方",
            "面包",
            "带",
            "地图",
            "搬",
            "小丽",
            "小刚",
        ],
        "dialogues": [
            [
                "周末你有什么打算？",
                "我早就想好了，请你吃饭、看电影、喝咖啡。",
                "请我？",
                "是啊，我已经找好饭馆了，电影票也买好了。",
                "我还没想好要不要跟你去呢。",
            ],
            [
                "你一直玩儿电脑游戏，作业写完了吗？",
                "都写完了。",
                "明天不是有考试吗？你怎么一点儿也不着急？",
                "我早就复习好了。",
                "那也不能一直玩儿啊。",
            ],
            [
                "下个月我去旅游，你能跟我一起去吗？",
                "我还没想好呢。你觉得哪儿最好玩儿？",
                "南方啊，我们去年就是这个时候去的。",
                "南方太热了，北方好一些，不冷也不热。",
            ],
            [
                "水果、面包、茶都准备好了，我们还带什么？",
                "手机、电脑、地图，一个也不能少。",
                "这些我昨天下午就准备好了。",
                "再多带几件衣服吧。",
                "我们是去旅游，不是搬家，还是少带一些吧。",
            ],
        ],
    }
}


def _lesson(order: int) -> dict:
    module = importlib.import_module(f"scripts.seed_hsk3_lesson_{order:02d}")
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
                f"HSK3 lesson {order} vocabulary mismatch:\n"
                f"  expected={expected['vocabulary']}\n"
                f"  actual={actual_vocabulary}"
            )

        if actual_dialogues != expected["dialogues"]:
            errors.append(
                f"HSK3 lesson {order} dialogue mismatch:\n"
                f"  expected={expected['dialogues']}\n"
                f"  actual={actual_dialogues}"
            )

    if errors:
        raise SystemExit("\n\n".join(errors))

    print("HSK3 lesson 1 vocabulary/dialogues match the PDF canonical list.")


if __name__ == "__main__":
    verify()
