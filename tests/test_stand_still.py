"""Плагин на странице хаба в Chrome: карточка вопроса стоит, пока приходят сообщения. Запуск — из папки кода хаба
(нужен его tests.test_web_e2e и тестовый Chrome): скопировать файл в <код хаба>/tests/ и `python3 tools/test.py
tests.test_stand_still.StandStill.test_the_question_being_read_stays_put_when_messages_arrive`. STAND_STILL_OFF=1 — без плагина (на коде без своей правки тест должен упасть)."""
import tests  # noqa: F401
import json
import os
from unittest import mock

from tests import test_web_e2e

PLUGIN = os.environ.get("STAND_STILL_PLUGIN") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class StandStill(test_web_e2e.PageInChrome):
    def plugin(self):
        if os.environ.get("STAND_STILL_OFF"):
            return
        cfg = os.path.join(self.state, "hub.json")
        with open(cfg, "w") as f:
            json.dump({"extensions": {"stand-still": {"path": PLUGIN, "web": "main.js"}}}, f)
        env = mock.patch.dict(os.environ, {"HUB_CONFIG": cfg})
        env.start()
        self.addCleanup(env.stop)

    def test_the_question_being_read_stays_put_when_messages_arrive(self):
        self.plugin()
        # 13.10, владелец: «чтоб при доставке сообщения чат не прыгал… мне надо вникнуть и прочитать варианты ответов»:
        # новое встаёт над карточкой вопроса, а место держалось по строке выше неё — карточку сталкивало вниз на высоту
        # нового; у низа её дёргала полоса очереди. Пока карточка перед глазами, на месте стоит она
        self.ev("session.requested", "a", session_id="s-a", cwd="/w", channel="cli", owner=True)
        self.ev("session.started", "a", session_id="s-a")
        for i in range(30):
            self.ev("session.said", "a", text=f"Абзац {i}: " + "строка текста " * (3 + i % 7))
        self.ev("turn.started", "a", marker=None, prompt_head="x")
        self.ev("permission.requested", "a", request_id="r1", tool="AskUserQuestion", interactive=True, input={
            "questions": [{"question": "Вопрос: как быть?",
                           "options": [{"label": f"Вариант {k}", "description": "пояснение " * 20} for k in range(4)]}]})
        self.ev("turn.stopped", "a")
        card = ("(() => { const f = document.querySelector('main .feed'); "
                "return Math.round(f.querySelector('.ask-card').getBoundingClientRect().top - f.getBoundingClientRect().top); })()")
        got = self.page({"go": f"http://127.0.0.1:{self.port}/#/s/a", "feed": "full"}, {"wait": "Вопрос: как быть"},
                        {"sleep": 800}, {"eval": card})
        at = got[-1]["eval"]
        for k, wheel in enumerate((0, -60)):   # у низа и чуть выше, вчитываясь в карточку
            if wheel:
                at = self.page({"wheel": wheel}, {"sleep": 500}, {"eval": card})[-1]["eval"]
            e = self.j.append("message.received", None, {"to": "a", "text": f"Сообщение {k}", "channel": "session",
                                                         "owner": False, "sender": "b"})
            got = self.page({"until": f"document.body.innerText.includes('Сообщение {k}')", "ms": 5000}, {"sleep": 400},
                            {"eval": card})
            self.assertLess(abs(got[-1]["eval"] - at), 3, f"в очереди: карточка уехала ({k})")
            self.ev("turn.started", "a", marker=f"m{e['seq']}", prompt_head="x")
            self.ev("session.said", "a", text=f"Ответ {k}: " + "строка текста " * 20)
            self.ev("turn.stopped", "a")
            got = self.page({"until": f"document.body.innerText.includes('Ответ {k}')", "ms": 5000}, {"sleep": 400},
                            {"eval": card})
            self.assertLess(abs(got[-1]["eval"] - at), 3, f"доставлено: карточка уехала ({k})")
        # ответил на вопрос и докрутил до низа — новое снова видно сразу
        self.ev("permission.answered", "a", request_id="r1", channel="web", owner=True)
        bottom = "(() => { const f = document.querySelector('main .feed'); return Math.round(f.scrollHeight - f.scrollTop - f.clientHeight); })()"
        self.page({"until": "!document.querySelector('main .ask-card')", "ms": 5000},
                  {"eval": "(() => { const f = document.querySelector('main .feed'); f.scrollTop = f.scrollHeight; "
                           "f.dispatchEvent(new Event('scroll')); return 1; })()"}, {"sleep": 200})
        self.ev("session.said", "a", text="Последнее")
        got = self.page({"until": "document.body.innerText.includes('Последнее')", "ms": 5000}, {"sleep": 300}, {"eval": bottom})
        self.assertLess(got[-1]["eval"], 5)

