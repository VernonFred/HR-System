"""
ModelScope 客户端 - 魔塔空间 API 调用

支持模型：
1. Qwen2.5-7B-Instruct - 主力画像模型（日常使用）
2. Qwen2.5-32B-Instruct - 高阶画像模型（高级岗位）
3. DeepSeek-R1-0528 - 专家推理模型（深度分析）

调用限制：
- 默认单账号每天 2000 次 API 调用
- 单模型一般不超过 500 次/天
- DeepSeek-R1 系列约 100 次/天
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ModelLevel(Enum):
    """模型级别."""
    NORMAL = "normal"    # 日常分析 - Qwen2.5-7B
    PRO = "pro"          # 高阶分析 - Qwen2.5-32B
    EXPERT = "expert"    # 专家分析 - DeepSeek-R1


class ModelScopeError(Exception):
    """ModelScope API 调用异常."""
    pass


@dataclass
class ModelScopeConfig:
    """ModelScope 模型配置."""
    model_id: str           # 模型 ID
    level: ModelLevel       # 模型级别
    timeout: int = 60       # 超时时间（秒）
    max_tokens: int = 2048  # 最大输出 token
    daily_limit: int = 500  # 每日调用限制（参考值）


# ModelScope 模型配置
MODELSCOPE_MODELS = {
    # 保留 normal 级别为轻量兜底
    ModelLevel.NORMAL: ModelScopeConfig(
        model_id="Qwen/Qwen2.5-7B-Instruct",
        level=ModelLevel.NORMAL,
        timeout=45,
        max_tokens=1536,
        daily_limit=500
    ),
    # 将 Pro 级别主力模型切换为 DeepSeek-R1（深度分析默认走 DeepSeek）
    ModelLevel.PRO: ModelScopeConfig(
        model_id="deepseek-ai/DeepSeek-R1-0528",
        level=ModelLevel.PRO,
        timeout=120,
        max_tokens=2048,
        daily_limit=100
    ),
    # 专家级仍使用 DeepSeek-R1（与 Pro 一致，供专家模式使用）
    ModelLevel.EXPERT: ModelScopeConfig(
        model_id="deepseek-ai/DeepSeek-R1-0528",
        level=ModelLevel.EXPERT,
        timeout=120,
        max_tokens=2048,
        daily_limit=100
    ),
}


def _get_modelscope_api_key() -> Optional[str]:
    """获取 ModelScope API Key."""
    return os.getenv("MODELSCOPE_API_KEY")


def _get_modelscope_api_base() -> str:
    """获取 ModelScope API Base URL."""
    return os.getenv("MODELSCOPE_API_BASE", "https://api-inference.modelscope.cn/v1/chat/completions")


def _get_api_key_expires() -> Optional[str]:
    """获取 API Key 过期时间."""
    return os.getenv("MODELSCOPE_API_KEY_EXPIRES")


def is_modelscope_available() -> bool:
    """检查 ModelScope 是否可用."""
    return bool(_get_modelscope_api_key())


def check_api_key_expiry() -> Dict[str, Any]:
    """
    检查 API Key 过期状态.
    
    Returns:
        {
            "available": bool,
            "expires": str or None,
            "days_remaining": int or None,
            "warning": str or None
        }
    """
    from datetime import datetime
    
    api_key = _get_modelscope_api_key()
    expires_str = _get_api_key_expires()
    
    result = {
        "available": bool(api_key),
        "expires": expires_str,
        "days_remaining": None,
        "warning": None,
    }
    
    if not api_key:
        result["warning"] = "未配置 MODELSCOPE_API_KEY"
        return result
    
    if expires_str:
        try:
            expires_date = datetime.strptime(expires_str, "%Y-%m-%d")
            days_remaining = (expires_date - datetime.now()).days
            result["days_remaining"] = days_remaining
            
            if days_remaining < 0:
                result["warning"] = f"API Key 已过期 {-days_remaining} 天，请更新！"
                logger.error(f"⚠️ ModelScope API Key 已过期！")
            elif days_remaining < 7:
                result["warning"] = f"API Key 将在 {days_remaining} 天后过期，请及时更新"
                logger.warning(f"⚠️ ModelScope API Key 将在 {days_remaining} 天后过期")
            elif days_remaining < 90:
                logger.info(f"📅 ModelScope API Key 剩余 {days_remaining} 天")
        except ValueError:
            logger.warning(f"无法解析过期时间: {expires_str}")
    
    return result


async def call_modelscope(
    messages: List[Dict[str, Any]],
    level: ModelLevel = ModelLevel.NORMAL,
    max_tokens: Optional[int] = None,
    temperature: float = 0.3,
    use_stream: bool = True,
) -> Dict[str, Any]:
    """
    调用 ModelScope API.
    
    Args:
        messages: 对话消息列表
        level: 模型级别（NORMAL/PRO/EXPERT）
        max_tokens: 最大输出 token（可选，默认使用配置值）
        temperature: 温度参数
        use_stream: 是否使用流式输出
        
    Returns:
        API 响应字典
        
    Raises:
        ModelScopeError: API 调用失败
    """
    api_key = _get_modelscope_api_key()
    if not api_key:
        raise ModelScopeError("未配置 MODELSCOPE_API_KEY 环境变量")
    
    config = MODELSCOPE_MODELS.get(level)
    if not config:
        raise ModelScopeError(f"未知的模型级别: {level}")
    
    api_base = _get_modelscope_api_base()
    actual_max_tokens = max_tokens or config.max_tokens
    
    logger.info(
        "🚀 调用 ModelScope 模型: %s (level=%s, timeout=%ds)",
        config.model_id, level.value, config.timeout
    )
    
    if use_stream:
        content = await _call_modelscope_stream(
            api_base, api_key, config, messages, actual_max_tokens, temperature
        )
    else:
        content = await _call_modelscope_sync(
            api_base, api_key, config, messages, actual_max_tokens, temperature
        )
    
    return {
        "choices": [{"message": {"content": content}}],
        "model": config.model_id,
        "level": level.value,
    }


async def _call_modelscope_stream(
    api_base: str,
    api_key: str,
    config: ModelScopeConfig,
    messages: List[Dict[str, Any]],
    max_tokens: int,
    temperature: float,
) -> str:
    """流式调用 ModelScope API."""
    payload = {
        "model": config.model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    
    full_content = ""
    started = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            async with client.stream(
                "POST",
                api_base,
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise ModelScopeError(
                        f"ModelScope API 错误 {response.status_code}: {error_text.decode()[:200]}"
                    )
                
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
        logger.info(
            "✅ ModelScope 流式调用成功 model=%s cost_ms=%.1f content_len=%d",
            config.model_id, elapsed, len(full_content)
        )
        return full_content
        
    except httpx.TimeoutException as e:
        elapsed = (time.time() - started) * 1000
        logger.warning(
            "⏱️ ModelScope 调用超时 model=%s cost_ms=%.1f err=%s",
            config.model_id, elapsed, str(e)
        )
        raise ModelScopeError(f"模型 {config.model_id} 超时: {e}")
    except Exception as e:
        elapsed = (time.time() - started) * 1000
        logger.warning(
            "❌ ModelScope 调用异常 model=%s cost_ms=%.1f err=%s",
            config.model_id, elapsed, str(e)
        )
        raise ModelScopeError(f"模型 {config.model_id} 异常: {e}")


async def _call_modelscope_sync(
    api_base: str,
    api_key: str,
    config: ModelScopeConfig,
    messages: List[Dict[str, Any]],
    max_tokens: int,
    temperature: float,
) -> str:
    """同步调用 ModelScope API."""
    payload = {
        "model": config.model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    started = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.post(api_base, headers=headers, json=payload)
        
        elapsed = (time.time() - started) * 1000
        
        if response.status_code >= 400:
            raise ModelScopeError(f"ModelScope API 错误 {response.status_code}")
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        logger.info(
            "✅ ModelScope 同步调用成功 model=%s cost_ms=%.1f content_len=%d",
            config.model_id, elapsed, len(content)
        )
        return content
        
    except httpx.TimeoutException as e:
        elapsed = (time.time() - started) * 1000
        logger.warning("⏱️ ModelScope 调用超时 model=%s cost_ms=%.1f", config.model_id, elapsed)
        raise ModelScopeError(f"模型 {config.model_id} 超时: {e}")
    except Exception as e:
        elapsed = (time.time() - started) * 1000
        logger.warning(
            "❌ ModelScope 调用异常 model=%s cost_ms=%.1f err=%s",
            config.model_id, elapsed, str(e)
        )
        raise ModelScopeError(f"模型 {config.model_id} 异常: {e}")


def get_model_info(level: ModelLevel) -> Dict[str, Any]:
    """获取模型信息."""
    config = MODELSCOPE_MODELS.get(level)
    if not config:
        return {}
    return {
        "model_id": config.model_id,
        "level": level.value,
        "timeout": config.timeout,
        "max_tokens": config.max_tokens,
        "daily_limit": config.daily_limit,
    }


def get_all_models_info() -> List[Dict[str, Any]]:
    """获取所有模型信息."""
    return [get_model_info(level) for level in ModelLevel]


def get_modelscope_status() -> Dict[str, Any]:
    """
    获取 ModelScope 完整状态.
    
    Returns:
        {
            "available": bool,
            "api_key_status": {...},
            "models": [...],
            "api_base": str
        }
    """
    api_key_status = check_api_key_expiry()
    
    return {
        "available": api_key_status["available"],
        "api_key_status": api_key_status,
        "models": get_all_models_info() if api_key_status["available"] else [],
        "api_base": _get_modelscope_api_base(),
    }

