# 项目计划：{{project_name}}

## 项目概述
- **项目名称**：{{project_name}}
- **创建时间**：{{created_at}}
- **预计完成时间**：{{estimated_completion}}
- **负责人**：{{project_owner}}
- **状态**：{{project_status}}

## 项目目标
{{project_goals}}

## 成功标准
{{success_criteria}}

## 任务分解

### 阶段1：准备阶段
{{phase1_tasks}}

### 阶段2：执行阶段
{{phase2_tasks}}

### 阶段3：测试与交付
{{phase3_tasks}}

## 时间线
```mermaid
gantt
    title {{project_name}} 时间线
    dateFormat  YYYY-MM-DD
    section 准备阶段
    需求分析     :a1, {{start_date}}, 3d
    技术选型     :a2, after a1, 2d
    环境搭建     :a3, after a2, 2d
    
    section 执行阶段
    核心功能开发 :b1, after a3, 5d
    界面开发     :b2, after b1, 4d
    集成测试     :b3, after b2, 3d
    
    section 交付阶段
    用户测试     :c1, after b3, 3d
    文档编写     :c2, after c1, 2d
    部署上线     :c3, after c2, 2d
```

## 资源需求
- **人力资源**：{{human_resources}}
- **技术资源**：{{technical_resources}}
- **时间资源**：{{time_resources}}
- **预算**：{{budget}}

## 风险与应对
| 风险描述 | 可能性 | 影响 | 应对措施 |
|---------|--------|------|----------|
| {{risk1}} | {{prob1}} | {{impact1}} | {{mitigation1}} |
| {{risk2}} | {{prob2}} | {{impact2}} | {{mitigation2}} |
| {{risk3}} | {{prob3}} | {{impact3}} | {{mitigation3}} |

## 沟通计划
- **进度汇报**：{{report_frequency}}
- **会议安排**：{{meeting_schedule}}
- **沟通渠道**：{{communication_channels}}

## 附录
- 详细需求文档
- 技术架构图
- 测试计划
- 部署 checklist
