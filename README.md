# 商品价格监控推送

定时抓取目标网站上的商品价格，与历史价格对比，**涨跌幅超过阈值时自动推送提醒**。

目标网站的域名不出现在仓库中，通过 Secret `TARGET_BASE_URL` 注入。

## 工作原理

1. GitHub Actions 按计划（默认每 5 分钟）运行 `checker`；
2. 调用 `config.yaml` 中配置的接口，取得「商品名（成色）→ 价格」；
3. 与 `data/history.json` 中的历史价格对比；
4. 涨跌幅超过阈值（默认 ±10%）就通过你配置的渠道推送；
5. 最新价格写回 `data/history.json` 并自动提交，保留价格曲线数据。

## 快速开始

### 1. 必需的 Secrets

在仓库 **Settings → Secrets and variables → Actions** 里添加：

| Secret | 说明 |
|---|---|
| `TARGET_BASE_URL` | **必填**。目标网站域名，如 `https://www.example.com` |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Telegram 机器人推送 |
| `SERVERCHAN_SENDKEY` | [Server酱](https://sct.ftqq.com) 微信推送 |
| `BARK_URL` | iOS [Bark](https://apps.apple.com/app/bark/id1403753865) 推送，形如 `https://api.day.app/你的KEY` |
| `WEBHOOK_URL` | 通用 Webhook（POST `{"text": "..."}`，可接钉钉/飞书/Slack 等） |

推送渠道至少配置一个。配置后可在 Actions 手动运行「测试推送渠道」验证。

### 2. 配置要监控的页面

编辑 `config.yaml` 的 `pages`。`url` / `api_url` 以 `/` 开头时，运行时自动拼上
`TARGET_BASE_URL`。阈值也在这里改：

```yaml
alert:
  percent_threshold: 10   # 涨跌 ±10% 就推送
  absolute_threshold: 0   # 或按绝对金额，0 = 不启用
```

### 3. 频率

`.github/workflows/price-check.yml` 中的 cron 当前为每 5 分钟
（GitHub 高峰期会延迟，实际约 5~15 分钟一次）。私有仓库请调低频率以免耗尽免费额度。

## 调试：抓取页面快照

监控新的分类页时，先在 Actions 手动运行 **「抓取页面快照（调试用）」**，填入页面路径（如 `/index`）：

- 日志会打印页面加载时调用的 **JSON 接口及响应**——从中找到该分类的接口路径和 `cateCode`，填入 `config.yaml` 的 `api_url` 即可；
- 同时产出原始 HTML 与浏览器渲染后的 HTML（工作流产物）。

也支持 HTML 解析模式（页面不提供 JSON 接口时）：不填 `api_url`，
配置 `render: true`（SPA 页面）和可选的 CSS 选择器，并在
`price-check.yml` 中恢复安装浏览器的步骤。

## 本地运行

```bash
pip install -r requirements.txt
export TARGET_BASE_URL="https://www.example.com"
python -m checker.main                    # 跑一轮检查
python -m checker.main --test-notify      # 测试推送渠道
python -m checker.main --snapshot /index  # 抓页面快照到 snapshots/
python -m pytest tests/                   # 跑测试
```

## 目录结构

```
checker/          抓取、解析、对比、推送逻辑
config.yaml       监控页面与阈值配置
data/history.json 价格历史（由 Actions 自动更新提交）
.github/workflows 定时监控 + 快照调试 + 推送测试
```
