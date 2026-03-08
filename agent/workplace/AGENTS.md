# Agent Guide

## 技能使用协议 (SKILL PROTOCAL) 
你可以使用技能来协助用户完成任务。
你拥有一个技能列表 (SKILL_SNAPSHOT), 其中列出了你可以使用的能力及其定义文件的位置。
**你需要优先使用技能来帮助用户解决问题!**

**当你要使用某个技能的时候, 必须严格遵循以下步骤:**
- 1. 第一步永远是使用 `read_file` 工具读取技能对应的 `location` 路径下的 Markdown 文件。 
- 2. 仔细阅读 Markdown 中的内容、步骤、和调用示例 。
- 3. 根据文件中的指示, 结合你内置的 Core Tools (terminal, python_repl, fetch_url, ask_user_question, read_file) 来执行具体任务。

**禁止**直接猜测技能的参数和使用方法， 必须先读取对应的Markdown文件。

## 记忆协议 (MEMORT PROTOCAL) 

### 长期记忆
- 文件位置 `memory/MEMORY.md` 
- 当对话中出现长期值得记忆的信息时 (例如**用户偏好**, **重要决策**), 使用 `terminal` 工具将内容 **追加** 到MEMORY.md 

### 任务规划 
- 如果用户的需求很复杂或者你认为该需求需要县进行任务规划, 请你**必须使用 `task-planner` 技能** 帮助你解决需求。 

### 会话日志 

- 文件位置: `memory/logs/YYYY-MM-DD.md`
- 每日自动归档对话摘要 
- 也可以用于任务规划记录

### 记忆读取
- 在回答问题之前, 可以检查 `memory/MEMORY.md` 中
- 优先使用已经记录的用户偏好
