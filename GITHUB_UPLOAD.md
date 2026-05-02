# GitHub 上传前检查清单

## 1. 上传前先确认

不要把本地密码、数据库文件、运行日志和上传图片提交到 GitHub。

已经通过 `.gitignore` 忽略的重点内容：

- `backend/.env`
- `.env.production`
- `frontend/node_modules/`
- `frontend/dist/`
- `backend/mariadb-data/`
- `backend/storage/`
- `tmp-web-tests/`
- `datasets/`
- `runs/`
- `results/`
- `*.zip`
- `*.log`

## 2. 检查项目是否还能运行

后端：

```powershell
python -m compileall .\backend\app
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```powershell
cd .\frontend
npm run build
npm run dev
```

## 3. 初始化 Git 仓库

在项目根目录执行，也就是包含 `backend/`、`frontend/`、`README.md` 的目录：

```powershell
git init
git branch -M main
git add .
git status --short
```

重点检查 `git status --short` 里不能出现：

```text
backend/.env
.env.production
frontend/node_modules/
frontend/dist/
backend/mariadb-data/
backend/storage/
tmp-web-tests/
*.zip
*.log
```

如果这些文件出现在待提交列表里，先不要提交，说明忽略规则需要再检查。

## 4. 提交代码

确认待提交文件没问题后：

```powershell
git commit -m "feat: add car plate recognition web app"
```

## 5. 连接 GitHub 仓库

先在 GitHub 新建一个空仓库，不要勾选自动生成 README。

然后把下面的地址换成你的仓库地址：

```powershell
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

如果你使用 SSH：

```powershell
git remote add origin git@github.com:你的用户名/你的仓库名.git
git push -u origin main
```

## 6. GitHub 页面展示建议

仓库简介可以写：

```text
Vue + FastAPI + YOLO + PaddleOCR license plate recognition web system.
```

README 首页已经放在 `README.md`，详细运行和面试学习内容在 `README_WEB.md`。

## 7. 上服务器时的配置

不要把真实生产 `.env.production` 提交到 GitHub。

服务器上复制示例：

```powershell
Copy-Item .\.env.production.example .\.env.production
```

然后修改 `.env.production` 里的：

- `MARIADB_ROOT_PASSWORD`
- `MARIADB_PASSWORD`
- `SESSION_SECRET`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ALLOWED_ORIGINS`

Docker 启动时：

```powershell
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```
