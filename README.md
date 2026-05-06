# daily-report

一个 Cursor / Claude Code / Codex 的 **Skill**：读取当前 git 仓库今日 commits + 可选备注，由对话里的 LLM 归纳成中文日报「今日工作 / 问题与风险 / 明日计划」，确认后通过 `lark-cli` 发到飞书。

归纳由你对话里的 LLM 完成，**不需要任何 API key**。

## 安装

```bash
# 1. clone 到任意位置
git clone https://github.com/shaw-baobao/daily-report.git ~/daily-report

# 2. 把 skill 软链进你用的客户端（三选一或全选）
ln -s ~/daily-report/skills/daily-report  ~/.cursor/skills/daily-report
ln -s ~/daily-report/skills/daily-report  ~/.claude/skills/daily-report
ln -s ~/daily-report/skills/daily-report  ~/.codex/skills/daily-report
```

放在别的路径，需要告诉 Skill 包根在哪：

```bash
export DAILY_REPORT_PACKAGE=/your/path/to/daily-report
```

想发飞书还需要装并登录 [`lark-cli`](https://github.com/larksuite/lark-openapi-sdk-cli)；只落盘不发的话无需。

## 使用

在客户端对话里，`cd` 到任意 git 仓库目录，说：

> 写今天的日报

Skill 会：

1. 抓取今日 commits（含 merge）
2. 读取可选备注 `~/.dailyreport/notes/<repo>/YYYY-MM-DD.md`
3. 用中文归纳为三段草稿并展示给你
4. 等你调整，确认后落盘到 `~/.dailyreport/reports/<repo>/YYYY-MM-DD.md`
5. 询问发送目标（飞书群 `oc_xxx` 或个人 `ou_xxx`），确认后才发

**未经确认永远不会发送**。

### 多仓场景

如果你在一个同时包含多个独立 git 仓库的工作目录下（例如 `~/Documents/company/` 下放了十几个项目，今天在其中几个里各有提交），直接说：

> 帮我写今天所有仓库的日报

Skill 会扫描一级子目录，只纳入今日有提交的仓库，归纳成一份综合日报：

- 「今日工作」按仓库分三级标题
- 「问题与风险」和「明日计划」跨仓合并，用 `[仓库名]` 前缀标注来源
- 落盘到 `~/.dailyreport/reports/_workspace_<目录名>/YYYY-MM-DD.md`
- 备注文件位置：`~/.dailyreport/notes/_workspace_<目录名>/YYYY-MM-DD.md`

## 备注格式（可选）

提前在 `~/.dailyreport/notes/<repo>/YYYY-MM-DD.md` 写 commit 里看不到的信息（会议、口头讨论、风险判断），它们会覆盖/补充 Skill 从 commit 归纳的结果：

```markdown
## 今日工作
- 和 X 口头对齐了 Y 方案

## 问题与风险
- Z 模块上线后观察到异常指标

## 明日计划
- 推进 W
```

三个标题必须用这三个固定名字才会被识别；标题外的内容归入「今日工作」。

## 产物位置

```
~/.dailyreport/
├── reports/<repo-name>/YYYY-MM-DD.md
└── notes/<repo-name>/YYYY-MM-DD.md
```

`<repo-name>` 取自 `git rev-parse --show-toplevel` 的 basename。

## License

MIT
