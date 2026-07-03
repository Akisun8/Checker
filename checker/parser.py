"""从页面 HTML 中提取「商品名 → 价格」列表。

两种模式：
1. 配置了 CSS 选择器时按选择器精确提取；
2. 否则用通用启发式：找出所有形如 ¥12,345 / 12,345円 的价格文本，
   再向上找包含商品名的最小容器。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

# ¥12,345 / ￥12,345 / 12,345円 / 12345 円
PRICE_RE = re.compile(r"(?:[¥￥]\s*([0-9][0-9,]*))|(?:([0-9][0-9,]*)\s*円)")

# 通用模式下，容器文本超过这个长度就认为它不是单个商品条目
MAX_ITEM_TEXT_LEN = 120


def parse_price(text: str) -> int | None:
    """从一段文本中解析出第一个价格（日元，整数）。"""
    m = PRICE_RE.search(text)
    if not m:
        return None
    digits = (m.group(1) or m.group(2)).replace(",", "")
    try:
        return int(digits)
    except ValueError:
        return None


def extract_items(html: str, page_cfg: dict) -> dict[str, int]:
    """返回 {商品名: 价格}。"""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    if page_cfg.get("item_selector"):
        return _extract_by_selector(soup, page_cfg)
    return _extract_heuristic(soup)


def _extract_by_selector(soup: BeautifulSoup, cfg: dict) -> dict[str, int]:
    items: dict[str, int] = {}
    for node in soup.select(cfg["item_selector"]):
        name_node = node.select_one(cfg["name_selector"]) if cfg.get("name_selector") else node
        price_node = node.select_one(cfg["price_selector"]) if cfg.get("price_selector") else node
        if name_node is None or price_node is None:
            continue
        name = _clean(name_node.get_text(" ", strip=True))
        price = parse_price(price_node.get_text(" ", strip=True))
        if name and price is not None:
            items[name] = price
    return items


def _extract_heuristic(soup: BeautifulSoup) -> dict[str, int]:
    items: dict[str, int] = {}
    for text_node in soup.find_all(string=PRICE_RE):
        container = _find_item_container(text_node.parent)
        if container is None:
            continue
        full_text = container.get_text(" ", strip=True)
        price = parse_price(full_text)
        if price is None:
            continue
        name = _clean(PRICE_RE.sub("", full_text))
        if len(name) < 2:
            continue
        items.setdefault(name, price)
    return items


def _find_item_container(node: Tag | None) -> Tag | None:
    """向上找一个既有价格又有商品名、且文本不太长的最小容器。"""
    while node is not None and isinstance(node, Tag):
        text = node.get_text(" ", strip=True)
        if len(text) > MAX_ITEM_TEXT_LEN:
            return None
        # 去掉价格后还剩下有意义的文字，说明容器里带着商品名
        rest = _clean(PRICE_RE.sub("", text))
        if len(rest) >= 2:
            return node
        node = node.parent
    return None


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # 去掉常见的价格标签词，避免它们混进商品名
    text = re.sub(r"(買取価格|買取金額|価格|上限|税込|：|:)\s*$", "", text).strip()
    return text
