#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env.docker"
ENV_EXAMPLE_FILE="$ROOT_DIR/.env.docker.example"
LOG_DIR="$ROOT_DIR/.deploy_runtime"
LOG_FILE="$LOG_DIR/deploy.log"
SKIP_GIT_PULL="${SKIP_GIT_PULL:-false}"

mkdir -p "$LOG_DIR"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" | tee -a "$LOG_FILE"
}

fail() {
  log "ERROR: $1"
  exit 1
}

find_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
    return
  fi

  fail "未找到 Docker Compose。请先安装 Docker Compose 插件或 docker-compose。"
}

require_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 || fail "缺少命令: $command_name"
}

ensure_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    return
  fi

  if [[ ! -f "$ENV_EXAMPLE_FILE" ]]; then
    fail "未找到环境变量模板: $ENV_EXAMPLE_FILE"
  fi

  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
  fail "已自动创建 $ENV_FILE，请先修改其中的数据库密码和端口后重新执行脚本。"
}

ensure_docker_ready() {
  docker info >/dev/null 2>&1 || fail "Docker 当前不可用，请先启动 Docker 服务并确认当前账号有权限执行 docker。"
}

update_git_repo() {
  if [[ "$SKIP_GIT_PULL" == "true" ]]; then
    log "已跳过 Git 拉取更新。"
    return
  fi

  if [[ ! -d "$ROOT_DIR/.git" ]]; then
    log "当前目录不是 Git 仓库，跳过 Git 拉取。"
    return
  fi

  if ! git -C "$ROOT_DIR" diff --quiet || ! git -C "$ROOT_DIR" diff --cached --quiet; then
    log "检测到本地未提交改动，跳过自动 git pull，继续部署当前代码。"
    return
  fi

  local branch_name
  branch_name="$(git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [[ -z "$branch_name" || "$branch_name" == "HEAD" ]]; then
    log "当前 Git 仓库不在普通分支上，跳过自动 git pull。"
    return
  fi

  log "正在同步 Git 最新代码: $branch_name"
  git -C "$ROOT_DIR" fetch --all --prune | tee -a "$LOG_FILE"
  git -C "$ROOT_DIR" pull --ff-only | tee -a "$LOG_FILE"
}

deploy_stack() {
  log "开始构建并启动容器服务"
  "${COMPOSE_CMD[@]}" --env-file "$ENV_FILE" up -d --build --remove-orphans | tee -a "$LOG_FILE"
}

print_status() {
  log "当前容器状态:"
  "${COMPOSE_CMD[@]}" --env-file "$ENV_FILE" ps | tee -a "$LOG_FILE"
}

read_env_value() {
  local key="$1"
  local default_value="$2"
  local raw_value
  raw_value="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 | cut -d '=' -f 2- || true)"
  if [[ -z "$raw_value" ]]; then
    printf '%s' "$default_value"
    return
  fi
  raw_value="${raw_value%\"}"
  raw_value="${raw_value#\"}"
  printf '%s' "$raw_value"
}

collect_access_urls() {
  local app_port
  app_port="$(read_env_value "APP_PORT" "80")"

  local host_ips=()
  if command -v hostname >/dev/null 2>&1; then
    while IFS= read -r ip; do
      [[ -n "$ip" ]] && host_ips+=("$ip")
    done < <(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' || true)
  fi

  if [[ ${#host_ips[@]} -eq 0 ]] && command -v ip >/dev/null 2>&1; then
    while IFS= read -r ip; do
      [[ -n "$ip" ]] && host_ips+=("$ip")
    done < <(ip -4 addr show scope global | awk '/inet / {print $2}' | cut -d/ -f1)
  fi

  log "部署完成。访问地址:"
  if [[ "$app_port" == "80" ]]; then
    printf '  http://127.0.0.1\n' | tee -a "$LOG_FILE"
  else
    printf '  http://127.0.0.1:%s\n' "$app_port" | tee -a "$LOG_FILE"
  fi

  for ip in "${host_ips[@]}"; do
    if [[ "$app_port" == "80" ]]; then
      printf '  http://%s\n' "$ip" | tee -a "$LOG_FILE"
    else
      printf '  http://%s:%s\n' "$ip" "$app_port" | tee -a "$LOG_FILE"
    fi
  done

  log "部署日志: $LOG_FILE"
}

main() {
  : > "$LOG_FILE"
  log "智信未来 Docker 一键发布开始"
  require_command docker
  if [[ -d "$ROOT_DIR/.git" ]]; then
    require_command git
  fi
  find_compose_cmd
  ensure_docker_ready
  ensure_env_file
  update_git_repo
  deploy_stack
  print_status
  collect_access_urls
}

main "$@"
