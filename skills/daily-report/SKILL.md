---
name: daily-report
version: 1.0.0
description: "生成并（经确认后通过飞书）发送今日工作日报。读取当前 git 仓库今日提交（含 merge）与用户备注，用中文归纳为「今日工作 / 问题与风险 / 明日计划」三段，草稿落盘到 ~/.dailyreport/reports/<repo>/，确认后通过 lark-cli 发送。用户说「写日报」「生成日报」「daily report」「发日报」时触发。"
metadata:
  requires:
    bins: ["git", "python3"]
    optionalBins: ["lark-cli"]
---

# daily-report (v1)

**核心价值**：由对话中的 LLM（你）负责**中文归纳**。`daily_report` Python 包只负责"读 git / 写文件 / 调 lark-cli"等确定性操作，不做任何归纳。

> 如果用户要求发送到飞书：MUST 先用 Read 工具读取 [`../lark-im/SKILL.md`](../lark-im/SKILL.md) 与 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)。

## Python 包路径解析

本 skill 依赖 `daily_report` Python 包。解析顺序：

1. 环境变量 `DAILY_REPORT_PACKAGE`（如已设置，直接用）
2. SKILL 文件所在目录的父的父目录即包根（`<skill>/../../daily_report` 是否存在）
3. 常见安装位置：`~/daily-report`

确认一个存在的根后，后续所有 `python3 -m daily_report.tools.*` 调用都要 `PYTHONPATH=<root>` 前缀。推荐开头做一次：

```bash
# 自动定位包（失败则直接问用户）
for cand in "$DAILY_REPORT_PACKAGE" "$HOME/daily-report"; do
  [ -d "$cand/daily_report" ] && export DAILY_REPORT_PACKAGE="$cand" && break
done
echo "$DAILY_REPORT_PACKAGE"
```

## 标准工作流（严格按顺序）

### 第 0 步：判定单仓 vs 多仓（Q3）

- 如果用户的 cwd 在一个 git 工作树里 → **默认单仓**。
- 如果用户的 cwd **不在** git 工作树里（例如 `~/Documents/company` 这种"工作区"根），**MUST 先问**用户：
  > 当前目录 `<path>` 不是 git 仓库。你想：
  > A. 扫描它下面的所有子仓库，汇总成一份多仓日报
  > B. 告诉我具体想写哪个仓库的日报（请 `cd` 进去或告诉我路径）

  **不要自作主张地扫描**；用户明确选 A 才走多仓流程。

- 如果用户在对话中明说"扫一下 X 目录" / "多仓日报" / "把 company 下今天改过的都汇总" → 直接走多仓流程。

### 第 1 步：收集数据

#### 单仓

```bash
PYTHONPATH="$DAILY_REPORT_PACKAGE" python3 -m daily_report.tools.collect --repo "$PWD"
```

输出 JSON 的顶层 `mode` 字段为 `"single"`，其它字段：

| 字段 | 含义 |
|------|------|
| `date` | `YYYY-MM-DD` |
| `repo_name` | `git rev-parse --show-toplevel` 的 basename |
| `branch` | 当前分支名（`git branch --show-current`），detached 时为 `HEAD` |
| `commits` | 今日所有 commit（**包含 merge commit**），每条 `"<hash> <subject>"`；超过 50 条时末尾追加 `"... 还有 N 条提交（已省略）"` |
| `notes` | `~/.dailyreport/notes/<repo>/<date>.md` 的内容，没有则 `null` |
| `notes_path` | 期望的备注路径 |
| `out_path` | 日报最终应写入的绝对路径 |

#### 多仓（workspace）

```bash
PYTHONPATH="$DAILY_REPORT_PACKAGE" python3 -m daily_report.tools.collect --scan "$PWD"
```

`--scan` 扫描一级子目录，**自动跳过**今日无提交的仓库。也可以手工指定：

```bash
python3 -m daily_report.tools.collect --repo path/A --repo path/B --repo path/C
```

输出 JSON 的 `mode == "workspace"`：

| 字段 | 含义 |
|------|------|
| `date` | `YYYY-MM-DD` |
| `workspace_name` | 工作区目录 basename（如 `company`） |
| `repos` | 数组，每项 `{repo_name, repo_path, branch, commits}`（**只含今日有提交的仓库**） |
| `notes` | `~/.dailyreport/notes/_workspace_<workspace_name>/<date>.md` 的内容，没有则 `null` |
| `notes_path` | 期望的 workspace 备注路径 |
| `out_path` | 日报最终应写入的绝对路径（`~/.dailyreport/reports/_workspace_<name>/<date>.md`）|

**如果 `repos` 为空**（扫到了子仓库但今日都无提交）→ 告诉用户"今天所有子仓库都无提交"，不要生成日报。

### 第 2 步：你（LLM）归纳为中文三段

#### 单仓结构

```markdown
# 日报 <date>

分支：`<branch>`

## 今日工作
- <要点 1>
  - `<hash>` <subject>
  - `<hash>` <subject>
- <要点 2>
  - `<hash>` <subject>
...

## 问题与风险
- <要点 1 或 "暂无">

## 明日计划
- <要点 1 或 "待补充">
```

#### 多仓结构

`今日工作` 按仓库分**三级标题**；`问题与风险` 和 `明日计划` **不分仓库**，用 `[<repo_name>]` 前缀标注来源：

```markdown
# 日报 <date>

## 今日工作

### <repo_name_A>（分支：`<branch>`）
- <要点 1>
  - `<hash>` <subject>
  - `<hash>` <subject>
- <要点 2>
  - `<hash>` <subject>

### <repo_name_B>（分支：`<branch>`）
- <要点 1>
  - `<hash>` <subject>

## 问题与风险
- [<repo_name_A>] <要点> 或 "暂无"

## 明日计划
- [<repo_name_B>] <要点> 或 "待补充"
```

每个仓库内部仍然严格遵循下面的归纳规则。

**归纳规则（MUST 遵守）**：

0. **分支与 commit 直接展示**：在日报正文中直接显示分支名。每条「今日工作」要点下方用**缩进子列表**列出对应的 commit（短 hash + subject 原文）。一条要点归纳自多个 commit 时，逐条列在该要点下方；每条要点下 commit 超过 5 条时，相同 scope 的 commit 合并为一行并在括号内注明数量，如 `` `25ac13c` feat(ble): ... 等共 4 条 ``，保证每个要点下不超过 5 行。

1. **合并同 scope（仅用于「今日工作」归纳段）**：`git` commit 如果共享同一 scope（如 `docs(ble):`、`feat(ble):`、`fix(ble):` 三条 BLE 相关），在工作要点中归纳成**一条**中文要点，突出产出价值；不要逐条罗列。提交记录区域仍然展示原始条目。
2. **merge commit 要纳入**：`Merge pull request #N from ...` / `Merge branch ...` 这类 commit，要从 PR/分支名提炼出**功能主题**（例如 `Merge pull request #42 from feat/ble-daemon` → "完成 BLE 守护进程特性合入主干"）。不要在「今日工作」归纳段出现 "Merge pull request #42" 这种原始字样；提交记录区域保留原始 subject。
3. **去噪（仅归纳段）**：「今日工作」归纳要点里**不要**出现 `type(scope):` 前缀、完整英文 commit 原文。技术专有名词（如 BLE、daemon、P0）可以保留。提交记录区域保留 hash + 原始 subject。
4. **视角换位**：从"提交动作"（add/record/update）改为"产出价值"（"实现了 / 修复了 / 梳理了"）。
5. **风险提炼（读 commit body，不止 subject）**：commit subject 含 `fix`、`bug`、`regression`、`revert`、`hack`、`workaround`、`P0`、`P1`、`crash`、`hotfix`、`rollback` 之一**可能**是风险信号，但**必须**用 `git show --no-patch --format='%s%n%n%b' <hash>` 读 body 做二次判定：
   - `body` 里出现 `design, not bug` / `by design` / `pass` / `accepted` / `as designed` → **不是**风险，是设计决策或测试结果
   - `regression test` / `regression pass` / `regression suite` → 是**测试轮次**，不是"回归 bug"
   - `body` 里才能看到具体是"修复了什么"/"什么情况下有什么限制"；只看 subject 非常容易误读
   提炼时用中文说清楚"什么场景下有什么问题"，不要臆测。无法判定时宁可不提取。
6. **计划推断**：commit subject 含 `WIP`、`draft`、`partial`、`TODO`、`wip` 之一，或 `feat` 类 commit 明显未完成（如文档说"第 1 步"），MUST 放入「明日计划」。无线索时写 "待补充" 而不是编造。
7. **截断提示处理**：若 `commits` 末尾出现 `"... 还有 N 条提交（已省略）"`，说明今天提交量超过 50 条上限。在「今日工作」末尾追加一条说明："（今日共提交超过 50 条，以上为摘要）"，提示读者工作量可能比列出的更多。
8. **全中文**：除专有名词外，禁止英文短语。
9. **用户备注优先**：`notes` 字段如果存在，其中的三段内容**覆盖**或**补充**你从 commit 归纳出来的结果；用户手写的永远更权威。
10. **多仓 commit 分组**：workspace 模式下，`今日工作` 按仓库分子标题；但合并同 scope / merge commit 归纳 / 去噪等规则在**每个仓库内部**照样适用。问题与风险 / 明日计划里用 `[repo_name]` 前缀标注来源仓库。

**示例（输入 → 输出）**：

输入 commits：
```
9faae1b docs(ble): propagate daemon P0 findings across skill / test report / manual
e6f115c docs(ble): record P0 regression findings (perf + design limits)
25ac13c feat(ble): add persistent daemon mode for BLE peripheral sessions
94083a6 docs(harness): add manual KBM + xbox360 sweep scripts
a1b2c3d Merge pull request #77 from feat/ble-daemon-handshake
```

输出（假设分支为 `feat/ble-daemon`，共 5 条 commit）：
```markdown
分支：`feat/ble-daemon`

## 今日工作
- 实现 BLE 外设会话常驻守护进程模式，并把守护进程的握手流程合入主干（#77）
  - `a1b2c3d` Merge pull request #77 from feat/ble-daemon-handshake
  - `25ac13c` feat(ble): add persistent daemon mode for BLE peripheral sessions
- 记录守护进程 P0 回归问题（性能与设计限制），同步到 skill / 测试报告 / 手册
  - `9faae1b` docs(ble): propagate daemon P0 findings across skill / test report / manual
  - `e6f115c` docs(ble): record P0 regression findings (perf + design limits)
- 为测试框架补充 KBM 与 Xbox360 手动扫测脚本
  - `94083a6` docs(harness): add manual KBM + xbox360 sweep scripts

## 问题与风险
- BLE 守护进程存在 P0 回归：性能与设计层面均有限制，已在文档中记录，需跟进解决方案

## 明日计划
- 待补充
```

### 第 3 步：展示草稿，询问用户是否需要调整

把渲染后的 markdown **完整展示**给用户。明确询问：

> 以上是草稿。需要我调整哪些段落？如果 OK，我就落盘到 `<out_path>`。

**NEVER** 跳过这一步直接落盘。用户可能要求：
- "把第 2 条拆开"
- "第 3 条改成 XXX"
- "加一条：明天要 review YYY 的 PR"

按用户反馈改 markdown，重新展示，直到用户说 OK。

### 第 4 步：落盘

用户确认后：

```bash
printf '%s' "$RENDERED_MARKDOWN" | PYTHONPATH="$DAILY_REPORT_PACKAGE" \
  python3 -m daily_report.tools.save --out-path "$OUT_PATH"
```

其中 `$OUT_PATH` 来自第 1 步 JSON 的 `out_path` 字段。

### 第 5 步：询问是否发送

问用户：

> 是否要通过飞书发送？发给谁？
> - 群：提供 chat_id（`oc_xxx`），若不知道可以用 `lark-cli im +chat-search --keyword <群名>` 查
> - 个人：提供 open_id（`ou_xxx`），或者不发送仅保留草稿

如果用户说"不发"或没回复 → **停止**，不要发送。

### 第 6 步：发送（仅在用户明确确认后）

```bash
# 发群
cat "$OUT_PATH" | PYTHONPATH="$DAILY_REPORT_PACKAGE" \
  python3 -m daily_report.tools.send --chat-id "$CHAT_ID"

# 或发个人
cat "$OUT_PATH" | PYTHONPATH="$DAILY_REPORT_PACKAGE" \
  python3 -m daily_report.tools.send --user-id "$USER_ID"
```

默认按 markdown 模式发送（`lark-cli` 会自动排版）。如果用户要求纯文本，加 `--text`。

测试时可先用 `--dry-run` 验证命令构造，再移除 `--dry-run` 正式发送。

## 不变量（MUST NOT 违反）

1. **未经用户确认永远不要调用 `send`**（需求 8）。`save` 也要确认，但门槛更低（改磁盘）。
2. **不要绕过 `daily_report` 包**直接在 shell 里写 markdown 到 `~/.dailyreport/reports/`。Skill 必须通过 `tools.save` 落盘，保证未来加钩子（如写入前审计）在一处生效。
3. **不要臆测**：如果 commit 归纳不出计划/风险，老老实实写"待补充 / 暂无"。
4. **不要把 `git hash` 暴露给用户看**（草稿里、发送里都不要）。

## 错误排查

| 症状 | 原因 / 处理 |
|------|------------|
| `ModuleNotFoundError: daily_report` | `PYTHONPATH` 未设置；确认 `$DAILY_REPORT_PACKAGE` 指向包根 |
| `collect` 报 `git log failed` | 当前目录不是 git 仓库或 git 未安装 |
| `send` 报 `未找到 lark-cli` | 未安装 lark-cli 或未登录，参考 lark-shared skill |
| `send` 报 `lark-cli 发送失败` | 多半是 chat-id / user-id 错了，或无权限，或需要切 `--as user`（本 skill 默认 bot 身份） |
