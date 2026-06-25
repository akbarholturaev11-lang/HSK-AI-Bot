import json
from datetime import datetime, timezone

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import or_, select

from app.bot.utils.course_miniapp import course_study_miniapp_url, normalize_miniapp_lang
from app.db.models.course_challenge import CourseChallenge
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService


CHALLENGE_STATUSES = {"pending", "accepted", "rejected", "completed"}


class CourseChallengeService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)

    @staticmethod
    def _level(value: str) -> str:
        level = str(value or "hsk1").strip().lower()
        if level in {"hsk4a", "hsk4b"}:
            return level
        if level not in {"hsk1", "hsk2", "hsk3", "hsk4"}:
            return "hsk1"
        return level

    @staticmethod
    def _practice_level(value: str) -> str:
        return "hsk4" if str(value or "").startswith("hsk4") else str(value or "hsk1")

    @staticmethod
    def _user_payload(user: User | None) -> dict:
        if not user:
            return {"id": None, "name": "HSK AI", "username": ""}
        return {
            "id": int(user.id),
            "telegram_id": int(user.telegram_id),
            "name": str(user.full_name or user.username or "HSK Student").strip()[:40],
            "username": str(user.username or "").strip().lstrip("@")[:32],
        }

    @staticmethod
    def _questions(challenge: CourseChallenge) -> list[dict]:
        try:
            value = json.loads(challenge.question_payload or "[]")
        except json.JSONDecodeError:
            return []
        return value if isinstance(value, list) else []

    def _challenge_payload(self, challenge: CourseChallenge, viewer: User, users: dict[int, User]) -> dict:
        challenger = users.get(int(challenge.challenger_user_id))
        opponent = users.get(int(challenge.opponent_user_id))
        viewer_role = "challenger" if int(viewer.id) == int(challenge.challenger_user_id) else "opponent"
        opponent_user = opponent if viewer_role == "challenger" else challenger
        viewer_score = challenge.challenger_score if viewer_role == "challenger" else challenge.opponent_score
        opponent_score = challenge.opponent_score if viewer_role == "challenger" else challenge.challenger_score
        return {
            "id": int(challenge.id),
            "status": challenge.status,
            "level": challenge.level,
            "lang": challenge.lang,
            "mode": challenge.mode,
            "viewer_role": viewer_role,
            "challenger": self._user_payload(challenger),
            "opponent": self._user_payload(opponent),
            "other_user": self._user_payload(opponent_user),
            "viewer_done": viewer_score is not None,
            "opponent_done": opponent_score is not None,
            "challenger_score": challenge.challenger_score,
            "challenger_total": challenge.challenger_total,
            "challenger_percent": challenge.challenger_percent,
            "opponent_score": challenge.opponent_score,
            "opponent_total": challenge.opponent_total,
            "opponent_percent": challenge.opponent_percent,
            "winner_user_id": challenge.winner_user_id,
            "created_at": challenge.created_at.isoformat() if challenge.created_at else "",
            "accepted_at": challenge.accepted_at.isoformat() if challenge.accepted_at else "",
        }

    async def _users_by_id(self, ids: set[int]) -> dict[int, User]:
        if not ids:
            return {}
        result = await self.session.execute(select(User).where(User.id.in_(ids)))
        return {int(user.id): user for user in result.scalars().all()}

    async def list_for_user(self, telegram_id: int) -> dict:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return {"ok": False, "error": "access_start_first"}
        result = await self.session.execute(
            select(CourseChallenge)
            .where(
                or_(
                    CourseChallenge.challenger_user_id == int(user.id),
                    CourseChallenge.opponent_user_id == int(user.id),
                ),
                CourseChallenge.status.in_(("pending", "accepted", "completed")),
            )
            .order_by(CourseChallenge.updated_at.desc())
            .limit(20)
        )
        challenges = list(result.scalars().all())
        users = await self._users_by_id(
            {int(item.challenger_user_id) for item in challenges}
            | {int(item.opponent_user_id) for item in challenges}
        )
        items = [self._challenge_payload(item, user, users) for item in challenges]
        pending_count = sum(1 for item in items if item["status"] == "pending" and item["viewer_role"] == "opponent")
        active_count = sum(1 for item in items if item["status"] == "accepted" and not item["viewer_done"])
        return {"ok": True, "pending_count": pending_count, "active_count": active_count, "items": items}

    async def create(
        self,
        telegram_id: int,
        *,
        opponent_telegram_id: int,
        level: str,
        lang: str,
        bot=None,
    ) -> dict:
        challenger = await self.user_repo.get_by_telegram_id(telegram_id)
        opponent = await self.user_repo.get_by_telegram_id(opponent_telegram_id)
        if not challenger or not opponent:
            return {"ok": False, "error": "challenge_user_not_found"}
        if int(challenger.id) == int(opponent.id):
            return {"ok": False, "error": "challenge_self_not_allowed"}

        level = self._level(level)
        lang = normalize_miniapp_lang(lang)
        questions = await CourseMiniAppPracticeService(self.session)._questions(
            "mock",
            self._practice_level(level),
            lang,
            "",
        )
        if not questions:
            return {"ok": False, "error": "practice_questions_not_found"}

        challenge = CourseChallenge(
            challenger_user_id=int(challenger.id),
            opponent_user_id=int(opponent.id),
            level=level,
            lang=lang,
            mode="mock",
            question_payload=json.dumps(questions[:10], ensure_ascii=False),
            status="pending",
        )
        self.session.add(challenge)
        await self.session.flush()
        if bot:
            await self.notify_invite(bot, challenge, challenger, opponent)
        return {"ok": True, "challenge": self._challenge_payload(challenge, challenger, {challenger.id: challenger, opponent.id: opponent})}

    async def get_for_user(self, telegram_id: int, challenge_id: int) -> tuple[User | None, CourseChallenge | None]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)
        if not user:
            return None, None
        result = await self.session.execute(
            select(CourseChallenge).where(
                CourseChallenge.id == int(challenge_id),
                or_(
                    CourseChallenge.challenger_user_id == int(user.id),
                    CourseChallenge.opponent_user_id == int(user.id),
                ),
            )
        )
        return user, result.scalar_one_or_none()

    async def respond(self, telegram_id: int, challenge_id: int, action: str, *, bot=None) -> dict:
        user, challenge = await self.get_for_user(telegram_id, challenge_id)
        if not user or not challenge:
            return {"ok": False, "error": "challenge_not_found"}
        if int(user.id) != int(challenge.opponent_user_id):
            return {"ok": False, "error": "challenge_only_opponent_can_respond"}
        if challenge.status != "pending":
            return {"ok": False, "error": "challenge_already_resolved"}
        action = str(action or "").strip().lower()
        if action not in {"accept", "reject"}:
            return {"ok": False, "error": "challenge_bad_action"}
        challenge.status = "accepted" if action == "accept" else "rejected"
        challenge.accepted_at = datetime.now(timezone.utc) if action == "accept" else None
        await self.session.flush()
        users = await self._users_by_id({int(challenge.challenger_user_id), int(challenge.opponent_user_id)})
        if bot:
            await self.notify_response(bot, challenge, users, accepted=action == "accept")
        return {"ok": True, "challenge": self._challenge_payload(challenge, user, users)}

    async def start(self, telegram_id: int, challenge_id: int) -> dict:
        user, challenge = await self.get_for_user(telegram_id, challenge_id)
        if not user or not challenge:
            return {"ok": False, "error": "challenge_not_found"}
        if challenge.status == "pending" and int(user.id) == int(challenge.challenger_user_id):
            challenge.status = "accepted"
            challenge.accepted_at = datetime.now(timezone.utc)
            await self.session.flush()
        if challenge.status not in {"accepted", "completed"}:
            return {"ok": False, "error": f"challenge_{challenge.status}"}
        role = "challenger" if int(user.id) == int(challenge.challenger_user_id) else "opponent"
        if role == "challenger" and challenge.challenger_score is not None:
            return {"ok": False, "error": "challenge_already_submitted"}
        if role == "opponent" and challenge.opponent_score is not None:
            return {"ok": False, "error": "challenge_already_submitted"}
        return {
            "ok": True,
            "session": {
                "id": f"challenge:{challenge.id}:{user.id}",
                "challenge_id": int(challenge.id),
                "mode": "challenge",
                "level": challenge.level,
                "questions": self._questions(challenge),
            },
        }

    async def submit(self, telegram_id: int, challenge_id: int, answers: list, *, duration_seconds: int = 0, bot=None) -> dict:
        user, challenge = await self.get_for_user(telegram_id, challenge_id)
        if not user or not challenge:
            return {"ok": False, "error": "challenge_not_found"}
        if challenge.status not in {"accepted", "completed"}:
            return {"ok": False, "error": f"challenge_{challenge.status}"}
        questions = self._questions(challenge)
        submitted = {
            str(item.get("question_id") or ""): item
            for item in answers if isinstance(item, dict) and item.get("question_id")
        }
        expected = {str(item["id"]) for item in questions}
        if set(submitted) != expected:
            return {"ok": False, "error": "challenge_answers_incomplete"}
        score = 0
        wrong = []
        for question in questions:
            selected = submitted[str(question["id"])].get("selected_index")
            try:
                selected = int(selected)
            except (TypeError, ValueError):
                return {"ok": False, "error": "challenge_answer_invalid"}
            correct = selected == int(question["answer_index"])
            score += int(correct)
            if not correct:
                wrong.append(
                    {
                        "question_id": question["id"],
                        "question": question["prompt"],
                        "correct_answer": question["options"][question["answer_index"]],
                    }
                )
        total = len(questions)
        percent = round((score / total) * 100) if total else 0
        now = datetime.now(timezone.utc)
        duration_seconds = max(0, min(86400, int(duration_seconds or 0)))
        role = "challenger" if int(user.id) == int(challenge.challenger_user_id) else "opponent"
        if role == "challenger" and challenge.challenger_score is not None:
            return {"ok": False, "error": "challenge_already_submitted"}
        if role == "opponent" and challenge.opponent_score is not None:
            return {"ok": False, "error": "challenge_already_submitted"}
        if role == "challenger":
            challenge.challenger_score = score
            challenge.challenger_total = total
            challenge.challenger_percent = percent
            challenge.challenger_duration_seconds = duration_seconds
            challenge.challenger_completed_at = now
        else:
            challenge.opponent_score = score
            challenge.opponent_total = total
            challenge.opponent_percent = percent
            challenge.opponent_duration_seconds = duration_seconds
            challenge.opponent_completed_at = now
        self._update_winner(challenge)
        await self.session.flush()
        users = await self._users_by_id({int(challenge.challenger_user_id), int(challenge.opponent_user_id)})
        if bot:
            await self.notify_submit(bot, challenge, user, users)
        return {
            "ok": True,
            "score": score,
            "total": total,
            "percent": percent,
            "wrong_items": wrong,
            "challenge": self._challenge_payload(challenge, user, users),
        }

    @staticmethod
    def _update_winner(challenge: CourseChallenge) -> None:
        if challenge.challenger_score is None or challenge.opponent_score is None:
            return
        challenge.status = "completed"
        if challenge.challenger_score > challenge.opponent_score:
            challenge.winner_user_id = int(challenge.challenger_user_id)
        elif challenge.opponent_score > challenge.challenger_score:
            challenge.winner_user_id = int(challenge.opponent_user_id)
        else:
            challenger_duration = challenge.challenger_duration_seconds or 86400
            opponent_duration = challenge.opponent_duration_seconds or 86400
            if challenger_duration < opponent_duration:
                challenge.winner_user_id = int(challenge.challenger_user_id)
            elif opponent_duration < challenger_duration:
                challenge.winner_user_id = int(challenge.opponent_user_id)
            else:
                challenge.winner_user_id = None

    @staticmethod
    def _invite_keyboard(challenge_id: int, lang: str) -> InlineKeyboardMarkup:
        labels = {
            "uz": ("Vizovni qabul qilish", "Rad qilish", "Mini Appni ochish"),
            "ru": ("Принять вызов", "Отклонить", "Открыть Mini App"),
            "tj": ("Қабул кардани даъват", "Рад кардан", "Кушодани Mini App"),
        }
        accept, reject, open_app = labels.get(lang, labels["uz"])
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=accept, callback_data=f"challenge:accept:{challenge_id}"),
                    InlineKeyboardButton(text=reject, callback_data=f"challenge:reject:{challenge_id}"),
                ],
                [
                    InlineKeyboardButton(
                        text=open_app,
                        web_app=WebAppInfo(url=course_study_miniapp_url(lang=lang, tab="profile")),
                    )
                ],
            ]
        )

    @staticmethod
    def _open_keyboard(lang: str) -> InlineKeyboardMarkup:
        labels = {
            "uz": "Mini Appni ochish",
            "ru": "Открыть Mini App",
            "tj": "Кушодани Mini App",
        }
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=labels.get(lang, labels["uz"]),
                        web_app=WebAppInfo(url=course_study_miniapp_url(lang=lang, tab="profile")),
                    )
                ],
            ]
        )

    async def notify_invite(self, bot, challenge: CourseChallenge, challenger: User, opponent: User) -> None:
        lang = normalize_miniapp_lang(opponent.language)
        name = challenger.full_name or challenger.username or "HSK Student"
        title = {
            "uz": f"{name} sizga belashuv tashladi.",
            "ru": f"{name} бросил вам вызов.",
            "tj": f"{name} ба шумо рақобат фиристод.",
        }.get(lang)
        body = {
            "uz": "10 ta bir xil savol, bir xil sharoit. Qabul qilsangiz raund ochiladi va natija profilga tushadi.",
            "ru": "10 одинаковых вопросов, равные условия. Примите вызов, закройте раунд и заберите результат в профиле.",
            "tj": "10 саволи якхела, шароити баробар. Қабул кунед, раундро анҷом диҳед ва натиҷаро дар профил бинед.",
        }.get(lang)
        text = f"{title}\n\n{body}\n\nLevel: {challenge.level.upper()}"
        try:
            await bot.send_message(
                chat_id=int(opponent.telegram_id),
                text=text,
                reply_markup=self._invite_keyboard(int(challenge.id), lang),
            )
        except Exception:
            return

    async def notify_response(self, bot, challenge: CourseChallenge, users: dict[int, User], *, accepted: bool) -> None:
        challenger = users.get(int(challenge.challenger_user_id))
        opponent = users.get(int(challenge.opponent_user_id))
        if not challenger or not opponent:
            return
        lang = normalize_miniapp_lang(challenger.language)
        name = opponent.full_name or opponent.username or "User"
        if accepted:
            text = {
                "uz": f"{name} vizovni qabul qildi. Duel ochiq, Mini App profilidan boshlang.",
                "ru": f"{name} принял вызов. Дуэль открыта, стартуйте из профиля Mini App.",
                "tj": f"{name} даъватро қабул кард. Дуэл кушода аст, аз профили Mini App оғоз кунед.",
            }.get(lang)
        else:
            text = {
                "uz": f"{name} vizovni rad qildi.",
                "ru": f"{name} отклонил вызов.",
                "tj": f"{name} даъватро рад кард.",
            }.get(lang)
        try:
            await bot.send_message(
                chat_id=int(challenger.telegram_id),
                text=text,
                reply_markup=self._open_keyboard(lang) if accepted else None,
            )
        except Exception:
            return

    async def notify_submit(self, bot, challenge: CourseChallenge, user: User, users: dict[int, User]) -> None:
        other_id = int(challenge.opponent_user_id) if int(user.id) == int(challenge.challenger_user_id) else int(challenge.challenger_user_id)
        other = users.get(other_id)
        if not other:
            return
        lang = normalize_miniapp_lang(other.language)
        role = "challenger" if int(user.id) == int(challenge.challenger_user_id) else "opponent"
        score = challenge.challenger_score if role == "challenger" else challenge.opponent_score
        total = challenge.challenger_total if role == "challenger" else challenge.opponent_total
        name = user.full_name or user.username or "User"
        score_text = f"{score}/{total}" if score is not None and total else ""
        text = {
            "uz": f"{name} testni yopdi{f' — {score_text}' if score_text else ''}. Endi navbat sizda: profilni ochib raundni yakunlang.",
            "ru": f"{name} уже закрыл тест{f' — {score_text}' if score_text else ''}. Теперь ваш ход: откройте профиль и завершите раунд.",
            "tj": f"{name} тестро анҷом дод{f' — {score_text}' if score_text else ''}. Акнун навбати шумо: профилро кушоед ва раундро анҷом диҳед.",
        }.get(lang)
        try:
            await bot.send_message(
                chat_id=int(other.telegram_id),
                text=text,
                reply_markup=self._open_keyboard(lang),
            )
        except Exception:
            return
