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

初始管理员默认为 `admin / admin12345`。正式使用前通过环境变量 `OJ_ADMIN_USERNAME`、`OJ_ADMIN_PASSWORD`、`OJ_SESSION_SECRET` 修改。

数据位于 `data/oj.db`，评测临时文件位于 `temp/`，备份位于 `backups/`。

## 测试

```powershell
pytest
```

## 已知限制

- 基础模块仅评测 Python。
- `memory_limit` 会保存，但基础版本不执行内存限制。
- 评测使用独立子进程和超时，不等价于 Docker 等强安全沙箱，请勿部署为公开互联网服务。
