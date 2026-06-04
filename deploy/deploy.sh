#!/bin/bash
set -e

PROJECT_DIR="/opt/aigen"

echo "=== 拉取最新代码 ==="
cd $PROJECT_DIR
git pull

echo "=== 配置后端 ==="
cd $PROJECT_DIR/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== 构建前端 ==="
cd $PROJECT_DIR/frontend
npm install
npm run build

echo "=== 重启服务 ==="
sudo systemctl restart aigenerate
sudo systemctl reload nginx

echo "=== 部署完成 ==="
