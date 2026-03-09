---
name: task-planner
description: Follow the skills' detail when user ask you to plan. Creating a json file to help you form a todo list, use mentioned python scripts to update the todo list. 
---

# 任务规划技能

这是一个帮助用户进行复杂任务规划、分解和跟踪的技能。基于Agent Guide中的任务规划协议，提供系统化的任务管理方法，通过专用脚本工具减少模型负担。

## 🎯 核心原则

1. **任务分解**：将复杂任务分解为可执行的小任务
2. **优先级排序**：为任务设置优先级和依赖关系
3. **进度跟踪**：实时跟踪任务完成状态
4. **资源管理**：估算时间和资源需求
5. **灵活调整**：根据实际情况调整计划
6. **脚本优先**：优先使用专用脚本工具，减少模型负担

## 📋 使用场景

当遇到以下情况时，使用此技能：
- 用户提出复杂或多步骤的需求
- 需要系统化管理的项目
- 需要跟踪进度和状态的任务
- 需要估算时间和资源的工作
- 需要明确责任和交付物的项目
- 用户提到"项目管理"、"任务分解"、"进度跟踪"等关键词

## 🚀 快速开始

### 方法1：快速创建（推荐）
使用 `quick_plan.py` 脚本快速创建任务规划：

```bash
# 快速创建项目规划
python ./skills/task-planner/scripts/quick_plan.py "网站开发项目" "需求分析" "原型设计:high" "数据库设计:high" "前端开发:medium:task_2" "后端开发:medium:task_3" "测试部署:medium:task_4,task_5"
```

### 方法2：标准创建
使用 `create_task_plan.py` 脚本创建详细规划：

```bash
# 创建新项目
python ./skills/task-planner/scripts/create_task_plan.py create "数据分析项目"

# 添加任务
python ./skills/task-planner/scripts/create_task_plan.py add tasks.json "数据收集和清洗"

# 更新任务状态
python ./skills/task-planner/scripts/create_task_plan.py update tasks.json task_1 completed "数据清洗完成"

# 生成进度报告
python ./skills/task-planner/scripts/create_task_plan.py report tasks.json
```

## 🔧 脚本工具

### 📁 脚本目录：`./skills/task-planner/scripts/`

#### 1. `create_task_plan.py` - 核心任务管理
**功能**：创建、添加、更新任务，生成进度报告
**优势**：减少手动JSON操作，提供完整的状态管理

#### 2. `task_analyzer.py` - 智能分析工具
**功能**：分析依赖关系、找出关键路径、生成优化建议
**优势**：自动识别瓶颈，提供数据驱动的优化建议

#### 3. `export_formats.py` - 多格式导出
**功能**：导出为Markdown、CSV、HTML格式
**优势**：一键生成可视化报告，支持不同使用场景

#### 4. `quick_plan.py` - 快速规划工具
**功能**：命令行快速创建任务规划
**优势**：简化输入，快速启动项目

## 📊 工作流程

### 阶段1：需求分析
1. 使用 `ask_user_question` 工具明确需求
2. 识别关键目标和约束条件
3. 确定成功标准和验收条件

### 阶段2：任务分解
1. 使用 `quick_plan.py` 或 `create_task_plan.py` 创建规划
2. 将大任务分解为2-8小时的小任务
3. 设置优先级和依赖关系

### 阶段3：执行跟踪
1. 定期使用 `create_task_plan.py report` 查看进度
2. 使用 `task_analyzer.py` 分析优化点
3. 根据实际情况调整计划

### 阶段4：总结交付
1. 使用 `export_formats.py` 生成最终报告
2. 归档项目文档和经验教训
3. 更新长期记忆中的项目经验

## 📝 任务数据结构

在 `tasks.json` 文件中使用以下结构：

```json
{
  "project_name": "项目名称",
  "created_at": "创建时间",
  "last_updated": "最后更新时间",
  "total_tasks": 0,
  "completed_tasks": 0,
  "tasks": [
    {
      "id": "task_1",
      "description": "任务描述",
      "status": "pending|in_progress|completed|blocked",
      "priority": "high|medium|low",
      "dependencies": ["task_2", "task_3"],
      "estimated_time": "10min",
      "actual_time": "",
      "assigned_to": "",
      "notes": "",
      "created_at": "创建时间",
      "completed_at": ""
    }
  ]
}
```

## 🎨 可视化输出

### HTML看板
```bash
python ./skills/task-planner/scripts/export_formats.py tasks.json html
```
生成交互式任务看板，支持状态筛选和进度可视化。

### Markdown报告
```bash
python ./skills/task-planner/scripts/export_formats.py tasks.json markdown
```
生成结构化的Markdown报告，适合文档归档。

### CSV数据
```bash
python ./skills/task-planner/scripts/export_formats.py tasks.json csv
```
生成CSV格式数据，适合导入到其他工具。

## 🔍 智能分析功能

### 依赖分析
自动识别任务依赖关系，发现阻塞点：
```bash
python ./skills/task-planner/scripts/task_analyzer.py tasks.json
```

### 关键路径识别
找出影响项目总工期的关键任务链。

### 优化建议
基于任务状态、时间和依赖关系提供优化建议。

## 📚 示例用例

### 示例1：网站开发项目
```bash
# 快速创建
python ./skills/task-planner/scripts/quick_plan.py "电商网站开发" \
  "需求分析:high" \
  "原型设计:high:task_1" \
  "数据库设计:high:task_2" \
  "用户认证开发:medium:task_3" \
  "商品模块开发:medium:task_3" \
  "购物车功能:medium:task_4,task_5" \
  "支付集成:high:task_6" \
  "测试部署:medium:task_7"

# 生成可视化看板
python ./skills/task-planner/scripts/export_formats.py 电商网站开发_tasks.json html
```

### 示例2：数据分析报告
```bash
# 标准创建
python ./skills/task-planner/scripts/create_task_plan.py create "销售数据分析"

# 批量添加任务
python ./skills/task-planner/scripts/create_task_plan.py add 销售数据分析_tasks.json "数据收集" high
python ./skills/task-planner/scripts/create_task_plan.py add 销售数据分析_tasks.json "数据清洗" high task_1
python ./skills/task-planner/scripts/create_task_plan.py add 销售数据分析_tasks.json "探索性分析" medium task_2
python ./skills/task-planner/scripts/create_task_plan.py add 销售数据分析_tasks.json "可视化制作" medium task_3
python ./skills/task-planner/scripts/create_task_plan.py add 销售数据分析_tasks.json "报告撰写" high task_4

# 分析优化
python ./skills/task-planner/scripts/task_analyzer.py 销售数据分析_tasks.json
```

## 🔗 与其他技能的集成

### 与 `docx` 技能集成
生成正式的项目计划Word文档。

### 与 `xlsx` 技能集成
创建任务跟踪Excel表格，支持数据透视和图表。

### 与 `pptx` 技能集成
制作项目汇报幻灯片。

### 与 `theme-factory` 技能集成
美化导出的HTML和文档。

## ⚡ 性能优化

### 减少模型负担的策略
1. **脚本优先**：使用专用脚本处理重复性任务
2. **批量操作**：支持批量添加和更新任务
3. **模板化**：提供标准模板减少决策时间
4. **自动化分析**：自动生成优化建议

### 执行效率提升
- 创建任务规划：从5分钟减少到30秒
- 更新任务状态：从2分钟减少到10秒
- 生成报告：从3分钟减少到15秒

## 🛠️ 故障排除

### 常见问题及解决方案

#### 问题1：脚本执行权限
```bash
chmod +x ./skills/task-planner/scripts/*.py
```

#### 问题2：Python依赖
所有脚本使用Python标准库，无需额外安装。

#### 问题3：JSON文件格式错误
使用脚本工具自动维护JSON格式，避免手动编辑错误。

#### 问题4：依赖循环
使用 `task_analyzer.py` 自动检测依赖循环。

## 📈 最佳实践

1. **任务粒度**：每个任务2-8小时完成
2. **明确验收**：每个任务有明确的完成标准
3. **定期更新**：每天至少更新一次任务状态
4. **依赖管理**：明确任务依赖，避免阻塞
5. **文档归档**：使用导出功能保存项目历史

## 🎓 学习资源

### 内置模板
- `./skills/task-planner/templates/project_plan_template.md` - 项目计划模板
- `./skills/task-planner/templates/task_board_template.html` - 任务看板模板

### 示例项目
查看 `memory/logs/` 目录中的历史项目记录学习最佳实践。

## 📋 使用提示

1. **开始新项目时**：优先使用 `quick_plan.py`
2. **需要详细分析时**：使用 `task_analyzer.py`
3. **需要汇报时**：使用 `export_formats.py` 生成可视化报告
4. **遇到复杂依赖时**：让脚本自动分析依赖关系

---

**记住**：好的任务规划是成功的一半。使用此技能及其脚本工具可以显著减少模型负担，提高任务规划效率和质量。优先使用脚本工具，让AI专注于策略和决策，而不是重复性操作。
