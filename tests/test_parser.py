from checker.parser import extract_items, parse_price

TABLE_HTML = """
<table class="kaitori">
  <tr><td class="name">iPhone 15 Pro 256GB</td><td class="price">¥120,000</td></tr>
  <tr><td class="name">Nintendo Switch 有機EL</td><td class="price">28,500円</td></tr>
</table>
"""

CARD_HTML = """
<div class="list">
  <div class="card"><p>iPhone 15 Pro 256GB</p><span>買取価格 ¥120,000</span></div>
  <div class="card"><p>PS5 デジタル・エディション</p><span>45,000円</span></div>
  <div class="footer">お問い合わせは 0120-000-000 まで</div>
</div>
"""


def test_parse_price():
    assert parse_price("¥120,000") == 120000
    assert parse_price("買取価格：28,500円") == 28500
    assert parse_price("値段はありません") is None


def test_selector_mode():
    items = extract_items(
        TABLE_HTML,
        {"item_selector": "tr", "name_selector": ".name", "price_selector": ".price"},
    )
    assert items == {
        "iPhone 15 Pro 256GB": 120000,
        "Nintendo Switch 有機EL": 28500,
    }


def test_heuristic_mode():
    items = extract_items(CARD_HTML, {})
    assert any("iPhone 15 Pro" in k and v == 120000 for k, v in items.items())
    assert any("PS5" in k and v == 45000 for k, v in items.items())
