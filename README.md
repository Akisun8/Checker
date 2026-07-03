# 買取一丁目（1-chome.com）价格监控推送

定时抓取 [1-chome.com](https://www.1-chome.com/index)（買取一丁目，日本中古回收报价网站）上的商品收购价格，与历史价格对比，**涨跌幅超过阈值时自动推送提醒**。

## 工作原理

1. GitHub Actions 按计划（默认每小时）运行 `checker`；
2. 抓取 `config.yaml` 中配置的页面，解析出「商品名 → 价格」；
3. 与 `data/history.json` 中的历史价格对比；
4. 涨跌幅超过阈值（默认 ±10%）就通过你配置的渠道推送；
5. 最新价格写回 `data/history.json` 并自动提交，保留价格曲线数据。

## 快速开始

### 1. 配置推送渠道（至少一个）

在仓库 **Settings → Secrets and variables → Actions** 里添加：

| Secret | 说明 |
|---|---|
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram 机器人推送 |
| `SERVERCHAN_SENDKEY` | [Server酱](https://sct.ftqq.com) 微信推送 |
| `BARK_URL` | iOS [Bark](https://apps.apple.com/app/bark/id1403753865) 推送，形如 `https://api.day.app/你的KEY` |
| `WEBHOOK_URL` | 通用 Webhook（POST `{"text": "..."}`，可接钉钉/飞书/Slack 等） |

### 2. 配置要监控的页面

编辑 `config.yaml` 的 `pages`，把想盯的分类页/商品页 URL 加进去。阈值也在这里改：

```yaml
alert:
  percent_threshold: 10   # 涨跌 ±10% 就推送
  absolute_threshold: 0   # 或按绝对金额（日元），0 = 不启用
```

### 3. 启用工作流

推到 GitHub 后，在 **Actions** 页启用工作流即可。也可以手动点 **Run workflow** 立即跑一次。

## 校准页面解析（重要）

内置的通用解析器会自动识别「商品名 + ¥xx,xxx / xx,xxx円」组合，但每个网站结构不同，建议先校准一次：

1. 在 Actions 里手动运行 **「抓取页面快照（调试用）」** 工作流，填入要监控的页面 URL；
2. 运行日志里会直接打印通用解析器抓到的商品和价格 —— 如果结果正确，就不用改任何东西；
3. 如果结果不对，下载工作流产物里的 HTML 快照，找到商品列表的结构，然后在 `config.yaml` 里为该页面填写精确选择器：

```yaml
pages:
  - name: "iPhone 买取价格"
    url: "https://www.1-chome.com/xxxx"
    render: true                           # SPA 页面需开启浏览器渲染
    item_selector: "table.price-list tr"   # 每个商品条目
    name_selector: "td.item-name"          # 条目内的商品名
    price_selector: "td.price"             # 条目内的价格
```

快照工作流会同时保存**原始 HTML**、**浏览器渲染后的 HTML**，以及页面加载时调用的 **JSON 接口响应**（`snapshots/api/`）。如果快照里发现网站有现成的价格 JSON 接口，直接对接接口会比解析 HTML 更稳定——把接口响应发给我即可帮你切换。

## 本地运行

```bash
pip install -r requirements.txt
python -m checker.main                  # 跑一轮检查
python -m checker.main --snapshot URL   # 抓页面快照到 snapshots/
python -m pytest tests/                 # 跑测试
```

## 目录结构

```
checker/          抓取、解析、对比、推送逻辑
config.yaml       监控页面与阈值配置
data/history.json 价格历史（由 Actions 自动更新提交）
.github/workflows 定时监控 + 快照调试两个工作流
```
