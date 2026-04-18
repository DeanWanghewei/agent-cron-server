#!/bin/bash
# Helper script for agent-cron-server operations
# Usage: ./scripts/cron.sh <action> [args]
#
# 交互方式（按优先级）：
#   1. MCP Tools（mcporter CLI）— 推荐，通过 MCP 协议调用
#   2. REST API（curl）— 备选，用于无 mcporter 的环境

set -e

MCP_URL="${ACS_MCP_URL:-http://localhost:${ACS_PORT:-8900}/mcp/}"
BASE_URL="${ACS_URL:-http://localhost:${ACS_PORT:-8900}}"

# 检测 mcporter 是否可用
has_mcporter() {
    command -v mcporter &>/dev/null || command -v npx &>/dev/null
}

# MCP 调用封装
mcporter_call() {
    if command -v mcporter &>/dev/null; then
        mcporter call --allow-http --http-url "$MCP_URL" "$@"
    else
        npx mcporter call --allow-http --http-url "$MCP_URL" "$@"
    fi
}

usage() {
    echo "Usage: $0 <action> [args]"
    echo ""
    echo "Actions (via MCP Tools):"
    echo "  health                          Check server health"
    echo "  create <name> <command> <cron>  Create a task"
    echo "  list                            List all tasks"
    echo "  get <id>                        Get task details"
    echo "  delete <id>                     Delete a task"
    echo "  trigger <id>                    Manually trigger a task"
    echo "  enable <id>                     Enable a task"
    echo "  disable <id>                    Disable a task"
    echo "  executions [task_id] [limit]    List executions"
    echo "  log <execution_id>              Get execution log"
    echo ""
    echo "Flags:"
    echo "  --api                           Force REST API mode (curl) instead of MCP"
    echo ""
    echo "Environment variables:"
    echo "  ACS_MCP_URL  - MCP Server URL (default: http://localhost:8900/mcp/)"
    echo "  ACS_URL      - REST API URL (default: http://localhost:8900)"
    echo "  ACS_PORT     - Server port (default: 8900)"
}

# 解析 --api 标志
FORCE_API=false
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --api) FORCE_API=true ;;
        *) ARGS+=("$arg") ;;
    esac
done
set -- "${ARGS[@]}"

case "${1:-}" in
    health)
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call get_service_health --output json 2>/dev/null
        else
            curl -s "$BASE_URL/health" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/health"
        fi
        ;;
    create)
        if [ $# -lt 4 ]; then
            echo "Usage: $0 create <name> <command> <cron_expression>"
            exit 1
        fi
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call create_cron_task name="$2" command="$3" cron_expression="$4" --output json 2>/dev/null
        else
            curl -s -X POST "$BASE_URL/api/v1/tasks" \
                -H 'Content-Type: application/json' \
                -d "{\"name\":\"$2\",\"command\":\"$3\",\"cron_expression\":\"$4\",\"enabled\":true}"
            echo ""
        fi
        ;;
    list)
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call list_cron_tasks --output json 2>/dev/null
        else
            curl -s "$BASE_URL/api/v1/tasks" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/api/v1/tasks"
        fi
        ;;
    get)
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call get_cron_task task_id="$2" --output json 2>/dev/null
        else
            curl -s "$BASE_URL/api/v1/tasks/$2" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/api/v1/tasks/$2"
        fi
        ;;
    delete)
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call delete_cron_task task_id="$2" --output json 2>/dev/null
        else
            curl -s -X DELETE "$BASE_URL/api/v1/tasks/$2"
            echo ""
        fi
        ;;
    trigger)
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call trigger_cron_task task_id="$2" --output json 2>/dev/null
        else
            curl -s -X POST "$BASE_URL/api/v1/tasks/$2/trigger"
            echo ""
        fi
        ;;
    enable)
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call enable_cron_task task_id="$2" --output json 2>/dev/null
        else
            curl -s -X POST "$BASE_URL/api/v1/tasks/$2/enable"
            echo ""
        fi
        ;;
    disable)
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call disable_cron_task task_id="$2" --output json 2>/dev/null
        else
            curl -s -X POST "$BASE_URL/api/v1/tasks/$2/disable"
            echo ""
        fi
        ;;
    executions)
        TASK_ID="${2:-}"
        LIMIT="${3:-10}"
        if has_mcporter && [ "$FORCE_API" = false ]; then
            if [ -n "$TASK_ID" ]; then
                mcporter_call list_executions task_id="$TASK_ID" limit="$LIMIT" --output json 2>/dev/null
            else
                mcporter_call list_executions limit="$LIMIT" --output json 2>/dev/null
            fi
        else
            if [ -n "$TASK_ID" ]; then
                curl -s "$BASE_URL/api/v1/executions?task_id=$TASK_ID&limit=$LIMIT"
            else
                curl -s "$BASE_URL/api/v1/executions?limit=$LIMIT"
            fi | python3 -m json.tool 2>/dev/null || cat
        fi
        ;;
    log)
        if has_mcporter && [ "$FORCE_API" = false ]; then
            mcporter_call get_execution_log execution_id="$2" --output json 2>/dev/null
        else
            curl -s "$BASE_URL/api/v1/executions/$2/log" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/api/v1/executions/$2/log"
        fi
        ;;
    *)
        usage
        exit 1
        ;;
esac
