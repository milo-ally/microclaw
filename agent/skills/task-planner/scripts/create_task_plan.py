#!/usr/bin/env python3
"""
任务规划创建脚本
自动创建任务规划JSON文件
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

def create_task_plan(project_name: str, tasks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    创建任务规划数据结构
    
    Args:
        project_name: 项目名称
        tasks: 初始任务列表
    
    Returns:
        任务规划数据结构
    """
    current_time = datetime.now().isoformat()
    
    plan = {
        "project_name": project_name,
        "created_at": current_time,
        "last_updated": current_time,
        "total_tasks": 0,
        "completed_tasks": 0,
        "estimated_completion": "",
        "project_owner": "",
        "project_status": "planning",
        "tasks": tasks or []
    }
    
    if tasks:
        plan["total_tasks"] = len(tasks)
        plan["completed_tasks"] = sum(1 for task in tasks if task.get("status") == "completed")
    
    return plan

def save_task_plan(plan: Dict[str, Any], filename: str = "tasks.json") -> None:
    """
    保存任务规划到文件
    
    Args:
        plan: 任务规划数据
        filename: 文件名
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    print(f"✅ 任务规划已保存到 {filename}")

def add_task(plan: Dict[str, Any], task_description: str, 
             priority: str = "medium", dependencies: List[str] = None,
             estimated_time: str = "2h") -> Dict[str, Any]:
    """
    添加新任务到规划中
    
    Args:
        plan: 任务规划数据
        task_description: 任务描述
        priority: 优先级 (high/medium/low)
        dependencies: 依赖任务ID列表
        estimated_time: 预估时间
    
    Returns:
        更新后的任务规划
    """
    task_id = f"task_{len(plan['tasks']) + 1}"
    
    task = {
        "id": task_id,
        "description": task_description,
        "status": "pending",
        "priority": priority,
        "dependencies": dependencies or [],
        "estimated_time": estimated_time,
        "actual_time": "",
        "assigned_to": "",
        "notes": "",
        "created_at": datetime.now().isoformat(),
        "completed_at": ""
    }
    
    plan["tasks"].append(task)
    plan["total_tasks"] = len(plan["tasks"])
    plan["last_updated"] = datetime.now().isoformat()
    
    print(f"✅ 已添加任务: {task_id} - {task_description}")
    return plan

def update_task_status(plan: Dict[str, Any], task_id: str, 
                       status: str, notes: str = "") -> Dict[str, Any]:
    """
    更新任务状态
    
    Args:
        plan: 任务规划数据
        task_id: 任务ID
        status: 新状态 (pending/in_progress/completed/blocked)
        notes: 备注信息
    
    Returns:
        更新后的任务规划
    """
    for task in plan["tasks"]:
        if task["id"] == task_id:
            old_status = task["status"]
            task["status"] = status
            task["notes"] = notes if notes else task.get("notes", "")
            
            if status == "completed":
                task["completed_at"] = datetime.now().isoformat()
                plan["completed_tasks"] = sum(1 for t in plan["tasks"] if t["status"] == "completed")
            
            plan["last_updated"] = datetime.now().isoformat()
            print(f"✅ 任务 {task_id} 状态已更新: {old_status} -> {status}")
            break
    else:
        print(f"❌ 未找到任务: {task_id}")
    
    return plan

def generate_progress_report(plan: Dict[str, Any]) -> str:
    """
    生成进度报告
    
    Args:
        plan: 任务规划数据
    
    Returns:
        进度报告文本
    """
    completed = plan["completed_tasks"]
    total = plan["total_tasks"]
    progress = (completed / total * 100) if total > 0 else 0
    
    report_lines = [
        f"📊 项目进度报告: {plan['project_name']}",
        f"📅 创建时间: {plan['created_at']}",
        f"🔄 最后更新: {plan['last_updated']}",
        f"📈 总体进度: {completed}/{total} ({progress:.1f}%)",
        "",
        "📋 任务状态概览:"
    ]
    
    # 按状态分组
    status_groups = {}
    for task in plan["tasks"]:
        status = task["status"]
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(task)
    
    status_display = {
        "pending": "⏳ 待处理",
        "in_progress": "🚧 进行中", 
        "completed": "✅ 已完成",
        "blocked": "🚫 已阻塞"
    }
    
    for status, display in status_display.items():
        if status in status_groups:
            tasks = status_groups[status]
            report_lines.append(f"\n{display} ({len(tasks)}个):")
            for task in tasks:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task["priority"], "⚪")
                report_lines.append(f"  {priority_emoji} [{task['id']}] {task['description']}")
    
    # 阻塞任务依赖分析
    blocked_tasks = [t for t in plan["tasks"] if t["status"] == "blocked"]
    if blocked_tasks:
        report_lines.append("\n⚠️  阻塞任务分析:")
        for task in blocked_tasks:
            if task["dependencies"]:
                deps = ", ".join(task["dependencies"])
                report_lines.append(f"  🚫 {task['id']} 等待: {deps}")
    
    return "\n".join(report_lines)

def main():
    """命令行主函数"""
    if len(sys.argv) < 2:
        print("用法: python create_task_plan.py <命令> [参数]")
        print("命令:")
        print("  create <项目名称> - 创建新项目")
        print("  add <项目文件> <任务描述> - 添加任务")
        print("  update <项目文件> <任务ID> <状态> - 更新任务状态")
        print("  report <项目文件> - 生成进度报告")
        return
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 3:
            print("错误: 需要项目名称")
            return
        project_name = sys.argv[2]
        plan = create_task_plan(project_name)
        save_task_plan(plan)
        
    elif command == "add":
        if len(sys.argv) < 4:
            print("错误: 需要项目文件和任务描述")
            return
        filename = sys.argv[2]
        task_desc = sys.argv[3]
        
        with open(filename, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        
        priority = sys.argv[4] if len(sys.argv) > 4 else "medium"
        plan = add_task(plan, task_desc, priority)
        save_task_plan(plan, filename)
        
    elif command == "update":
        if len(sys.argv) < 5:
            print("错误: 需要项目文件、任务ID和状态")
            return
        filename = sys.argv[2]
        task_id = sys.argv[3]
        status = sys.argv[4]
        notes = sys.argv[5] if len(sys.argv) > 5 else ""
        
        with open(filename, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        
        plan = update_task_status(plan, task_id, status, notes)
        save_task_plan(plan, filename)
        
    elif command == "report":
        if len(sys.argv) < 3:
            print("错误: 需要项目文件")
            return
        filename = sys.argv[2]
        
        with open(filename, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        
        report = generate_progress_report(plan)
        print(report)
        
    else:
        print(f"未知命令: {command}")

if __name__ == "__main__":
    main()
