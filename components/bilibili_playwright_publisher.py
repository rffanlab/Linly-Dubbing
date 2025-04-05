import os
import sys
import time
import socket
import asyncio
import subprocess
from typing import List, Optional, Tuple
from loguru import logger


def is_port_in_use(port):
    """检查端口是否已在使用中"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def get_chrome_debugging_instances(port=9222):
    """获取Chrome远程调试实例列表"""
    if not is_port_in_use(port):
        return []

    try:
        import requests
        response = requests.get(f"http://localhost:{port}/json/list")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        logger.error(f"获取Chrome实例列表出错: {e}")
        return []


def find_chrome_path():
    """查找系统Chrome浏览器路径"""
    import platform

    system = platform.system()

    if system == "Windows":
        paths = [
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                         'Google\\Chrome\\Application\\chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
                         'Google\\Chrome\\Application\\chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google\\Chrome\\Application\\chrome.exe')
        ]
    elif system == "Darwin":  # macOS
        paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            os.path.expanduser('~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        ]
    else:  # Linux
        paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
        ]

    for path in paths:
        if os.path.exists(path):
            return path

    return None


def open_chrome_with_debugging(port=9222, chrome_path=None, prompt_user=True):
    """提示用户打开带调试模式的Chrome，如果已有实例则返回True"""

    # 检查端口是否已在使用
    if is_port_in_use(port):
        # 检查是否有可用的调试实例
        instances = get_chrome_debugging_instances(port)
        if instances:
            logger.info(f"已检测到Chrome实例，将连接到端口 {port}")
            return True
        else:
            logger.warning(f"端口 {port} 已被占用，但未找到可用的Chrome实例")

    if chrome_path is None:
        chrome_path = find_chrome_path()

    if chrome_path and os.path.exists(chrome_path):
        cmd = f'"{chrome_path}" --remote-debugging-port={port}'
        logger.info(f"请使用以下命令启动Chrome: {cmd}")

        # 尝试自动启动Chrome
        try:
            logger.info("正在尝试自动启动Chrome...")
            subprocess.Popen([chrome_path, f"--remote-debugging-port={port}"])

            # 等待Chrome启动
            for i in range(10):
                time.sleep(1)
                logger.info(f"等待Chrome启动 ({i + 1}/10)...")
                if is_port_in_use(port) and get_chrome_debugging_instances(port):
                    logger.info("Chrome已成功启动，并开启了远程调试")
                    return True

            logger.warning("Chrome已启动，但未能检测到调试实例，可能需要手动设置")
        except Exception as e:
            logger.error(f"自动启动Chrome失败: {e}")

    if prompt_user:
        logger.info(f"请手动启动Chrome浏览器，并访问B站确保已登录")
        logger.info(f"然后使用以下参数重新启动Chrome: --remote-debugging-port={port}")
        logger.info(f"完整命令示例: chrome.exe --remote-debugging-port={port}")
        logger.info(f"启动后，按回车键继续...")
        input()

        # 再次检查端口
        if is_port_in_use(port):
            instances = get_chrome_debugging_instances(port)
            if instances:
                logger.info(f"已检测到Chrome实例，将连接到端口 {port}")
                return True
            else:
                logger.warning(f"端口 {port} 已被占用，但未找到可用的Chrome实例")
                return False
        else:
            logger.error(f"未检测到Chrome实例，请确保使用了正确的参数启动Chrome")
            return False

    return False


async def upload_to_bilibili(
        video_path: str,
        title: str,
        tags: List[str],
        description: str,
        category: str = "知识",
        port=9222,
        login_timeout=300
):
    """上传视频到B站"""

    # 检查视频文件是否存在
    if not os.path.exists(video_path):
        logger.error(f"视频文件不存在: {video_path}")
        return False, "视频文件不存在"

    # 检查Chrome是否已启动并开启了调试模式
    if not is_port_in_use(port):
        logger.error(f"未检测到Chrome实例，请确保Chrome已启动并开启了远程调试端口 {port}")
        return False, f"未检测到Chrome实例 (端口 {port})"

    instances = get_chrome_debugging_instances(port)
    if not instances:
        logger.error(f"未检测到Chrome调试实例，请确保使用了正确的参数启动Chrome")
        logger.info(f"启动Chrome的命令: chrome.exe --remote-debugging-port={port}")
        return False, "未检测到Chrome调试实例"

    # 导入playwright
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("请先安装playwright: pip install playwright")
        return False, "缺少playwright库，请使用命令安装: pip install playwright"

    # 定义分区映射
    category_map = {
        "知识": 201,  # 科学科普
        "科技": 188,  # 科技
        "数码": 95,  # 数码
        "游戏": 4,  # 游戏
        "生活": 160,  # 生活
        "美食": 76,  # 美食
        "鬼畜": 119,  # 鬼畜
        "时尚": 155,  # 时尚
        "娱乐": 5,  # 娱乐
        "音乐": 3,  # 音乐
        "影视": 181,  # 影视
        "舞蹈": 129,  # 舞蹈
        "动画": 1,  # 动画
        "汽车": 223,  # 汽车
        "运动": 234,  # 运动
    }
    tid = category_map.get(category, 201)  # 默认使用知识分类

    # 使用Playwright连接到Chrome
    try:
        async with async_playwright() as p:
            logger.info(f"连接到Chrome浏览器 (端口 {port})...")
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{port}")

            # 创建新的上下文和页面
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 打开B站投稿页面
                logger.info("正在打开B站投稿页面...")
                await page.goto("https://member.bilibili.com/platform/upload/video/frame", timeout=60000)

                # 等待页面加载
                await page.wait_for_load_state("networkidle")

                # 检查登录状态
                logger.info("检查登录状态...")

                # 尝试查找上传按钮或标题输入框（表示已登录）
                is_logged_in = False
                try:
                    await page.wait_for_selector(
                        ".upload-btn, .webuploader-container, input[placeholder='请输入稿件标题']", timeout=5000)
                    is_logged_in = True
                    logger.info("已登录B站")
                except Exception:
                    logger.warning("未登录B站，需要登录")

                # 如果未登录，等待用户登录
                if not is_logged_in:
                    # 检查是否有登录按钮，如果有则提示用户点击
                    login_btn = await page.query_selector("a:has-text('登录')")
                    if login_btn:
                        logger.info("检测到登录按钮，请在Chrome浏览器中完成登录...")

                    logger.info(f"请在Chrome浏览器中完成登录，超时时间为 {login_timeout} 秒...")
                    logger.info("提示: 可直接在已打开的Chrome浏览器中登录B站")

                    try:
                        # 等待登录成功的指示器
                        await page.wait_for_selector(
                            ".upload-btn, .webuploader-container, input[placeholder='请输入稿件标题']",
                            timeout=login_timeout * 1000)
                        logger.info("登录成功")
                    except Exception as e:
                        # 截图记录当前状态
                        os.makedirs("logs", exist_ok=True)
                        screenshot_path = f"logs/bilibili_login_timeout_{int(time.time())}.png"
                        await page.screenshot(path=screenshot_path)
                        logger.error(f"等待登录超时: {e}")
                        logger.info(f"当前页面状态截图: {screenshot_path}")

                        # 检查是否在登录页面
                        if "passport.bilibili.com" in page.url:
                            logger.info("当前在登录页面，但未完成登录")
                            return False, f"登录超时，请手动登录B站后重试。当前页面状态截图: {screenshot_path}"
                        else:
                            # 可能页面跳转了但没有找到预期元素，尝试重新导航到上传页面
                            logger.info("尝试重新导航到上传页面...")
                            await page.goto("https://member.bilibili.com/platform/upload/video/frame", timeout=60000)
                            await page.wait_for_load_state("networkidle")

                            # 再次检查登录状态
                            try:
                                await page.wait_for_selector(
                                    ".upload-btn, .webuploader-container, input[placeholder='请输入稿件标题']",
                                    timeout=5000)
                                logger.info("重新导航后检测到已登录")
                            except Exception:
                                return False, f"登录失败或页面结构变化，请在Chrome浏览器中手动登录后重试。当前页面状态截图: {screenshot_path}"

                # 上传视频
                logger.info(f"开始上传视频: {video_path}")

                # 查找文件上传输入框
                try:
                    file_input = await page.wait_for_selector('input[type="file"]', timeout=10000)
                    if not file_input:
                        raise Exception("找不到文件上传输入框")
                except Exception as e:
                    logger.error(f"找不到文件上传输入框: {e}")

                    # 截图记录当前状态
                    os.makedirs("logs", exist_ok=True)
                    screenshot_path = f"logs/bilibili_error_no_upload_input_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"当前状态截图已保存: {screenshot_path}")

                    # 尝试刷新页面后重试
                    logger.info("尝试刷新页面后重试...")
                    await page.reload()
                    await page.wait_for_load_state("networkidle")

                    try:
                        file_input = await page.wait_for_selector('input[type="file"]', timeout=10000)
                        if not file_input:
                            return False, f"刷新页面后仍找不到文件上传输入框，请查看截图: {screenshot_path}"
                        logger.info("刷新页面后找到了上传输入框")
                    except Exception:
                        return False, f"找不到文件上传输入框，请查看截图: {screenshot_path}"

                # 设置文件路径
                try:
                    await file_input.set_input_files(video_path)
                    logger.info("已选择视频文件")
                except Exception as e:
                    logger.error(f"设置文件路径失败: {e}")
                    return False, f"设置文件路径失败: {str(e)}"

                # 等待视频上传开始
                try:
                    await page.wait_for_selector(".bili-progress, .info-box-progress, .upload-progress", timeout=15000)
                    logger.info("视频上传开始...")
                except Exception as e:
                    logger.error(f"等待上传开始超时: {e}")

                    # 截图记录当前状态
                    screenshot_path = f"logs/bilibili_error_upload_not_start_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path)

                    return False, f"上传未开始，请查看截图了解详情: {screenshot_path}"

                # 等待上传完成
                max_wait_time = 60 * 30  # 最多等待30分钟
                start_time = time.time()
                last_progress = None
                last_progress_update_time = time.time()

                while True:
                    elapsed_time = time.time() - start_time
                    if elapsed_time > max_wait_time:
                        screenshot_path = f"logs/bilibili_upload_timeout_{int(time.time())}.png"
                        await page.screenshot(path=screenshot_path)
                        return False, f"上传超时（{max_wait_time / 60}分钟），请检查网络状况。截图: {screenshot_path}"

                    # 检查进度条
                    progress_element = await page.query_selector(".bili-progress, .info-box-progress, .upload-progress")
                    if not progress_element:
                        # 进度条消失可能表示上传完成
                        await asyncio.sleep(2)
                        # 再次检查是否有标题输入框，确认上传完成
                        if await page.query_selector('input[placeholder="请输入稿件标题"]'):
                            logger.info("视频上传完成")
                            break
                    else:
                        progress_text = await progress_element.text_content()
                        if progress_text and progress_text != last_progress:
                            elapsed_min = int(elapsed_time / 60)
                            elapsed_sec = int(elapsed_time % 60)
                            logger.info(f"上传进度: {progress_text} (已用时: {elapsed_min}分{elapsed_sec}秒)")
                            last_progress = progress_text
                            last_progress_update_time = time.time()

                        # 检查上传是否卡住（超过5分钟没有进度更新）
                        if time.time() - last_progress_update_time > 300:
                            logger.warning(f"上传似乎卡住了，5分钟内没有进度更新: {last_progress}")
                            # 这里不直接中断，只是记录警告，因为某些情况下进度条可能不会更新但上传仍在进行

                        if progress_text and "100%" in progress_text:
                            logger.info("视频上传完成")
                            # 等待一会儿确保处理完成
                            await asyncio.sleep(3)
                            break

                    # 短暂等待后再次检查
                    await asyncio.sleep(2)

                # 填写视频信息
                logger.info("填写视频信息...")

                # 等待标题输入框出现
                try:
                    title_input = await page.wait_for_selector('input[placeholder="请输入稿件标题"]', timeout=15000)
                    if not title_input:
                        raise Exception("找不到标题输入框")

                    # 填写标题
                    await title_input.fill("")
                    await title_input.fill(title)
                    logger.info(f"已填写标题: {title}")
                except Exception as e:
                    logger.error(f"填写标题失败: {e}")

                    # 截图记录当前状态
                    screenshot_path = f"logs/bilibili_error_title_input_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path)

                    return False, f"填写标题失败: {str(e)}，可能上传成功但无法编辑信息，请手动检查。截图: {screenshot_path}"

                # 填写简介
                try:
                    desc_input = await page.wait_for_selector(
                        'textarea.upload-content-input, .content-desc-editor textarea', timeout=5000)
                    if desc_input:
                        await desc_input.fill(description)
                        logger.info("已填写简介")
                except Exception as e:
                    logger.warning(f"填写简介失败: {e}，继续下一步")

                # 选择分区
                try:
                    logger.info(f"选择分区: {category}")
                    # 点击分区选择器
                    select_area = await page.query_selector(".select-item-cont, .category-select-wrp")
                    if select_area:
                        await select_area.click()
                        await asyncio.sleep(1)

                        # 查找并选择分区
                        category_items = await page.query_selector_all(".category-item")
                        category_selected = False

                        for item in category_items:
                            item_text = await item.text_content()
                            if category in item_text:
                                await item.click()
                                await asyncio.sleep(1)
                                category_selected = True
                                logger.info(f"已选择主分区: {item_text}")
                                break

                        if not category_selected and category_items:
                            # 如果没有找到匹配的分区，选择第一个
                            await category_items[0].click()
                            await asyncio.sleep(1)
                            logger.info("未找到匹配分区，已选择默认分区")

                        # 选择子分区
                        sub_items = await page.query_selector_all(".sub-category-item")
                        if sub_items:
                            await sub_items[0].click()
                            logger.info("已选择子分区")
                except Exception as e:
                    logger.warning(f"选择分区出错: {e}，将使用默认分区")

                # 添加标签
                logger.info(f"添加标签: {tags}")
                tag_input = await page.query_selector('input[placeholder*="标签"], input[placeholder*="回车提交"]')
                if tag_input:
                    for tag in tags[:10]:  # 最多10个标签
                        await tag_input.fill("")
                        await tag_input.fill(tag)
                        await tag_input.press("Enter")
                        await asyncio.sleep(0.5)
                    logger.info("已添加标签")
                else:
                    logger.warning("找不到标签输入框，跳过添加标签")

                # 点击投稿按钮
                logger.info("准备提交视频...")

                # 截图记录提交前状态
                os.makedirs("logs", exist_ok=True)
                screenshot_path = f"logs/bilibili_before_submit_{int(time.time())}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"提交前截图已保存: {screenshot_path}")

                # 查找提交按钮
                submit_btn = None
                try:
                    # 尝试多种选择器找到提交按钮
                    selectors = [
                        'button:has-text("立即投稿")',
                        'button:has-text("提交")',
                        'span:has-text("立即投稿")',
                        '//button[contains(., "立即投稿")]',
                        '//button[contains(., "提交")]',
                        '//span[contains(., "立即投稿")]',
                        '.submit-add',
                        '.submit-btn'
                    ]

                    for selector in selectors:
                        submit_btn = await page.query_selector(selector)
                        if submit_btn:
                            logger.info(f"找到提交按钮: {selector}")
                            break

                    if not submit_btn:
                        logger.error("找不到提交按钮")
                        return False, f"找不到提交按钮，详情请查看截图: {screenshot_path}"

                    # 点击提交按钮
                    await submit_btn.click()
                    logger.info("已点击提交按钮")

                    # 处理可能的确认对话框
                    try:
                        confirm_selectors = [
                            'button:has-text("确定")',
                            'span:has-text("确定")',
                            '//button[contains(., "确定")]',
                            '//span[contains(., "确定")]'
                        ]

                        for selector in confirm_selectors:
                            confirm_btn = await page.wait_for_selector(selector, timeout=5000)
                            if confirm_btn:
                                await confirm_btn.click()
                                logger.info("已确认提交")
                                break
                    except Exception:
                        logger.info("无需确认提交")

                    # 等待投稿结果
                    try:
                        success_selectors = [
                            ':has-text("投稿成功")',
                            ':has-text("已投稿")',
                            ':has-text("稿件提交成功")',
                            '//div[contains(., "投稿成功")]',
                            '//div[contains(., "已投稿")]',
                            '//div[contains(., "稿件提交成功")]'
                        ]

                        for selector in success_selectors:
                            try:
                                success_msg = await page.wait_for_selector(selector, timeout=15000)
                                if success_msg:
                                    logger.info("视频投稿成功")

                                    # 尝试获取视频链接
                                    video_link = await page.query_selector('a[href*="bilibili.com/video/"]')
                                    if video_link:
                                        video_url = await video_link.get_attribute('href')
                                        logger.info(f"视频链接: {video_url}")
                                        return True, video_url

                                    return True, "投稿成功，但未获取到视频链接"
                            except:
                                continue

                        # 如果所有选择器都找不到成功消息，截图记录当前状态
                        screenshot_path = f"logs/bilibili_after_submit_{int(time.time())}.png"
                        await page.screenshot(path=screenshot_path)
                        logger.info(f"提交后截图已保存: {screenshot_path}")

                        # 检查当前URL，如果跳转到稿件管理页面，可能是成功了
                        current_url = page.url
                        if "member.bilibili.com/platform/home" in current_url or "member.bilibili.com/platform/upload-manager" in current_url:
                            logger.info("已跳转到稿件管理页面，视频可能已成功投稿")
                            return True, "视频可能已成功投稿，请在B站稿件管理页面查看"

                        # 等待一段时间再次检查页面状态
                        logger.info("未明确确认投稿结果，等待5秒后再次检查...")
                        await asyncio.sleep(5)

                        # 再次检查当前URL
                        current_url = page.url
                        if "member.bilibili.com/platform/home" in current_url or "member.bilibili.com/platform/upload-manager" in current_url:
                            logger.info("延迟后检测到已跳转到稿件管理页面，视频可能已成功投稿")
                            return True, "视频可能已成功投稿，请在B站稿件管理页面查看"

                        # 如果还在上传页面但没有明确的成功消息，检查是否有错误提示
                        error_element = await page.query_selector(".error-msg, .bili-message__content")
                        if error_element:
                            error_text = await error_element.text_content()
                            logger.error(f"投稿时出现错误: {error_text}")
                            return False, f"投稿失败: {error_text}，请查看截图: {screenshot_path}"

                        return False, f"未能确认投稿结果，请查看截图: {screenshot_path}"

                    except Exception as e:
                        logger.error(f"等待投稿结果时出错: {e}")

                        # 截图保存错误状态
                        screenshot_path = f"logs/bilibili_error_{int(time.time())}.png"
                        await page.screenshot(path=screenshot_path)
                        logger.info(f"错误截图已保存: {screenshot_path}")

                        return False, f"投稿过程中出错，详情请查看错误截图: {screenshot_path}"

                except Exception as e:
                    logger.error(f"点击提交按钮出错: {e}")

                    # 截图保存错误状态
                    screenshot_path = f"logs/bilibili_submit_error_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path)

                    return False, f"点击提交按钮出错: {str(e)}"

            except Exception as e:
                logger.error(f"视频上传过程中出错: {e}")
                import traceback
                logger.error(traceback.format_exc())

                # 尝试截图保存错误状态
                try:
                    os.makedirs("logs", exist_ok=True)
                    screenshot_path = f"logs/bilibili_error_{int(time.time())}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"错误截图已保存: {screenshot_path}")
                except Exception:
                    pass

                return False, f"上传失败: {str(e)}"

            finally:
                # 关闭页面和上下文
                await page.close()
                await context.close()

    except Exception as e:
        logger.error(f"连接Chrome浏览器出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"连接浏览器失败: {str(e)}"

    return False, "上传过程未完成"


def upload_video(
        video_path: str,
        title: str,
        tags: List[str],
        description: str,
        category: str = "知识",
        port: int = 9222,
        login_timeout: int = 300  # 新增参数，登录超时时间
) -> Tuple[bool, str]:
    """上传视频到B站的主函数

    Args:
        video_path: 视频文件路径
        title: 视频标题
        tags: 标签列表
        description: 视频描述
        category: 视频分类
        port: Chrome远程调试端口
        login_timeout: 登录超时时间（秒）

    Returns:
        Tuple[bool, str]: 上传结果（成功/失败）和详细信息（视频链接或错误信息）
    """
    # 确保Chrome已启动并开启了调试模式
    chrome_ready = is_port_in_use(port) and get_chrome_debugging_instances(port)

    if not chrome_ready:
        logger.info("未检测到可用的Chrome调试实例，请先手动启动Chrome")
        if not open_chrome_with_debugging(port=port, prompt_user=True):
            return False, f"无法连接到Chrome调试实例 (端口 {port})"

    # 运行异步上传函数
    try:
        return asyncio.run(upload_to_bilibili(
            video_path=video_path,
            title=title,
            tags=tags,
            description=description,
            category=category,
            port=port,
            login_timeout=login_timeout
        ))
    except KeyboardInterrupt:
        logger.warning("用户中断上传")
        return False, "用户中断上传"
    except Exception as e:
        logger.error(f"上传过程中出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"上传出错: {str(e)}"


# 主函数 - 直接写死参数而不使用命令行解析
if __name__ == "__main__":
    # 设置日志格式
    logger.remove()
    logger.add(sys.stdout,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    logger.add("logs/bilibili_upload_{time}.log", rotation="500 MB", retention="10 days")

    # 创建logs目录（如果不存在）
    os.makedirs("logs", exist_ok=True)

    # 您可以直接在这里修改上传参数
    video_path = "G:/真人出镜.mp4"  # 视频文件路径
    title = "测试视频上传"  # 视频标题
    tags = ["测试", "自动上传"]  # 标签列表
    description = "这是一个自动上传的测试视频"  # 视频描述
    category = "知识"  # 视频分类
    port = 9222  # Chrome远程调试端口
    login_timeout = 600  # 登录超时时间（秒）

    logger.info(f"上传视频: {video_path}")
    logger.info(f"标题: {title}")
    logger.info(f"标签: {tags}")
    logger.info(f"简介: {description}")
    logger.info(f"分类: {category}")
    logger.info(f"Chrome远程调试端口: {port}")
    logger.info(f"登录超时时间: {login_timeout}秒")
    logger.info("请确保Chrome已经以远程调试模式启动并登录了B站账号")
    logger.info("启动Chrome的命令: chrome.exe --remote-debugging-port=9222")

    # 上传视频
    success, result = upload_video(
        video_path=video_path,
        title=title,
        tags=tags,
        description=description,
        category=category,
        port=port,
        login_timeout=login_timeout
    )

    if success:
        logger.info(f"上传成功: {result}")
        sys.exit(0)
    else:
        logger.error(f"上传失败: {result}")
        sys.exit(1)