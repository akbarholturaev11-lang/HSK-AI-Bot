import json
from datetime import datetime, timezone

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import or_, select

from app.bot.utils.course_miniapp import course_study_miniapp_url, normalize_miniapp_lang
from app.db.models.course_challenge import CourseChallenge
from app.db.models.user import User
from app.repositories.user_repo import UserRepository
from app.services.course_gamification_service import CourseGamificationService
from app.services.course_miniapp_practice_service import CourseMiniAppPracticeService


CHALLENGE_STATUSES = {"pending", "accepted", "rejected", "completed"}
CHALLENGE_COMPLETE_XP = 6
CHALLENGE_WIN_XP = 24
CHALLENGE_TIE_XP = 12


class CourseChallengeService:
    def __init__(self, session):
        self.session = session
        self.user_repo = UserRepository(session)
        self.gamification = CourseGamificationService(session)

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
    def _payload_map(challenge: CourseChallenge) -> dict:
        """Parse question_payload into a {role: [questions]} map.

        Backwards compatible: legacy challenges stored a flat list shared by
        both players; expose it under both roles."""
        def as_list(value) -> list:
            return value if isinstance(value, list) else []

        try:
            value = json.loads(challenge.question_payload or "[]")
        except json.JSONDecodeError:
            return {"challenger": [], "opponent": []}
        if isinstance(value, list):
            return {"challenger": value, "opponent": value}
        if isinstance(value, dict):
            return {
                "challenger": as_list(value.get("challenger")),
                "opponent": as_list(value.get("opponent")),
            }
        return {"challenger": [], "opponent": []}

    @classmethod
    def _questions(cls, challenge: CourseChallenge, role: str = "challenger") -> list[dict]:
        """Questions for one player. Each player gets their own level-matched
        set; legacy challenges fall back to the shared list."""
        data = cls._payload_map(challenge)
        return data.get(role) or data.get("challenger") or []

    async def _generate_questions_for(self, user: User) -> list[dict]:
        """Generate a fresh practice set matched to this user's own HSK level."""
        level = self._level(getattr(user, "level", None))
        lang = normalize_miniapp_lang(getattr(user, "language", None))
        questions = await CourseMiniAppPracticeService(self.session)._questions(
            "mock",
            self._practice_level(level),
            lang,
            "",
        )
        return questions[:10]

    async def _ensure_questions(self, challenge: CourseChallenge, user: User, role: str) -> list[dict]:
        """Return this player's questions, generating + persisting them at the
        player's own level the first time they are needed (e.g. on accept)."""
        data = self._payload_map(challenge)
        if data.get(role):
            return data[role]
        questions = await self._generate_questions_for(user)
        data[role] = questions
        challenge.question_payload = json.dumps(data, ensure_ascii=False)
        await self.session.flush()
        return questions

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

        # Challenge ham Course/QA bilan bir xil manbadan yuradi: botdagi user.level
        # va user.language. Client payload faqat eski URLlar uchun kelishi mumkin.
        level = self._level(getattr(challenger, "level", None))
        lang = normalize_miniapp_lang(getattr(challenger, "language", None))
        # Each player answers a set matched to their OWN level. The challenger's
        # set is built now; the opponent's is built when they accept (their
        # level may differ). Winner is decided by percentage, not raw score.
        challenger_questions = await self._generate_questions_for(challenger)
        if not challenger_questions:
            return {"ok": False, "error": "practice_questions_not_found"}

        challenge = CourseChallenge(
            challenger_user_id=int(challenger.id),
            opponent_user_id=int(opponent.id),
            level=level,
            lang=lang,
            mode="mock",
            question_payload=json.dumps(
                {"challenger": challenger_questions, "opponent": []},
                ensure_ascii=False,
            ),
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
        if action == "accept":
            # Build the opponent's questions at THEIR own level before marking
            # the round accepted, so a failed generation does not open a broken duel.
            questions = await self._ensure_questions(challenge, user, "opponent")
            if not questions:
                return {"ok": False, "error": "practice_questions_not_found"}
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
        role = "challenger" if int(user.id) == int(challenge.challenger_user_id) else "opponent"
        questions = await self._ensure_questions(challenge, user, role)
        if not questions:
            return {"ok": False, "error": "practice_questions_not_found"}
        if challenge.status == "pending" and int(user.id) == int(challenge.challenger_user_id):
            challenge.status = "accepted"
            challenge.accepted_at = datetime.now(timezone.utc)
            await self.session.flush()
        if challenge.status not in {"accepted", "completed"}:
            return {"ok": False, "error": f"challenge_{challenge.status}"}
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
                "level": self._level(getattr(user, "level", None)),
                "questions": questions,
            },
        }

    async def submit(self, telegram_id: int, challenge_id: int, answers: list, *, duration_seconds: int = 0, bot=None) -> dict:
        user, challenge = await self.get_for_user(telegram_id, challenge_id)
        if not user or not challenge:
            return {"ok": False, "error": "challenge_not_found"}
        if challenge.status not in {"accepted", "completed"}:
            return {"ok": False, "error": f"challenge_{challenge.status}"}
        role = "challenger" if int(user.id) == int(challenge.challenger_user_id) else "opponent"
        questions = self._questions(challenge, role)
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
        users = await self._users_by_id({int(challenge.challenger_user_id), int(challenge.opponent_user_id)})
        reward = await self.gamification.award(
            user,
            activity_type="challenge",
            activity_ref=f"challenge:{challenge.id}:user:{user.id}:completed",
            base_xp=CHALLENGE_COMPLETE_XP,
            level=challenge.level,
        )
        final_rewards = await self._award_final_rewards(challenge, users)
        await self.session.flush()
        if bot:
            await self.notify_submit(bot, challenge, user, users)
        viewer_final_reward = final_rewards.get(int(user.id))
        return {
            "ok": True,
            "score": score,
            "total": total,
            "percent": percent,
            "wrong_items": wrong,
            "reward": reward,
            "winner_reward": viewer_final_reward,
            "final_rewards": {
                str(user_id): {
                    "awarded_xp": int((payload or {}).get("awarded_xp") or 0),
                    "xp": int((payload or {}).get("xp") or 0),
                    "duplicate": bool((payload or {}).get("duplicate")),
                }
                for user_id, payload in final_rewards.items()
            },
            "challenge": self._challenge_payload(challenge, user, users),
        }

    async def _award_final_rewards(self, challenge: CourseChallenge, users: dict[int, User]) -> dict[int, dict]:
        if challenge.status != "completed":
            return {}
        rewards: dict[int, dict] = {}
        if challenge.winner_user_id:
            winner = users.get(int(challenge.winner_user_id))
            if winner:
                rewards[int(winner.id)] = await self.gamification.award(
                    winner,
                    activity_type="challenge_win",
                    activity_ref=f"challenge:{challenge.id}:winner",
                    base_xp=CHALLENGE_WIN_XP,
                    level=challenge.level,
                )
            return rewards

        for user_id in (int(challenge.challenger_user_id), int(challenge.opponent_user_id)):
            player = users.get(user_id)
            if not player:
                continue
            rewards[int(player.id)] = await self.gamification.award(
                player,
                activity_type="challenge_tie",
                activity_ref=f"challenge:{challenge.id}:tie:{player.id}",
                base_xp=CHALLENGE_TIE_XP,
                level=challenge.level,
            )
        return rewards

    @staticmethod
    def _update_winner(challenge: CourseChallenge) -> None:
        if challenge.challenger_score is None or challenge.opponent_score is None:
            return
        challenge.status = "completed"
        # Players may answer different question sets at their own levels, so
        # compare by percentage (not raw score); duration breaks ties.
        challenger_pct = CourseChallengeService._result_percent(
            challenge.challenger_score,
            challenge.challenger_total,
            challenge.challenger_percent,
        )
        opponent_pct = CourseChallengeService._result_percent(
            challenge.opponent_score,
            challenge.opponent_total,
            challenge.opponent_percent,
        )
        if challenger_pct > opponent_pct:
            challenge.winner_user_id = int(challenge.challenger_user_id)
        elif opponent_pct > challenger_pct:
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
    def _result_percent(score: int | None, total: int | None, percent: int | None) -> int:
        if percent is not None:
            return int(percent)
        if total:
            return round((int(score or 0) / int(total)) * 100)
        # Legacy rows from the old equal-question flow may only have raw score.
        return int(score or 0)

    @staticmethod
    def _challenge_url(challenge_id: int, lang: str, level: str | None = None) -> str:
        return course_study_miniapp_url(
            lang=lang,
            level=level,
            tab="rating",
            challenge_id=int(challenge_id),
        )

    @staticmethod
    def _invite_keyboard(challenge_id: int, lang: str, level: str | None = None) -> InlineKeyboardMarkup:
        labels = {
            "uz": ("Belashuvni qabul qilish", "Rad qilish", "Musobaqani ochish"),
            "ru": ("Принять дуэль", "Отклонить", "Открыть дуэль"),
            "tj": ("Қабули рақобат", "Рад кардан", "Кушодани рақобат"),
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
                        web_app=WebAppInfo(url=CourseChallengeService._challenge_url(challenge_id, lang, level)),
                    )
                ],
            ]
        )

    @staticmethod
    def _open_keyboard(lang: str, challenge_id: int | None = None, level: str | None = None) -> InlineKeyboardMarkup:
        labels = {
            "uz": "Musobaqaga kirish",
            "ru": "Перейти к дуэли",
            "tj": "Ба рақобат гузаштан",
        }
        url = (
            CourseChallengeService._challenge_url(challenge_id, lang, level)
            if challenge_id
            else course_study_miniapp_url(lang=lang, tab="rating")
        )
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=labels.get(lang, labels["uz"]),
                        web_app=WebAppInfo(url=url),
                    )
                ],
            ]
        )

    @staticmethod
    def _level_label(level: str) -> str:
        return str(level or "hsk1").upper().replace("HSK", "HSK ")

    @staticmethod
    def invite_text(challenge: CourseChallenge, challenger: User, lang: str) -> str:
        name = challenger.full_name or challenger.username or "HSK Student"
        title = {
            "uz": f"⚔️ {name} sizni HSK jangiga chaqirdi!",
            "ru": f"⚔️ {name} бросает вам вызов на HSK-дуэль!",
            "tj": f"⚔️ {name} шуморо ба дуэли HSK даъват мекунад!",
        }.get(lang)
        body = {
            "uz": (
                "🔥 10 ta savol — so'z, pinyin, tarjima va grammatika aralash.\n"
                "🎯 Har biringiz O'Z darajangizdagi savollarga javob berasiz — adolatli jang!\n"
                "🏆 G'olib eng baland foiz bilan aniqlanadi. Teng bo'lsa — tezroq tugatgani oladi.\n\n"
                f"⚡ G'olibga +{CHALLENGE_WIN_XP} XP, har bir jangchiga +{CHALLENGE_COMPLETE_XP} XP.\n"
                "Qani, kuchingni ko'rsat! 💪"
            ),
            "ru": (
                "🔥 10 вопросов — слова, пиньинь, перевод и грамматика вперемешку.\n"
                "🎯 Каждый отвечает на вопросы СВОЕГО уровня — честный бой!\n"
                "🏆 Победитель — у кого выше процент. При равенстве решает скорость.\n\n"
                f"⚡ Победителю +{CHALLENGE_WIN_XP} XP, каждому бойцу +{CHALLENGE_COMPLETE_XP} XP.\n"
                "Покажи, на что способен! 💪"
            ),
            "tj": (
                "🔥 10 савол — калима, пинйин, тарҷума ва грамматика омехта.\n"
                "🎯 Ҳар яки шумо ба саволҳои дараҷаи ХУДатон ҷавоб медиҳед — ҷанги одилона!\n"
                "🏆 Ғолиб бо фоизи баландтар муайян мешавад. Агар баробар бошад — тезтараш мебарад.\n\n"
                f"⚡ Ба ғолиб +{CHALLENGE_WIN_XP} XP, ба ҳар ҷанговар +{CHALLENGE_COMPLETE_XP} XP.\n"
                "Қувваи худро нишон деҳ! 💪"
            ),
        }.get(lang)
        return f"{title}\n\n{body}\n\nLevel: {CourseChallengeService._level_label(challenge.level)}"

    @staticmethod
    def resolved_invite_text(challenge: CourseChallenge | dict, *, accepted: bool, lang: str) -> str:
        level = CourseChallengeService._level_label(
            challenge.get("level") if isinstance(challenge, dict) else challenge.level
        )
        if accepted:
            text = {
                "uz": (
                    "✅ Jang qabul qilindi! ⚔️\n\n"
                    "🎯 Maydon tayyor: 10 ta savol, har biringiz o'z darajangizda.\n"
                    "🔥 Kir va g'alabani qo'lga ol!"
                ),
                "ru": (
                    "✅ Вызов принят! ⚔️\n\n"
                    "🎯 Арена готова: 10 вопросов, каждый на своём уровне.\n"
                    "🔥 Заходи и забирай победу!"
                ),
                "tj": (
                    "✅ Дуэл қабул шуд! ⚔️\n\n"
                    "🎯 Майдон тайёр: 10 савол, ҳар яке дар дараҷаи худаш.\n"
                    "🔥 Даро ва ғалабаро ба даст ор!"
                ),
            }.get(lang)
        else:
            text = {
                "uz": "😌 Bu safar jang bo'lmadi.\n\nQayg'urma — boshqa raqibni chaqir va g'alabani ol! 💪",
                "ru": "😌 В этот раз дуэли не будет.\n\nНе беда — вызови другого соперника и побеждай! 💪",
                "tj": "😌 Ин дафъа дуэл нашуд.\n\nҒам махӯр — рақиби дигарро даъват кун ва ғалаба кун! 💪",
            }.get(lang)
        return f"{text}\n\nLevel: {level}"

    async def notify_invite(self, bot, challenge: CourseChallenge, challenger: User, opponent: User) -> None:
        lang = normalize_miniapp_lang(opponent.language)
        try:
            await bot.send_message(
                chat_id=int(opponent.telegram_id),
                text=self.invite_text(challenge, challenger, lang),
                reply_markup=self._invite_keyboard(int(challenge.id), lang, challenge.level),
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
                "uz": f"🔥 {name} chaqiringizni qabul qildi! ⚔️\nMaydon tayyor — kir va birinchi bo'lib zarba ber! 💪",
                "ru": f"🔥 {name} принял твой вызов! ⚔️\nАрена готова — заходи и бей первым! 💪",
                "tj": f"🔥 {name} даъвати шуморо қабул кард! ⚔️\nМайдон тайёр — даро ва аввал зарба зан! 💪",
            }.get(lang)
        else:
            text = {
                "uz": f"😌 {name} bu safar jangga chiqmadi.\nQayg'urma — kuchli raqib doim topiladi! Yana birovni chaqir. 💪",
                "ru": f"😌 {name} в этот раз не вышел на бой.\nНе беда — сильный соперник всегда найдётся! Вызови другого. 💪",
                "tj": f"😌 {name} ин дафъа ба ҷанг набаромад.\nҒам махӯр — рақиби қавӣ ҳамеша ёфт мешавад! Дигареро даъват кун. 💪",
            }.get(lang)
        try:
            await bot.send_message(
                chat_id=int(challenger.telegram_id),
                text=text,
                reply_markup=self._open_keyboard(lang, int(challenge.id), challenge.level) if accepted else None,
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
        if challenge.status == "completed":
            challenger_score = f"{challenge.challenger_score}/{challenge.challenger_total}" if challenge.challenger_total else "-"
            opponent_score = f"{challenge.opponent_score}/{challenge.opponent_total}" if challenge.opponent_total else "-"
            other_won = challenge.winner_user_id and int(challenge.winner_user_id) == int(other.id)
            no_winner = challenge.winner_user_id is None
            text = {
                "uz": (
                    f"🏁 Raund tugadi! {name} natijani yubordi{f' — {score_text}' if score_text else ''}.\n\n"
                    f"📊 Hisob: {challenger_score} vs {opponent_score}.\n"
                    + ("🏆 G'OLIB SIZSIZ! Bonus XP profilingizga tushdi. Ajoyibsan! 🔥" if other_won else "💪 Bu safar mag'lub bo'lding, ammo jang tugagani yo'q — revansh ol!" if not no_winner else "🤝 Durrang! Ikkalangizga ham bonus XP. Keyingisida hal qil!")
                ),
                "ru": (
                    f"🏁 Раунд завершён! {name} отправил результат{f' — {score_text}' if score_text else ''}.\n\n"
                    f"📊 Счёт: {challenger_score} vs {opponent_score}.\n"
                    + ("🏆 ПОБЕДА ЗА ТОБОЙ! Бонус XP уже в профиле. Красава! 🔥" if other_won else "💪 В этот раз поражение, но бой не окончен — бери реванш!" if not no_winner else "🤝 Ничья! Бонус XP обоим. В следующий раз реши исход!")
                ),
                "tj": (
                    f"🏁 Раунд анҷом ёфт! {name} натиҷаро фиристод{f' — {score_text}' if score_text else ''}.\n\n"
                    f"📊 Ҳисоб: {challenger_score} vs {opponent_score}.\n"
                    + ("🏆 ҒАЛАБА АЗ ОНи ШУМОСТ! Бонус XP дар профил аст. Офарин! 🔥" if other_won else "💪 Ин дафъа мағлуб шудӣ, аммо ҷанг тамом нашуд — реваншро гир!" if not no_winner else "🤝 Мусовӣ! Ба ҳар ду бонус XP. Дафъаи оянда ҳал кун!")
                ),
            }.get(lang)
        else:
            text = {
                "uz": f"⚡ {name} o'z raundini yakunladi{f' — {score_text}' if score_text else ''}! Endi navbat senda — kir va zarbangni ber! 🔥",
                "ru": f"⚡ {name} прошёл свой раунд{f' — {score_text}' if score_text else ''}! Теперь твой ход — заходи и бей! 🔥",
                "tj": f"⚡ {name} раунди худро анҷом дод{f' — {score_text}' if score_text else ''}! Акнун навбати туст — даро ва зарба зан! 🔥",
            }.get(lang)
        try:
            await bot.send_message(
                chat_id=int(other.telegram_id),
                text=text,
                reply_markup=self._open_keyboard(lang, int(challenge.id), challenge.level),
            )
        except Exception:
            return
