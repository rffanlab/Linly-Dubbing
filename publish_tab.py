import os
import json
import datetime
from typing import List, Dict, Any

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QTextEdit, QTabWidget, QGroupBox, QFormLayout,
                               QCheckBox, QFileDialog, QListWidget, QMessageBox, QComboBox,
                               QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon

from platform_publisher import (MultiPlatformPublisher, PublishResult,
                                BilibiliPublisher, ToutiaoPublisher,
                                DouyinPublisher, KuaishouPublisher)
from ui_components import VideoPlayer


class PlatformSetupWidget(QWidget):
    """平台设置界面组件"""

    credentials_updated = Signal(str, dict)  # 平台名称, 凭证信息

    def __init__(self, platform_name: str, parent=None):
        super().__init__(parent)
        self.platform_name = platform_name
        self.setup_ui()
        self.load_credentials()

    def setup_ui(self):
        """设置UI"""
        # 主布局
        self.layout = QVBoxLayout(self)

        # 创建表单布局
        form_layout = QFormLayout()

        # 平台相关的输入字段
        if self.platform_name == "哔哩哔哩":
            self.cookie = QLineEdit()
            self.cookie.setEchoMode(QLineEdit.Password)  # 密码模式
            self.sessdata = QLineEdit()
            self.sessdata.setEchoMode(QLineEdit.Password)
            self.bili_jct = QLineEdit()
            self.bili_jct.setEchoMode(QLineEdit.Password)

            form_layout.addRow("Cookie:", self.cookie)
            form_layout.addRow("SESSDATA:", self.sessdata)
            form_layout.addRow("bili_jct:", self.bili_jct)

            # 分区选项
            self.categories = QComboBox()
            self.categories.addItems([
                "知识", "科技", "动画", "游戏", "生活", "美食", "鬼畜",
                "时尚", "娱乐", "音乐", "影视", "舞蹈", "汽车", "运动"
            ])
            form_layout.addRow("默认分区:", self.categories)

        elif self.platform_name in ["今日头条", "抖音", "快手"]:
            self.api_key = QLineEdit()
            self.api_key.setEchoMode(QLineEdit.Password)
            self.api_secret = QLineEdit()
            self.api_secret.setEchoMode(QLineEdit.Password)
            self.access_token = QLineEdit()
            self.access_token.setEchoMode(QLineEdit.Password)

            form_layout.addRow("API Key:", self.api_key)
            form_layout.addRow("API Secret:", self.api_secret)
            form_layout.addRow("Access Token:", self.access_token)

        # 将表单添加到主布局
        self.layout.addLayout(form_layout)

        # 添加保存按钮
        self.save_button = QPushButton("保存凭证")
        self.save_button.clicked.connect(self.save_credentials)
        self.layout.addWidget(self.save_button)

        # 添加测试按钮
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        self.layout.addWidget(self.test_button)

        # 添加说明文字
        note_label = QLabel(f"注意: {self.platform_name}的凭证信息将安全地存储在本地。")
        note_label.setWordWrap(True)
        self.layout.addWidget(note_label)

        self.setLayout(self.layout)

    def get_credentials(self) -> Dict[str, str]:
        """获取凭证信息"""
        if self.platform_name == "哔哩哔哩":
            return {
                "cookie": self.cookie.text(),
                "sessdata": self.sessdata.text(),
                "bili_jct": self.bili_jct.text(),
                "category": self.categories.currentText()
            }
        else:
            return {
                "api_key": self.api_key.text(),
                "api_secret": self.api_secret.text(),
                "access_token": self.access_token.text()
            }

    def set_credentials(self, credentials: Dict[str, str]):
        """设置凭证信息"""
        if self.platform_name == "哔哩哔哩":
            self.cookie.setText(credentials.get("cookie", ""))
            self.sessdata.setText(credentials.get("sessdata", ""))
            self.bili_jct.setText(credentials.get("bili_jct", ""))
            category = credentials.get("category", "知识")
            index = self.categories.findText(category)
            if index >= 0:
                self.categories.setCurrentIndex(index)
        else:
            self.api_key.setText(credentials.get("api_key", ""))
            self.api_secret.setText(credentials.get("api_secret", ""))
            self.access_token.setText(credentials.get("access_token", ""))

    def save_credentials(self):
        """保存凭证信息"""
        try:
            credentials = self.get_credentials()

            # 创建凭证目录
            os.makedirs("credentials", exist_ok=True)

            # 保存凭证到文件
            filename = f"credentials_{self.platform_name.lower()}.json"
            filepath = os.path.join("credentials", filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(credentials, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, "保存成功", f"{self.platform_name}的凭证信息已保存")

            # 发送凭证更新信号
            self.credentials_updated.emit(self.platform_name, credentials)

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存凭证时出错: {str(e)}")

    def load_credentials(self):
        """加载凭证信息"""
        try:
            filename = f"credentials_{self.platform_name.lower()}.json"
            filepath = os.path.join("credentials", filename)

            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    credentials = json.load(f)

                self.set_credentials(credentials)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"加载凭证时出错: {str(e)}")

    def test_connection(self):
        """测试连接"""
        QMessageBox.information(
            self,
            "测试连接",
            f"这是{self.platform_name}的连接测试功能，目前处于模拟模式。"
        )


class PublishTab(QWidget):
    """发布标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 平台发布器
        self.publisher = MultiPlatformPublisher()

        # 视频记录字典 {视频路径: 视频信息}
        self.video_records = {}

        # 初始化UI
        self.setup_ui()

        # 加载已有视频记录
        self.load_video_records()

    def setup_ui(self):
        """设置UI"""
        # 主布局
        self.main_layout = QHBoxLayout(self)

        # 左侧面板 - 视频列表与发布设置
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)

        # 视频选择区域
        self.video_group = QGroupBox("视频选择")
        self.video_layout = QVBoxLayout()

        # 视频输入与浏览
        self.video_input_layout = QHBoxLayout()
        self.video_path = QLineEdit()
        self.video_path.setPlaceholderText("视频文件路径")
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self.browse_video)
        self.video_input_layout.addWidget(self.video_path)
        self.video_input_layout.addWidget(self.browse_button)

        # 已处理视频下拉列表
        self.processed_label = QLabel("最近处理的视频:")
        self.processed_videos = QComboBox()
        self.processed_videos.currentIndexChanged.connect(self.on_processed_video_changed)

        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_processed_videos)

        # 横向布局
        self.processed_layout = QHBoxLayout()
        self.processed_layout.addWidget(self.processed_label)
        self.processed_layout.addWidget(self.processed_videos, 1)  # 1是拉伸因子
        self.processed_layout.addWidget(self.refresh_button)

        # 添加到视频布局
        self.video_layout.addLayout(self.video_input_layout)
        self.video_layout.addLayout(self.processed_layout)

        # 发布预览
        self.video_player = VideoPlayer("视频预览:")
        self.video_preview_button = QPushButton("预览视频")
        self.video_preview_button.clicked.connect(self.preview_video)
        self.video_layout.addWidget(self.video_player)
        self.video_layout.addWidget(self.video_preview_button)

        self.video_group.setLayout(self.video_layout)

        # 发布设置区域
        self.publish_settings = QGroupBox("发布设置")
        self.settings_layout = QFormLayout()

        # 标题
        self.title = QLineEdit()
        self.title.setPlaceholderText("视频标题")
        self.settings_layout.addRow("标题:", self.title)

        # 标签
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("标签，用逗号分隔")
        self.settings_layout.addRow("标签:", self.tags)

        # 分区选择
        self.category = QComboBox()
        self.category.addItems(["知识", "科技", "动画", "游戏", "生活", "美食", "鬼畜",
                                "时尚", "娱乐", "音乐", "影视", "舞蹈", "汽车", "运动"])
        self.settings_layout.addRow("分区:", self.category)

        # 简介
        self.description = QTextEdit()
        self.description.setPlaceholderText("视频简介")
        self.description.setMinimumHeight(100)
        self.settings_layout.addRow("简介:", self.description)

        # 平台选择
        self.platform_group = QGroupBox("目标平台")
        self.platform_layout = QVBoxLayout()

        # 添加平台复选框
        self.platform_checkboxes = {}
        for platform in ["哔哩哔哩", "今日头条", "抖音", "快手"]:
            checkbox = QCheckBox(platform)
            self.platform_checkboxes[platform] = checkbox
            self.platform_layout.addWidget(checkbox)

        self.platform_group.setLayout(self.platform_layout)
        self.settings_layout.addRow("目标平台:", self.platform_group)

        # 保存为模板复选框
        self.save_template = QCheckBox("保存为模板")
        self.template_name = QLineEdit()
        self.template_name.setPlaceholderText("模板名称")
        template_layout = QHBoxLayout()
        template_layout.addWidget(self.save_template)
        template_layout.addWidget(self.template_name)

        # 添加模板布局
        template_widget = QWidget()
        template_widget.setLayout(template_layout)
        self.settings_layout.addRow("保存模板:", template_widget)

        self.publish_settings.setLayout(self.settings_layout)

        # 添加到左侧布局
        self.left_layout.addWidget(self.video_group)
        self.left_layout.addWidget(self.publish_settings)

        # 发布按钮
        self.publish_button = QPushButton("发布到选定平台")
        self.publish_button.setMinimumHeight(40)
        self.publish_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.publish_button.clicked.connect(self.publish_video)
        self.left_layout.addWidget(self.publish_button)

        # 右侧面板 - 平台设置和发布记录
        self.right_panel = QTabWidget()

        # 平台设置标签页
        self.platform_settings = QTabWidget()

        # 添加各平台设置页
        self.platform_setups = {}
        for platform in ["哔哩哔哩", "今日头条", "抖音", "快手"]:
            setup_widget = PlatformSetupWidget(platform)
            setup_widget.credentials_updated.connect(self.on_credentials_updated)
            self.platform_setups[platform] = setup_widget
            self.platform_settings.addTab(setup_widget, platform)

        # 发布记录标签页
        self.publish_records = QWidget()
        self.records_layout = QVBoxLayout(self.publish_records)

        # 发布历史表格
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["平台", "标题", "状态", "时间", "链接"])
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # 设置列宽
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 平台
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 标题
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 时间
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 链接

        # 表格操作按钮
        table_buttons = QHBoxLayout()
        self.clear_history_button = QPushButton("清空历史")
        self.clear_history_button.clicked.connect(self.clear_history)
        self.export_history_button = QPushButton("导出历史")
        self.export_history_button.clicked.connect(self.export_history)
        table_buttons.addWidget(self.clear_history_button)
        table_buttons.addWidget(self.export_history_button)

        self.records_layout.addWidget(self.history_table)
        self.records_layout.addLayout(table_buttons)

        # 模板管理标签页
        self.templates_tab = QWidget()
        self.templates_layout = QVBoxLayout(self.templates_tab)

        # 模板列表
        self.templates_list = QListWidget()
        self.templates_list.itemClicked.connect(self.load_template)

        # 模板操作按钮
        template_buttons = QHBoxLayout()
        self.delete_template_button = QPushButton("删除模板")
        self.delete_template_button.clicked.connect(self.delete_template)
        template_buttons.addWidget(self.delete_template_button)

        self.templates_layout.addWidget(QLabel("已保存的模板:"))
        self.templates_layout.addWidget(self.templates_list)
        self.templates_layout.addLayout(template_buttons)

        # 将标签页添加到右侧面板
        self.right_panel.addTab(self.platform_settings, "平台设置")
        self.right_panel.addTab(self.publish_records, "发布记录")
        self.right_panel.addTab(self.templates_tab, "模板管理")

        # 设置分割比例
        self.main_layout.addWidget(self.left_panel, 1)  # 左侧占1份
        self.main_layout.addWidget(self.right_panel, 1)  # 右侧占1份

        # 初始化加载模板列表
        self.load_template_list()

        # 刷新视频列表
        self.refresh_processed_videos()

    def on_credentials_updated(self, platform: str, credentials: Dict[str, str]):
        """处理凭证更新信号"""
        print(f"{platform}凭证已更新")

    def browse_video(self):
        """浏览选择视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)"
        )
        if file_path:
            self.video_path.setText(file_path)
            self.load_video_info(file_path)

    def refresh_processed_videos(self):
        """刷新已处理视频列表"""
        self.processed_videos.clear()
        self.processed_videos.addItem("-- 选择最近处理的视频 --")

        # 查找视频文件夹下的所有处理过的视频
        video_folder = "videos"  # 默认视频文件夹
        if os.path.exists(video_folder):
            for root, dirs, files in os.walk(video_folder):
                for file in files:
                    if file.endswith(".mp4") and os.path.exists(os.path.join(root, "summary.json")):
                        video_path = os.path.join(root, file)
                        # 添加到下拉菜单
                        self.processed_videos.addItem(video_path)
                        # 加载视频信息
                        self.load_video_info(video_path)

    def load_video_info(self, video_path: str):
        """加载视频信息"""
        try:
            # 检查是否已加载
            if video_path in self.video_records:
                return

            # 尝试加载summary.json文件
            video_dir = os.path.dirname(video_path)
            summary_path = os.path.join(video_dir, "summary.json")

            if os.path.exists(summary_path):
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary = json.load(f)

                # 保存视频信息
                self.video_records[video_path] = {
                    "title": summary.get("title", os.path.basename(video_path)),
                    "tags": summary.get("tags", []),
                    "summary": summary.get("summary", ""),
                    "author": summary.get("author", "")
                }
        except Exception as e:
            print(f"加载视频信息出错: {str(e)}")

    def on_processed_video_changed(self, index: int):
        """当选择已处理视频时"""
        if index <= 0:
            return

        video_path = self.processed_videos.currentText()

        # 设置路径
        self.video_path.setText(video_path)

        # 尝试加载视频信息
        if video_path in self.video_records:
            info = self.video_records[video_path]
            self.title.setText(info.get("title", ""))
            self.tags.setText(",".join(info.get("tags", [])))
            self.description.setText(info.get("summary", ""))

        # 预览视频
        self.preview_video()

    def preview_video(self):
        """预览视频"""
        video_path = self.video_path.text()
        if os.path.exists(video_path):
            self.video_player.set_video(video_path)

    def publish_video(self):
        """发布视频到选定平台"""
        # 获取选定的平台
        selected_platforms = []
        for platform, checkbox in self.platform_checkboxes.items():
            if checkbox.isChecked():
                selected_platforms.append(platform)

        if not selected_platforms:
            QMessageBox.warning(self, "发布提示", "请至少选择一个目标平台")
            return

        video_path = self.video_path.text()
        if not video_path or not os.path.exists(video_path):
            QMessageBox.warning(self, "发布提示", "请选择有效的视频文件")
            return

        title = self.title.text()
        if not title:
            QMessageBox.warning(self, "发布提示", "请输入视频标题")
            return

        # 获取所有输入内容
        tags = [tag.strip() for tag in self.tags.text().split(",") if tag.strip()]
        description = self.description.toPlainText()
        category = self.category.currentText()

        # 如果选中"保存为模板"，则保存模板
        if self.save_template.isChecked():
            template_name = self.template_name.text()
            if template_name:
                self.save_publish_template(template_name, title, tags, description, category, selected_platforms)

        # 确认发布
        confirm = QMessageBox.question(
            self,
            "确认发布",
            f"确定要将视频发布到以下平台?\n{', '.join(selected_platforms)}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            # 显示发布进度对话框
            QMessageBox.information(
                self,
                "发布进度",
                "视频发布已开始，完成后将在发布记录中显示结果。"
            )

            # 异步发布
            self.do_publish(video_path, title, tags, description, category, selected_platforms)

    def do_publish(self, video_path: str, title: str, tags: List[str],
                   description: str, category: str, platforms: List[str]):
        """执行实际的发布操作"""
        try:
            # 发布到选定平台
            results = self.publisher.publish_to_platforms(
                platforms=platforms,
                video_path=video_path,
                title=title,
                tags=tags,
                description=description,
                category=category
            )

            # 更新历史记录
            self.update_history_table(results)

            # 保存结果
            self.publisher.save_results("publish_results.json")

            # 通知完成
            QTimer.singleShot(100, lambda: QMessageBox.information(
                self,
                "发布完成",
                f"视频已发布到选定平台，成功: {self.publisher.get_success_count()}, "
                f"失败: {self.publisher.get_fail_count()}"
            ))

        except Exception as e:
            QMessageBox.critical(self, "发布错误", f"发布过程中出错: {str(e)}")

    def update_history_table(self, results: List[PublishResult]):
        """更新历史记录表格"""
        try:
            for result in results:
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)

                # 平台
                self.history_table.setItem(row, 0, QTableWidgetItem(result.platform))

                # 标题 (从视频路径中提取)
                video_path = result.message.split("视频:")[1].split("\n")[
                    0].strip() if "视频:" in result.message else ""
                title = self.video_records.get(video_path, {}).get("title", os.path.basename(video_path))
                self.history_table.setItem(row, 1, QTableWidgetItem(title))

                # 状态
                status = "成功" if result.success else "失败"
                status_item = QTableWidgetItem(status)
                status_item.setBackground(Qt.green if result.success else Qt.red)
                self.history_table.setItem(row, 2, status_item)

                # 时间
                self.history_table.setItem(row, 3, QTableWidgetItem(result.timestamp))

                # 链接
                link_item = QTableWidgetItem(result.url if result.url else "")
                if result.url:
                    link_item.setForeground(Qt.blue)
                self.history_table.setItem(row, 4, link_item)
        except Exception as e:
            print(f"更新历史记录表格出错: {str(e)}")

    def clear_history(self):
        """清空历史记录"""
        confirm = QMessageBox.question(
            self,
            "确认清空",
            "确定要清空所有发布历史记录吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.history_table.setRowCount(0)
            self.publisher.clear_results()
            self.publisher.save_results("publish_results.json")

    def export_history(self):
        """导出历史记录"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "导出历史记录", "", "JSON文件 (*.json);;CSV文件 (*.csv);;所有文件 (*)"
            )

            if not filename:
                return

            # 根据扩展名选择导出格式
            if filename.endswith(".json"):
                self.publisher.save_results(filename)
            elif filename.endswith(".csv"):
                # 导出为CSV
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("平台,标题,状态,时间,链接\n")
                    for i in range(self.history_table.rowCount()):
                        platform = self.history_table.item(i, 0).text()
                        title = self.history_table.item(i, 1).text()
                        status = self.history_table.item(i, 2).text()
                        time = self.history_table.item(i, 3).text()
                        link = self.history_table.item(i, 4).text()
                        f.write(f"{platform},{title},{status},{time},{link}\n")
            else:
                # 默认JSON格式
                self.publisher.save_results(filename)

            QMessageBox.information(self, "导出成功", f"历史记录已导出到 {filename}")

        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出历史记录时出错: {str(e)}")

    def save_publish_template(self, template_name: str, title: str, tags: List[str],
                              description: str, category: str, platforms: List[str]):
        """保存发布模板"""
        try:
            # 创建模板目录
            os.makedirs("templates", exist_ok=True)

            # 构建模板数据
            template = {
                "title": title,
                "tags": tags,
                "description": description,
                "category": category,
                "platforms": platforms,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # 保存模板
            template_path = os.path.join("templates", f"{template_name}.json")
            with open(template_path, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)

            # 刷新模板列表
            self.load_template_list()

            QMessageBox.information(self, "保存成功", f"模板 '{template_name}' 已保存")

        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存模板时出错: {str(e)}")

    def load_template_list(self):
        """加载模板列表"""
        try:
            self.templates_list.clear()

            # 检查模板目录
            template_dir = "templates"
            if not os.path.exists(template_dir):
                return

            # 加载所有模板
            for filename in os.listdir(template_dir):
                if filename.endswith(".json"):
                    template_name = os.path.splitext(filename)[0]
                    self.templates_list.addItem(template_name)

        except Exception as e:
            print(f"加载模板列表时出错: {str(e)}")

    def load_template(self, item):
        """加载选中的模板"""
        try:
            template_name = item.text()
            template_path = os.path.join("templates", f"{template_name}.json")

            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    template = json.load(f)

                # 应用模板
                self.title.setText(template.get("title", ""))
                self.tags.setText(",".join(template.get("tags", [])))
                self.description.setText(template.get("description", ""))

                # 设置分类
                category = template.get("category", "知识")
                index = self.category.findText(category)
                if index >= 0:
                    self.category.setCurrentIndex(index)

                # 设置平台
                for platform, checkbox in self.platform_checkboxes.items():
                    checkbox.setChecked(platform in template.get("platforms", []))

                QMessageBox.information(self, "加载模板", f"已加载模板 '{template_name}'")

        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载模板时出错: {str(e)}")

    def delete_template(self):
        """删除选中的模板"""
        selected_items = self.templates_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "删除模板", "请先选择要删除的模板")
            return

        template_name = selected_items[0].text()
        confirm = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模板 '{template_name}' 吗?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            try:
                template_path = os.path.join("templates", f"{template_name}.json")
                if os.path.exists(template_path):
                    os.remove(template_path)

                # 刷新列表
                self.load_template_list()

                QMessageBox.information(self, "删除成功", f"模板 '{template_name}' 已删除")

            except Exception as e:
                QMessageBox.critical(self, "删除错误", f"删除模板时出错: {str(e)}")

    def load_video_records(self):
        """加载视频记录"""
        try:
            records_path = "video_records.json"
            if os.path.exists(records_path):
                with open(records_path, "r", encoding="utf-8") as f:
                    self.video_records = json.load(f)
        except Exception as e:
            print(f"加载视频记录时出错: {str(e)}")

    def save_video_records(self):
        """保存视频记录"""
        try:
            records_path = "video_records.json"
            with open(records_path, "w", encoding="utf-8") as f:
                json.dump(self.video_records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存视频记录时出错: {str(e)}")