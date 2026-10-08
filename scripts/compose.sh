#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
case "${1:-start}" in
  start) docker compose up -d --build --wait ;;
  stop) docker compose stop ;;
  restart) docker compose restart ;;
  status) docker compose ps ;;
  logs) docker compose logs --tail 100 ;;
  check) docker compose config --quiet ;;
  *) echo 'usage: compose.sh start|stop|restart|status|logs|check'; exit 2 ;;
esac
