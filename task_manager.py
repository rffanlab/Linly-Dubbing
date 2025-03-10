import os
import sqlite3
import datetime
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import QMessageBox


class Task:
    """任务数据模型"""

    def __init__(self, id=None, url="", status="待处理", created_at=None, started_at=None,
                 completed_at=None, result="", output_path="", config=None):
        self.id = id
        self.url = url
        self.status = status  # 待处理, 处理中, 已完成, 失败
        self.created_at = created_at or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.started_at = started_at
        self.completed_at = completed_at
        self.result = result
        self.output_path = output_path
        self.config = config or "{}"  # 存储任务配置的JSON字符串


# 修改 task_manager.py 中的 TaskTableModel 类的显示逻辑
# 注意：这个修改不会改变数据库结构或Task类定义，只是调整显示方式

class TaskTableModel(QAbstractTableModel):
    """任务表格数据模型"""

    def __init__(self, tasks=None):
        super().__init__()
        self.tasks = tasks or []
        # 只显示这些列，移除"创建时间"和"状态"列
        self.headers = ["ID", "URL", "开始时间", "完成时间", "结果"]

    def rowCount(self, parent=QModelIndex()):
        return len(self.tasks)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.tasks)):
            return None

        task = self.tasks[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == 0:
                return task.id
            elif column == 1:
                # 增加URL显示长度
                return task.url[:70] + "..." if len(task.url) > 70 else task.url
            elif column == 2:
                return task.started_at or ""
            elif column == 3:
                return task.completed_at or ""
            elif column == 4:
                # 截断过长的结果
                return task.result[:50] + "..." if len(task.result) > 50 else task.result

        # 根据状态设置不同的背景颜色（保留状态的视觉提示）
        if role == Qt.BackgroundRole:
            if task.status == "待处理":
                return Qt.lightGray
            elif task.status == "处理中":
                return Qt.yellow
            elif task.status == "已完成":
                return Qt.green
            elif task.status == "失败":
                return Qt.red

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def appendTask(self, task):
        self.beginInsertRows(QModelIndex(), len(self.tasks), len(self.tasks))
        self.tasks.append(task)
        self.endInsertRows()

    def updateTask(self, task_id, **kwargs):
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                for key, value in kwargs.items():
                    setattr(task, key, value)
                self.dataChanged.emit(self.index(i, 0), self.index(i, len(self.headers) - 1))
                return True
        return False


class TaskManager:
    """任务管理器，负责任务的CRUD操作和数据库交互"""
    task_updated = Signal(int)  # 任务更新信号，参数为任务ID

    def __init__(self, db_path="task.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            result TEXT,
            output_path TEXT,
            config TEXT
        )
        ''')

        conn.commit()
        conn.close()

    def add_task(self, task):
        """添加任务到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        INSERT INTO tasks (url, status, created_at, started_at, completed_at, result, output_path, config)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.url,
            task.status,
            task.created_at,
            task.started_at,
            task.completed_at,
            task.result,
            task.output_path,
            task.config
        ))

        task_id = cursor.lastrowid
        task.id = task_id

        conn.commit()
        conn.close()

        return task_id

    def update_task(self, task_id, **kwargs):
        """更新任务信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 构建更新语句
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(task_id)

        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)

        conn.commit()
        conn.close()

        if hasattr(self, 'task_updated') and callable(getattr(self.task_updated, 'emit', None)):
            self.task_updated.emit(task_id)

        return cursor.rowcount > 0

    def get_task(self, task_id):
        """获取特定任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return Task(
                id=row[0],
                url=row[1],
                status=row[2],
                created_at=row[3],
                started_at=row[4],
                completed_at=row[5],
                result=row[6],
                output_path=row[7],
                config=row[8]
            )

        return None

    def get_all_tasks(self):
        """获取所有任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        rows = cursor.fetchall()

        conn.close()

        tasks = []
        for row in rows:
            tasks.append(Task(
                id=row[0],
                url=row[1],
                status=row[2],
                created_at=row[3],
                started_at=row[4],
                completed_at=row[5],
                result=row[6],
                output_path=row[7],
                config=row[8]
            ))

        return tasks

    def get_next_pending_task(self):
        """获取下一个待处理的任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE status = '待处理' ORDER BY created_at ASC LIMIT 1")
        row = cursor.fetchone()

        conn.close()

        if row:
            return Task(
                id=row[0],
                url=row[1],
                status=row[2],
                created_at=row[3],
                started_at=row[4],
                completed_at=row[5],
                result=row[6],
                output_path=row[7],
                config=row[8]
            )

        return None

    def delete_task(self, task_id):
        """删除任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        conn.commit()
        conn.close()

        return cursor.rowcount > 0

    def clear_all_tasks(self):
        """清空所有任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM tasks")

        conn.commit()
        conn.close()

        return True