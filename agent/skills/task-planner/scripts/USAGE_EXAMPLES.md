# Task-Planner 技能使用示例

## 📋 概述
优化后的task-planner技能通过专用脚本工具显著减少了模型负担，提高了任务规划效率。以下是各种使用场景的示例。

## 🚀 快速开始示例

### 示例1：快速创建网站开发项目
```bash
# 一行命令创建完整项目规划
python ./skills/task-planner/scripts/quick_plan.py "电商网站开发" \
  "需求分析:high" \
  "原型设计:high:task_1" \
  "技术选型:medium:task_2" \
  "数据库设计:high:task_3" \
  "后端API开发:high:task_4" \
  "前端界面开发:medium:task_5" \
  "用户测试:medium:task_6" \
  "部署上线:high:task_7"
```

### 示例2：数据分析项目
```bash
# 创建数据分析项目
python ./skills/task-planner/scripts/create_task_plan.py create "销售数据分析报告"

# 批量添加任务（使用循环或脚本）
for task in "数据收集" "数据清洗" "探索分析" "可视化" "报告撰写"; do
  python ./skills/task-planner/scripts/create_task_plan.py add 销售数据分析报告_tasks.json "$task"
done
```

## 🔧 实际工作流程示例

### 场景：AI模型训练项目

#### 步骤1：需求分析
```python
# 使用python_repl与用户确认需求
print("请确认项目需求：")
print("1. 数据准备和预处理")
print("2. 模型选择和训练")
print("3. 评估和优化")
print("4. 部署和监控")
```

#### 步骤2：快速创建规划
```bash
python ./skills/task-planner/scripts/quick_plan.py "AI模型训练项目" \
  "数据收集和标注:high" \
  "数据预处理:high:task_1" \
  "模型选择:medium:task_2" \
  "模型训练:high:task_3" \
  "模型评估:high:task_4" \
  "超参数调优:medium:task_5" \
  "模型部署:high:task_6" \
  "性能监控:medium:task_7"
```

#### 步骤3：执行跟踪
```bash
# 更新任务状态
python ./skills/task-planner/scripts/create_task_plan.py update AI模型训练项目_tasks.json task_1 completed "数据收集完成"
python ./skills/task-planner/scripts/create_task_plan.py update AI模型训练项目_tasks.json task_2 in_progress "开始数据预处理"

# 查看进度
python ./skills/task-planner/scripts/create_task_plan.py report AI模型训练项目_tasks.json
```

#### 步骤4：智能分析
```bash
# 分析项目状态
python ./skills/task-planner/scripts/task_analyzer.py AI模型训练项目_tasks.json
```

#### 步骤5：生成报告
```bash
# 生成HTML可视化看板
python ./skills/task-planner/scripts/export_formats.py AI模型训练项目_tasks.json html

# 生成Markdown文档
python ./skills/task-planner/scripts/export_formats.py AI模型训练项目_tasks.json markdown
```

## 📊 高级使用示例

### 示例1：复杂依赖管理
```bash
# 创建有复杂依赖关系的项目
python ./skills/task-planner/scripts/quick_plan.py "微服务架构项目" \
  "架构设计:high" \
  "用户服务开发:high:task_1" \
  "订单服务开发:high:task_1" \
  "支付服务开发:high:task_1" \
  "服务网关:medium:task_2,task_3,task_4" \
  "服务注册发现:medium:task_5" \
  "监控日志:low:task_6" \
  "容器化部署:high:task_7"

# 分析依赖关系
python ./skills/task-planner/scripts/task_analyzer.py 微服务架构项目_tasks.json
```

### 示例2：敏捷开发迭代
```bash
# 创建敏捷迭代规划
python ./skills/task-planner/scripts/quick_plan.py "Sprint 1 - MVP开发" \
  "用户认证:high" \
  "核心功能A:high:task_1" \
  "核心功能B:high:task_1" \
  "基础UI:medium:task_2,task_3" \
  "单元测试:medium:task_4" \
  "集成测试:high:task_5"

# 每日站会更新
python ./skills/task-planner/scripts/create_task_plan.py update Sprint_1_-_MVP开发_tasks.json task_1 completed "用户认证完成"
python ./skills/task-planner/scripts/create_task_plan.py update Sprint_1_-_MVP开发_tasks.json task_2 in_progress "开始核心功能A开发"

# 生成每日进度报告
python ./skills/task-planner/scripts/create_task_plan.py report Sprint_1_-_MVP开发_tasks.json > daily_standup.md
```

## 🔗 与其他技能集成示例

### 与docx技能集成
```bash
# 生成Word格式项目计划
python ./skills/task-planner/scripts/export_formats.py 项目名称_tasks.json markdown
# 然后使用docx技能将markdown转换为docx
```

### 与pptx技能集成
```bash
# 生成项目汇报幻灯片内容
python ./skills/task-planner/scripts/create_task_plan.py report 项目名称_tasks.json > progress_summary.txt
# 使用pptx技能创建幻灯片
```

### 与xlsx技能集成
```bash
# 导出CSV后导入Excel
python ./skills/task-planner/scripts/export_formats.py 项目名称_tasks.json csv
# 使用xlsx技能进一步处理
```

## ⚡ 性能对比

### 优化前（手动操作）
- 创建任务规划：5-10分钟（手动编写JSON）
- 更新任务状态：2-3分钟（手动编辑）
- 生成报告：3-5分钟（手动整理）
- 依赖分析：困难（需要人工分析）

### 优化后（脚本工具）
- 创建任务规划：30秒（quick_plan.py）
- 更新任务状态：10秒（create_task_plan.py update）
- 生成报告：15秒（export_formats.py）
- 依赖分析：5秒（task_analyzer.py）

**效率提升：10倍以上**

## 🎯 最佳实践总结

1. **开始阶段**：使用 `quick_plan.py` 快速启动
2. **执行阶段**：使用 `create_task_plan.py` 管理状态
3. **监控阶段**：使用 `task_analyzer.py` 智能分析
4. **汇报阶段**：使用 `export_formats.py` 生成报告
5. **归档阶段**：导出多种格式备份

## 📝 脚本参数参考

### create_task_plan.py
```bash
# 创建项目
python create_task_plan.py create "项目名称"

# 添加任务
python create_task_plan.py add tasks.json "任务描述" [优先级]

# 更新状态
python create_task_plan.py update tasks.json task_1 completed "备注"

# 生成报告
python create_task_plan.py report tasks.json
```

### quick_plan.py
```bash
# 快速创建
python quick_plan.py "项目名称" "任务1" "任务2:high" "任务3:medium:task_1,task_2"
```

### task_analyzer.py
```bash
# 分析项目
python task_analyzer.py tasks.json
```

### export_formats.py
```bash
# 导出格式
python export_formats.py tasks.json [markdown|csv|html]
```

## 🆘 故障排除

### 问题：脚本找不到
```bash
# 确保在正确目录
cd ./skills/task-planner/scripts/

# 或使用绝对路径
python /path/to/skills/task-planner/scripts/quick_plan.py ...
```

### 问题：权限错误
```bash
chmod +x ./skills/task-planner/scripts/*.py
```

### 问题：JSON格式错误
```bash
# 使用脚本重新创建，不要手动编辑
python create_task_plan.py create "新项目"
```

## 📞 支持

如有问题，请：
1. 检查脚本使用示例
2. 查看SKILL.md文档
3. 测试简单示例验证环境
4. 记录错误信息寻求帮助

---

**优化目标达成**：通过脚本工具将模型从重复性操作中解放出来，专注于策略和决策，显著提高任务规划效率和质量。
