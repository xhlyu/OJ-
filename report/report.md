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

主要数据存储在 `data/oj.db`。SQLite 使用 WAL 和 busy timeout 改善并发读写。备份目录包含数据库文件和 `manifest.json`，清单记录文件名和 SHA-256。恢复前验证清单、摘要和 SQLite 完整性，并使用 SQLite 在线备份创建当前数据库的安全副本。替换数据库前清理 WAL/SHM 辅助文件，避免旧事务重新应用到恢复后的数据库；失败时不会破坏当前数据。恢复成功后清除当前 Session，要求管理员按恢复后的用户状态重新登录。

## 5. API 说明

所有业务接口使用 `/api` 前缀，完整可交互文档位于 `/docs`。统一响应包含 `code`、`message` 和 `data`，HTTP 状态码与响应体 code 保持一致；无数据时 `data` 为 `null`。分页统一使用 `page`（默认 1）和 `page_size`（默认 20，范围 1～100）。

### 5.1 认证与用户

| 方法和路径 | 权限 | 请求参数 | 成功响应 | 主要错误 |
|---|---|---|---|---|
| POST `/api/auth/register` | 公开 | JSON：`username`、`password` | 201，安全用户视图 | 409 用户名重复；422 格式错误 |
| POST `/api/auth/login` | 公开 | JSON：`username`、`password` | 200，写入 Session 并返回用户 | 401 凭证错误；403 用户禁用；422 格式错误 |
| POST `/api/auth/logout` | 公开 | 无 | 200，清除 Session | 500 系统错误 |
| GET `/api/auth/me` | 已登录且启用 | Session Cookie | 200，当前用户 | 401 未登录/用户不存在；403 用户禁用 |
| GET `/api/users` | admin | `page`、`page_size`、可选 `username` | 200，分页用户列表 | 401、403、422 |
| GET `/api/users/{user_id}` | admin | 路径参数 `user_id` | 200，用户详情 | 401、403、404 |
| PUT `/api/users/{user_id}` | admin | JSON：`role`、`is_active` | 200，更新后的用户 | 400 禁用自己；403；404；422 |

用户响应不包含 `password_hash`。注册接口不接受 role，新用户固定为 student。管理员修改角色、禁用用户时写审计日志。

### 5.2 题目

| 方法和路径 | 权限 | 请求参数 | 成功响应 | 主要错误 |
|---|---|---|---|---|
| GET `/api/problems` | 已登录且启用 | `page`、`page_size` | 200，分页题目摘要 | 401、403、422 |
| GET `/api/problems/{problem_id}` | 已登录且启用 | 路径参数 `problem_id` | 200，题目详情 | 401、403、404 |
| POST `/api/problems` | teacher/admin | 完整 `ProblemIn` JSON | 201，完整题目 | 403；409 编号重复；422 字段/总分错误 |
| PUT `/api/problems/{problem_id}` | teacher/admin | 完整 `ProblemIn` JSON | 200，修改后的题目 | 400 修改 ID；403；404；422 |
| DELETE `/api/problems/{problem_id}` | teacher/admin | 路径参数 `problem_id` | 200，`data=null` | 403；404 |

`ProblemIn` 包含 id、title、description、input/output description、samples、constraints、time/memory limit、difficulty、tags 和 test_cases。学生题目详情不包含 `test_cases`；教师和管理员获得完整配置。

### 5.3 提交与重新评测

| 方法和路径 | 权限 | 请求参数 | 成功响应 | 主要错误 |
|---|---|---|---|---|
| POST `/api/submissions` | 已登录且启用 | JSON：`problem_id`、`language=python`、`source_code` | 202，`submission_id` 和 pending 状态 | 404 题目不存在；422 空白/超 64 KiB |
| GET `/api/submissions` | 已登录且启用 | 分页；可选 problem_id、user_id、status、result、start/end time | 200，分页提交列表 | 400 时间范围；401；403；422 |
| GET `/api/submissions/{submission_id}` | 本人或 teacher/admin | 路径参数 | 200，提交详情 | 403 非本人；404 |
| POST `/api/submissions/{submission_id}/rejudge` | teacher/admin | 路径参数 | 202，重置后的 pending 状态 | 403；404；409 状态冲突 |

学生列表查询始终由服务器限制为本人数据，即使传入其他 `user_id` 也不能越权。重新评测清空旧结果与日志，并写 `REJUDGE_SUBMISSION` 审计记录。

### 5.4 评测日志与审计日志

| 方法和路径 | 权限 | 请求参数 | 成功响应 | 主要错误 |
|---|---|---|---|---|
| GET `/api/submissions/{submission_id}/logs` | 本人或 teacher/admin | 路径参数 | 200，提交摘要和测试点日志 | 403 非本人；404 |
| GET `/api/logs` | teacher/admin | 分页；submission/problem/user/result/start/end time | 200，完整分页测试点日志 | 400、403、422 |
| GET `/api/audit-logs` | admin | 分页；operator/action/target/start/end time | 200，分页审计日志 | 400、403、422 |

学生日志按 `is_hidden` 裁剪；教师和管理员查看完整日志时写 `VIEW_FULL_JUDGE_LOG` 审计记录。所有角色看到的错误文本仍执行长度限制，学生错误路径另外执行脱敏。

### 5.5 备份、页面和健康检查

| 方法和路径 | 权限 | 请求参数 | 成功响应 | 主要错误 |
|---|---|---|---|---|
| POST `/api/admin/backups` | admin | 无 | 201，backup_id 和时间 | 403；500 创建失败 |
| GET `/api/admin/backups` | admin | 无 | 200，备份列表 | 403 |
| POST `/api/admin/backups/{backup_id}/restore` | admin | 路径参数 | 200，恢复的 backup_id | 400 非法/损坏备份；404；500 替换失败 |
| GET `/api/health` | 公开 | 无 | 200，Web 与 SQLite 健康状态 | 500 数据库不可用 |
| GET `/` | 公开 | 无 | 200，`frontend/index.html` | 500 文件不可用 |

## 6. 测试结果

在 Python 3.13 环境执行 `pytest -q`。2026-07-23 最终复核结果为：

```text
.........................................                                [100%]
41 passed in 17.88s
```

测试覆盖：

- AC、WA、RE、TLE、SE、多测试点和输出规范化；
- 非 UTF-8 输出、超长输出、空白代码、64 KiB 限制和临时目录清理；
- 注册登录、三角色权限、禁用用户和密码安全；
- 题目 CRUD、字段校验和隐藏测试点；
- 提交状态机、筛选分页、所有权与重新评测；
- 日志裁剪、路径脱敏和完整日志审计；
- 重启持久化、备份恢复、损坏及篡改备份保护。
- 教师通过 API 创建、修改和删除题目，以及结构化教师题目编辑页面；
- 前端登录提示、题目详情、提交时间/状态/结果/得分和教师操作所需元素。

测试通过 `tests/conftest.py` 切换到独立 SQLite 数据库和备份目录，避免自动化测试污染正式演示数据。

最低验收步骤见 `report/acceptance-checklist.md`，原始 43 页要求的逐项源码与测试证据见 `report/requirements-compliance.md`。

人工前端复核流程包括：学生注册登录、查看题目、提交 AC/WA/RE/TLE、自动轮询和查看历史；教师加载完整题目并创建/修改/删除、筛选提交、查看完整日志和 rejudge；管理员修改用户、查看审计、创建与恢复备份。页面错误区能够显示未登录、账号禁用、403、404、422、网络失败、500、评测中和空列表等状态。

| 人工前端项目 | 复核结果 |
|---|---|
| 注册、登录、当前用户与登出 | 通过 |
| 题目列表、详情、公开样例和开始作答 | 通过 |
| Python 源码提交、202 返回和自动轮询 | 通过 |
| 提交编号、时间、状态、结果、得分、总时间和允许查看的日志 | 通过 |
| 学生历史提交与所有权限制 | 通过 |
| 教师结构化创建、修改和删除题目 | 通过 |
| 教师筛选提交、完整日志和重新评测 | 通过 |
| 管理员用户状态、审计、备份和恢复 | 通过 |
| 未登录、禁用、无权限、参数错误、空列表和请求错误提示 | 通过 |

## 7. 问题与解决过程

1. Pydantic 自定义校验错误包含不可直接 JSON 序列化的异常对象，曾导致 422 请求出现服务器错误。通过统一使用 `jsonable_encoder` 转换验证错误解决。
2. Windows 校验损坏 SQLite 备份时，异常路径没有关闭连接，导致文件被锁定。通过 `try/finally` 保证连接释放，并增加损坏备份测试解决。
3. 长期运行的开发数据库超过一页用户后，依赖第一页查找新用户的测试失败。增加用户名精确筛选，并让测试不再依赖数据库规模。
4. 自动化测试最初直接使用正式数据库，积累了大量测试账号和题目；启用 WAL 后还发现旧 WAL 可能覆盖恢复数据。通过测试专用环境变量隔离数据库，并在恢复时关闭连接、清除 WAL/SHM 后再替换文件解决。

## 8. AI 工具使用说明

项目使用 Codex 辅助读取和整理需求、设计模块、生成基础实现、补充自动化测试、排查缺陷和编写文档。本人对最终功能进行了启动、真实页面操作、API 响应检查和 pytest 验证，并确认了认证与角色权限、提交状态机、子进程评测、输出比较、隐藏数据裁剪、日志脱敏、SQLite WAL、备份恢复和教师题目管理等核心设计。针对页面无题目、422 信息不明确、测试污染正式数据库、WAL 影响恢复、教师编辑题目不便等实际问题，本人根据运行结果确认并采用了当前修复方案。AI 生成内容不作为正确性依据，最终以原始作业要求、源码行为和测试结果为准。
