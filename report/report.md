# Mini OJ 实验报告

## 1. 项目概述

本项目使用 Python 3.13、FastAPI、SQLite 和原生 HTML/CSS/JavaScript，实现一个小型 Online Judge。系统已完成注册登录、三角色权限、题目管理、异步 Python 评测、提交状态管理、分级评测日志、审计日志、数据持久化、备份恢复和前端交互。基础版本不执行内存限制，也未实现 Docker 强隔离和进阶模块。

## 2. 系统架构

```text
浏览器前端
    │ Cookie Session / JSON API
    ▼
FastAPI 路由层
    │ 认证与角色依赖
    ▼
业务服务层 ─────── 评测层
    │                 │ 独立 Python 子进程
    ▼                 ▼
SQLAlchemy ─────── SQLite
```

- 路由层：接收请求、执行依赖注入和返回统一响应。
- 业务层：管理提交状态和后台评测流程。
- 数据层：使用 SQLAlchemy 操作 SQLite，并启用外键约束。
- 评测层：每个测试点在独立子进程运行，捕获输出、错误、退出码和耗时。
- 日志层：保存测试点日志和管理员操作审计记录。
- 前端层：维护 Cookie Session，调用后端接口并轮询提交状态。

## 3. 数据设计

| 数据实体 | 主要字段 | 用途 |
|---|---|---|
| User | id、username、password_hash、role、is_active | 用户认证与权限 |
| Problem | id、title、description、time_limit、memory_limit | 题目公开配置 |
| TestCase | problem_id、case_id、input、output、score、is_hidden | 公开及隐藏测试点 |
| Submission | user_id、problem_id、source_code、status、result、score | 提交状态和结果 |
| JudgeLog | submission_id、case_id、stdout、stderr、expected_output | 测试点级日志 |
| AuditLog | operator_id、action、target_id、success | 敏感操作审计 |
| Backup | id、created_at | 备份记录 |

历史提交只保存 `problem_id` 字符串，因此删除题目不会级联删除历史提交和日志。

## 4. 核心实现

### 4.1 异步评测

提交接口先创建 `pending` 记录并返回 HTTP 202，再使用 FastAPI `BackgroundTasks` 启动评测。后台任务把状态改为 `running`，完成后改为 `finished`，系统异常则改为 `failed`。

合法状态流转：

```text
pending -> running -> finished
   │          │
   └-> failed <-┘
```

### 4.2 子进程和结果判断

学生代码保存到独立临时目录的 `main.py`，通过 `asyncio.create_subprocess_exec()` 运行，禁止使用 `eval()` 和 `exec()`。每个测试点单独启动子进程并应用时间限制。系统支持 AC、WA、RE、TLE 和 SE，最终结果优先级为 `SE > TLE > RE > WA > AC`。

输出比较会统一换行符、删除行尾空格和文件末尾空行，但保留行首与行内空格。评测结束后使用 `finally` 清理临时目录。

### 4.3 权限与隐藏数据

注册用户固定为学生，密码使用 bcrypt 哈希。受保护接口依次检查 Session、用户是否存在、启用状态和角色。学生只能查看自己的提交；教师可以管理题目、筛选全部提交和查看完整日志；管理员拥有教师权限并管理用户与备份。

学生题目响应不包含 `test_cases`。学生日志视图不返回隐藏输入、隐藏标准答案或隐藏实际输出，并会脱敏服务器绝对路径、截断超长文本。教师查看完整日志会产生 `VIEW_FULL_JUDGE_LOG` 审计记录。

### 4.4 持久化与备份

主要数据存储在 `data/oj.db`。备份目录包含数据库文件和 `manifest.json`，清单记录文件名和 SHA-256。恢复前验证清单、摘要和 SQLite 完整性，并先创建当前数据库的安全副本；失败时不会破坏当前数据。

## 5. API 说明

所有业务接口使用 `/api` 前缀，完整交互文档位于 `/docs`。

| 模块 | 方法和路径 | 权限 |
|---|---|---|
| 认证 | POST `/auth/register`、`/auth/login`、`/auth/logout`；GET `/auth/me` | 公开/登录 |
| 用户 | GET `/users`、`/users/{id}`；PUT `/users/{id}` | 管理员 |
| 题目 | GET `/problems`、`/problems/{id}` | 已登录 |
| 题目管理 | POST `/problems`；PUT/DELETE `/problems/{id}` | 教师、管理员 |
| 提交 | POST/GET `/submissions`；GET `/submissions/{id}` | 已登录，学生限本人 |
| 重评 | POST `/submissions/{id}/rejudge` | 教师、管理员 |
| 日志 | GET `/submissions/{id}/logs` | 本人或教师、管理员 |
| 日志检索 | GET `/logs` | 教师、管理员 |
| 审计日志 | GET `/audit-logs` | 管理员 |
| 备份 | POST/GET `/admin/backups`；POST `/admin/backups/{id}/restore` | 管理员 |

统一响应包含 `code`、`message` 和 `data`，HTTP 状态码与响应体 code 保持一致。分页统一使用 `page` 和 `page_size`。

## 6. 测试结果

执行 `pytest -q` 运行测试。当前测试覆盖：

- AC、WA、RE、TLE、SE、多测试点和输出规范化；
- 非 UTF-8 输出、超长输出、空白代码、64 KiB 限制和临时目录清理；
- 注册登录、三角色权限、禁用用户和密码安全；
- 题目 CRUD、字段校验和隐藏测试点；
- 提交状态机、筛选分页、所有权与重新评测；
- 日志裁剪、路径脱敏和完整日志审计；
- 重启持久化、备份恢复、损坏及篡改备份保护。

最低验收步骤见 `report/acceptance-checklist.md`。最终提交前需要补充本机测试输出和前端操作截图。

## 7. 问题与解决过程

1. Pydantic 自定义校验错误包含不可直接 JSON 序列化的异常对象，曾导致 422 请求出现服务器错误。通过统一使用 `jsonable_encoder` 转换验证错误解决。
2. Windows 校验损坏 SQLite 备份时，异常路径没有关闭连接，导致文件被锁定。通过 `try/finally` 保证连接释放，并增加损坏备份测试解决。
3. 长期运行的开发数据库超过一页用户后，依赖第一页查找新用户的测试失败。增加用户名精确筛选，并让测试不再依赖数据库规模。

## 8. AI 工具使用说明

项目使用 Codex 辅助整理需求、设计模块、生成基础实现和自动化测试。所有生成内容均通过 pytest、真实 HTTP 请求和人工页面检查进行验证。提交者需要阅读并理解认证、状态机、子进程评测、日志脱敏和备份恢复等核心代码，并对最终实现进行确认。
