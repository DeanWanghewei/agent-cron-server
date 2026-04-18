#!/usr/bin/python3
"""国内黄金日报 — SGE 数据 + 推送微信"""
import subprocess, sys, os, json
from datetime import datetime

HERMES_PYTHON = "/root/.hermes/hermes-agent/venv/bin/python3"
HERMES_PATH = "/root/.hermes/hermes-agent"
WECHAT_ID = "o9cq807froLBzH_lTVDD5TAqGjT4@im.wechat"
AKVENV_PYTHON = "/tmp/akvenv/bin/python3"

# ── 1. 获取 SGE 数据 (akshare via专用venv) ──
script = """
import akshare as ak
import json

df = ak.macro_china_au_report()
targets = ['Au99.99', 'Au100g', 'Au99.95']
filtered = df[df['商品'].isin(targets)]
latest = filtered.groupby('商品').last().reset_index()

result = {}
for _, row in latest.iterrows():
    name = row['商品']
    result[name] = {
        'price': float(row['收盘价']),
        'change_pct': float(row['涨跌幅']) if row['涨跌幅'] != '-' else 0.0,
        'change': float(row['涨跌']) if row['涨跌'] != '-' else 0.0,
    }
print(json.dumps(result, ensure_ascii=False))
"""

r = subprocess.run([AKVENV_PYTHON, '-c', script], capture_output=True, text=True, timeout=30)
if r.returncode != 0:
    print(f"ERROR: akshare failed: {r.stderr}")
    sys.exit(2)

prices = json.loads(r.stdout.strip())

# ── 2. 构建 Markdown ──
today = datetime.now().strftime('%Y-%m-%d')

au99 = prices.get('Au99.99', {})
au100 = prices.get('Au100g', {})
au95 = prices.get('Au99.95', {})

def arrow(pct):
    if pct > 0: return '🔼'
    elif pct < 0: return '🔽'
    return '➡️'

def fmt_price(p):
    return f"{p:,.2f}" if p else "N/A"

premium_100 = au100.get('price', 0) - au99.get('price', 0)
liang = au99.get('price', 0) * 50
qian = au99.get('price', 0) * 3.125

msg = f"""📈 黄金日报 · {today}

---

### 上海黄金交易所（SGE）现货

| 品种 | 最新价 | 涨跌幅 |
|------|-------:|-------:|
| Au99.99 | {fmt_price(au99.get('price'))} 元/克 | {arrow(au99.get('change_pct',0))} {au99.get('change_pct',0):+.2f}% |
| Au100g | {fmt_price(au100.get('price'))} 元/克 | {arrow(au100.get('change_pct',0))} {au100.get('change_pct',0):+.2f}% |
| Au99.95 | {fmt_price(au95.get('price'))} 元/克 | {arrow(au95.get('change_pct',0))} {au95.get('change_pct',0):+.2f}% |

> Au100g 相对 Au99.99 溢价 {premium_100:+.2f} 元/克

---

### 银行金条参考价（建行浇铸）

| 规格 | 单价 | 总价 |
|-----:|-----:|-----:|
| 5g | 1,079 元/克 | ¥5,395 |
| 10g | 1,079 元/克 | ¥10,790 |

> 相对 SGE Au99.99 溢价约 **+31 元/克**（加工费）
> 注：各银行价格存在差异，此为建行参考价

---

### 折算参考

- 1 钱（3.125g）≈ ¥{qian:,.0f}（按 Au99.99）
- 1 两（50g）≈ ¥{liang:,.0f}（按 Au99.99）"""

# ── 3. 推送微信 ──
os.chdir(HERMES_PATH)
# 保存 msg 到临时文件，避免 shell 转义问题
tmpf = '/tmp/gold_daily_msg.txt'
with open(tmpf, 'w') as f:
    f.write(msg)

subprocess.run([HERMES_PYTHON, '-c', f"""
import sys; sys.path.insert(0, '{HERMES_PATH}')
from tools.send_message_tool import send_message_tool
with open('/tmp/gold_daily_msg.txt', 'r') as f:
    msg = f.read()
send_message_tool({{
    'action': 'send',
    'target': 'weixin:{WECHAT_ID}',
    'message': msg
}})
"""], check=True)
print("Gold daily report sent")
