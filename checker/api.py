"""直接调用 1-chome.com 的 JSON 接口获取商品价格。

listPage 类接口的响应结构（keitai / 其他品类通用字段）：
  data.totalPages
  data.content[] -> title, price, goodsKbDetails[] -> kbDetailName, kbDetailPrice
一个商品可能有多个成色（未開封/開封済未使用品/中古…），每个成色单独作为一条监控项。
"""
from __future__ import annotations

import time
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import requests


def fetch_api_items(page_cfg: dict, cfg: dict) -> dict[str, int]:
    items: dict[str, int] = {}
    url = page_cfg["api_url"]
    max_pages = page_cfg.get("max_pages", 1)

    page_no = 1
    while True:
        data = _get_json(_with_page(url, page_no), cfg)
        payload = data.get("data") or {}
        for entry in payload.get("content", []):
            _collect(entry, items)
        total_pages = payload.get("totalPages") or 1
        page_no += 1
        if page_no > total_pages or page_no > max_pages:
            break
        time.sleep(1)  # 翻页间隔，避免请求过快
    return items


def _collect(entry: dict, items: dict[str, int]) -> None:
    title = (entry.get("title") or "").strip()
    if not title:
        return
    details = entry.get("goodsKbDetails") or []
    if details:
        for d in details:
            price = d.get("kbDetailPrice")
            if price is None:
                continue
            name = f"{title}（{d.get('kbDetailName', '').strip()}）"
            items[name] = int(price)
    elif entry.get("price") is not None:
        items[title] = int(entry["price"])


def _get_json(url: str, cfg: dict) -> dict:
    resp = requests.get(
        url,
        headers={
            "User-Agent": cfg["request"]["user_agent"],
            "Accept": "application/json",
            "Accept-Language": "ja,en;q=0.8",
        },
        timeout=cfg["request"]["timeout"],
    )
    resp.raise_for_status()
    return resp.json()


def _with_page(url: str, page_no: int) -> str:
    parts = urlsplit(url)
    query = parse_qs(parts.query, keep_blank_values=True)
    query["page"] = [str(page_no)]
    return urlunsplit(parts._replace(query=urlencode(query, doseq=True)))
