import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from loguru import logger

# 设置基本日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class PublishResult:
    """发布结果类"""

    def __init__(self, success: bool, message: str, url: str = None, platform: str = None):
        self.success = success
        self.message = message
        self.url = url
        self.platform = platform
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "message": self.message,
            "url": self.url,
            "platform": self.platform,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PublishResult':
        """从字典创建对象"""
        result = cls(
            success=data["success"],
            message=data["message"],
            url=data.get("url"),
            platform=data.get("platform")
        )
        result.timestamp = data.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
        return result

    def __str__(self) -> str:
        """字符串表示"""
        status = "成功" if self.success else "失败"
        url_str = f", 发布地址: {self.url}" if self.url else ""
        return f"[{self.platform}] 发布{status}: {self.message}{url_str} ({self.timestamp})"


class PlatformPublisher(ABC):
    """平台发布基类，定义发布接口"""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = logging.getLogger(f"publisher.{platform_name}")

    @abstractmethod
    def publish(self,
                video_path: str,
                title: str,
                tags: List[str],
                description: str,
                category: str = None,
                **kwargs) -> PublishResult:
        """发布视频到平台的抽象方法"""
        pass

    def save_credentials(self, credentials: Dict[str, str], filename: str = None) -> bool:
        """保存平台凭证"""
        try:
            if filename is None:
                filename = f"credentials_{self.platform_name.lower()}.json"

            # 创建凭证目录
            os.makedirs("credentials", exist_ok=True)
            filepath = os.path.join("credentials", filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(credentials, f, ensure_ascii=False, indent=2)

            self.logger.info(f"凭证已保存到 {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"保存凭证失败: {str(e)}")
            return False

    def load_credentials(self, filename: str = None) -> Dict[str, str]:
        """加载平台凭证"""
        try:
            if filename is None:
                filename = f"credentials_{self.platform_name.lower()}.json"

            filepath = os.path.join("credentials", filename)

            if not os.path.exists(filepath):
                self.logger.warning(f"凭证文件不存在: {filepath}")
                return {}

            with open(filepath, "r", encoding="utf-8") as f:
                credentials = json.load(f)

            self.logger.info(f"已加载凭证 {filepath}")
            return credentials
        except Exception as e:
            self.logger.error(f"加载凭证失败: {str(e)}")
            return {}

    def _simulation_publish(self,
                            video_path: str,
                            title: str,
                            tags: List[str],
                            description: str,
                            category: str = None) -> PublishResult:
        """模拟发布过程（用于测试）"""
        self.logger.info(f"模拟发布到 {self.platform_name}")
        self.logger.info(f"视频: {video_path}")
        self.logger.info(f"标题: {title}")
        self.logger.info(f"标签: {tags}")
        self.logger.info(f"分类: {category}")
        self.logger.info(f"简介: {description[:50]}...")

        # 模拟发布延迟
        time.sleep(2)

        # 模拟视频链接
        url = f"https://{self.platform_name.lower()}.com/video/{abs(hash(video_path)) % 10000000}"

        return PublishResult(
            success=True,
            message=f"模拟发布到{self.platform_name}成功",
            url=url,
            platform=self.platform_name
        )


# 具体平台实现类

class BilibiliPublisher(PlatformPublisher):
    """哔哩哔哩发布类"""

    def __init__(self):
        super().__init__("哔哩哔哩")

    def publish(self,
                video_path: str,
                title: str,
                tags: List[str],
                description: str,
                category: str = None,
                **kwargs) -> PublishResult:
        """发布视频到B站"""
        # 1. 从凭证获取登录信息
        credentials = self.load_credentials()
        if not credentials:
            return PublishResult(
                success=False,
                message="未找到B站凭证信息",
                platform=self.platform_name
            )

        # 2. 检查视频文件
        if not os.path.exists(video_path):
            return PublishResult(
                success=False,
                message=f"视频文件不存在: {video_path}",
                platform=self.platform_name
            )

        # 3. 实际上传逻辑 (模拟实现)
        return self._simulation_publish(video_path, title, tags, description, category)


class ToutiaoPublisher(PlatformPublisher):
    """今日头条发布类"""

    def __init__(self):
        super().__init__("今日头条")

    def publish(self,
                video_path: str,
                title: str,
                tags: List[str],
                description: str,
                category: str = None,
                **kwargs) -> PublishResult:
        """发布视频到今日头条"""
        # 凭证检查
        credentials = self.load_credentials()
        if not credentials:
            return PublishResult(
                success=False,
                message="未找到今日头条凭证信息",
                platform=self.platform_name
            )

        # 文件检查
        if not os.path.exists(video_path):
            return PublishResult(
                success=False,
                message=f"视频文件不存在: {video_path}",
                platform=self.platform_name
            )

        # 模拟发布
        return self._simulation_publish(video_path, title, tags, description, category)


class DouyinPublisher(PlatformPublisher):
    """抖音发布类"""

    def __init__(self):
        super().__init__("抖音")

    def publish(self,
                video_path: str,
                title: str,
                tags: List[str],
                description: str,
                category: str = None,
                **kwargs) -> PublishResult:
        """发布视频到抖音"""
        # 凭证检查
        credentials = self.load_credentials()
        if not credentials:
            return PublishResult(
                success=False,
                message="未找到抖音凭证信息",
                platform=self.platform_name
            )

        # 文件检查
        if not os.path.exists(video_path):
            return PublishResult(
                success=False,
                message=f"视频文件不存在: {video_path}",
                platform=self.platform_name
            )

        # 模拟发布
        return self._simulation_publish(video_path, title, tags, description, category)


class KuaishouPublisher(PlatformPublisher):
    """快手发布类"""

    def __init__(self):
        super().__init__("快手")

    def publish(self,
                video_path: str,
                title: str,
                tags: List[str],
                description: str,
                category: str = None,
                **kwargs) -> PublishResult:
        """发布视频到快手"""
        # 凭证检查
        credentials = self.load_credentials()
        if not credentials:
            return PublishResult(
                success=False,
                message="未找到快手凭证信息",
                platform=self.platform_name
            )

        # 文件检查
        if not os.path.exists(video_path):
            return PublishResult(
                success=False,
                message=f"视频文件不存在: {video_path}",
                platform=self.platform_name
            )

        # 模拟发布
        return self._simulation_publish(video_path, title, tags, description, category)


class PublisherFactory:
    """发布器工厂类"""

    @staticmethod
    def create_publisher(platform: str) -> Optional[PlatformPublisher]:
        """根据平台名称创建对应的发布器"""
        platform = platform.lower()

        if platform in ['bilibili', '哔哩哔哩', 'b站']:
            return BilibiliPublisher()
        elif platform in ['toutiao', '今日头条', '头条']:
            return ToutiaoPublisher()
        elif platform in ['douyin', '抖音']:
            return DouyinPublisher()
        elif platform in ['kuaishou', '快手']:
            return KuaishouPublisher()
        else:
            logger.error(f"不支持的平台: {platform}")
            return None


class MultiPlatformPublisher:
    """多平台发布管理器"""

    def __init__(self):
        self.results = []

    def publish_to_platforms(self,
                             platforms: List[str],
                             video_path: str,
                             title: str,
                             tags: List[str],
                             description: str,
                             category: str = None,
                             **kwargs) -> List[PublishResult]:
        """发布到多个平台"""
        results = []

        for platform in platforms:
            publisher = PublisherFactory.create_publisher(platform)
            if publisher:
                try:
                    result = publisher.publish(
                        video_path=video_path,
                        title=title,
                        tags=tags,
                        description=description,
                        category=category,
                        **kwargs
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"发布到 {platform} 时出错: {str(e)}")
                    results.append(PublishResult(
                        success=False,
                        message=f"发布异常: {str(e)}",
                        platform=platform
                    ))

        self.results.extend(results)
        return results

    def get_results(self) -> List[PublishResult]:
        """获取所有发布结果"""
        return self.results

    def get_success_count(self) -> int:
        """获取成功发布数量"""
        return sum(1 for result in self.results if result.success)

    def get_fail_count(self) -> int:
        """获取失败发布数量"""
        return sum(1 for result in self.results if not result.success)

    def clear_results(self):
        """清空结果"""
        self.results = []

    def save_results(self, filename: str = "publish_results.json") -> bool:
        """保存发布结果到文件"""
        try:
            results_data = [result.to_dict() for result in self.results]

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)

            logger.info(f"发布结果已保存到 {filename}")
            return True
        except Exception as e:
            logger.error(f"保存发布结果失败: {str(e)}")
            return False

    def load_results(self, filename: str = "publish_results.json") -> bool:
        """从文件加载发布结果"""
        try:
            if not os.path.exists(filename):
                logger.warning(f"结果文件不存在: {filename}")
                return False

            with open(filename, "r", encoding="utf-8") as f:
                results_data = json.load(f)

            self.results = [PublishResult.from_dict(data) for data in results_data]
            logger.info(f"已加载 {len(self.results)} 条发布结果")
            return True
        except Exception as e:
            logger.error(f"加载发布结果失败: {str(e)}")
            return False


# 使用示例
if __name__ == "__main__":
    # 创建多平台发布管理器
    publisher = MultiPlatformPublisher()

    # 模拟发布
    results = publisher.publish_to_platforms(
        platforms=["哔哩哔哩", "今日头条", "抖音"],
        video_path="example.mp4",
        title="测试视频标题",
        tags=["测试", "示例", "自动发布"],
        description="这是一个测试视频描述，用于测试自动发布功能。",
        category="科技"
    )

    # 打印结果
    for result in results:
        print(result)

    # 保存结果
    publisher.save_results("test_results.json")