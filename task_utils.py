import os
import datetime
import json
import traceback
from PySide6.QtWidgets import QMessageBox

from task_manager import Task


class TaskUtils:
    """Task-related utility functions for the FullAutoTab"""

    @staticmethod
    def load_tasks(task_manager, task_table, task_model_class, append_log_func):
        """Load all tasks and update the table"""
        try:
            tasks = task_manager.get_all_tasks()
            task_model = task_model_class(tasks)
            task_table.setModel(task_model)
            append_log_func(f"已加载 {len(tasks)} 个任务")
            return task_model
        except Exception as e:
            append_log_func(f"加载任务失败: {str(e)}")
            append_log_func(traceback.format_exc())
            return None

    @staticmethod
    def add_task(url, config, task_manager, task_model, append_log_func):
        """Add a new task to the list"""
        if not url.strip():
            QMessageBox.warning(None, "输入错误", "请输入视频URL或选择本地视频文件")
            return None

        try:
            # Create new task
            task = Task(
                url=url,
                status="待处理",
                created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                config=json.dumps(config) if config else "{}"
            )

            # Add to database
            task_id = task_manager.add_task(task)

            # Update table
            if task_model:
                task_model.appendTask(task)

            append_log_func(f"已添加任务 #{task_id}: {url}")
            return task_id
        except Exception as e:
            append_log_func(f"添加任务失败: {str(e)}")
            append_log_func(traceback.format_exc())
            return None

    @staticmethod
    def clear_tasks(task_manager, append_log_func):
        """Clear all tasks"""
        try:
            task_manager.clear_all_tasks()
            append_log_func("已清空所有任务")
            return True
        except Exception as e:
            append_log_func(f"清空任务失败: {str(e)}")
            return False

    @staticmethod
    def get_next_pending_task(task_manager, append_log_func):
        """Get the next pending task"""
        try:
            return task_manager.get_next_pending_task()
        except Exception as e:
            append_log_func(f"获取下一个待处理任务失败: {str(e)}")
            return None

    @staticmethod
    def update_task_status(task_id, task_manager, task_model, status, started_at=None,
                           completed_at=None, result="", output_path="", append_log_func=None):
        """Update task status in database and UI"""
        try:
            # Update in database
            update_data = {"status": status}
            if started_at is not None:
                update_data["started_at"] = started_at
            if completed_at is not None:
                update_data["completed_at"] = completed_at
            if result:
                update_data["result"] = result
            if output_path:
                update_data["output_path"] = output_path

            task_manager.update_task(task_id, **update_data)

            # Update in UI model
            if task_model:
                task_model.updateTask(task_id, **update_data)

            if append_log_func:
                append_log_func(f"已更新任务 #{task_id} 状态为: {status}")

            return True
        except Exception as e:
            if append_log_func:
                append_log_func(f"更新任务状态失败: {str(e)}")
            return False

    @staticmethod
    def delete_task(task_id, task_manager, append_log_func):
        """Delete a task"""
        try:
            task_manager.delete_task(task_id)
            append_log_func(f"已删除任务 #{task_id}")
            return True
        except Exception as e:
            append_log_func(f"删除任务失败: {str(e)}")
            return False

    @staticmethod
    def format_task_details(task):
        """Format task details for display"""
        if not task:
            return "任务不存在或已被删除"

        details = f"任务ID: {task.id}\n"
        details += f"URL: {task.url}\n"
        details += f"状态: {task.status}\n"
        details += f"创建时间: {task.created_at}\n"

        if task.started_at:
            details += f"开始时间: {task.started_at}\n"

        if task.completed_at:
            details += f"完成时间: {task.completed_at}\n"

        details += f"结果: {task.result}\n"

        if task.output_path and os.path.exists(task.output_path):
            details += f"输出路径: {task.output_path}\n"

        return details