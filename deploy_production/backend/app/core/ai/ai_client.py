"""
AI客户端 - 硅基流动API调用（按官方文档优化）

优化策略：
1. 使用流式输出（stream=true）避免504超时
2. 多模型fallback策略
3. 完善的错误处理和重试机制
4. 详细的日志记录

参考文档：https://docs.siliconflow.cn/cn/faqs/stream-mode
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """统一的AI客户端异常."""
    pass


@dataclass
class ModelConfig:
    """模型配置."""
    name: str           # 模型名称
    api_base: str       # API地址
    api_key: str        # API密钥
    priority: int = 0   # 优先级（数字越小优先级越高）
    timeout: int = 45   # 超时时间（秒）


def _get_env_bool(name: str, default: bool = False) -> bool:
    """获取布尔类型环境变量."""
    val = os.getenv(name, "").lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("false", "0", "no", "off"):
        return False
    return default


def _get_env_int(name: str, default: int) -> int:
    """获取整数类型环境变量."""
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def get_model_configs() -> List[ModelConfig]:
    """获取模型配置列表（支持多模型fallback）."""
    configs = []
    primary_key = os.getenv("AI_API_KEY")
    primary_base = os.getenv("AI_API_BASE", "https://api.siliconflow.cn/v1/chat/completions")
    timeout = _get_env_int("AI_TIMEOUT", 45)
    
    if primary_key:
        configs.append(ModelConfig(
            name=os.getenv("AI_MODEL", "Qwen/Qwen3-8B"),
            api_base=primary_base,
            api_key=primary_key,
            priority=0,
            timeout=timeout
        ))
    
    simple_fallbacks = os.getenv("AI_FALLBACK_MODELS_SIMPLE", "")
    if simple_fallbacks and primary_key:
        model_names = [m.strip() for m in simple_fallbacks.split(",") if m.strip()]
        for idx, model_name in enumerate(model_names):
            configs.append(ModelConfig(
                name=model_name,
                api_base=primary_base,
                api_key=primary_key,
                priority=idx + 1,
                timeout=timeout
            ))
    
    configs.sort(key=lambda x: x.priority)
    
    if configs:
        logger.info("🤖 AI模型池: %s", [c.name for c in configs])
    
    return configs


async def _call_with_stream(
    config: ModelConfig,
    messages: List[Dict[str, Any]],
    max_tokens: int = 1536,
    temperature: float = 0.3,
) -> str:
    """流式调用API."""
    payload = {
        "model": config.name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    
    full_content = ""
    started = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            async with client.stream(
                "POST",
                config.api_base,
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise AIClientError(f"API错误 {response.status_code}: {error_text.decode()[:200]}")
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if line == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(line)
                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_content += content
                    except json.JSONDecodeError:
                        continue
        
        elapsed = (time.time() - started) * 1000
        logger.info("✅ AI流式调用成功 model=%s cost_ms=%.1f content_len=%d", config.name, elapsed, len(full_content))
        return full_content
        
    except httpx.TimeoutException as e:
        elapsed = (time.time() - started) * 1000
        logger.warning("⏱️ AI调用超时 model=%s cost_ms=%.1f err=%s", config.name, elapsed, str(e))
        raise AIClientError(f"模型{config.name}超时: {e}")
    except Exception as e:
        elapsed = (time.time() - started) * 1000
        logger.warning("❌ AI调用异常 model=%s cost_ms=%.1f err=%s", config.name, elapsed, str(e))
        raise AIClientError(f"模型{config.name}异常: {e}")


async def _call_without_stream(
    config: ModelConfig,
    messages: List[Dict[str, Any]],
    max_tokens: int = 1536,
    temperature: float = 0.3,
) -> str:
    """非流式调用（备用方案）."""
    payload = {
        "model": config.name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    
    started = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.post(config.api_base, headers=headers, json=payload)
        
        elapsed = (time.time() - started) * 1000
        
        if response.status_code >= 400:
            raise AIClientError(f"API错误 {response.status_code}")
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        logger.info("✅ AI非流式调用成功 model=%s cost_ms=%.1f content_len=%d", config.name, elapsed, len(content))
        return content
        
    except httpx.TimeoutException as e:
        elapsed = (time.time() - started) * 1000
        logger.warning("⏱️ AI调用超时 model=%s cost_ms=%.1f", config.name, elapsed)
        raise AIClientError(f"模型{config.name}超时: {e}")
    except Exception as e:
        elapsed = (time.time() - started) * 1000
        logger.warning("❌ AI调用异常 model=%s cost_ms=%.1f err=%s", config.name, elapsed, str(e))
        raise AIClientError(f"模型{config.name}异常: {e}")


async def post_chat(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    max_tokens: int = 1536,
    temperature: float = 0.3,
    use_stream: Optional[bool] = None,
    max_retry: int = 2,
) -> Dict[str, Any]:
    """调用AI聊天接口，支持多模型fallback."""
    configs = get_model_configs()
    
    if not configs:
        raise AIClientError("未配置AI模型，请设置AI_API_KEY环境变量")
    
    if use_stream is None:
        use_stream = _get_env_bool("AI_STREAM", True)
    
    if model:
        matching_configs = [c for c in configs if c.name == model]
        if matching_configs:
            configs = matching_configs + [c for c in configs if c.name != model]
    
    errors = []
    
    for config in configs:
        logger.info("🔄 尝试AI模型: %s (优先级=%d, 流式=%s)", config.name, config.priority, use_stream)
        
        for attempt in range(1, max_retry + 1):
            try:
                if use_stream:
                    content = await _call_with_stream(config, messages, max_tokens, temperature)
                else:
                    content = await _call_without_stream(config, messages, max_tokens, temperature)
                
                if content and len(content.strip()) > 10:
                    return {
                        "choices": [{"message": {"content": content}}],
                        "model": config.name,
                    }
                else:
                    logger.warning("⚠️ AI返回内容为空或过短，重试...")
                    
            except AIClientError as e:
                error_msg = f"{config.name}(尝试{attempt}): {e}"
                errors.append(error_msg)
                logger.warning("❌ %s", error_msg)
                
                if attempt < max_retry:
                    await asyncio.sleep(min(1.0 * attempt, 3.0))
                    continue
            except Exception as e:
                error_msg = f"{config.name}(尝试{attempt}): 未知错误 {e}"
                errors.append(error_msg)
                logger.error("💥 %s", error_msg)
                break
        
        logger.warning("🔀 模型%s失败，切换到下一个备用模型...", config.name)
    
    error_summary = "; ".join(errors[-5:])
    raise AIClientError(f"所有AI模型调用失败: {error_summary}")


def pick_content_text(response: Dict[str, Any]) -> str:
    """提取AI返回的文本内容."""
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""


def parse_json_safely(text: str) -> Dict[str, Any]:
    """安全解析JSON文本."""
    if not text:
        return {}
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    import re
    json_patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*\}',
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    logger.warning("⚠️ JSON解析失败，返回空字典")
    return {}
