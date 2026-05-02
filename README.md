# 车牌识别 Web 系统

这是一个前后端分离的车牌识别项目，支持图片上传、视频上传、浏览器摄像头识别、游客本地记录、登录服务器记录和结果导出。

## 技术栈

- 前端：Vue 3、Vite、Axios
- 后端：FastAPI、SQLAlchemy、MySQL/MariaDB
- 识别：YOLO 车牌检测、PaddleOCR 文字识别、OpenCV 图像处理
- 部署：Docker、Docker Compose、Nginx

## 核心功能

- 图片识别：上传图片后返回车牌号、置信度和截图结果
- 视频识别：上传视频后创建异步任务，前端轮询识别进度
- 摄像头识别：浏览器采集摄像头画面并定时截帧识别
- 游客模式：默认进入游客模式，识别记录只保存在当前浏览器
- 登录模式：登录后识别记录保存到服务器数据库
- 数据导出：游客模式导出 CSV，登录模式导出 Excel
- 多类型车牌：支持蓝牌、绿牌、黄牌、白牌、红牌候选检测，并增加 OCR 兜底

## 快速开始

完整运行、部署和面试学习说明请看：

- [README_WEB.md](README_WEB.md)
- [DEPLOY_SERVER.md](DEPLOY_SERVER.md)
- [GITHUB_UPLOAD.md](GITHUB_UPLOAD.md)

本地开发常用命令：

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问：

```text
http://127.0.0.1:5173
```

## 环境变量

本地后端配置从 `backend/.env` 读取。不要提交真实 `.env` 文件。

可以复制示例文件后修改：

```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

服务器 Docker 部署可以参考：

```powershell
Copy-Item .\.env.production.example .\.env.production
```

再把里面的数据库密码、管理员账号和会话密钥换成自己的值。

## 上传 GitHub 前注意

请确认不要上传：

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
- 各类 `.zip` 发布包和日志文件
