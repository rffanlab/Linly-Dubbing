# task_manager.py (已修正 Optional 导入错误)
import os
import sqlite3
import datetime
import json
# *** 修改点 1: 从 typing 导入 Optional 和 List ***
from typing import Optional, List
# *** 结束修改点 1 ***
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal, QObject
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox


class Task:
    """任务数据模型"""
    def __init__(self, id=None, url="", status="待处理", created_at=None, started_at=None,
                 completed_at=None, result="", output_path="", config="{}"):
        self.id = id
        self.url = url
        self.status = status
        self.created_at = created_at or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.started_at = started_at
        self.completed_at = completed_at
        self.result = result
        self.output_path = output_path
        # 确保 config 是字符串
        if isinstance(config, dict):
             try: self.config = json.dumps(config)
             except TypeError: print(f"警告: 任务 {id} 配置无法序列化"); self.config = "{}"
        elif isinstance(config, str): self.config = config
        else: print(f"警告: 任务 {id} 配置类型无效"); self.config = "{}"


class TaskTableModel(QAbstractTableModel):
    """任务表格数据模型"""
    COLOR_PENDING = QColor(Qt.lightGray); COLOR_PROCESSING = QColor("#fffacd"); COLOR_COMPLETED = QColor("#d4edda"); COLOR_FAILED = QColor("#f8d7da"); COLOR_CANCELLED = QColor("#fff3cd")

    def __init__(self, tasks=None):
        super().__init__()
        self.tasks = [t for t in (tasks or []) if isinstance(t, Task)]
        self.headers = ["ID", "URL", "开始时间", "完成时间", "结果"]
        self.column_indices = {name: i for i, name in enumerate(self.headers)}

    def rowCount(self, parent=QModelIndex()): return len(self.tasks) if hasattr(self, 'tasks') else 0
    def columnCount(self, parent=QModelIndex()): return len(self.headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or not hasattr(self, 'tasks') or not (0 <= index.row() < len(self.tasks)): return None
        try:
            task = self.tasks[index.row()]; col = index.column(); col_name = self.headers[col]
            if role == Qt.DisplayRole:
                if col_name=="ID": return str(task.id) if task.id is not None else "N/A"
                if col_name=="URL": url=task.url; fn=os.path.basename(url) if os.path.isfile(url) else url; max_len=60; return fn[:max_len]+"..." if len(fn)>max_len else fn
                if col_name=="开始时间": return task.started_at or "---"
                if col_name=="完成时间": return task.completed_at or "---"
                if col_name=="结果": res=task.result or ""; res=res.split(':',1)[1].strip() if ':' in res else res; max_len=50; return res[:max_len]+"..." if len(res)>max_len else res
            elif role == Qt.ToolTipRole:
                if col_name=="URL": return task.url
                if col_name=="结果": return task.result
                if col_name=="ID": return f"ID: {task.id}\n状态: {task.status}"
            elif role == Qt.BackgroundRole:
                s=task.status.lower(); return self.COLOR_PENDING if s=="待处理" else self.COLOR_PROCESSING if s=="处理中" else self.COLOR_COMPLETED if s=="已完成" else self.COLOR_FAILED if s=="失败" else self.COLOR_CANCELLED if s=="已取消" else None
            elif role == Qt.TextAlignmentRole: return Qt.AlignCenter if col_name in ["开始时间", "完成时间"] else None
        except Exception as e: print(f"Model data error: {e}"); return None
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole): return self.headers[section] if orientation==Qt.Horizontal and role==Qt.DisplayRole and 0<=section<len(self.headers) else None
    def appendTask(self, task: Task):
        if not isinstance(task, Task): print("错误: 添加非 Task 对象"); return
        rc=self.rowCount(); self.beginInsertRows(QModelIndex(), rc, rc); self.tasks.append(task); self.endInsertRows()

    def updateTask(self, task_id, **kwargs):
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                try:
                    changed=False
                    for k,v in kwargs.items():
                        if hasattr(task,k) and getattr(task,k)!=v: setattr(task,k,v); changed=True
                    if changed: self.dataChanged.emit(self.index(i,0), self.index(i, self.columnCount()-1)); return True
                    else: return True # 找到但无变化也算成功
                except Exception as e: print(f"错误: 更新模型任务 {task_id}: {e}"); return False
        return False # 未找到

    def removeTask(self, task_id):
        for i, task in enumerate(self.tasks):
            if task.id == task_id: self.beginRemoveRows(QModelIndex(),i,i); del self.tasks[i]; self.endRemoveRows(); return True
        return False

    def clear(self):
        if not self.tasks: return
        rc=self.rowCount(); self.beginRemoveRows(QModelIndex(),0,rc-1); self.tasks=[]; self.endRemoveRows()


class TaskManager(QObject):
    """任务管理器，负责任务的CRUD操作和数据库交互"""
    task_updated = Signal(int); task_added = Signal(int); task_removed = Signal(int); tasks_cleared = Signal()

    def __init__(self, db_path="task.db"):
        super().__init__()
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try: os.makedirs(db_dir, exist_ok=True)
            except OSError as e: raise OSError(f"无法创建数据库目录 '{db_dir}': {e}") from e
        self._init_db()

    def _get_connection(self):
        try: conn = sqlite3.connect(self.db_path, timeout=10); conn.row_factory = sqlite3.Row; return conn
        except sqlite3.Error as e: print(f"数据库连接错误: {e}"); raise ConnectionError(f"无法连接数据库 '{self.db_path}': {e}") from e

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(''' CREATE TABLE IF NOT EXISTS tasks ( id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT NOT NULL, status TEXT NOT NULL DEFAULT '待处理', created_at TEXT NOT NULL, started_at TEXT, completed_at TEXT, result TEXT, output_path TEXT, config TEXT DEFAULT '{}' ) ''')
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks (status);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON tasks (created_at);")
                conn.commit()
        except (sqlite3.Error, ConnectionError) as e: print(f"数据库初始化失败: {e}"); raise RuntimeError(f"数据库初始化失败: {e}") from e

    # *** 类型提示 Optional 需要从 typing 导入 ***
    def add_task(self, task: Task) -> Optional[int]:
        if not isinstance(task, Task): print("错误: add_task 需要 Task 对象"); return None
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(''' INSERT INTO tasks (url, status, created_at, started_at, completed_at, result, output_path, config) VALUES (?, ?, ?, ?, ?, ?, ?, ?) ''',
                               (task.url, task.status, task.created_at, task.started_at, task.completed_at, task.result, task.output_path, task.config))
                task_id = cursor.lastrowid; conn.commit(); task.id = task_id
                self.task_added.emit(task_id); return task_id
        except (sqlite3.Error, ConnectionError) as e: print(f"添加任务到数据库失败: {e}"); return None

    def update_task(self, task_id: int, **kwargs) -> bool:
        if not kwargs: return True
        valid_fields = ["url", "status", "started_at", "completed_at", "result", "output_path", "config"]
        update_data = {k: v for k, v in kwargs.items() if k in valid_fields}
        if not update_data: print(f"警告: update_task 未提供有效字段 for task {task_id}"); return False
        if 'config' in update_data and isinstance(update_data['config'], dict):
             try: update_data['config'] = json.dumps(update_data['config'])
             except TypeError: print(f"错误: 无法序列化配置以更新任务 {task_id}"); del update_data['config']
        set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()]); values = list(update_data.values()); values.append(task_id)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(); cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values); updated_rows = cursor.rowcount; conn.commit()
                if updated_rows > 0: self.task_updated.emit(task_id); return True
                else: return False
        except (sqlite3.Error, ConnectionError) as e: print(f"更新数据库任务 {task_id} 失败: {e}"); return False

    # *** 类型提示 Optional 需要从 typing 导入 ***
    def get_task(self, task_id: int) -> Optional[Task]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(); cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)); row = cursor.fetchone()
            if row: return Task(id=row["id"], url=row["url"], status=row["status"], created_at=row["created_at"], started_at=row["started_at"], completed_at=row["completed_at"], result=row["result"], output_path=row["output_path"], config=row["config"])
        except (sqlite3.Error, ConnectionError) as e: print(f"获取任务 {task_id} 失败: {e}")
        return None

    # *** 类型提示 List 需要从 typing 导入 ***
    def get_all_tasks(self) -> List[Task]:
        tasks = []
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(); cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC"); rows = cursor.fetchall()
            for row in rows: tasks.append(Task(id=row["id"], url=row["url"], status=row["status"], created_at=row["created_at"], started_at=row["started_at"], completed_at=row["completed_at"], result=row["result"], output_path=row["output_path"], config=row["config"]))
        except (sqlite3.Error, ConnectionError) as e: print(f"获取所有任务失败: {e}")
        return tasks

    # *** 类型提示 Optional 需要从 typing 导入 ***
    def get_next_pending_task(self) -> Optional[Task]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(); cursor.execute("SELECT * FROM tasks WHERE status = '待处理' ORDER BY created_at ASC LIMIT 1"); row = cursor.fetchone()
            if row: return Task(id=row["id"], url=row["url"], status=row["status"], created_at=row["created_at"], started_at=row["started_at"], completed_at=row["completed_at"], result=row["result"], output_path=row["output_path"], config=row["config"])
        except (sqlite3.Error, ConnectionError) as e: print(f"获取下一个待处理任务失败: {e}")
        return None

    def delete_task(self, task_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(); cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,)); deleted_rows = cursor.rowcount; conn.commit()
                if deleted_rows > 0: self.task_removed.emit(task_id); return True
                else: return False
        except (sqlite3.Error, ConnectionError) as e: print(f"删除数据库任务 {task_id} 失败: {e}"); return False

    def clear_all_tasks(self) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(); cursor.execute("DELETE FROM tasks"); conn.commit()
                self.tasks_cleared.emit(); return True
        except (sqlite3.Error, ConnectionError) as e: print(f"清空数据库任务失败: {e}"); return False