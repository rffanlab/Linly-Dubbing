# task_utils.py

import os
import datetime
import json
import traceback # 确保导入 traceback
from PySide6.QtWidgets import QMessageBox

# 确保 Task 类被正确导入或定义
try:
    from task_manager import Task
except ImportError:
    # 如果 Task 在别处定义或需要模拟
    class Task:
        def __init__(self, id=None, url="", status="待处理", created_at=None, config="{}", **kwargs):
            self.id = id; self.url=url; self.status=status; self.created_at=created_at
            self.config=config; self.started_at=None; self.completed_at=None
            self.result=""; self.output_path=""

class TaskUtils:
    """Task-related utility functions for the FullAutoTab"""

    @staticmethod
    def load_tasks(task_manager, task_table, task_model_class, append_log_func):
        """Load all tasks and update the table"""
        try:
            # 健壮性：确保 task_manager 有 get_all_tasks 方法
            if not hasattr(task_manager, 'get_all_tasks'):
                 if append_log_func: append_log_func("[错误] TaskManager 没有 get_all_tasks 方法。")
                 return None
            tasks = task_manager.get_all_tasks()
            # 健壮性：确保 task_model_class 是可调用的
            if not callable(task_model_class):
                 if append_log_func: append_log_func(f"[错误] task_model_class ({task_model_class}) 不是有效的类。")
                 return None
            task_model = task_model_class(tasks)
            # 健壮性：确保 task_table 有 setModel 方法
            if not hasattr(task_table, 'setModel'):
                 if append_log_func: append_log_func("[错误] task_table 没有 setModel 方法。")
                 # 即使表格设置失败，模型也创建了，返回模型
                 return task_model
            task_table.setModel(task_model)
            if append_log_func: append_log_func(f"已加载 {len(tasks) if tasks else 0} 个任务")
            return task_model
        except Exception as e:
            if append_log_func:
                append_log_func(f"加载任务失败: {str(e)}")
                append_log_func(f"详细错误:\n{traceback.format_exc()}")
            return None

    @staticmethod
    def add_task(url, config, task_manager, task_model, append_log_func):
        """Add a new task to the list"""
        if not url.strip():
            # 不要在工具类里弹窗，返回错误让调用者处理
            # QMessageBox.warning(None, "输入错误", "请输入视频URL或选择本地视频文件")
            if append_log_func: append_log_func("[错误] 添加任务失败：URL 为空。")
            return None

        try:
            task = Task(
                url=url,
                status="待处理",
                created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                # 确保 config 始终是 JSON 字符串
                config=json.dumps(config) if isinstance(config, dict) else (config if isinstance(config, str) else "{}")
            )

            # 健壮性：检查 task_manager
            if not task_manager or not hasattr(task_manager, 'add_task'):
                 if append_log_func: append_log_func("[错误] TaskManager 无效或缺少 add_task 方法。")
                 return None
            task_id = task_manager.add_task(task)

            if task_id is None: # 如果数据库添加失败
                 if append_log_func: append_log_func(f"[错误] 数据库添加任务失败: {url}")
                 return None

            # 更新 UI 模型 (如果存在且有效)
            if task_model and hasattr(task_model, 'appendTask'):
                # 确保 task 对象有 ID (add_task 应该已经设置了)
                if task.id is None: task.id = task_id
                task_model.appendTask(task)
            elif task_model:
                 if append_log_func: append_log_func("[警告] TaskTableModel 没有 appendTask 方法。")

            if append_log_func: append_log_func(f"已添加任务 #{task_id}: {url}")
            return task_id
        except Exception as e:
            if append_log_func:
                append_log_func(f"添加任务时发生异常: {str(e)}")
                append_log_func(f"详细错误:\n{traceback.format_exc()}")
            return None

    @staticmethod
    def clear_tasks(task_manager, append_log_func):
        """Clear all tasks"""
        try:
            if not task_manager or not hasattr(task_manager, 'clear_all_tasks'):
                if append_log_func: append_log_func("[错误] TaskManager 无效或缺少 clear_all_tasks 方法。")
                return False
            success = task_manager.clear_all_tasks()
            if success:
                if append_log_func: append_log_func("已清空所有任务")
            else:
                 if append_log_func: append_log_func("[错误] TaskManager 清空任务失败。")
            return success
        except Exception as e:
            if append_log_func:
                append_log_func(f"清空任务时发生异常: {str(e)}")
                append_log_func(f"详细错误:\n{traceback.format_exc()}")
            return False

    @staticmethod
    def get_next_pending_task(task_manager, append_log_func):
        """Get the next pending task"""
        try:
            if not task_manager or not hasattr(task_manager, 'get_next_pending_task'):
                 if append_log_func: append_log_func("[错误] TaskManager 无效或缺少 get_next_pending_task 方法。")
                 return None
            return task_manager.get_next_pending_task()
        except Exception as e:
            if append_log_func:
                append_log_func(f"获取下一个待处理任务失败: {str(e)}")
                append_log_func(f"详细错误:\n{traceback.format_exc()}")
            return None

    # *** 修改后的 update_task_status 方法 ***
    @staticmethod
    def update_task_status(task_id, task_manager, task_model, status, started_at=None,
                           completed_at=None, result="", output_path="", append_log_func=None):
        """Update task status in database and UI with detailed exception logging"""
        db_updated = False
        ui_updated = False
        action_description = f"更新任务 #{task_id} 状态为 '{status}'" # 用于日志

        try:
            # --- 1. Prepare Update Data ---
            update_data = {"status": status}
            if started_at is not None: update_data["started_at"] = started_at
            if completed_at is not None: update_data["completed_at"] = completed_at
            # 始终包含 result 和 output_path，允许清空字段
            update_data["result"] = result
            update_data["output_path"] = output_path

            # 健壮性检查：确保 task_manager 有效
            if not task_manager or not hasattr(task_manager, 'update_task'):
                if append_log_func: append_log_func(f"[错误] {action_description} 失败：TaskManager无效。")
                return False

            # --- 2. Update Database ---
            if append_log_func: append_log_func(f"准备{action_description} (数据库)...")
            db_updated = task_manager.update_task(task_id, **update_data) # 假设它内部处理异常并返回 bool

            if db_updated:
                if append_log_func: append_log_func(f"数据库{action_description} 成功。")
            else:
                # TaskManager 内部应该记录了具体错误，这里只记录结果
                if append_log_func: append_log_func(f"[错误] 数据库{action_description} 失败 (TaskManager返回False)。")
                # 数据库失败，通常不应继续更新UI
                return False

            # --- 3. Update UI Model (如果数据库成功) ---
            if task_model:
                if hasattr(task_model, 'updateTask'):
                    if append_log_func: append_log_func(f"准备{action_description} (UI模型)...")
                    ui_updated = task_model.updateTask(task_id, **update_data)
                    if ui_updated:
                        if append_log_func: append_log_func(f"UI模型{action_description} 成功。")
                    else:
                        # 模型更新失败可能是因为任务ID在模型中不存在（理论上不应发生）或无变化
                        if append_log_func: append_log_func(f"[警告] UI模型{action_description} 失败 (updateTask返回False)。")
                else:
                    if append_log_func: append_log_func(f"[错误] TaskTableModel 没有 updateTask 方法！无法更新UI。")
            # else: # task_model 不存在不是错误，只是无法更新UI
            #     if append_log_func: append_log_func(f"UI模型不存在，跳过UI更新。")

            # --- 4. Return overall success (based on DB update) ---
            return db_updated

        # *** 关键：捕获所有异常并记录详细 traceback ***
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            # 获取完整的 traceback 字符串
            detailed_traceback = traceback.format_exc()
            log_message = f"[致命错误] 在 {action_description} 过程中发生异常!\n" \
                          f"类型: {error_type}\n" \
                          f"消息: {error_msg}\n" \
                          f"Traceback:\n{detailed_traceback}"

            if append_log_func:
                append_log_func(log_message) # 记录极其详细的错误日志
            else:
                print(log_message) # 后备打印到控制台

            # 返回 False 表示操作失败
            return False
    # *** 结束修改 ***

    @staticmethod
    def delete_task(task_id, task_manager, append_log_func):
        """Delete a task"""
        try:
            if not task_manager or not hasattr(task_manager, 'delete_task'):
                 if append_log_func: append_log_func("[错误] TaskManager 无效或缺少 delete_task 方法。")
                 return False
            success = task_manager.delete_task(task_id)
            if success:
                if append_log_func: append_log_func(f"已删除任务 #{task_id}")
            else:
                 if append_log_func: append_log_func(f"[错误] 删除任务 #{task_id} 失败 (TaskManager返回False)。")
            return success
        except Exception as e:
            if append_log_func:
                append_log_func(f"删除任务时发生异常: {str(e)}")
                append_log_func(f"详细错误:\n{traceback.format_exc()}")
            return False

    @staticmethod
    def format_task_details(task):
        """Format task details for display"""
        if not task: return "任务不存在或已被删除"
        try:
            details = f"任务ID: {task.id}\n" \
                      f"URL: {task.url}\n" \
                      f"状态: {task.status}\n" \
                      f"创建时间: {task.created_at}\n"
            if task.started_at: details += f"开始时间: {task.started_at}\n"
            if task.completed_at: details += f"完成时间: {task.completed_at}\n"
            details += f"结果: {task.result or '无'}\n" # 显示“无”如果为空
            if task.output_path: # 只在有路径时显示
                 exists = os.path.exists(task.output_path) if task.output_path else False
                 details += f"输出路径: {task.output_path}{' (存在)' if exists else ' (不存在或未指定)'}\n"
            # 可以考虑显示 config 内容（部分或全部）
            # config_dict = json.loads(task.config or '{}')
            # details += f"配置摘要: ..."
            return details
        except Exception as e:
             print(f"格式化任务详情时出错: {e}")
             return f"格式化任务 {task.id if task else '?'} 详情时出错。"