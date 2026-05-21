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
    },
    2: {
        "vocabulary": [
            "腿",
            "疼",
            "脚",
            "树",
            "容易",
            "难",
            "太太",
            "秘书",
            "经理",
            "办公室",
            "辆",
            "楼",
            "拿",
            "把",
            "伞",
            "胖",
            "其实",
            "瘦",
            "周",
            "周明",
        ],
        "dialogues": [
            [
                "休息一下吧。",
                "怎么了？",
                "我现在腿也疼，脚也疼。",
                "好，那边树多，我们过去坐一下吧。",
                "上来的时候我怎么没觉得这么累？",
                "上山容易下山难，你不知道？",
            ],
            [
                "喂，你好，请问周明在吗？",
                "周经理出去了，不在办公室。",
                "他去哪儿了？什么时候回来？",
                "他出去办事了，下午回来。",
                "回来了就让他给我打个电话。",
                "好的，他到了办公室我就告诉他。",
            ],
            [
                "雨下得真大。你怎么回去？我送你吧。",
                "没事，我出去叫辆出租车就行了。",
                "那你等等，我上楼去给你拿把伞。",
                "好的。我跟你一起上去吧。",
                "你在这儿等吧，我拿了伞就下来。",
            ],
            [
                "你看，我这么胖，怎么办呢？",
                "你每天晚上吃了饭就睡觉，也不出去走走，能不胖吗？",
                "其实我每天都运动。",
                "但是你一点儿也没瘦！你做什么运动了？",
                "做饭啊。",
            ],
        ],
    },
    3: {
        "vocabulary": [
            "还是",
            "爬山",
            "小心",
            "条",
            "裤子",
            "记得",
            "衬衫",
            "元",
            "新鲜",
            "甜",
            "只",
            "放",
            "饮料",
            "或者",
            "舒服",
            "花",
            "绿",
        ],
        "dialogues": [
            [
                "明天是晴天还是阴天？",
                "阴天，电视上说多云。怎么了？有事？",
                "没事，我们明天要去爬山。",
                "爬山的时候要小心点儿。",
                "好，你也去吗？",
                "我不去，我有事。",
            ],
            [
                "你觉得这条裤子怎么样？",
                "我记得你已经有两条这样的裤子了。",
                "那我们再看看别的。",
                "这件衬衫怎么样？",
                "还不错，多少钱？",
                "这上面写着320元。",
                "买一件。",
            ],
            [
                "这些水果真新鲜，我们买西瓜还是苹果？",
                "西瓜吧。你看，这上面写着“西瓜不甜不要钱”。",
                "那我们买一个大点儿的吧。",
                "再买几个苹果。",
                "好啊，今天晚上只吃水果不吃饭！",
            ],
            [
                "桌子上放着很多饮料，你喝什么？",
                "茶或者咖啡都可以。你呢？你喝什么？",
                "我喝茶，茶是我的最爱。天冷了或者工作累了的时候，喝杯热茶会很舒服。",
                "你喜欢喝什么茶？",
                "花茶、绿茶、红茶，我都喜欢。",
            ],
        ],
    },
    4: {
        "vocabulary": [
            "比赛",
            "照片",
            "年级",
            "又",
            "聪明",
            "热情",
            "努力",
            "总是",
            "回答",
            "站",
            "饿",
            "超市",
            "蛋糕",
            "年轻",
            "认真",
            "客人",
            "小明",
            "马可",
            "李小美",
        ],
        "dialogues": [
            [
                "这是你们比赛的照片吗？",
                "是，这是我们比赛后照的。",
                "照得不错，你们都是一个年级的吗？",
                "不是。那个又高又漂亮的女孩儿是二年级的。",
                "旁边那个拿着书笑的人是谁？",
                "那是我！",
            ],
            [
                "你觉得李小美怎么样？",
                "她又聪明又热情，也很努力。",
                "我看她总是笑着回答老师的问题。",
                "她对每个人都笑，也常常对我笑。",
                "你是不是喜欢她啊？",
                "喜欢她的人太多了，你看那些拿着鲜花站在门口的，都是等她的。",
            ],
            [
                "我有点儿饿了，我们进超市买点儿东西吧。",
                "好啊，这家超市的蛋糕又便宜又好吃，一块只要2.99元。",
                "我们买两块，回家吃着蛋糕看电视，怎么样？",
                "好啊，我再去买一些喝的。",
                "喝着咖啡吃蛋糕，太好了！",
            ],
            [
                "您好！您找谁？",
                "你们这儿是不是有一个又年轻又漂亮的服务员？",
                "我们这儿年轻、漂亮的服务员有很多。",
                "她工作又认真又热情。",
                "您能再说说吗？",
                "她总是笑着跟客人说话。",
                "啊，我知道了，你说的是李小美吧？",
            ],
        ],
    },
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

    print("HSK3 lessons 1-4 vocabulary/dialogues match the PDF canonical list.")


if __name__ == "__main__":
    verify()
