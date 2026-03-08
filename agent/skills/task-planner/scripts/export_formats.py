#!/usr/bin/env python3
"""
任务规划导出脚本
将任务规划导出为不同格式
"""

import json
import sys
import csv
from datetime import datetime
from typing import Dict, List, Any

def export_to_markdown(plan: Dict[str, Any]) -> str:
    """
    导出为Markdown格式
    
    Args:
        plan: 任务规划数据
    
    Returns:
        Markdown格式文本
    """
    tasks = plan["tasks"]
    
    md_lines = [
        f"# 项目计划: {plan['project_name']}",
        "",
        f"**创建时间**: {plan['created_at']}",
        f"**最后更新**: {plan['last_updated']}",
        f"**进度**: {plan['completed_tasks']}/{plan['total_tasks']} 个任务",
        "",
        "## 任务列表",
        ""
    ]
    
    # 按状态分组
    status_groups = {}
    for task in tasks:
        status = task["status"]
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(task)
    
    status_order = ["pending", "in_progress", "completed", "blocked"]
    status_headers = {
        "pending": "⏳ 待处理",
        "in_progress": "🚧 进行中",
        "completed": "✅ 已完成", 
        "blocked": "🚫 已阻塞"
    }
    
    for status in status_order:
        if status in status_groups:
            md_lines.append(f"### {status_headers[status]}")
            md_lines.append("")
            
            for task in status_groups[status]:
                priority_symbol = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task["priority"], "⚪")
                
                md_lines.append(f"#### {priority_symbol} {task['id']}: {task['description']}")
                md_lines.append("")
                md_lines.append(f"- **状态**: {task['status']}")
                md_lines.append(f"- **优先级**: {task['priority']}")
                md_lines.append(f"- **预估时间**: {task['estimated_time']}")
                
                if task.get("dependencies"):
                    md_lines.append(f"- **依赖**: {', '.join(task['dependencies'])}")
                
                if task.get("notes"):
                    md_lines.append(f"- **备注**: {task['notes']}")
                
                if task.get("assigned_to"):
                    md_lines.append(f"- **负责人**: {task['assigned_to']}")
                
                md_lines.append(f"- **创建时间**: {task['created_at']}")
                
                if task["status"] == "completed" and task.get("completed_at"):
                    md_lines.append(f"- **完成时间**: {task['completed_at']}")
                
                md_lines.append("")
    
    return "\n".join(md_lines)

def export_to_csv(plan: Dict[str, Any]) -> str:
    """
    导出为CSV格式
    
    Args:
        plan: 任务规划数据
    
    Returns:
        CSV格式文本
    """
    tasks = plan["tasks"]
    
    # 创建CSV输出
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入标题行
    writer.writerow([
        "任务ID", "描述", "状态", "优先级", "预估时间",
        "实际时间", "依赖", "负责人", "备注", "创建时间", "完成时间"
    ])
    
    # 写入数据行
    for task in tasks:
        writer.writerow([
            task["id"],
            task["description"],
            task["status"],
            task["priority"],
            task["estimated_time"],
            task.get("actual_time", ""),
            ";".join(task.get("dependencies", [])),
            task.get("assigned_to", ""),
            task.get("notes", ""),
            task["created_at"],
            task.get("completed_at", "")
        ])
    
    return output.getvalue()

def export_to_html(plan: Dict[str, Any]) -> str:
    """
    导出为HTML格式
    
    Args:
        plan: 任务规划数据
    
    Returns:
        HTML格式文本
    """
    tasks = plan["tasks"]
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>项目计划 - {plan['project_name']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .task-board {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .column {{
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
        }}
        .column-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #ddd;
        }}
        .task-card {{
            background: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        .task-card.high {{ border-left-color: #e53e3e; }}
        .task-card.medium {{ border-left-color: #d69e2e; }}
        .task-card.low {{ border-left-color: #38a169; }}
        .task-card.completed {{ border-left-color: #38a169; opacity: 0.7; }}
        .task-id {{
            font-weight: bold;
            color: #667eea;
        }}
        .task-priority {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-right: 5px;
        }}
        .priority-high {{ background: #fed7d7; color: #c53030; }}
        .priority-medium {{ background: #feebc8; color: #d69e2e; }}
        .priority-low {{ background: #c6f6d5; color: #38a169; }}
        .task-deps {{
            font-size: 0.9em;
            color: #718096;
            margin-top: 5px;
        }}
        .progress-bar {{
            height: 10px;
            background: #e2e8f0;
            border-radius: 5px;
            margin: 20px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 5px;
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📋 {plan['project_name']}</h1>
        <p>创建时间: {plan['created_at']} | 最后更新: {plan['last_updated']}</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div>总任务数</div>
            <div class="stat-value">{plan['total_tasks']}</div>
        </div>
        <div class="stat-card">
            <div>已完成</div>
            <div class="stat-value">{plan['completed_tasks']}</div>
        </div>
        <div class="stat-card">
            <div>进行中</div>
            <div class="stat-value">{sum(1 for t in tasks if t['status'] == 'in_progress')}</div>
        </div>
        <div class="stat-card">
            <div>进度</div>
            <div class="stat-value">{int((plan['completed_tasks']/plan['total_tasks']*100) if plan['total_tasks'] > 0 else 0)}%</div>
        </div>
    </div>
    
    <div class="progress-bar">
        <div class="progress-fill" style="width: {(plan['completed_tasks']/plan['total_tasks']*100) if plan['total_tasks'] > 0 else 0}%"></div>
    </div>
    
    <div class="task-board">
"""
    
    # 按状态分组
    status_groups = {}
    for task in tasks:
        status = task["status"]
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(task)
    
    status_config = {
        "pending": {"title": "⏳ 待处理", "color": "#d69e2e"},
        "in_progress": {"title": "🚧 进行中", "color": "#3182ce"},
        "completed": {"title": "✅ 已完成", "color": "#38a169"},
        "blocked": {"title": "🚫 已阻塞", "color": "#e53e3e"}
    }
    
    for status, config in status_config.items():
        if status in status_groups:
            html += f"""
        <div class="column">
            <div class="column-title" style="color: {config['color']}">{config['title']} ({len(status_groups[status])})</div>
"""
            
            for task in status_groups[status]:
                priority_class = f"priority-{task['priority']}"
                priority_display = {"high": "高", "medium": "中", "low": "低"}.get(task["priority"], task["priority"])
                
                html += f"""
            <div class="task-card {task['priority']} {task['status']}">
                <div class="task-id">{task['id']}</div>
                <div>{task['description']}</div>
                <div>
                    <span class="task-priority {priority_class}">{priority_display}优先级</span>
                    <span>⏱️ {task['estimated_time']}</span>
                </div>
"""
                
                if task.get("dependencies"):
                    html += f"""
                <div class="task-deps">📎 依赖: {', '.join(task['dependencies'])}</div>
"""
                
                if task.get("assigned_to"):
                    html += f"""
                <div class="task-deps">👤 {task['assigned_to']}</div>
"""
                
                html += """
            </div>
"""
            
            html += """
        </div>
"""
    
    html += """
    </div>
    
    <script>
        // 简单的交互功能
        document.addEventListener('DOMContentLoaded', function() {
            const taskCards = document.querySelectorAll('.task-card');
            taskCards.forEach(card => {
                card.addEventListener('click', function() {
                    this.style.transform = 'translateY(-2px)';
                    this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                    setTimeout(() => {
                        this.style.transform = '';
                        this.style.boxShadow = '';
                    }, 200);
                });
            });
        });
    </script>
</body>
</html>
"""
    
    return html

def main():
    """命令行主函数"""
    if len(sys.argv) < 3:
        print("用法: python export_formats.py <项目文件> <格式>")
        print("格式: markdown, csv, html")
        return
    
    filename = sys.argv[1]
    format_type = sys.argv[2].lower()
    
    with open(filename, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    
    if format_type == "markdown":
        output = export_to_markdown(plan)
        output_file = f"{plan['project_name'].replace(' ', '_')}_plan.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"✅ Markdown文件已保存: {output_file}")
        
    elif format_type == "csv":
        output = export_to_csv(plan)
        output_file = f"{plan['project_name'].replace(' ', '_')}_tasks.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            f.write(output)
        print(f"✅ CSV文件已保存: {output_file}")
        
    elif format_type == "html":
        output = export_to_html(plan)
        output_file = f"{plan['project_name'].replace(' ', '_')}_dashboard.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"✅ HTML文件已保存: {output_file}")
        print(f"📂 用浏览器打开: file://{output_file}")
        
    else:
        print(f"❌ 不支持的格式: {format_type}")
        print("支持的格式: markdown, csv, html")

if __name__ == "__main__":
    main()
