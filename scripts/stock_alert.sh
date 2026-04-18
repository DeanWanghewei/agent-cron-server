#!/bin/bash
# 招商蛇口(sz001979)股价监控 — 达到目标区间时推送微信
# 用法: bash stock_alert.sh
# 返回值: 0=达到目标已推送, 1=未达目标(静默), 2=出错

set -euo pipefail

CODE="0.001979"
TARGET_LOW=10.4
TARGET_HIGH=10.9
COST=9.06
HERMES_PYTHON="/root/.hermes/hermes-agent/venv/bin/python3"
HERMES_PATH="/root/.hermes/hermes-agent"
WECHAT_ID="o9cq807froLBzH_lTVDD5TAqGjT4@im.wechat"

# 获取股价
raw=$(curl -s --max-time 10 \
  "https://push2delay.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f4,f12,f14&secids=${CODE}" \
  -H "Referer: https://www.eastmoney.com" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

if [ -z "$raw" ]; then
  echo "ERROR: empty response from eastmoney"
  exit 2
fi

# 解析: f2=最新价, f3=涨跌幅, f4=涨跌额, f14=名称
price=$(echo "$raw" | /usr/bin/python3 -c "import sys,json; d=json.load(sys.stdin)['data']['diff'][0]; print(d['f2'])")
pct=$(echo "$raw" | /usr/bin/python3 -c "import sys,json; d=json.load(sys.stdin)['data']['diff'][0]; print(d['f3'])")
chg=$(echo "$raw" | /usr/bin/python3 -c "import sys,json; d=json.load(sys.stdin)['data']['diff'][0]; print(d['f4'])")
name=$(echo "$raw" | /usr/bin/python3 -c "import sys,json; d=json.load(sys.stdin)['data']['diff'][0]; print(d['f14'])")

if [ -z "$price" ] || [ "$price" = "-" ]; then
  echo "ERROR: invalid price data"
  exit 2
fi

profit_pct=$(/usr/bin/python3 -c "print(f'{($price - $COST) / $COST * 100:+.2f}')")

echo "$(date '+%Y-%m-%d %H:%M') | $name 当前 ¥$price ($pct% / $chg) | 成本 $COST | 盈亏 $profit_pct%"

# 判断是否达到目标区间
above=$(/usr/bin/python3 -c "print('yes' if $price >= $TARGET_LOW else 'no')")

if [ "$above" = "yes" ]; then
  msg="🎯 *$name 达到目标价！*

当前: *¥$price* ($pct% / $chg)
成本: ¥$COST | 盈亏: $profit_pct%

目标区间: ¥${TARGET_LOW} ~ ¥${TARGET_HIGH}
建议: *考虑卖出*"

  cd "$HERMES_PATH" && $HERMES_PYTHON -c "
import sys; sys.path.insert(0, '$HERMES_PATH')
from tools.send_message_tool import send_message_tool
send_message_tool({
    'action': 'send',
    'target': 'weixin:$WECHAT_ID',
    'message': '''$msg'''
})
"
  echo "ALERT SENT: price=$price >= $TARGET_LOW"
  exit 0
fi

echo "SILENT: price=$price < target=$TARGET_LOW"
exit 1
