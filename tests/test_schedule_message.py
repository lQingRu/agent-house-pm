from datetime import date, timedelta
from bot.handlers import build_reminder_schedule_html

today = date.today()


def test_all_thresholds_fire_when_expiry_is_far():
    expiry = today + timedelta(days=10)
    html = build_reminder_schedule_html(expiry)
    assert "<s>" not in html
    assert "7 days" in html
    assert "3 days" in html
    assert "on the day" in html


def test_7d_and_3d_struck_when_expiry_is_in_2_days():
    expiry = today + timedelta(days=2)
    html = build_reminder_schedule_html(expiry)
    assert html.count("<s>") == 2
    assert "<s>7 days</s>" in html
    assert "<s>3 days</s>" in html
    assert "✓ on the day" in html


def test_only_7d_struck_when_expiry_is_in_5_days():
    expiry = today + timedelta(days=5)
    html = build_reminder_schedule_html(expiry)
    assert html.count("<s>") == 1
    assert "<s>7 days</s>" in html
    assert "✓ 3 days" in html
    assert "✓ on the day" in html


def test_all_struck_when_expiry_is_today():
    expiry = today
    html = build_reminder_schedule_html(expiry)
    # fire dates for 7d and 3d are in the past; on-the-day fires today
    assert "<s>7 days</s>" in html
    assert "<s>3 days</s>" in html
    assert "✓ on the day" in html
