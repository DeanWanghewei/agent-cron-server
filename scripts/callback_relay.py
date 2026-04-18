#!/usr/bin/env python3
"""
agent-cron-server Callback Relay -> OpenClaw Gateway Hook
监听本地端口，接收 agent-cron-server 的 callback POST，
注入 Authorization header 后转发给 OpenClaw Gateway /hooks/agent
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flask import Flask, request, abort
import httpx

app = Flask(__name__)

GATEWAY_URL = "http://localhost:18789/hooks/agent"
GATEWAY_TOKEN = "cron-callback-2026"  # 与 openclaw.json 中 hooks.token 一致
PORT = 8645

HEADERS_TO_COPY = ["X-Task-Id", "X-Task-Name", "X-Execution-Id"]


def task_summary(payload: dict) -> str:
    """把 callback payload 格式化成人类可读摘要"""
    status = payload.get("status", "?")
    task_name = payload.get("task_name", "?")
    duration_ms = payload.get("duration_ms", 0)
    exit_code = payload.get("exit_code")
    error = payload.get("error_message")
    stdout = payload.get("stdout_summary", "")
    stderr = payload.get("stderr_summary", "")

    lines = [f"【{task_name}】执行{status}"]
    if error:
        lines.append(f"  错误: {error}")
    if stdout:
        # 只取第一行
        first_line = stdout.strip().split("\n")[0][:200]
        lines.append(f"  输出: {first_line}")
    if stderr:
        first_err = stderr.strip().split("\n")[0][:200]
        lines.append(f"  警告: {first_err}")
    lines.append(f"  耗时: {duration_ms}ms | exit: {exit_code}")
    return "\n".join(lines)


@app.route("/webhooks/acs-callback", methods=["POST"])
def receive_callback():
    try:
        payload = request.get_json(force=True)
    except Exception:
        payload = {}

    # 构造发给 Gateway 的 message
    summary = task_summary(payload)
    trigger_type = payload.get("trigger_type", "callback")
    task_name = payload.get("task_name", "定时任务")

    gateway_payload = {
        "message": f"【{trigger_type}回调】{summary}\n\n原始回调ID: {payload.get('execution_id','?')}",
        "agentId": "main",
        "deliver": True,
        "channel": "feishu",
        "to": "user:ou_290bc0556776370d5464d9315fdbb197",
    }

    # 打印日志
    print(f"[{datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M:%S')}] "
          f"Callback received: {task_name} | {payload.get('status','?')} | "
          f"duration={payload.get('duration_ms','?')}ms")

    # 打印完整 payload（调试用）
    print(f"  -> JSON: {json.dumps(payload, ensure_ascii=False)[:300]}")

    # 转发给 Gateway
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                GATEWAY_URL,
                json=gateway_payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GATEWAY_TOKEN}",
                },
            )
            print(f"  -> Gateway response: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"  -> Gateway forward error: {e}")

    return {"ok": True}


if __name__ == "__main__":
    print(f"Starting callback relay on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
