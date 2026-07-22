# Mini OJ

Python 3.10+、FastAPI、SQLite 实现的小型 Online Judge。

## 安装与启动

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

访问 `http://127.0.0.1:8000/`，API 文档位于 `/docs`。

前端源码位于 `frontend/index.html`，由 FastAPI 的 `/` 路由直接提供，因此不需要单独安装或启动前端。执行上面的 Uvicorn 命令后，后端 API 和前端页面会同时可用。

健康检查接口为 `GET /api/health`，用于确认 Web 服务和 SQLite 连接正常。

VS Code 用户可以直接打开项目，选择 `Run Mini OJ (Uvicorn)` 调试配置，或运行默认测试任务。

初始管理员默认为 `admin / admin12345`。正式使用前通过环境变量 `OJ_ADMIN_USERNAME`、`OJ_ADMIN_PASSWORD`、`OJ_SESSION_SECRET` 修改。

系统首次启动会自动创建三道中文演示题：A+B、三个数最大值、1 到 N 的整数和。

部署到 HTTPS 时设置 `OJ_SESSION_HTTPS_ONLY=true`；Session 默认有效期为 86400 秒，可通过 `OJ_SESSION_MAX_AGE` 调整。

数据位于 `data/oj.db`，评测临时文件位于 `temp/`，备份位于 `backups/`。

管理员可以在前端创建、查看和恢复备份。恢复前会校验 `manifest.json`、SHA-256 文件摘要和 SQLite 完整性；恢复会覆盖备份之后产生的数据，并使当前 Session 失效，管理员需要重新登录。

用户管理接口支持通过 `username` 精确筛选，方便管理员在数据量较大时定位账号。

代码提交后，前端会自动轮询状态并在完成后展示允许当前角色查看的评测日志。教师和管理员可以在提交列表发起重新评测。

教师页面同时提供完整题目管理，以及按题目、用户、状态、结果筛选全部提交并查看完整日志的功能。

教师和管理员登录后，可以使用结构化题目表单创建和维护编程题目：填写题目编号、题面、输入输出说明、样例、限制、难度和标签，并动态增加或删除评测测试点。点击题目列表中的“查看 / 编辑”可加载已有题目并保存修改；测试点总分必须为 100，隐藏测试点不会返回给学生。

## 测试

```powershell
pytest
```

当前自动化测试覆盖项目的核心验收流程；详细人工验收步骤见 `report/acceptance-checklist.md`。

完整安装、启动和测试命令为：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
.\.venv\Scripts\python.exe -m pytest -q
```

pytest 自动使用 `work/pytest-runtime/` 下的隔离数据库、临时目录和备份目录，测试不会修改正式的 `data/oj.db`。

SQLite 使用 WAL 和 5 秒 busy timeout 提高后台评测写入可靠性；恢复备份时会清理 WAL/SHM 文件，避免旧事务覆盖恢复结果。

## 已知限制

- 基础模块仅评测 Python。
- `memory_limit` 会保存，但基础版本不执行内存限制。
- 评测使用独立子进程和超时，不等价于 Docker 等强安全沙箱，请勿部署为公开互联网服务。
- 服务重启时，遗留的 `pending` 或 `running` 提交会标记为 `failed/SE`，教师可对其重新评测。
