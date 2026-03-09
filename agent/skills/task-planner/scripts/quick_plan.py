#!/usr/bin/env python3
"""
快速任务规划脚本
简化版的任务规划创建工具
"""

import json
import sys
from datetime import datetime

def quick_create(project_name, tasks_list):
    """
    快速创建任务规划
    
    Args:
        project_name: 项目名称
        tasks_list: 任务描述列表，格式: ["任务1", "任务2:high", "任务3:medium:task_1"]
    
    Returns:
        任务规划数据
    """
    current_time = datetime.now().isoformat()
    
    plan = {
        "project_name": project_name,
        "created_at": current_time,
        "last_updated": current_time,
        "total_tasks": len(tasks_list),
        "completed_tasks": 0,
        "tasks": []
    }
    
    for i, task_desc in enumerate(tasks_list, 1):
        # 解析任务描述
        parts = task_desc.split(":")
        description = parts[0].strip()
        
        # 默认值
        priority = "medium"
        dependencies = []
        
        if len(parts) > 1:
            priority_part = parts[1].strip().lower()
            if priority_part in ["high", "medium", "low"]:
                priority = priority_part
        
        if len(parts) > 2:
            deps_part = parts[2].strip()
            if deps_part:
                dependencies = [dep.strip() for dep in deps_part.split(",")]
        
        task = {
            "id": f"task_{i}",
            "description": description,
            "status": "pending",
            "priority": priority,
            "dependencies": dependencies,
            "estimated_time": "5min",
            "actual_time": "",
            "assigned_to": "",
            "notes": "",
            "created_at": current_time,
            "completed_at": ""
        }
        
        plan["tasks"].append(task)
    
    return plan

def main():
    """命令行主函数"""
    if len(sys.argv) < 3:
        print("快速任务规划工具")
        print("用法: python quick_plan.py <项目名称> <任务1> [任务2] [任务3] ...")
        print("\n任务格式:")
        print("  简单: '需求分析'")
        print("  带优先级: '核心功能开发:high'")
        print("  带依赖: '测试阶段:medium:task_1,task_2'")
        print("\n示例:")
        print("  python quick_plan.py '网站开发' '需求分析' '设计原型:high' '开发核心功能:high:task_2'")
        return
    
    project_name = sys.argv[1]
    tasks_list = sys.argv[2:]
    
    plan = quick_create(project_name, tasks_list)
    
    # 保存文件
    filename = f"{project_name.replace(' ', '_')}_tasks.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 快速任务规划创建完成!")
    print(f"📁 文件: {filename}")
    print(f"📋 项目: {project_name}")
    print(f"📊 任务数: {len(tasks_list)}")
    print("\n📝 创建的任务:")
    for task in plan["tasks"]:
        deps = f" (依赖: {', '.join(task['dependencies'])})" if task["dependencies"] else ""
        print(f"  {task['id']}: {task['description']} [{task['priority']}]{deps}")
    
    print(f"\n💡 下一步:")
    print(f"  查看进度: python create_task_plan.py report {filename}")
    print(f"  分析规划: python task_analyzer.py {filename}")
    print(f"  导出HTML: python export_formats.py {filename} html")

if __name__ == "__main__":
    main()
