
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class DatabaseAnalyzer:
    def __init__(self):
        self.analysis_results = {}
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def analyze_students(self):
        """分析学生数据"""
        query = """
        SELECT 
            COUNT(*) as total_students,
            AVG(gpa) as avg_gpa,
            MIN(gpa) as min_gpa,
            MAX(gpa) as max_gpa,
            STDDEV(gpa) as std_gpa,
            COUNT(DISTINCT major) as distinct_majors,
            STRING_AGG(DISTINCT major, ', ') as majors_list
        FROM students
        """
        return query
    
    def analyze_professors(self):
        """分析教授数据"""
        query = """
        SELECT 
            COUNT(*) as total_professors,
            AVG(salary) as avg_salary,
            MIN(salary) as min_salary,
            MAX(salary) as max_salary,
            COUNT(DISTINCT department) as distinct_departments,
            STRING_AGG(DISTINCT department, ', ') as departments_list,
            AVG(EXTRACT(YEAR FROM AGE(CURRENT_DATE, hire_date))) as avg_years_of_service
        FROM professors
        """
        return query
    
    def analyze_courses(self):
        """分析课程数据"""
        query = """
        SELECT 
            COUNT(*) as total_courses,
            AVG(credits) as avg_credits,
            MIN(credits) as min_credits,
            MAX(credits) as max_credits,
            COUNT(DISTINCT department) as distinct_departments,
            STRING_AGG(DISTINCT department, ', ') as departments_list
        FROM courses
        """
        return query
    
    def analyze_enrollments(self):
        """分析选课数据"""
        query = """
        SELECT 
            COUNT(*) as total_enrollments,
            COUNT(DISTINCT student_id) as unique_students_enrolled,
            COUNT(DISTINCT course_id) as unique_courses_offered,
            AVG(CASE 
                WHEN grade = 'A' THEN 4.0
                WHEN grade = 'B' THEN 3.0
                WHEN grade = 'C' THEN 2.0
                WHEN grade = 'D' THEN 1.0
                WHEN grade = 'F' THEN 0.0
                ELSE NULL
            END) as avg_grade_score,
            COUNT(DISTINCT semester) as total_semesters,
            STRING_AGG(DISTINCT semester, ', ') as semesters_list
        FROM enrollments
        WHERE grade IS NOT NULL AND grade != 'W'
        """
        return query
    
    def analyze_grade_distribution(self):
        """分析成绩分布"""
        query = """
        SELECT 
            grade,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
        FROM enrollments
        WHERE grade IS NOT NULL AND grade != 'W'
        GROUP BY grade
        ORDER BY 
            CASE grade
                WHEN 'A' THEN 1
                WHEN 'B' THEN 2
                WHEN 'C' THEN 3
                WHEN 'D' THEN 4
                WHEN 'F' THEN 5
                ELSE 6
            END
        """
        return query
    
    def analyze_department_stats(self):
        """分析院系统计"""
        query = """
        SELECT 
            c.department,
            COUNT(DISTINCT c.course_id) as course_count,
            COUNT(DISTINCT e.student_id) as student_count,
            COUNT(e.enrollment_id) as enrollment_count,
            AVG(CASE 
                WHEN e.grade = 'A' THEN 4.0
                WHEN e.grade = 'B' THEN 3.0
                WHEN e.grade = 'C' THEN 2.0
                WHEN e.grade = 'D' THEN 1.0
                WHEN e.grade = 'F' THEN 0.0
                ELSE NULL
            END) as avg_grade_score
        FROM courses c
        LEFT JOIN enrollments e ON c.course_id = e.course_id
        GROUP BY c.department
        ORDER BY enrollment_count DESC
        """
        return query
    
    def analyze_student_enrollment_patterns(self):
        """分析学生选课模式"""
        query = """
        SELECT 
            s.student_id,
            s.first_name || ' ' || s.last_name as student_name,
            s.gpa,
            s.major,
            COUNT(e.enrollment_id) as courses_taken,
            AVG(CASE 
                WHEN e.grade = 'A' THEN 4.0
                WHEN e.grade = 'B' THEN 3.0
                WHEN e.grade = 'C' THEN 2.0
                WHEN e.grade = 'D' THEN 1.0
                WHEN e.grade = 'F' THEN 0.0
                ELSE NULL
            END) as avg_grade_score
        FROM students s
        LEFT JOIN enrollments e ON s.student_id = e.student_id
        GROUP BY s.student_id, s.first_name, s.last_name, s.gpa, s.major
        ORDER BY s.gpa DESC
        """
        return query
    
    def analyze_course_popularity(self):
        """分析课程受欢迎程度"""
        query = """
        SELECT 
            c.course_id,
            c.course_code,
            c.course_name,
            c.department,
            c.credits,
            COUNT(e.enrollment_id) as enrollment_count,
            AVG(CASE 
                WHEN e.grade = 'A' THEN 4.0
                WHEN e.grade = 'B' THEN 3.0
                WHEN e.grade = 'C' THEN 2.0
                WHEN e.grade = 'D' THEN 1.0
                WHEN e.grade = 'F' THEN 0.0
                ELSE NULL
            END) as avg_grade_score
        FROM courses c
        LEFT JOIN enrollments e ON c.course_id = e.course_id
        GROUP BY c.course_id, c.course_code, c.course_name, c.department, c.credits
        ORDER BY enrollment_count DESC
        """
        return query
    
    def generate_summary_report(self):
        """生成汇总报告"""
        queries = {
            "学生统计": self.analyze_students(),
            "教授统计": self.analyze_professors(),
            "课程统计": self.analyze_courses(),
            "选课统计": self.analyze_enrollments(),
            "成绩分布": self.analyze_grade_distribution(),
            "院系统计": self.analyze_department_stats(),
            "学生选课模式": self.analyze_student_enrollment_patterns(),
            "课程受欢迎程度": self.analyze_course_popularity()
        }
        
        return queries

# 创建分析器实例
analyzer = DatabaseAnalyzer()
queries = analyzer.generate_summary_report()

# 保存查询到文件
with open('database_analysis_queries.json', 'w', encoding='utf-8') as f:
    json.dump(queries, f, ensure_ascii=False, indent=2)

print("数据分析查询已生成并保存到 database_analysis_queries.json")
