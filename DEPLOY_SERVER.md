# 云服务器部署说明

这份说明用于把项目部署到公网服务器，让别人通过链接访问网页并导出 Excel。

## 1. 你需要准备什么

建议配置：

- Ubuntu 22.04 或 24.04 云服务器
- 至少 4 核 CPU、8 GB 内存、40 GB 硬盘
- 如果要多人同时上传视频，建议 8 核 CPU、16 GB 内存以上
- 开放安全组端口：`80`，如果后面做 HTTPS 再开放 `443`
- 一个域名可选；没有域名也可以先用服务器公网 IP 访问

这个项目目前按 CPU 推理准备，能跑图片和视频识别，但视频处理速度取决于服务器 CPU。

如果你要让别人使用“浏览器摄像头识别”，必须准备域名并配置 HTTPS。公网 `http://服务器IP` 一般只能测试图片/视频上传，浏览器通常不会给摄像头权限。

## 2. 在服务器安装 Docker

推荐按 Docker 官方文档安装 Docker Engine 和 Compose 插件。

安装后确认：

```bash
docker --version
docker compose version
```

## 3. 上传项目到服务器

把项目目录上传到服务器，例如：

```bash
/opt/car-plate-web
```

上传时不要带这些本地生成目录：

```text
.venv/
frontend/node_modules/
frontend/dist/
backend/storage/uploads/
backend/storage/plates/
backend/storage/frames/
backend/mariadb-data/
backend/.env
__pycache__/
datasets/
runs/
results/
```

必须带这些：

```text
backend/
frontend/
models/best.pt
paddleModels/
Font/
requirements.txt
docker-compose.prod.yml
.env.production.example
```

## 4. 配置生产环境变量

不要把真实密码直接写进 `docker-compose.prod.yml`。服务器上复制一份生产环境变量文件：

```bash
cp .env.production.example .env.production
```

然后修改 `.env.production`：

```env
MARIADB_ROOT_PASSWORD=replace_with_strong_root_password
MARIADB_PASSWORD=replace_with_strong_database_password
SESSION_SECRET=replace_with_a_long_random_session_secret
ADMIN_USERNAME=replace_with_admin_username
ADMIN_PASSWORD=replace_with_admin_password
```

游客模式下数据只保存在访问者自己的浏览器；登录模式下识别结果会保存到服务器数据库。

如果你绑定了域名，还可以把 `ALLOWED_ORIGINS` 改成你的域名，例如：

```env
ALLOWED_ORIGINS=https://your-domain.com,http://your-domain.com
```

## 5. 启动服务

在服务器项目目录执行：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

查看状态：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

查看后端日志：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend
```

查看前端日志：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f frontend
```

## 6. 访问

如果还没有域名：

```text
http://服务器公网IP/
```

如果已经把域名 A 记录解析到服务器：

```text
http://你的域名/
```

## 7. 更新项目

上传新代码后执行：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

## 8. 停止服务

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

如果要连数据库数据一起删除，谨慎执行：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down -v
```

## 9. 做 HTTPS

有域名后建议加 HTTPS；如果要用摄像头识别，这一步是必需的。最简单的做法是在服务器上再部署 Caddy 或 Nginx Proxy Manager，给这个项目反向代理到宿主机 `80`。这一步需要你的域名和服务器环境，建议等服务器买好、域名解析好后再配置。
