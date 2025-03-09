"""
主程序入口
这个脚本为简化版本的Linly-Dubbing主程序
处理了原版GUI中可能导致崩溃的问题
"""

import sys
import os

# 设置环境变量，可能有助于解决一些库加载问题
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 禁用不必要的警告
import warnings

warnings.filterwarnings("ignore")

print("正在启动简化版本Linly-Dubbing...")

# 尝试导入Qt核心组件
try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QLabel, QVBoxLayout, QWidget
    from PySide6.QtCore import Qt

    print("Qt核心组件导入成功")
except ImportError as e:
    print(f"Qt核心组件导入失败: {e}")
    sys.exit(1)


# 使用全局异常处理器，避免程序突然崩溃
def global_exception_handler(exctype, value, traceback):
    print(f"未捕获的异常: {exctype.__name__}: {value}")
    import traceback as tb
    tb.print_tb(traceback)
    # 保持程序运行，不退出
    print("程序将继续运行，但可能出现异常行为")


# 替换默认的异常处理器
sys.excepthook = global_exception_handler

# 尝试导入必要的自定义组件
try:
    # 从ui_components.py中导入组件
    print("尝试导入自定义组件...")
    from ui_components import CustomSlider, FloatSlider, RadioButtonGroup, AudioSelector, VideoPlayer

    print("自定义组件导入成功")

    # 导入工具模块
    print("尝试导入工具模块...")
    from task_utils import TaskUtils
    from ui_utils import UIUtils
    from config_utils import ConfigUtils

    print("工具模块导入成功")

    # 导入标签页
    print("尝试导入标签页...")
    from full_auto_tab import FullAutoTab
    from settings_tab import SettingsTab

    print("标签页导入成功")
except ImportError as e:
    print(f"组件导入失败: {e}")
    print("将使用基本的UI界面")


    class FullAutoTab(QWidget):
        def __init__(self):
            super().__init__()
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("组件加载失败，请检查依赖项"))


    class SettingsTab(QWidget):
        config_changed = None

        def __init__(self):
            super().__init__()
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("组件加载失败，请检查依赖项"))
            from PySide6.QtCore import Signal
            self.config_changed = Signal(dict)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("简化版本 - Linly-Dubbing")
        self.resize(1024, 768)

        try:
            # 创建选项卡
            self.tab_widget = QTabWidget()

            # 创建标签页实例
            print("创建FullAutoTab实例...")
            self.full_auto_tab = FullAutoTab()
            print("创建SettingsTab实例...")
            self.settings_tab = SettingsTab()

            # 如果可能，连接配置页面的配置变更信号
            if hasattr(self.settings_tab, 'config_changed') and self.settings_tab.config_changed is not None:
                print("连接配置变更信号...")
                try:
                    self.settings_tab.config_changed.connect(self.full_auto_tab.update_config)
                    print("信号连接成功")
                except Exception as e:
                    print(f"信号连接失败: {e}")

            # 添加选项卡
            self.tab_widget.addTab(self.full_auto_tab, "一键自动化 One-Click")
            self.tab_widget.addTab(self.settings_tab, "配置页面 Settings")

            # 设置中央窗口部件
            self.setCentralWidget(self.tab_widget)
            print("窗口设置完成")
        except Exception as e:
            print(f"窗口创建失败: {e}")
            # 显示错误信息
            central_widget = QWidget()
            layout = QVBoxLayout(central_widget)
            layout.addWidget(QLabel(f"初始化失败: {str(e)}"))
            self.setCentralWidget(central_widget)


def main():
    try:
        # 设置高DPI缩放
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)

        # 设置应用样式
        app.setStyle("Fusion")

        # 创建主窗口
        print("创建主窗口...")
        window = MainWindow()
        window.show()
        print("应用程序启动完成")

        sys.exit(app.exec())
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()