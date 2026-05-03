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

# 车牌识别 Web 项目运行说明

这是一个前后端分离的车牌识别系统：

- 后端：FastAPI + SQLAlchemy + MySQL/MariaDB
- 前端：Vue 3 + Vite + Axios
- 识别：YOLO 检测车牌区域，PaddleOCR 识别车牌号
- 数据：识别结果写入数据库，支持列表查询和 Excel 导出

本机已测试通过的环境：

- Windows
- Python 3.11
- Node.js 24.14.1
- MariaDB 12.2.2，也可以换成 MySQL 8.x
- PaddleOCR 2.10.0
- PaddlePaddle 2.6.2
- PyTorch 2.5.1 CPU 版

## 1. 打包发给别人时要包含什么

必须包含：

- `backend/`
- `frontend/`
- `models/best.pt`
- `paddleModels/`
- `Font/`
- `requirements.txt`
- `README_WEB.md`

## 2. 安装 Node.js

Windows 可以用 winget：

```powershell
winget install --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
```

安装后重新打开一个 PowerShell，确认：

```powershell
node --version
npm --version
```

如果没有 winget，也可以从 Node.js 官网安装 LTS 版本。

## 3. 安装 MySQL 或 MariaDB

本机测试用的是 MariaDB，和 MySQL 协议兼容：

```powershell
winget install --id MariaDB.Server --accept-package-agreements --accept-source-agreements
```

也可以安装 MySQL 8.x。安装后创建数据库：

```sql
CREATE DATABASE car_plate_detection CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## 4. 配置后端

进入项目根目录，也就是包含 `backend/`、`frontend/`、`models/` 的目录。

复制配置文件：

```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

按本机数据库账号和管理员登录信息修改 `backend/.env`：

```env
DATABASE_URL=mysql+pymysql://root:your_mysql_password@127.0.0.1:3306/car_plate_detection?charset=utf8mb4
SESSION_SECRET=replace_with_a_long_random_secret
ADMIN_USERNAME=replace_with_admin_username
ADMIN_PASSWORD=replace_with_admin_password
```

其中：

- `DATABASE_URL` 是数据库连接
- `SESSION_SECRET` 用于登录态 Cookie 签名，必须换成你自己的随机字符串
- `ADMIN_USERNAME` 和 `ADMIN_PASSWORD` 是网页登录账号密码

游客模式下识别结果只保存在当前浏览器本地；登录模式下识别记录才保存到服务器数据库。

## 5. 安装 Python 依赖

建议使用 Python 3.11。先安装基础依赖：

```powershell
python -m pip install -r requirements.txt
```

如果 Windows 上出现 PyTorch DLL 加载错误，重装 CPU 版 PyTorch：

```powershell
python -m pip install --force-reinstall torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
```

项目里的 `paddleModels/` 是旧版 PaddleOCR 推理模型，所以不要升级到 PaddleOCR 3.x。保持下面这组版本最稳：

```powershell
python -m pip install --force-reinstall paddleocr==2.10.0 paddlepaddle==2.6.2
```

## 6. 启动后端

在项目根目录执行：

```powershell
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后打开：

```text
http://127.0.0.1:8000
```

后端会自动创建这些表：

- `recognition_records`
- `recognition_jobs`

识别截图默认保存在：

- `backend/storage/uploads/`
- `backend/storage/plates/`
- `backend/storage/frames/`

## 7. 启动前端

进入前端目录：

```powershell
cd .\frontend
npm install
npm run dev
```

浏览器打开：

```text
http://127.0.0.1:5173
```

Vite 已配置代理：

- `/api` -> `http://127.0.0.1:8000`
- `/media` -> `http://127.0.0.1:8000`

## 8. 功能说明

- 游客模式：进入页面默认使用游客模式，识别结果只保存在当前浏览器 `localStorage`。
- 登录模式：登录后切换到服务器模式，图片、视频、摄像头识别结果会保存到 MySQL/MariaDB。
- 图片识别：上传图片后立即返回识别结果，前端按当前模式决定本地保存或服务器保存。
- 视频识别：上传视频后创建异步任务，前端轮询任务进度。
- 摄像头识别：浏览器打开摄像头，每秒截取一帧上传识别。
- 记录列表：支持车牌号、来源、时间范围筛选。
- 导出：游客模式导出本地 CSV，登录模式导出服务器 Excel。

## 9. 常见问题

- 后端提示数据库连接失败：检查 MySQL/MariaDB 是否启动，`DATABASE_URL` 的账号、密码、库名是否正确。
- 前端打不开接口：确认后端 `8000` 端口正在运行。
- 摄像头打不开：检查浏览器权限；摄像头通常要求页面运行在 `localhost`、`127.0.0.1` 或 HTTPS。
- 车牌中文显示乱码：优先用浏览器查看，PowerShell 旧编码窗口里中文有时会显示异常。
- 图片链接打不开：确认后端正在运行，并且 `/media` 代理没有改动。

## 10. 项目面试学习总览

这个项目适合在简历里定位为一个“AI 识别能力 Web 化”的工程项目。基于已有 YOLO 车牌检测模型和 PaddleOCR 文字识别能力，完成前后端分离改造、识别流程封装、游客/登录双模式、数据导出和部署方案。


面试时的介绍：

> 这是一个车牌识别 Web 系统。我把原来偏脚本式的 Python 识别流程封装成 FastAPI 服务，前端用 Vue 做上传、摄像头采集、任务进度、结果列表和导出。识别流程上使用 YOLO 定位车牌区域，再用 PaddleOCR 识别车牌字符，并针对蓝牌、绿牌等场景做了颜色候选、OCR 兜底和车牌格式纠错。数据层支持游客本地存储和登录后服务器存储两种模式，方便展示和保护用户隐私。

## 11. 核心业务流程

图片识别流程：

```text
用户选择图片
  -> Vue 使用 FormData 上传
  -> FastAPI 接收 UploadFile
  -> 保存临时文件
  -> OpenCV 读取图片
  -> YOLO 检测车牌框
  -> 颜色候选和 OCR 兜底补充检测
  -> 裁剪车牌区域
  -> PaddleOCR 识别车牌号
  -> 车牌格式归一化和字符纠错
  -> 返回前端
  -> 游客模式写 localStorage，登录模式写数据库
```

视频识别流程：

```text
用户上传视频
  -> 后端创建识别任务 job_id
  -> 后台按固定间隔抽帧
  -> 每帧走图片识别流程
  -> 对短时间重复车牌做去重
  -> 前端轮询 /api/jobs/{job_id}
  -> 任务完成后刷新列表或写入本地记录
```

摄像头识别流程：

```text
浏览器 getUserMedia 打开摄像头
  -> video 显示实时画面
  -> canvas 每秒截取一帧
  -> 转成 Blob/File
  -> 调用图片识别接口
  -> 前端追加识别结果
```

## 12. 项目难点

1. 脚本式识别改造成 Web 服务

难点：原来的识别代码更偏向本地运行，可能直接读文件、弹窗口、写 CSV，不适合浏览器调用。

解决：把识别逻辑封装成 `PlateRecognizer` 服务类，FastAPI 接口只负责接收文件、调用服务、返回结构化 JSON。模型在应用启动时加载一次，避免每次请求都重新加载模型。

面试回答版：

> 我把识别代码从脚本调用拆成了服务层，接口层不直接写模型细节。这样图片、视频、摄像头都能复用同一套识别函数，也更方便后期扩展。

2. 图片、视频、摄像头三种输入统一处理

难点：三种来源不同，但最终都要识别车牌。

解决：统一转成图片帧处理。图片直接识别；视频抽帧识别；摄像头由前端 canvas 截图后上传。

面试回答：

> 我没有为三种输入写三套识别逻辑，而是把它们统一成帧图像。这样核心识别流程只有一套，维护成本更低。

3. 视频识别不能阻塞前端

难点：视频处理耗时长，如果同步等待，接口容易超时，页面体验也会很差。

解决：上传视频后立即返回 `job_id`，后端后台处理，前端轮询任务进度。

面试回答：

> 视频识别采用异步任务设计。前端先拿到 job_id，再定时查询进度，这样用户能看到任务状态，接口也不会因为视频处理时间过长而阻塞。

4. 蓝牌、绿牌等多类型车牌兼容

难点：不同车牌颜色、光照、角度、距离都会影响检测和 OCR。

解决：YOLO 检测之外增加 HSV 颜色候选，支持蓝、黄、绿、白、红；当 YOLO 和颜色候选没有有效结果时，启用 PaddleOCR 整图文本检测作为兜底，再反推出车牌区域。

面试回答：

> 我发现单靠 YOLO 或颜色阈值对某些蓝牌不稳定，所以加了多路候选。先用 YOLO 找框，再用颜色检测补充，最后用 OCR 的文本检测兜底。这样能降低“未检测到车牌”的概率。

5. OCR 容易误识别相似字符

难点：车牌里的 `0/O/D/Q`、`1/I/L`、`5/S`、`8/B` 容易混淆。

解决：增加车牌格式归一化和字符纠错规则。比如新能源车牌中后半部分更可能是数字，就把容易混淆的字母纠正成数字。

面试回答：

> OCR 的结果不能直接相信，我加了一层后处理。根据中国车牌的格式规则，对省份简称、城市字母、后续数字字母位置做归一化，提高最终结果的可用性。

6. 游客模式和登录模式的数据隔离

难点：展示项目时不一定希望所有访问者的数据都进入服务器数据库。

解决：游客模式默认启用，数据只保存在浏览器 `localStorage`；登录后才切换服务器模式，记录写入数据库并支持 Excel 导出。

面试回答：

> 我把存储模式分成游客和登录两种。游客模式减少服务器数据压力，也保护用户隐私；登录模式适合管理员查看历史记录和导出 Excel。

7. 中文文件、中文车牌和编码问题

难点：PowerShell、数据库、JSON、Excel 都可能出现中文乱码。

解决：接口统一返回 JSON；数据库使用 `utf8mb4`；Excel 使用 `openpyxl`；中文显示优先以浏览器为准。

面试回答：

> 中文车牌涉及编码问题。我数据库使用 utf8mb4，接口通过 JSON 返回，导出用 openpyxl 生成 xlsx，避免 CSV 在不同 Excel 环境里乱码。

8. 部署环境复杂

难点：Python AI 依赖、PaddleOCR、PyTorch、Node、数据库版本都可能不一致。

解决：准备 Docker Compose 部署方案，把前端、后端、数据库拆成容器；本地 README 也固定了关键版本。

面试回答：

> AI 项目的环境依赖比较重，所以我在文档里固定了 Python、PaddleOCR、PaddlePaddle、PyTorch 等版本，并准备了 Docker Compose，降低迁移到服务器时的环境差异。

## 13. 项目亮点

1. 前后端分离

前端负责交互，后端负责识别和数据，接口边界清晰。

2. 多输入方式

支持图片上传、视频上传、浏览器摄像头识别，覆盖常见展示场景。

3. 多车牌类型识别

支持蓝牌、绿牌、黄牌、白牌、红牌候选检测，并增加 OCR 文本检测兜底。

4. 游客/登录双模式

游客默认本地存储，登录后服务器存储，更适合公开展示和隐私保护。

5. 视频异步任务

视频上传后用任务 ID 轮询进度，避免长请求阻塞。

6. 结果可查询可导出

登录模式支持数据库分页、筛选和 Excel 导出；游客模式支持本地 CSV 导出。

7. 识别后处理

针对车牌格式做归一化和字符纠错，提高识别结果可用性。

8. 可部署性

提供 Dockerfile、Nginx 配置、Docker Compose 和服务器部署说明。

## 14. 需要掌握的技术点

前端：

- Vue 3 组合式 API：`ref`、`reactive`、`computed`、`watch`、`onMounted`
- Axios 请求封装：文件上传、Cookie 会话、Blob 下载
- FormData：上传图片和视频
- getUserMedia：调用浏览器摄像头
- canvas：截取摄像头画面并转成图片
- localStorage：游客模式本地保存识别结果
- 前端分页、筛选、导出 CSV

后端：

- FastAPI：路由、文件上传、依赖注入、静态文件服务
- SQLAlchemy：模型定义、增删查、分页
- MySQL/MariaDB：数据库连接、utf8mb4 编码
- Session Cookie：登录态
- BackgroundTasks：视频异步任务
- openpyxl：Excel 导出

AI 与图像处理：

- YOLO：目标检测，负责找车牌位置
- PaddleOCR：文字识别，负责识别车牌字符
- OpenCV：读取图片、裁剪、颜色空间转换、画框
- HSV 颜色阈值：蓝牌、黄牌、绿牌等候选检测
- OCR 后处理：车牌格式校验和相似字符纠错

部署：

- Vite 构建前端
- Nginx 托管前端并代理 `/api` 和 `/media`
- Dockerfile 构建前后端镜像
- Docker Compose 编排前端、后端、数据库
- HTTPS 与摄像头权限关系

## 15. 猜测面试高频问题和参考答案

1. 这个项目是做什么的？

答：这是一个车牌识别 Web 系统，用户可以通过浏览器上传图片、视频或调用摄像头识别车牌。系统会返回车牌号、置信度、来源和识别时间，并支持列表查询和导出。

2. 你主要负责了什么？

答：我主要负责把本地 Python 识别脚本 Web 化，完成 Vue 前端页面、FastAPI 接口、识别服务封装、游客/登录模式、结果列表、导出和部署配置。

3. YOLO 和 PaddleOCR 分别做什么？

答：YOLO 负责目标检测，也就是找出车牌在图片中的位置；PaddleOCR 负责文字识别，也就是识别裁剪出来的车牌号。

4. 为什么不直接用 OCR 识别整张图？

答：整张图背景复杂，OCR 容易识别到无关文字。先用 YOLO 定位车牌区域，再 OCR 裁剪图，能减少干扰。不过对某些蓝牌场景，我也加了 OCR 整图检测作为兜底。

5. 为什么视频要做异步任务？

答：视频需要逐帧或抽帧处理，耗时明显比图片长。异步任务可以先返回 job_id，前端轮询进度，避免接口超时和页面长时间等待。

6. 摄像头识别怎么实现？

答：前端用 `navigator.mediaDevices.getUserMedia()` 获取视频流，用 `video` 标签展示，再用 `canvas` 定时截帧，把截图转成 `Blob/File` 上传到图片识别接口。

7. 游客模式为什么用 localStorage？

答：游客模式主要用于公开展示，不希望所有访问者的数据都进入服务器数据库。localStorage 能把记录留在当前浏览器，刷新后还在，也减少服务器存储压力。

8. 登录模式的数据怎么存？

答：登录后后端通过 Session Cookie 判断用户身份，识别结果写入 MySQL/MariaDB，前端从 `/api/recognitions` 分页查询，并可以通过导出接口生成 Excel。

9. 怎么避免上传目录不存在？

答：后端启动和保存文件时会用 `mkdir(parents=True, exist_ok=True)` 自动创建 `uploads`、`plates`、`frames` 目录。

10. 怎么处理蓝牌识别失败？

答：我加了多路检测策略。YOLO 先检测，如果没有有效结果，再用颜色候选检测蓝牌区域；如果仍然失败，就用 PaddleOCR 的整图文本检测找到疑似车牌文字，再反推出车牌区域。

11. 怎么处理 OCR 错字？

答：通过车牌格式规则做后处理。比如省份简称必须在第一位，第二位通常是城市字母，后面按燃油车或新能源车牌长度做相似字符纠错。

12. 项目如何导出 Excel？

答：登录模式下后端根据筛选条件查询数据库，用 `openpyxl` 生成 `.xlsx` 文件并返回给前端下载。游客模式下没有服务器记录，所以前端导出本地 CSV。

13. 为什么要用 FastAPI？

答：FastAPI 和 Python AI 生态结合方便，文件上传、JSON 接口、后台任务都比较容易实现，而且自动生成接口文档，适合快速开发和调试。

14. 为什么要用 Vue？

答：我熟悉 Vue，它适合构建这种交互型工作台，比如上传文件、展示进度、列表筛选、模式切换和导出操作。

15. 如果多人同时上传视频怎么办？

答：CPU 推理会成为瓶颈。可以限制视频大小和并发数量，增加任务队列，比如 Celery 或 Redis Queue，也可以升级服务器 CPU 或使用 GPU 推理。

16. 如果部署到公网，摄像头为什么可能不能用？

答：浏览器摄像头 API 通常要求安全上下文，也就是 localhost 或 HTTPS。公网 HTTP 页面可能无法调用摄像头，所以正式上线我配置域名和 HTTPS。

17. 数据库表怎么设计？

答：主要有识别记录表和任务表。识别记录保存车牌号、置信度、来源、截图路径、识别时间；任务表保存视频任务状态、进度、总帧数、已处理帧数和错误信息。

18. 项目有什么不足？

答：目前适合展示和小规模使用，高并发视频识别还需要任务队列、限流和更强算力。模型准确率也受图片质量影响，后续可以补充更多蓝牌、夜间、模糊场景数据做训练或微调。

19. 如果面试官问“模型是你训练的吗”怎么答？

答：可以如实说：这个项目重点是工程集成和 Web 化。我使用已有 YOLO 检测模型和 PaddleOCR 推理模型，主要完成识别流程封装、接口化、前端交互、数据存储、导出和部署优化。

20. 如果面试官问“你最大的收获是什么”怎么答？

答：我最大的收获是理解了 AI 模型从本地脚本到真实 Web 应用的完整链路。模型只是其中一部分，文件上传、异步任务、数据存储、错误处理、部署和用户体验都很关键。

## 16. STAR 法则简历写法

STAR 是：

- S：Situation，项目背景
- T：Task，承担任务
- A：Action，采取行动
- R：Result，最终结果

简历项目写法一，适合初级前端：

```text
车牌识别 Web 系统 | Vue 3 + FastAPI + MySQL + YOLO + PaddleOCR

项目背景：原项目为本地 Python 车牌识别脚本，使用不便，无法通过浏览器上传图片、视频或摄像头实时识别。
负责内容：负责将识别能力 Web 化，完成前端工作台、接口联调、游客/登录双模式、结果列表、导出和部署配置。
核心行动：
- 使用 Vue 3 + Vite 实现图片上传、视频上传、摄像头采集、任务进度、筛选列表和导出功能。
- 使用 Axios + FormData 对接 FastAPI 文件上传接口，并通过轮询实现视频识别进度展示。
- 设计游客模式和登录模式：游客数据保存在 localStorage，登录后识别记录写入 MySQL。
- 配合后端封装 YOLO + PaddleOCR 识别流程，增加蓝牌、黄牌、绿牌等多类型车牌候选检测和 OCR 兜底。
- 编写 Docker Compose、Nginx 和部署文档，支持项目迁移到云服务器运行。
项目结果：实现图片、视频、摄像头三种识别入口，支持本地 CSV 和服务器 Excel 导出，提升了项目展示性和可部署性。
```

简历项目写法二，偏工程完整度：

```text
车牌识别前后端分离系统

基于 Vue 3、FastAPI、MySQL、YOLO 和 PaddleOCR 开发车牌识别 Web 应用，将本地识别脚本改造成可通过浏览器访问的工程化系统。前端实现图片/视频上传、摄像头抽帧识别、识别记录列表、筛选和导出；后端封装模型推理流程，支持图片同步识别、视频异步任务、数据库持久化和 Excel 导出。针对蓝牌、绿牌、黄牌等场景增加颜色候选、OCR 整图检测兜底和车牌格式纠错，并提供游客本地存储和登录服务器存储两种模式，降低公开展示时的数据存储压力。
```

## 17. 按 STAR 法则回答“介绍一下你的项目”

可以这样背：

```text
S：这个项目最开始是一个本地 Python 车牌识别脚本，只能在本机运行，交互不方便，也不适合给别人在线演示。

T：我的目标是把它改造成一个前后端分离的 Web 系统，让用户可以通过浏览器上传图片、视频或调用摄像头识别车牌，并能查看和导出识别结果。

A：我用 Vue 3 做前端工作台，用 FastAPI 封装后端接口，把 YOLO 车牌检测和 PaddleOCR 文字识别封装成统一服务。图片直接同步识别，视频通过后台任务异步处理，摄像头则由前端 canvas 定时截帧上传。数据层做了游客和登录两种模式，游客结果保存在浏览器本地，登录后写入 MySQL 并支持 Excel 导出。针对蓝牌检测不稳定的问题，我增加了颜色候选、OCR 整图检测兜底和车牌格式纠错。

R：最后项目可以完整支持图片、视频和摄像头三种识别方式，能展示识别结果、筛选记录并导出文件，也准备了 Docker 部署配置，方便部署到云服务器用于作品展示。
```

## 18. 按 STAR 法则回答“项目里最难的问题”

可以这样说：

```text
S：项目上线前测试时，我发现部分蓝色车牌会出现未检测到车牌的问题，尤其是整车图里车牌较小、背景又有其他蓝色物体时，颜色检测容易被干扰。

T：我要解决的是提高蓝牌场景的检出率，同时不能明显影响绿牌、新能源车牌等已有识别效果。

A：我先用网上真实蓝牌图片复现问题，确认不是前端上传问题，而是检测候选没有拿到有效车牌区域。然后我在 YOLO 和颜色候选之外增加了 PaddleOCR 整图文本检测兜底：当常规候选没有识别出有效车牌时，用 OCR 检测整图文字，筛选符合中国车牌格式的文本，再根据 OCR 文本框反推出车牌区域。同时保留原有的车牌格式归一化和字符纠错。

R：修改后，之前未检测到的蓝牌整车图可以识别出 `京EW6049`，蓝牌近图可以识别出 `京BK0074`，原来的新能源测试图也能继续识别，并修正了漏字问题。
```

## 19. 面试官追问时的安全回答

如果问模型训练：

> 这个项目的重点不是从零训练模型，而是把已有检测和 OCR 能力工程化落地。我主要做的是模型加载、推理封装、Web 接口、前端交互、存储导出和部署。

如果问为什么准确率不是 100%：

> 车牌识别受光照、角度、模糊、遮挡、距离影响很大。工程上我做了多路候选和后处理，但要继续提升准确率，还需要补充更多场景数据训练检测模型，或者接入更专业的车牌识别模型。

如果问为什么不用纯前端识别：

> YOLO 和 PaddleOCR 模型较大，浏览器端推理成本高，而且兼容性和性能不稳定。服务器端推理更容易管理模型、依赖和算力，前端只负责采集和展示。

如果问为什么游客模式不存服务器：

> 这是为了公开展示时减少隐私和存储压力。游客识别结果只留在当前浏览器，登录模式才保存到服务器，适合管理员管理和导出。

如果问如何优化性能：

> 图片可以限制尺寸并压缩；视频可以抽帧、限制大小、限制并发；后端可以加入任务队列和缓存；模型可以使用 GPU、ONNX 或 TensorRT 优化；部署上可以把静态资源交给 Nginx，后端只处理 API 和推理。

## 20. 学习顺序

建议按这个顺序学这个项目：

1. 先看前端入口：[frontend/src/App.vue](frontend/src/App.vue)
2. 理解游客模式、登录模式、本地存储和导出
3. 看前端接口封装：[frontend/src/api/client.js](frontend/src/api/client.js)
4. 看后端图片、视频、导出接口：[backend/app/routers/recognitions.py](backend/app/routers/recognitions.py)
5. 看登录接口：[backend/app/routers/auth.py](backend/app/routers/auth.py)
6. 看识别服务：[backend/app/services/recognizer.py](backend/app/services/recognizer.py)
7. 看视频任务：[backend/app/services/video.py](backend/app/services/video.py)
8. 看数据库模型：[backend/app/models.py](backend/app/models.py)
9. 最后看部署：[docker-compose.prod.yml](docker-compose.prod.yml)

每学一块，你要能回答三个问题：

- 它解决什么问题？
- 它输入什么，输出什么？
- 如果它出错，我该怎么排查？
