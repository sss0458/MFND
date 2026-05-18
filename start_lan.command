#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.lan_runtime"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"

mkdir -p "$RUNTIME_DIR"

print_header() {
  echo "========================================"
  echo " 智信未来 - 局域网一键启动"
  echo "========================================"
}

check_requirements() {
  if [[ ! -x "$ROOT_DIR/backend/venv/bin/python" ]]; then
    echo "未找到后端虚拟环境: $ROOT_DIR/backend/venv/bin/python"
    exit 1
  fi

  if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
    echo "未找到前端依赖，请先在 frontend 目录执行 npm install"
    exit 1
  fi
}

is_pid_running() {
  local pid="$1"
  if [[ -z "$pid" ]]; then
    return 1
  fi
  kill -0 "$pid" >/dev/null 2>&1
}

ensure_port_free_or_owned() {
  local port="$1"
  local label="$2"
  local pid_file="$3"

  if [[ -f "$pid_file" ]]; then
    local known_pid
    known_pid="$(cat "$pid_file" 2>/dev/null || true)"
    if is_pid_running "$known_pid"; then
      echo "$label 已在运行 (PID: $known_pid)"
      return 0
    fi
    rm -f "$pid_file"
  fi

  local occupied_pid
  occupied_pid="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
  if [[ -n "$occupied_pid" ]]; then
    echo "端口 $port 已被其他进程占用 (PID: $occupied_pid)，请先释放后再启动。"
    exit 1
  fi
}

start_backend() {
  ensure_port_free_or_owned 8000 "后端服务" "$BACKEND_PID_FILE"
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    return 0
  fi

  echo "启动后端服务..."
  (
    cd "$ROOT_DIR"
    exec "$ROOT_DIR/backend/venv/bin/python" "$ROOT_DIR/backend/web_system/app.py"
  ) >"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
}

start_frontend() {
  ensure_port_free_or_owned 5173 "前端服务" "$FRONTEND_PID_FILE"
  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    return 0
  fi

  echo "启动前端服务..."
  (
    cd "$ROOT_DIR/frontend"
    exec npm run dev:lan
  ) >"$FRONTEND_LOG" 2>&1 &
  echo $! >"$FRONTEND_PID_FILE"
}

wait_for_service() {
  local pid_file="$1"
  local port="$2"
  local label="$3"
  local log_file="$4"

  sleep 2

  if [[ ! -f "$pid_file" ]]; then
    echo "$label 启动失败，未生成 PID。"
    exit 1
  fi

  local pid
  pid="$(cat "$pid_file")"
  if ! is_pid_running "$pid"; then
    rm -f "$pid_file"
    echo "$label 启动失败，请查看日志:"
    echo "  $log_file"
    exit 1
  fi

  local listening_pid
  listening_pid="$(lsof -ti tcp:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
  if [[ -z "$listening_pid" ]]; then
    rm -f "$pid_file"
    echo "$label 进程已启动，但端口 $port 尚未监听。请查看日志:"
    echo "  $log_file"
    exit 1
  fi
}

print_access_urls() {
  local ips
  ips="$(
    python3 - <<'PY'
import socket
ips = []
for host in ("en0", "en1"):
    pass
try:
    hostname = socket.gethostname()
    for item in socket.getaddrinfo(hostname, None, family=socket.AF_INET):
        ip = item[4][0]
        if not ip.startswith("127.") and ip not in ips:
            ips.append(ip)
except Exception:
    pass

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    if ip not in ips and not ip.startswith("127."):
        ips.append(ip)
except Exception:
    pass

for ip in ips:
    print(ip)
PY
  )"

  echo
  echo "服务已启动。可访问地址："
  echo "  本机:   http://127.0.0.1:5173"
  if [[ -n "$ips" ]]; then
    while IFS= read -r ip; do
      [[ -n "$ip" ]] && echo "  局域网: http://$ip:5173"
    done <<< "$ips"
  else
    echo "  局域网: 请查看本机 IP 后访问 http://<本机IP>:5173"
  fi
  echo
  echo "日志文件："
  echo "  后端: $BACKEND_LOG"
  echo "  前端: $FRONTEND_LOG"
  echo
  echo "停止服务请双击: stop_lan.command"
}

print_header
check_requirements
start_backend
start_frontend
wait_for_service "$BACKEND_PID_FILE" 8000 "后端服务" "$BACKEND_LOG"
wait_for_service "$FRONTEND_PID_FILE" 5173 "前端服务" "$FRONTEND_LOG"
print_access_urls
