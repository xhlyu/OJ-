# 原始作业要求逐项符合性矩阵

复核依据：`C:\Users\21353\Downloads\第二次大作业说明.pdf`，共 43 页，2026-07-23 重新逐页读取。

结论范围：本项目已完成全部 **基础必做模块**、代码规范、自动化测试、实验报告和线下验收材料，并额外实现 Adv 1 Special Judge。Adv 2 安全隔离和 Adv 3 代码相似度检测仍为未实现选做项，不影响基础符合性结论。

状态说明：

- `符合`：源码、页面和测试中均有直接证据。
- `符合（已知边界）`：满足基础要求，同时原文允许或项目明确说明限制。
- `选做已实现`：额外完成的进阶模块。
- `选做未实现`：不影响基础模块验收。

## 1. 技术与工程要求

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| Python 3.10+ | 符合 | 当前环境 Python 3.13，README 声明 3.10+ | 全量 pytest 在 3.13 运行 |
| FastAPI + Uvicorn | 符合 | `app/main.py`、`requirements.txt` | `/api/health`、TestClient |
| Pydantic 数据模型 | 符合 | `app/schemas.py` | 422、字段和整体校验测试 |
| pytest 自动化测试 | 符合 | `tests/`、`pytest.ini` | `pytest -q` 直接运行 |
| Git + Conventional Commits | 符合 | Git 历史使用 feat/fix/test/docs | `git log --oneline` |
| SQLite 或 JSON 持久化 | 符合 | SQLAlchemy + `data/oj.db` | 重启生命周期测试、备份恢复测试 |
| JSON API | 符合 | 业务接口统一 JSONResponse | API 测试 |
| 所有业务路由使用 async def | 符合 | `app/routers/*.py`、`app/main.py` | `test_all_fastapi_routes_are_async` |
| 提交接口在评测结束前返回 | 符合 | BackgroundTasks + HTTP 202 | 完整提交流程测试 |
| 禁止 eval/exec | 符合 | 使用 `asyncio.create_subprocess_exec` | 源码静态检查、评测测试 |
| 不在 FastAPI 主进程执行学生代码 | 符合 | `app/judge/runner.py` 子进程 | AC/WA/RE/TLE 测试 |
| 不提交虚拟环境、缓存、数据库和临时文件 | 符合 | `.gitignore` | `git ls-files`、`git check-ignore` |
| 代码不得全部集中在 main.py | 符合 | routers/models/judge/service/serializer 等模块 | 项目目录检查 |

目录结构与示例不完全同名：原文允许增加目录并给出“建议职责”。本项目使用单文件 `app/services.py` 和 `app/utils.py`，SQLAlchemy 数据访问集中在 `app/database.py` 与各路由查询中，没有单独 repositories 目录；代码已按职责拆分，满足“不得全部集中一个文件”的强制要求。

## 2. 统一接口规范

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| 业务 API 使用 `/api` 前缀 | 符合 | main include_router prefix；health 明确 `/api` | API 路由清单测试 |
| code/message/data 统一响应 | 符合 | `app/utils.py:response`、异常处理器 | 响应一致性测试 |
| HTTP 状态与 body code 一致 | 符合 | response 和异常处理器统一设置 | 响应一致性测试 |
| 无返回数据时 data=null | 符合 | 删除、登出等 response(None) | API 测试 |
| Pydantic 失败返回 422 | 符合 | RequestValidationError handler | 多项 422 测试 |
| 不返回完整内部异常 | 符合 | Exception handler 返回通用 500 | 错误结构检查 |
| ISO 8601 UTC 时间 | 符合 | `utils.iso()` 输出 Z | 日志时间测试 |
| 分页 page/page_size 统一 | 符合 | users/problems/submissions/logs/audit | 分页范围和结构测试 |

## 3. 身份认证与权限

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| student/teacher/admin 三角色 | 符合 | User.role、Literal、依赖函数 | 三角色权限测试 |
| is_active 禁用控制 | 符合 | current_user 和 login 检查 | 禁用用户测试 |
| Cookie Session | 符合 | SessionMiddleware、request.session | Cookie 属性和登录测试 |
| 注册/登录/登出/me 四接口 | 符合 | `auth_users.py` | 完整认证测试 |
| 注册固定 student | 符合 | register 不接受 role，Model 默认 student | 权限测试 |
| 密码安全哈希 | 符合 | bcrypt hashpw/checkpw | API 不泄露哈希测试 |
| 初始管理员 | 符合 | lifespan 首次创建；README 说明 | 启动与登录测试 |
| 权限判断顺序 | 符合 | current_user：Session→用户→启用；teacher/admin：角色；路由：资源归属 | 401/403/所有权测试 |
| 学生不能管理题目 | 符合 | Depends(teacher) | 403 测试 |
| 学生不能看其他人提交 | 符合 | submission ownership | 403 测试 |
| 教师不能管理用户 | 符合 | users 依赖 admin | 403 测试 |
| 管理员不能禁用自己 | 符合 | update_user 防护 | 400 测试 |

## 4. Step 1：题目管理

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| 题目规定字段完整 | 符合 | Problem、TestCase、ProblemIn | CRUD 测试 |
| ID/标题/非空/限制/难度校验 | 符合 | Field + model_validator | 422 测试 |
| 至少一个样例和测试点 | 符合 | Field(min_length=1) | 422 测试 |
| case_id 同题唯一 | 符合 | model_validator | 校验测试 |
| 测试点总分 100 | 符合 | model_validator + 前端预检 | 422 与前端元素测试 |
| GET 列表和详情 | 符合 | problems router | API 测试 |
| 学生响应无 test_cases | 符合 | `problem_view(full=False)` | 隐藏测试点测试 |
| 教师/管理员完整题目 | 符合 | role 决定 full=True | 教师 CRUD 测试 |
| POST 创建 201/重复 409 | 符合 | create_problem | 测试 |
| PUT 完整修改且 ID 不可变 | 符合 | update_problem | 400/更新测试 |
| DELETE 不删除历史提交日志 | 符合 | Submission.problem_id 保留字符串 | 生命周期测试 |
| 服务重启后题目存在 | 符合 | SQLite | 持久化测试和人工清单 |

## 5. Step 2：Python 自动评测

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| 独立临时目录和 main.py | 符合 | UUID run_dir | 临时目录清理测试 |
| 当前 Python 解释器 | 符合 | `sys.executable` | Runner 测试 |
| stdin/stdout/stderr/exit code/time | 符合 | subprocess PIPE + perf_counter | 结构化结果测试 |
| 每测试点独立执行 | 符合 | for case 每次创建 subprocess | 多测试点测试 |
| time_limit 与 kill | 符合 | wait_for、kill、communicate | TLE 测试 |
| UTF-8 无法解码判 RE | 符合 | UnicodeDecodeError 分支 | 非 UTF-8 测试 |
| AC/WA/RE/TLE/SE | 符合 | Runner 判断与优先级 | 五结果测试 |
| 规范化换行/行尾/末尾空行 | 符合 | normalize_output | 规范化测试 |
| 保留行首和行内空格 | 符合 | normalize_output | 行首差异测试 |
| 按 AC 测试点计分 | 符合 | CaseResult score 与 sum | 多点测试 |
| 评测后清理临时目录 | 符合 | finally rmtree | 清理测试 |
| memory_limit 保存即可 | 符合（已知边界） | Problem 字段保存并返回 | README 明确未执行限制 |

## 6. Step 3：用户与权限管理

全部规定接口、分页、角色修改、启用状态、重复用户名、密码长度、登录失败统一 401、禁用 403、登出失效和密码字段隐藏均已实现，对应测试集中在 `tests/test_requirements.py`、`tests/test_security_and_log_search.py` 和 `tests/test_api.py`。

项目额外加强了用户名允许字符、密码必须包含字母和数字、bcrypt 72 UTF-8 字节限制。这些规则比最低要求更严格，前端已清楚展示，不与原文冲突。

## 7. Step 4：提交与状态管理

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| Submission 全部规定字段 | 符合 | ORM Model、submission_view | 字段完整性测试 |
| pending/running/finished/failed | 符合 | Model + ALLOWED_TRANSITIONS | 状态机测试 |
| pending/running result=null | 符合 | 创建与 running 时不赋结果 | 提交测试 |
| finished 对应 AC/WA/RE/TLE | 符合 | Service | Judge/提交测试 |
| failed 对应 SE | 符合 | Service 异常分支 | SE 测试 |
| language 仅 python | 符合 | Literal | 422 测试 |
| 空代码和 64 KiB 限制 | 符合 | Schema + route | 422 测试 |
| POST 返回 202 + ID | 符合 | create_submission | 完整流程测试 |
| 单次详情所有权 | 符合 | get_submission | 403 测试 |
| 列表全部筛选和分页 | 符合 | list_submissions | 分页/时间测试 |
| rejudge 权限、状态、清理和审计 | 符合 | rejudge | 重评测试 |

## 8. Step 5：评测日志

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| 提交摘要、测试点日志、审计日志 | 符合 | Submission/JudgeLog/AuditLog | API 测试 |
| JudgeLog 全部规定字段 | 符合 | ORM Model | 日志字段测试 |
| 文本持久化前最多 4000 字符 | 符合 | Runner + Service truncate | 截断测试 |
| 学生日志裁剪 | 符合 | `log_view(full=False)` | 隐藏字段测试 |
| 教师完整日志 | 符合 | `log_view(full=True)` | 教师日志测试 |
| Windows/Linux 路径脱敏 | 符合 | sanitize_error | 双平台路径测试 |
| 教师查看完整日志写审计 | 符合 | submission_logs/all_logs | 审计测试 |
| GET submission logs | 符合 | router | 所有权测试 |
| GET logs 全部筛选 | 符合 | router | 日志搜索测试 |
| GET audit logs 全部筛选 | 符合 | admin router | 时间和审计测试 |
| 规定敏感动作均审计 | 符合 | user/rejudge/log/backup/restore；额外记录 ENABLE_USER | 分模块测试 |

## 9. Step 6：持久化、备份与恢复

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| 所有主要数据持久化 | 符合 | SQLite 七类表 | lifespan 重启测试 |
| POST/GET backup、POST restore | 符合 | admin router | 备份测试 |
| manifest 包含时间/类型/文件 | 符合 | create_backup | 文件内容测试 |
| 创建和恢复写审计 | 符合 | AuditLog | 审计测试 |
| 不存在备份 404 | 符合 | restore 检查 | API 行为 |
| manifest/文件/SHA/quick_check | 符合 | restore 校验 | 损坏/篡改测试 |
| 恢复失败不破坏数据 | 符合 | restore-safety 回滚 | 损坏备份测试 |
| WAL/SHM 恢复一致性 | 符合 | dispose + sidecar 清理 | 恢复测试 |
| 恢复成功后 Session 可失效 | 符合 | restore 成功后 clear Session | 恢复测试 |

## 10. Step 7：前端交互

| 原始要求 | 状态 | 实现证据 | 验证证据 |
|---|---|---|---|
| 注册、登录、当前身份、登出 | 符合 | frontend auth/me/logout | 前端静态检查 + 人工流程 |
| 登录失败/禁用/Session 失效提示 | 符合 | apiError、me 分支 | 前端内容测试 |
| 题目列表与完整公开题面 | 符合 | loadProblems/openProblem | 前端测试 |
| 代码区和提交接口 | 符合 | submitCode | 完整人工流程 |
| 显示提交 ID 和 pending | 符合 | msg(create result) | 提交流程 |
| 自动轮询状态 | 符合 | pollSubmission | 前端测试/人工流程 |
| 显示详情、结果、得分、总时间和日志 | 符合 | details 输出后端结构化 JSON | API 测试 |
| 学生历史列表显示时间/题目/状态/结果/得分 | 符合 | loadSubs | 前端内容测试 |
| 教师完整题目管理 | 符合 | 结构化动态表单 CRUD | 教师 CRUD + 前端测试 |
| 教师提交筛选、完整日志和重评 | 符合（额外完成） | teacher submissions panel | API 测试 |
| 未登录、权限、404、422、网络、500、评测中、空列表反馈 | 符合 | api/apiError/msg/各分支 | 前端内容与人工清单 |
| 页面数据来自后端 API | 符合 | Fetch `/api` | 源码检查 |
| 学生页面不出现隐藏数据 | 符合 | 后端不返回 | API 安全测试 |
| README 可直接启动前后端 | 符合 | 后端直接提供 frontend/index.html | README 命令 |

## 11. 测试、报告与提交材料

| 原始要求 | 状态 | 实现证据 |
|---|---|---|
| pytest 覆盖规定模块 | 符合 | 题目、Judge、权限、提交、日志、持久化全部有测试 |
| report/report.md 八个章节 | 符合 | 概述、架构、数据、核心、API、测试、问题、AI |
| README 必需内容 | 符合 | Python、安装、启动、测试、管理员、SQLite、数据/备份、前端、限制 |
| 必需源码目录和文件 | 符合 | app/frontend/tests/report/requirements/README/.gitignore |
| 不跟踪运行数据或敏感信息 | 符合 | Git 跟踪清单不含 .venv、数据库、备份、temp、work |

## 12. 选做模块

| 模块 | 状态 | 说明 |
|---|---|---|
| Adv 1 Special Judge | 选做已实现 | 题目可选择 standard/special；教师维护 Python `check` 检查器；独立子进程运行；前端支持编辑；自动化测试覆盖 AC、WA、SE 和端到端提交 |
| Adv 2 安全隔离 | 选做未实现 | 只有独立子进程和时间限制，不宣称强沙箱 |
| Adv 3 代码相似度检测 | 选做未实现 | 不影响基础分 |

## 13. 最终结论

按 43 页原始作业说明重新逐项审查后，当前项目覆盖全部基础必做接口、数据字段、权限、状态、评测结果、日志可见性、持久化、备份恢复、前端流程、pytest、README、实验报告与 Git 忽略要求。

“完全符合”在此特指 **全部基础必做要求**，并额外完成 Adv 1 Special Judge。Adv 2 和 Adv 3 是原文明示的选做内容，当前未实现；评测器仍不执行 memory_limit，且不宣称可安全公开部署。
