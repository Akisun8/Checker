"""价格监控主流程：抓取 → 与历史对比 → 超过阈值则推送。

用法：
    python -m checker.main                 # 执行一轮检查
    python -m checker.main --snapshot URL  # 抓取页面 HTML 存到 snapshots/，用于调试选择器
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

from . import notify
from .parser import extract_items

ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = ROOT / "data" / "history.json"
SNAPSHOT_DIR = ROOT / "snapshots"
MAX_HISTORY_POINTS = 500


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def save_history(history: dict) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def fetch(url: str, cfg: dict) -> str:
    resp = requests.get(
        url,
        headers={
            "User-Agent": cfg["request"]["user_agent"],
            "Accept-Language": "ja,en;q=0.8",
        },
        timeout=cfg["request"]["timeout"],
    )
    resp.raise_for_status()
    return resp.text


def check_page(page: dict, cfg: dict, history: dict) -> list[str]:
    """检查一个页面，返回需要推送的消息行。"""
    alerts: list[str] = []
    alert_cfg = cfg["alert"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    html = fetch(page["url"], cfg)
    items = extract_items(html, page)
    print(f"[{page['name']}] 抓到 {len(items)} 个商品")

    for name, price in items.items():
        key = f"{page['name']}||{name}"
        record = history.get(key)
        if record is None:
            history[key] = {"price": price, "updated": now, "history": [[now, price]]}
            if alert_cfg.get("notify_on_new"):
                alerts.append(f"🆕 新收录: {name} — ¥{price:,}")
            continue

        old_price = record["price"]
        if price != old_price:
            record["price"] = price
            record["updated"] = now
            record["history"].append([now, price])
            record["history"] = record["history"][-MAX_HISTORY_POINTS:]

            diff = price - old_price
            pct = diff / old_price * 100 if old_price else 0
            hit_pct = abs(pct) >= alert_cfg["percent_threshold"] > 0
            hit_abs = alert_cfg["absolute_threshold"] > 0 and abs(diff) >= alert_cfg["absolute_threshold"]
            if hit_pct or hit_abs:
                arrow = "📈 上涨" if diff > 0 else "📉 下跌"
                alerts.append(
                    f"{arrow} {name}\n"
                    f"  ¥{old_price:,} → ¥{price:,}（{pct:+.1f}%，{diff:+,} 円）"
                )

    if alerts:
        alerts.append(f"页面: {page['url']}")
    return alerts


def run_check() -> int:
    cfg = load_config()
    history = load_history()
    all_alerts: list[str] = []
    errors: list[str] = []

    for i, page in enumerate(cfg["pages"]):
        if i > 0:
            time.sleep(cfg["request"].get("delay_seconds", 3))
        try:
            all_alerts.extend(check_page(page, cfg, history))
        except Exception as exc:
            errors.append(f"[{page['name']}] 抓取失败: {exc}")
            print(errors[-1], file=sys.stderr)

    save_history(history)

    if all_alerts:
        body = "\n\n".join(all_alerts)
        title = "買取一丁目 价格变动提醒"
        sent = notify.send(title, body)
        print(f"已推送 {len(all_alerts) - 1} 条变动到: {sent or '（未配置任何推送渠道）'}")
        print(body)
    else:
        print("没有超过阈值的价格变动。")

    # 页面全部抓取失败时退出非零，让 Actions 显示红色便于发现问题
    return 1 if errors and len(errors) == len(cfg["pages"]) else 0


def save_snapshot(url: str) -> None:
    cfg = load_config()
    html = fetch(url, cfg)
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    safe = re.sub(r"[^0-9A-Za-z._-]+", "_", url.split("//", 1)[-1])[:80]
    path = SNAPSHOT_DIR / f"{safe}.html"
    path.write_text(html, encoding="utf-8")
    print(f"已保存快照: {path} ({len(html)} 字节)")


def main() -> None:
    ap = argparse.ArgumentParser(description="1-chome.com 价格监控")
    ap.add_argument("--snapshot", metavar="URL", help="抓取页面 HTML 保存到 snapshots/")
    args = ap.parse_args()
    if args.snapshot:
        save_snapshot(args.snapshot)
        return
    sys.exit(run_check())


if __name__ == "__main__":
    main()
