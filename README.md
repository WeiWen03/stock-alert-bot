# Stock Alert Bot

Stock Alert Bot 会扫描一组流动性较好的美股和 ETF，寻找适合盘中交易、短线期权观察的候选标的，然后把观察名单发送到 Discord。

默认通过 GitHub Actions 在每个美股交易日 **太平洋时间 6:30 AM** 自动运行。

## 功能

- 从可配置股票池里寻找高波动美股
- 给每个标的评级：`A+`、`A`、`B`、`C`、`D`
- 标记方向：`看涨 / Call`、`看跌 / Put`、`观察 / Watch`
- 显示 ticker、价格、涨跌幅、RVOL、新闻催化、风险等级
- 通过 `DISCORD_WEBHOOK_URL` Secret 发送到 Discord
- 支持在 GitHub Actions 里手动运行

## 免责声明

本项目仅用于信息展示和学习研究，不构成投资建议、交易建议或任何买卖证券/期权/金融产品的推荐。期权交易风险很高，可能快速产生亏损，请自行判断并控制风险。

## 文件

```text
main.py
requirements.txt
README.md
.github/workflows/daily-options-watchlist.yml
```

## Discord Webhook 设置

1. 打开 Discord。
2. 进入你想接收提醒的服务器频道。
3. 打开频道设置。
4. 进入 `Integrations / 整合`。
5. 打开 `Webhooks`。
6. 新建一个 Webhook。
7. 复制 Webhook URL。

请保管好 Webhook URL。任何拿到这个 URL 的人都可以往你的频道发消息。

## GitHub Secret 设置

1. 打开你的 GitHub 仓库。
2. 进入 `Settings`。
3. 进入 `Secrets and variables`。
4. 打开 `Actions`。
5. 点击 `New repository secret`。
6. Secret 名称填写：

```text
DISCORD_WEBHOOK_URL
```

7. Value 填入你的 Discord Webhook URL。
8. 保存。

## 可选变量

如果你想自定义股票池或显示数量，进入：

`Settings` -> `Secrets and variables` -> `Actions` -> `Variables`

可选变量：

```text
WATCHLIST_TICKERS
```

示例：

```text
SPY,QQQ,IWM,AAPL,MSFT,NVDA,AMD,TSLA,META,AMZN,GOOGL,NFLX,AVGO,COIN,MSTR,PLTR,SMCI
```

可选变量：

```text
MAX_RESULTS
```

示例：

```text
8
```

如果不设置这些变量，程序会使用默认股票池和默认数量。

## 本地手动运行

安装依赖：

```bash
python -m pip install -r requirements.txt
```

设置 Webhook：

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

运行：

```bash
python main.py
```

Windows PowerShell：

```powershell
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python main.py
```

## GitHub Actions 手动运行

1. 打开 GitHub 仓库。
2. 进入 `Actions`。
3. 选择 `Daily Options Watchlist`。
4. 点击 `Run workflow`。

## 自动运行时间

GitHub Actions 使用 UTC 时间，而太平洋时间有夏令时和冬令时。

工作流会在两个 UTC 时间触发：

- `13:30 UTC`
- `14:30 UTC`

程序会检查当前是否为 `America/Los_Angeles` 的早上 6 点，只在正确时间发送，另一条重复任务会自动跳过。

GitHub Actions 的定时任务有时会延迟几分钟，这是正常现象。

## 数据说明

本项目使用 `yfinance`，适合轻量观察和自动提醒，但不是专业实时行情源。如果用于更严肃的交易流程，建议后续接入 Polygon、Tradier、Benzinga、ORATS 等付费数据源。
