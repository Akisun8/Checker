"""用 Playwright 无头浏览器渲染 SPA 页面，可选记录页面调用的 JSON 接口。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def fetch_rendered(url: str, cfg: dict, capture_api_dir: Path | None = None) -> str:
    from playwright.sync_api import sync_playwright

    timeout_ms = cfg["request"]["timeout"] * 1000
    captured: list[dict] = []

    with sync_playwright() as p:
        # 一般无需设置；本地 chromium 不在默认路径时可用该变量指定
        exe = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(user_agent=cfg["request"]["user_agent"])

        if capture_api_dir is not None:
            def on_response(resp):
                ctype = resp.headers.get("content-type", "")
                if "json" not in ctype:
                    return
                try:
                    captured.append({"url": resp.url, "status": resp.status, "body": resp.json()})
                except Exception:
                    pass
            page.on("response", on_response)

        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass  # 有轮询请求的页面等不到 networkidle，用已渲染的内容即可
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()

    if capture_api_dir is not None and captured:
        capture_api_dir.mkdir(parents=True, exist_ok=True)
        for i, item in enumerate(captured):
            tail = re.sub(r"[^0-9A-Za-z._-]+", "_", item["url"].split("//", 1)[-1])[-80:]
            path = capture_api_dir / f"{i:02d}_{tail}.json"
            path.write_text(
                json.dumps(item, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        print(f"已记录 {len(captured)} 个 JSON 接口响应到 {capture_api_dir}/")

    return html
