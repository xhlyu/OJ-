# Mini OJ

使用 Python、FastAPI、SQLAlchemy 和 SQLite 实现的小型 Online Judge。

## 1. Python 版本

- 要求：Python 3.10 或更高版本。
- 本项目开发和验收使用：Python 3.13。
- 查看本机版本：

```powershell
py -3.13 --version
```

## 2. 安装依赖命令

第一次在一台电脑上运行项目时，在项目根目录打开 PowerShell，执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

第一条命令创建项目专用虚拟环境，第二条命令安装 `requirements.txt` 中的依赖。已经安装完成后，平时启动不需要重复执行这两条命令。

## 3. 后端启动命令

```powershell
.\.venv\Scripts\python.exe -X utf8 -m fastapi dev app\main.py
```

这是 FastAPI 官方开发服务器启动方式，默认启用代码热重载。`-X utf8` 用于避免中文 Windows 控制台的 GBK 编码错误。看到 `http://127.0.0.1:8000` 后表示启动成功，按 `Ctrl+C` 停止系统。

- 系统页面：`http://127.0.0.1:8000/`
- API 文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/api/health`

VS Code 用户也可以选择 `Run Mini OJ (FastAPI)` 调试配置启动。

## 4. 测试命令

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

pytest 使用 `work/pytest-runtime/` 下的隔离数据，不会修改正式数据库。

## 5. 初始管理员账号的创建与配置

应用首次启动时会在 FastAPI lifespan 中自动检查管理员账号。如果数据库中不存在该用户名，系统会自动创建管理员：

```text
用户名：admin
密码：admin12345
角色：admin
```

正式部署前，可以在启动服务前通过 PowerShell 环境变量修改初始管理员账号和 Session 密钥：

```powershell
$env:OJ_ADMIN_USERNAME="myadmin"
$env:OJ_ADMIN_PASSWORD="请设置至少8位且同时包含字母和数字的密码"
$env:OJ_SESSION_SECRET="请设置随机且足够长的Session密钥"
.\.venv\Scripts\python.exe -X utf8 -m fastapi dev app\main.py
```

这些初始账号环境变量只负责“账号不存在时创建”。如果管理员已经存在，修改环境变量不会自动修改数据库中原账号的密码。

系统还会自动创建独立教师账号 `teacher / teacher12345`。教师负责题目和评测管理，管理员额外负责用户、角色、审计和备份管理。

## 6. 持久化方式

- ORM：SQLAlchemy 2。
- 数据库：SQLite。
- SQLite 使用 WAL 模式、外键约束和 5 秒 busy timeout。
- 用户、题目、测试点、提交、评测日志、审计日志和备份记录都会持久化保存，重启服务后数据仍然存在。

## 7. 数据文件位置

- 正式 SQLite 数据库：`data/oj.db`
- 评测临时文件：`temp/`
- pytest 隔离数据：`work/pytest-runtime/`

可以通过环境变量 `OJ_DATABASE_PATH`、`OJ_DATA_DIR` 和 `OJ_TEMP_DIR` 修改默认位置。

## 8. 备份文件位置

- 默认备份目录：`backups/`
- 每次备份存放在 `backups/backup_时间戳/` 中。
- 每个备份包含 `oj.db` 和用于完整性校验的 `manifest.json`。

管理员可以在前端创建、查看和恢复备份。恢复前会校验 SHA-256 摘要和 SQLite 完整性。可以通过 `OJ_BACKUP_DIR` 修改备份目录。

## 9. 前端安装与启动命令

前端使用原生 HTML、CSS 和 JavaScript，源码位于 `frontend/index.html`，不使用 npm，因此没有额外的前端依赖安装命令。

```powershell
# 前端安装命令：无
# 前端启动命令：与后端相同
.\.venv\Scripts\python.exe -X utf8 -m fastapi dev app\main.py
```

FastAPI 的 `/` 路由会直接返回 `frontend/index.html`，所以执行后端启动命令后，前端和后端会同时启动。

## 10. 主要功能

- 学生注册、登录、提交 Python 代码并查看自己的结果。
- 教师创建、修改、删除题目，管理测试点，筛选提交并重新评测。
- 管理员管理用户和角色、查询审计日志、创建与恢复备份。
- 支持 AC、WA、RE、TLE、SE、多测试点计分和分级日志。
- 支持标准文本比对和 Python Special Judge。

## 11. 已知限制

- 当前只评测 Python 提交。
- `memory_limit` 会保存，但当前版本不执行内存限制，因此没有 MLE 判定。
- 参赛代码和 Special Judge 使用独立子进程与超时控制，但不等价于 Docker 等强安全沙箱，请勿直接开放为公共互联网判题服务。
- 当前没有实现代码相似度检测。
- 服务重启时，遗留的 `pending` 或 `running` 提交会标记为 `failed/SE`，教师可重新评测。
- SQLite 适合课程项目和单机部署，不适合高并发、分布式生产环境。
