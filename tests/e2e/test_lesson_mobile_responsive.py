"""Regression: long localized lesson prompts must fit mobile Mini App viewports."""
import pytest

from test_miniapp_smoke import (
    app_url,
    mock_course_map,
    mock_learning_audio,
    mock_price_preview,
    mock_telegram_ready,
    page,
)


@pytest.mark.parametrize("width,height", [
    (320, 568),
    (375, 667),
    (390, 844),
    (430, 932),
    (768, 900),
])
def test_long_lesson_choice_stays_full_width_and_scrollable(page, width, height):
    page.set_viewport_size({"width": width, "height": height})
    mock_price_preview(page)
    mock_telegram_ready(page)
    mock_course_map(page, language="ru")
    mock_learning_audio(page)
    page.add_init_script("localStorage.setItem('hsk_v3_onb', '1');")
    page.goto(
        app_url("/course-v3.html?lang=ru&level=hsk1&onboarded=1"),
        wait_until="networkidle",
    )

    page.evaluate("""() => {
        document.querySelector('#flow').classList.add('on');
        Flow.queue = [{
            type: 'hanzi_choice',
            title: {ru: 'Выберите верное предложение'},
            prompt: {ru: '«лошадь (3-й тон)» — какое предложение по-китайски?'},
            options: ['你好', '妈', '骂', '马'],
            correct_index: 3,
            _sNo: 1,
            _sTitle: 'Повторение'
        }];
        Flow.i = 0;
        Flow.lessonIdx = null;
        renderFlowCard();
    }""")
    page.wait_for_function(
        "() => !!document.querySelector('#f-body > .qcard .qh.qask')"
        " && document.querySelectorAll('#f-body > .opt').length === 4"
    )

    metrics = page.evaluate("""() => {
        const card = document.querySelector('#f-body > .qcard');
        const body = document.querySelector('#f-body');
        const coach = document.querySelector('#f-coach-dock');
        const optionRects = Array.from(body.querySelectorAll('.opt'))
            .map(node => node.getBoundingClientRect());
        const cardRect = card.getBoundingClientRect();
        return {
            cardWidth: cardRect.width,
            cardRight: cardRect.right,
            overflowX: Math.max(document.documentElement.scrollWidth,
                document.body.scrollWidth) > innerWidth + 1,
            optionsFit: optionRects.every(rect =>
                rect.width > 0 && rect.left >= 0 && rect.right <= innerWidth + 1),
            fontSize: parseFloat(getComputedStyle(card.querySelector('.qh.qask')).fontSize),
            coachHeight: coach.getBoundingClientRect().height,
            scrollingEnabled: getComputedStyle(body).overflowY === 'auto',
        };
    }""")

    assert metrics["cardWidth"] >= min(width, 480) * 0.75, metrics
    assert metrics["cardRight"] <= width + 1, metrics
    assert not metrics["overflowX"], metrics
    assert metrics["optionsFit"], metrics
    assert metrics["scrollingEnabled"], metrics
    if width <= 600:
        assert metrics["fontSize"] <= 27, metrics
        assert metrics["coachHeight"] <= 105, metrics
