# AI Image Generator 部署指南

## 环境要求

- **操作系统**: Ubuntu 20.04 或更高版本
- **Python**: 3.10+
- **Node.js**: 18+
- **Nginx**: 任意较新版本
- **Git**: 用于拉取代码

## 部署步骤

### 1. 克隆代码到服务器

```bash
sudo mkdir -p /opt/aigen
sudo chown $USER:$USER /opt/aigen
git clone <your-repo-url> /opt/aigen
cd /opt/aigen
```

### 2. 配置后端环境变量

```bash
cd /opt/aigen/backend
cp .env.example .env
nano .env
```

根据实际情况填写 `.env` 中的配置项（数据库连接、API 密钥等）。

### 3. 安装 systemd 服务

```bash
sudo cp /opt/aigen/deploy/aigenerate.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable aigenerate
sudo systemctl start aigenerate
sudo systemctl status aigenerate
```

### 4. 配置 Nginx

```bash
sudo cp /opt/aigen/deploy/nginx.conf /etc/nginx/sites-available/aigenerate
sudo ln -s /etc/nginx/sites-available/aigenerate /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**重要**: 请将 `nginx.conf` 中的 `server_name your-domain.com` 替换为你的实际域名。

### 5. 执行部署脚本

```bash
chmod +x /opt/aigen/deploy/deploy.sh
/opt/aigen/deploy/deploy.sh
```

该脚本会自动拉取最新代码、安装后端依赖、构建前端并重启服务。

### 6. 配置 SSL 证书（推荐）

使用 certbot 自动获取并配置 Let's Encrypt SSL 证书：

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

certbot 会自动修改 Nginx 配置，添加 HTTPS 支持，并设置 HTTP 到 HTTPS 的重定向。

### 7. SSL 证书自动续期

certbot 安装时会自动创建 systemd timer，无需手动配置：

```bash
sudo systemctl status certbot.timer
```

也可以手动测试续期流程：

```bash
sudo certbot renew --dry-run
```

---

## 常用运维命令

| 操作 | 命令 |
|------|------|
| 查看后端状态 | `sudo systemctl status aigenerate` |
| 重启后端 | `sudo systemctl restart aigenerate` |
| 查看后端日志 | `sudo journalctl -u aigenerate -f` |
| 重载 Nginx | `sudo systemctl reload nginx` |
| 测试 Nginx 配置 | `sudo nginx -t` |

---

## 故障排查

### 后端无法启动

1. 检查服务状态：`sudo systemctl status aigenerate`
2. 查看详细日志：`sudo journalctl -u aigenerate -n 50 --no-pager`
3. 确认 `.env` 文件存在且配置正确
4. 确认 Python 虚拟环境已创建：`ls /opt/aigen/backend/venv/bin/uvicorn`
5. 手动运行测试：`cd /opt/aigen/backend && source venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000`

### Nginx 返回 502 Bad Gateway

1. 确认后端服务正在运行：`sudo systemctl status aigenerate`
2. 确认端口 8000 正在监听：`ss -tlnp | grep 8000`
3. 检查 Nginx 错误日志：`sudo tail -f /var/log/nginx/error.log`

### 前端页面空白 / 路由 404

1. 确认 `nginx.conf` 中 `try_files $uri $uri/ /index.html` 配置正确
2. 确认 `/opt/aigen/frontend/dist/` 目录存在且包含 `index.html`
3. 检查浏览器控制台是否有网络错误

### SSL 证书问题

1. 确认域名 DNS 已正确解析到服务器 IP
2. 确认防火墙已开放 80 和 443 端口
3. 检查 certbot 日志：`sudo certbot certificates`

---

## 目录结构说明

```
/opt/aigen/
├── backend/            # FastAPI 后端
│   ├── app/            # 应用代码
│   ├── venv/           # Python 虚拟环境（部署时自动创建）
│   ├── .env            # 环境变量配置
│   └── requirements.txt
├── frontend/           # Vue 3 前端
│   ├── src/            # 源代码
│   └── dist/           # 构建产物（部署时自动生成）
└── deploy/             # 部署相关文件
    ├── aigenerate.service  # systemd 服务文件
    ├── nginx.conf          # Nginx 站点配置
    ├── deploy.sh           # 一键部署脚本
    └── README_deploy.md    # 本部署指南
```
