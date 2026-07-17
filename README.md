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

健康检查接口为 `GET /api/health`，用于确认 Web 服务和 SQLite 连接正常。

VS Code 用户可以直接打开项目，选择 `Run Mini OJ (Uvicorn)` 调试配置，或运行默认测试任务。

初始管理员默认为 `admin / admin12345`。正式使用前通过环境变量 `OJ_ADMIN_USERNAME`、`OJ_ADMIN_PASSWORD`、`OJ_SESSION_SECRET` 修改。

部署到 HTTPS 时设置 `OJ_SESSION_HTTPS_ONLY=true`；Session 默认有效期为 86400 秒，可通过 `OJ_SESSION_MAX_AGE` 调整。

数据位于 `data/oj.db`，评测临时文件位于 `temp/`，备份位于 `backups/`。

管理员可以在前端创建、查看和恢复备份。恢复前会校验 `manifest.json` 和 SQLite 完整性；恢复会覆盖备份之后产生的数据。

代码提交后，前端会自动轮询状态并在完成后展示允许当前角色查看的评测日志。教师和管理员可以在提交列表发起重新评测。

教师页面同时提供完整题目管理，以及按题目、用户、状态、结果筛选全部提交并查看完整日志的功能。

## 测试

```powershell
pytest
```

当前自动化测试覆盖项目的核心验收流程；详细人工验收步骤见 `report/acceptance-checklist.md`。

## 已知限制

- 基础模块仅评测 Python。
- `memory_limit` 会保存，但基础版本不执行内存限制。
- 评测使用独立子进程和超时，不等价于 Docker 等强安全沙箱，请勿部署为公开互联网服务。
- 服务重启时，遗留的 `pending` 或 `running` 提交会标记为 `failed/SE`，教师可对其重新评测。
