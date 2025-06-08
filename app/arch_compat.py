#!/usr/bin/env python3
"""
架构兼容性模块 - 为ARM Mac提供兼容性支持

这个模块检测系统架构，并在ARM处理器上提供额外的兼容性设置，
以解决可能导致403错误的指纹识别问题。
"""
import logging
import platform
import re
import subprocess
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("arch_compat")

def get_system_info() -> Dict[str, str]:
    """获取系统信息"""
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "architecture": platform.architecture()[0],
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version()
    }
    
    # 检测Apple Silicon
    if info["os"] == "Darwin" and info["machine"] in ("arm64", "aarch64"):
        info["is_apple_silicon"] = "true"
        
        # 尝试获取具体型号 (M1/M2/M3)
        try:
            sysctl_output = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
            if "Apple M1" in sysctl_output:
                info["apple_chip"] = "M1"
            elif "Apple M2" in sysctl_output:
                info["apple_chip"] = "M2"
            elif "Apple M3" in sysctl_output:
                info["apple_chip"] = "M3"
            else:
                info["apple_chip"] = "Unknown Apple Silicon"
        except Exception:
            info["apple_chip"] = "Apple Silicon (unspecified)"
    else:
        info["is_apple_silicon"] = "false"
    
    return info

def is_apple_silicon() -> bool:
    """检查是否为Apple Silicon"""
    return get_system_info().get("is_apple_silicon") == "true"

def get_compatible_user_agents() -> List[str]:
    """返回适合当前架构的User-Agent列表"""
    # 为ARM Mac提供特殊的UA字符串
    if is_apple_silicon():
        return [
            # Intel Mac UA - 掩盖ARM架构
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.57",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/114.0",
            
            # 一些Windows UA来增加多样性
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"
        ]
    else:
        # 标准多样UA列表
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.57"
        ]

def get_request_overrides() -> Dict[str, any]:
    """获取请求参数重写，以规避ARM架构引起的反爬检测"""
    overrides = {}
    
    if is_apple_silicon():
        # 重写请求行为，减少指纹特征
        overrides["http_version"] = "1.1"  # 不使用HTTP/2
        overrides["http2"] = False  # 禁用HTTP/2
        overrides["stream"] = False  # 禁用流式传输
        
        # 禁用某些可能在ARM上表现不同的功能
        overrides["timeout"] = 30  # 增加超时时间
        
        # 删除可能暴露ARM架构的头部
        overrides["headers_to_remove"] = [
            "sec-ch-ua-platform",
            "sec-ch-ua-platform-version",
            "sec-ch-ua-model",
            "sec-ch-ua-mobile",
            "sec-ch-ua-arch"
        ]
    
    return overrides

def apply_compatibility_settings(session) -> None:
    """应用架构兼容性设置到会话对象"""
    if is_apple_silicon():
        logger.info("检测到Apple Silicon (ARM)架构，应用兼容性设置")
        
        # 应用请求参数重写
        overrides = get_request_overrides()
        
        # 修改会话设置
        session.headers.update({
            "Accept-Encoding": "gzip, deflate",  # 避免使用特殊编码
            "Accept-Language": "en-US,en;q=0.9",  # 使用常见语言设置
        })
        
        # 删除可能暴露ARM架构的头部
        for header in overrides.get("headers_to_remove", []):
            if header in session.headers:
                del session.headers[header]
                
        # 应用其他设置
        if hasattr(session, "mount"):
            from requests.adapters import HTTPAdapter
            adapter = HTTPAdapter(max_retries=3)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
    return session

def get_system_report() -> str:
    """获取系统报告，用于调试目的"""
    info = get_system_info()
    
    report_lines = [
        "系统兼容性报告:",
        "----------------",
        f"操作系统: {info.get('os')} {info.get('os_version')}",
        f"处理器: {info.get('processor')}",
        f"架构: {info.get('machine')} ({info.get('architecture')})",
    ]
    
    if info.get("is_apple_silicon") == "true":
        report_lines.extend([
            f"Apple Silicon: {info.get('apple_chip', 'Unknown')}",
            "* 已应用ARM兼容性设置",
            "* 使用Intel Mac的User-Agent伪装",
            "* 已禁用可能泄露架构的HTTP标头"
        ])
    
    report_lines.extend([
        f"Python: {info.get('python_implementation')} {info.get('python_version')}",
        "----------------"
    ])
    
    return "\n".join(report_lines)

# 在导入时输出系统报告
if is_apple_silicon():
    logger.info("检测到Apple Silicon，将使用兼容性模式") 