#!/bin/bash
# Helper script for agent-cron-server operations
# Usage: ./scripts/cron.sh <action> [args]

set -e

BASE_URL="${ACS_URL:-http://localhost:${ACS_PORT:-8900}}"

usage() {
    echo "Usage: $0 <action> [args]"
    echo ""
    echo "Actions:"
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
    echo "Environment variables:"
    echo "  ACS_URL   - Server URL (default: http://localhost:8900)"
    echo "  ACS_PORT  - Server port (default: 8900)"
}

case "${1:-}" in
    health)
        curl -s "$BASE_URL/health" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/health"
        ;;
    create)
        if [ $# -lt 4 ]; then
            echo "Usage: $0 create <name> <command> <cron_expression>"
            exit 1
        fi
        curl -s -X POST "$BASE_URL/api/v1/tasks" \
            -H 'Content-Type: application/json' \
            -d "{\"name\":\"$2\",\"command\":\"$3\",\"cron_expression\":\"$4\",\"enabled\":true}"
        echo ""
        ;;
    list)
        curl -s "$BASE_URL/api/v1/tasks" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/api/v1/tasks"
        ;;
    get)
        curl -s "$BASE_URL/api/v1/tasks/$2" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/api/v1/tasks/$2"
        ;;
    delete)
        curl -s -X DELETE "$BASE_URL/api/v1/tasks/$2"
        echo ""
        ;;
    trigger)
        curl -s -X POST "$BASE_URL/api/v1/tasks/$2/trigger"
        echo ""
        ;;
    enable)
        curl -s -X POST "$BASE_URL/api/v1/tasks/$2/enable"
        echo ""
        ;;
    disable)
        curl -s -X POST "$BASE_URL/api/v1/tasks/$2/disable"
        echo ""
        ;;
    executions)
        TASK_ID="${2:-}"
        LIMIT="${3:-10}"
        if [ -n "$TASK_ID" ]; then
            curl -s "$BASE_URL/api/v1/executions?task_id=$TASK_ID&limit=$LIMIT"
        else
            curl -s "$BASE_URL/api/v1/executions?limit=$LIMIT"
        fi | python3 -m json.tool 2>/dev/null || cat
        ;;
    log)
        curl -s "$BASE_URL/api/v1/executions/$2/log" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/api/v1/executions/$2/log"
        ;;
    *)
        usage
        exit 1
        ;;
esac
