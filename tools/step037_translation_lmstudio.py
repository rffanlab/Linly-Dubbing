# -*- coding: utf-8 -*-
import json
import os
import time
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI, APIConnectionError, APIError # 导入 openai 库

# 加载 .env 文件中的环境变量
load_dotenv()

# --- 配置 LM Studio ---
# LM Studio 服务地址，通常是这个，请根据你的 LM Studio 设置确认
LM_STUDIO_API_BASE = os.getenv('LM_STUDIO_API_BASE', 'http://localhost:1234/v1')
# 在 LM Studio 中加载的模型标识符。
# 这个需要和你 LM Studio "Local Server" 选项卡中看到的模型文件对应，
# 或者通常可以写一个占位符，因为 LM Studio 目前一次只服务一个模型。
# 使用你要求的 'qwen2.5-14b-instruct' 作为默认值，但请在 LM Studio 确认实际加载的模型。
# 注意：截至我所知，官方还没有 Qwen2.5-14B，可能是 Qwen1.5-14B 或 Qwen2-7B 等，请核对。
LM_STUDIO_MODEL = os.getenv('LM_STUDIO_MODEL', 'qwen/Qwen2-7B-Instruct-GGUF') # 使用一个常见的 GGUF 示例

# 全局 OpenAI 客户端实例
client = None

def init_llm_client():
    """
    初始化 OpenAI 客户端以连接到 LM Studio。
    """
    global client
    if client is None:
        logger.info(f"Initializing OpenAI client for LM Studio at {LM_STUDIO_API_BASE}")
        # api_key 对于本地 LM Studio 通常不是必需的，但 openai 库需要它，可以填任意非空字符串
        client = OpenAI(base_url=LM_STUDIO_API_BASE, api_key="lm-studio")
        # 可以选择性地添加一个简单的连接测试
        try:
            client.models.list() # 尝试列出模型，验证连接
            logger.success("Successfully connected to LM Studio API.")
        except APIConnectionError as e:
            logger.error(f"Failed to connect to LM Studio at {LM_STUDIO_API_BASE}.")
            logger.error(f"Please ensure LM Studio is running and the server is enabled.")
            logger.error(f"Error details: {e}")
            client = None # 连接失败，重置 client
        except APIError as e:
            logger.warning(f"Connected to LM Studio, but API returned an error during initialization: {e}")
            # 可能仍然可以工作，所以不重置 client，但记录警告
        except Exception as e:
            logger.error(f"An unexpected error occurred during client initialization: {e}")
            client = None # 未知错误，重置 client


def llm_response(messages, temperature=0.7, max_tokens=512):
    """
    使用 LM Studio 服务获取 LLM 响应。

    Args:
        messages (list): OpenAI 格式的消息列表，例如 [{"role": "user", "content": "你好"}]
        temperature (float): 控制生成文本的随机性，默认为 0.7。
        max_tokens (int): 生成响应的最大 token 数量，默认为 512。

    Returns:
        str: 模型生成的响应文本，如果出错则返回空字符串或错误信息。
    """
    global client
    # 如果客户端未初始化，尝试初始化
    if client is None:
        init_llm_client()
        # 如果初始化后仍然为 None，说明连接失败
        if client is None:
            logger.error("LM Studio client is not available. Cannot process request.")
            return "Error: Could not connect to LM Studio."

    logger.info(f"Sending request to LM Studio with model: {LM_STUDIO_MODEL}")
    logger.debug(f"Messages: {messages}")

    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=LM_STUDIO_MODEL, # 指定要使用的模型
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            # stream=False # 可以选择是否使用流式输出，这里设为 False 获取完整响应
        )
        end_time = time.time()
        logger.info(f"Received response from LM Studio in {end_time - start_time:.2f} seconds.")

        # 提取响应内容
        if response.choices:
            result = response.choices[0].message.content.strip()
            logger.debug(f"Response content: {result}")
            return result
        else:
            logger.warning("Received empty response from LM Studio.")
            return "Error: Received empty response from the model."

    except APIConnectionError as e:
        logger.error(f"Connection Error: Failed to connect to LM Studio at {LM_STUDIO_API_BASE}.")
        logger.error(f"Is LM Studio running and the server active? Details: {e}")
        # 尝试重新初始化客户端，也许服务刚刚启动
        client = None
        return f"Error: Connection failed - {e}"
    except APIError as e:
        logger.error(f"API Error: LM Studio returned an error. Status Code: {e.status_code}, Message: {e.message}")
        # 检查是否是模型未找到的错误
        if e.status_code == 404 or "model_not_found" in str(e).lower():
             logger.error(f"Model '{LM_STUDIO_MODEL}' might not be loaded or identifier is incorrect in LM Studio.")
        return f"Error: API error - {e.message}"
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return f"Error: Unexpected error - {e}"

# --- 主程序入口 ---
if __name__ == '__main__':
    # 配置 Loguru 日志级别
    # logger.add("file_{time}.log") # 可以取消注释以保存日志到文件
    logger.remove() # 移除默认的 stderr 输出
    logger.add(lambda msg: print(msg, end=''), level="INFO") # 重新添加 INFO 级别以上的输出到控制台

    # 确保 LM Studio 正在运行，并且已加载指定的模型 (qwen/Qwen2-7B-Instruct-GGUF 或你在 .env 中设置的)
    # 并已启动 "Local Server"

    logger.info("Starting LLM test with LM Studio...")

    # 第一次调用会触发客户端初始化
    test_message = [{"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "你好，介绍一下你自己"}]

    response = llm_response(test_message)

    print("\n--- Response ---")
    if response.startswith("Error:"):
        logger.error(f"Test failed: {response}")
    else:
        logger.success("Test completed successfully.")
        print(f"LLM Response:\n{response}")

    # 可以再测试一次，这次应该会复用已初始化的客户端
    logger.info("\nPerforming another test...")
    test_message_2 = [{"role": "user", "content": "给我讲个关于程序员的笑话"}]
    response_2 = llm_response(test_message_2, temperature=0.8)
    print("\n--- Response 2 ---")
    if response_2.startswith("Error:"):
        logger.error(f"Second test failed: {response_2}")
    else:
        logger.success("Second test completed successfully.")
        print(f"LLM Response 2:\n{response_2}")