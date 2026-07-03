"""推送通知。支持的渠道通过环境变量启用：

- Telegram:   TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID
- Server酱:   SERVERCHAN_SENDKEY（微信推送，https://sct.ftqq.com）
- Bark (iOS): BARK_URL，形如 https://api.day.app/你的KEY
- 通用 Webhook: WEBHOOK_URL，POST {"text": 消息}
"""
from __future__ import annotations

import os

import requests

TIMEOUT = 15


def send(title: str, body: str) -> list[str]:
    """向所有已配置的渠道推送，返回成功的渠道名列表。"""
    sent: list[str] = []
    for channel, func in (
        ("telegram", _telegram),
        ("serverchan", _serverchan),
        ("bark", _bark),
        ("webhook", _webhook),
    ):
        try:
            if func(title, body):
                sent.append(channel)
        except Exception as exc:  # 单个渠道失败不影响其他渠道
            print(f"[notify] {channel} 推送失败: {exc}")
    return sent


def _telegram(title: str, body: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": f"{title}\n\n{body}"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return True


def _serverchan(title: str, body: str) -> bool:
    key = os.environ.get("SERVERCHAN_SENDKEY")
    if not key:
        return False
    resp = requests.post(
        f"https://sctapi.ftqq.com/{key}.send",
        data={"title": title, "desp": body},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return True


def _bark(title: str, body: str) -> bool:
    url = os.environ.get("BARK_URL")
    if not url:
        return False
    resp = requests.post(
        url.rstrip("/"),
        json={"title": title, "body": body},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return True


def _webhook(title: str, body: str) -> bool:
    url = os.environ.get("WEBHOOK_URL")
    if not url:
        return False
    resp = requests.post(url, json={"text": f"{title}\n{body}"}, timeout=TIMEOUT)
    resp.raise_for_status()
    return True
