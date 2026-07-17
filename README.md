# Mini OJ

Python 3.10+、FastAPI、SQLite 实现的小型 Online Judge。

## 安装与启动

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

访问 `http://127.0.0.1:8000/`，API 文档位于 `/docs`。

VS Code 用户可以直接打开项目，选择 `Run Mini OJ (Uvicorn)` 调试配置，或运行默认测试任务。

初始管理员默认为 `admin / admin12345`。正式使用前通过环境变量 `OJ_ADMIN_USERNAME`、`OJ_ADMIN_PASSWORD`、`OJ_SESSION_SECRET` 修改。

数据位于 `data/oj.db`，评测临时文件位于 `temp/`，备份位于 `backups/`。

管理员可以在前端创建、查看和恢复备份。恢复前会校验 `manifest.json` 和 SQLite 完整性；恢复会覆盖备份之后产生的数据。

代码提交后，前端会自动轮询状态并在完成后展示允许当前角色查看的评测日志。教师和管理员可以在提交列表发起重新评测。

教师页面同时提供完整题目管理，以及按题目、用户、状态、结果筛选全部提交并查看完整日志的功能。

## 测试

```powershell
pytest
```

## 已知限制

- 基础模块仅评测 Python。
- `memory_limit` 会保存，但基础版本不执行内存限制。
- 评测使用独立子进程和超时，不等价于 Docker 等强安全沙箱，请勿部署为公开互联网服务。
- 服务重启时，遗留的 `pending` 或 `running` 提交会标记为 `failed/SE`，教师可对其重新评测。
