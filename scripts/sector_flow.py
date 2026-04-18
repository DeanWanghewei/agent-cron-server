#!/usr/bin/python3.12
"""东方财富概念板块资金流向 TOP15 绑图 + 微信推送"""
import subprocess, json, sys, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker
from matplotlib.font_manager import FontProperties

HERMES_PYTHON = "/root/.hermes/hermes-agent/venv/bin/python3"
HERMES_PATH = "/root/.hermes/hermes-agent"
WECHAT_ID = "o9cq807froLBzH_lTVDD5TAqGjT4@im.wechat"
OUTPUT = "/data_mnt/app/bk_flow_top15.png"
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# ── 1. 获取数据 ──
r = subprocess.run([
    'curl', '-s', '--max-time', '10',
    'https://data.eastmoney.com/dataapi/bkzj/getbkzj?key=f62&code=m:90+e:4',
    '-H', 'Referer: https://www.eastmoney.com',
    '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
], capture_output=True, text=True)

if r.returncode != 0 or not r.stdout.strip():
    print(f"ERROR: curl failed (rc={r.returncode})")
    sys.exit(2)

data = json.loads(r.stdout)
items = data.get('data', {}).get('diff', [])
if not items:
    print("ERROR: no data returned")
    sys.exit(2)

sorted_items = sorted(items, key=lambda x: x.get('f62', 0), reverse=True)
top15 = sorted_items[:15]

names = [item['f14'] for item in top15]
values = [item['f62'] / 10000 for item in top15]  # 万元

# ── 2. 绑图 ──
font_prop = FontProperties(fname=FONT)
fig, ax = plt.subplots(figsize=(14, 9))
fig.patch.set_facecolor('#f8f9fa')
ax.set_facecolor('#f8f9fa')

colors = ['#e74c3c' if v >= 0 else '#27ae60' for v in values]
bars = ax.barh(range(len(names)), values, color=colors, edgecolor='white', linewidth=0.7, height=0.7)

ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=11, fontproperties=font_prop)
ax.invert_yaxis()
ax.set_xlabel('资金净流入（万元）', fontsize=12, fontproperties=font_prop)
ax.set_title('概念板块资金流向 TOP15（今日）', fontsize=15, fontweight='bold',
             pad=18, fontproperties=font_prop, color='#2c3e50')

for i, (bar, val) in enumerate(zip(bars, values)):
    ax.text(val + max(values)*0.008, i, f'{val:,.0f}万', va='center', ha='left',
            fontsize=9, color='#2c3e50', fontproperties=font_prop)

ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
ax.grid(axis='x', linestyle='--', alpha=0.4, color='#bdc3c7')
ax.set_xlim(-max(values)*0.03, max(values)*1.13)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
plt.tick_params(left=False)
plt.tight_layout()
plt.savefig(OUTPUT, dpi=150, bbox_inches='tight', facecolor='#f8f9fa')
plt.close()
print(f"Chart saved: {OUTPUT}")

# ── 3. 推送微信 ──
os.chdir(HERMES_PATH)
subprocess.run([HERMES_PYTHON, '-c', f"""
import sys; sys.path.insert(0, '{HERMES_PATH}')
from tools.send_message_tool import send_message_tool
send_message_tool({{
    'action': 'send',
    'target': 'weixin:{WECHAT_ID}',
    'message': '📊 概念板块资金流向 TOP15（今日）\\n\\nMEDIA:{OUTPUT}'
}})
"""], check=True)
print("WeChat message sent")
