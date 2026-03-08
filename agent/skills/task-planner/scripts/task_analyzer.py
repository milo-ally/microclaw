#!/usr/bin/env python3
"""
任务分析脚本
分析任务规划，提供优化建议和依赖分析
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Any

def analyze_dependencies(plan: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    分析任务依赖关系
    
    Args:
        plan: 任务规划数据
    
    Returns:
        依赖分析结果
    """
    tasks = plan["tasks"]
    
    # 构建依赖图
    dependency_graph = {}
    for task in tasks:
        task_id = task["id"]
        dependency_graph[task_id] = {
            "deps": task.get("dependencies", []),
            "status": task["status"],
            "blocked_by": []
        }
    
    # 找出阻塞关系
    for task_id, info in dependency_graph.items():
        for dep in info["deps"]:
            if dep in dependency_graph:
                dep_status = dependency_graph[dep]["status"]
                if dep_status != "completed":
                    info["blocked_by"].append(dep)
    
    return dependency_graph

def find_critical_path(plan: Dict[str, Any]) -> List[str]:
    """
    找出关键路径
    
    Args:
        plan: 任务规划数据
    
    Returns:
        关键路径任务ID列表
    """
    tasks = plan["tasks"]
    
    # 简单的关键路径分析（基于依赖深度）
    task_depths = {}
    
    def calculate_depth(task_id: str, visited: set = None) -> int:
        if visited is None:
            visited = set()
        
        if task_id in visited:
            return 0
        
        visited.add(task_id)
        
        # 找到任务
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return 0
        
        max_depth = 0
        for dep in task.get("dependencies", []):
            depth = calculate_depth(dep, visited.copy())
            max_depth = max(max_depth, depth)
        
        return max_depth + 1
    
    for task in tasks:
        task_depths[task["id"]] = calculate_depth(task["id"])
    
    # 按深度排序
    sorted_tasks = sorted(task_depths.items(), key=lambda x: x[1], reverse=True)
    
    # 返回深度最大的任务链（简化版关键路径）
    critical_path = []
    if sorted_tasks:
        max_depth = sorted_tasks[0][1]
        critical_path = [task_id for task_id, depth in sorted_tasks if depth == max_depth]
    
    return critical_path

def analyze_task_distribution(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析任务分布
    
    Args:
        plan: 任务规划数据
    
    Returns:
        分布分析结果
    """
    tasks = plan["tasks"]
    
    analysis = {
        "by_status": {},
        "by_priority": {},
        "time_estimates": {
            "total_estimated": 0,
            "completed_estimated": 0,
            "remaining_estimated": 0
        }
    }
    
    # 状态分布
    for task in tasks:
        status = task["status"]
        analysis["by_status"][status] = analysis["by_status"].get(status, 0) + 1
        
        priority = task["priority"]
        analysis["by_priority"][priority] = analysis["by_priority"].get(priority, 0) + 1
        
        # 时间估算分析
        est_time = task["estimated_time"]
        if est_time:
            try:
                if est_time.endswith("h"):
                    hours = float(est_time[:-1])
                elif est_time.endswith("d"):
                    hours = float(est_time[:-1]) * 8
                else:
                    hours = float(est_time)
                
                analysis["time_estimates"]["total_estimated"] += hours
                if status == "completed":
                    analysis["time_estimates"]["completed_estimated"] += hours
                else:
                    analysis["time_estimates"]["remaining_estimated"] += hours
            except ValueError:
                pass
    
    return analysis

def generate_optimization_suggestions(plan: Dict[str, Any]) -> List[str]:
    """
    生成优化建议
    
    Args:
        plan: 任务规划数据
    
    Returns:
        优化建议列表
    """
    suggestions = []
    tasks = plan["tasks"]
    
    # 检查没有依赖的阻塞任务
    blocked_without_deps = [
        task for task in tasks 
        if task["status"] == "blocked" and not task.get("dependencies")
    ]
    if blocked_without_deps:
        suggestions.append("⚠️  发现阻塞任务但没有明确依赖，请检查阻塞原因")
    
    # 检查长时间进行中的任务
    current_time = datetime.now()
    for task in tasks:
        if task["status"] == "in_progress":
            created_time = datetime.fromisoformat(task["created_at"])
            days_diff = (current_time - created_time).days
            if days_diff > 7:
                suggestions.append(f"⏰ 任务 {task['id']} 已进行 {days_diff} 天，考虑重新评估或分解")
    
    # 检查高优先级但未开始的任务
    high_priority_pending = [
        task for task in tasks 
        if task["priority"] == "high" and task["status"] == "pending"
    ]
    if high_priority_pending:
        suggestions.append("🚨 有高优先级任务尚未开始，建议优先处理")
    
    # 检查依赖循环
    dependency_graph = analyze_dependencies(plan)
    for task_id, info in dependency_graph.items():
        # 简单的循环检测（深度优先搜索）
        def has_cycle(current: str, visited: set) -> bool:
            if current in visited:
                return True
            visited.add(current)
            for dep in dependency_graph.get(current, {}).get("deps", []):
                if has_cycle(dep, visited.copy()):
                    return True
            return False
        
        if has_cycle(task_id, set()):
            suggestions.append(f"🔄 检测到可能的依赖循环，涉及任务 {task_id}")
            break
    
    # 检查任务粒度
    for task in tasks:
        est_time = task["estimated_time"]
        if est_time:
            try:
                if est_time.endswith("h"):
                    hours = float(est_time[:-1])
                elif est_time.endswith("d"):
                    hours = float(est_time[:-1]) * 8
                else:
                    hours = float(est_time)
                
                if hours > 16:  # 超过2天
                    suggestions.append(f"📏 任务 {task['id']} 预估时间较长 ({est_time})，考虑进一步分解")
            except ValueError:
                pass
    
    return suggestions

def main():
    """命令行主函数"""
    if len(sys.argv) < 2:
        print("用法: python task_analyzer.py <项目文件>")
        return
    
    filename = sys.argv[1]
    
    with open(filename, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    
    print(f"📊 项目分析报告: {plan['project_name']}")
    print("=" * 50)
    
    # 依赖分析
    print("\n🔗 依赖关系分析:")
    dep_graph = analyze_dependencies(plan)
    blocked_tasks = [tid for tid, info in dep_graph.items() if info["blocked_by"]]
    if blocked_tasks:
        print(f"  阻塞任务: {len(blocked_tasks)}个")
        for task_id in blocked_tasks:
            blockers = dep_graph[task_id]["blocked_by"]
            print(f"    {task_id} ← 等待: {', '.join(blockers)}")
    else:
        print("  无阻塞任务")
    
    # 关键路径
    print("\n🎯 关键路径分析:")
    critical_path = find_critical_path(plan)
    if critical_path:
        print(f"  关键路径任务: {len(critical_path)}个")
        for task_id in critical_path:
            task = next(t for t in plan["tasks"] if t["id"] == task_id)
            print(f"    {task_id}: {task['description']}")
    else:
        print("  无法确定关键路径")
    
    # 任务分布
    print("\n📈 任务分布统计:")
    distribution = analyze_task_distribution(plan)
    
    print("  状态分布:")
    for status, count in distribution["by_status"].items():
        status_display = {
            "pending": "待处理",
            "in_progress": "进行中",
            "completed": "已完成",
            "blocked": "已阻塞"
        }.get(status, status)
        print(f"    {status_display}: {count}个")
    
    print("\n  优先级分布:")
    for priority, count in distribution["by_priority"].items():
        priority_display = {
            "high": "高",
            "medium": "中", 
            "low": "低"
        }.get(priority, priority)
        print(f"    {priority_display}优先级: {count}个")
    
    # 时间分析
    print("\n⏱️  时间估算:")
    time_est = distribution["time_estimates"]
    print(f"   总预估时间: {time_est['total_estimated']:.1f}小时")
    print(f"   已完成预估: {time_est['completed_estimated']:.1f}小时")
    print(f"   剩余预估: {time_est['remaining_estimated']:.1f}小时")
    
    # 优化建议
    print("\n💡 优化建议:")
    suggestions = generate_optimization_suggestions(plan)
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion}")
    else:
        print("  任务规划良好，无优化建议")

if __name__ == "__main__":
    main()
