#!/usr/bin/env bash
# 一键复现「电商小程序后台」的 MVP 生成过程。
#
# 用法：
#   cp ../.env.example ../.env   # 先填好模型配置
#   bash run_demo.sh
set -euo pipefail

cd "$(dirname "$0")/.."

export PYTHONPATH="${PYTHONPATH:-}:src"

# 想换模型就改这里；也可以提前写在 .env 里
export MVP_MAX_TOKENS="${MVP_MAX_TOKENS:-16000}"
export MVP_MAX_QA_ROUNDS="${MVP_MAX_QA_ROUNDS:-2}"

echo "▶ 团队成员："
python -m mvp_team roster

echo
echo "▶ 开始生成：电商小程序后台"
python -m mvp_team run \
  "我想做一个电商小程序后台，用来管理商品和订单" \
  --out ./generated \
  --json | tee ./generated/last_run.json

echo
echo "▶ 产物目录：./generated/mini-shop-admin"
