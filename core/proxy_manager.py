"""
Qingxin Translator - Proxy Manager
代理管理模块
"""

import os
import winreg


def setup_proxy():
    """自动检测并设置系统代理"""
    # 如果已经设置了代理环境变量，跳过
    if os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY'):
        return os.environ.get('HTTP_PROXY') or os.environ.get('HTTPS_PROXY')
    
    try:
        # 读取Windows系统代理设置
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        )
        
        # 检查代理是否启用
        proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
        if proxy_enable:
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if proxy_server:
                proxy_url = f"http://{proxy_server}"
                os.environ['HTTP_PROXY'] = proxy_url
                os.environ['HTTPS_PROXY'] = proxy_url
                os.environ['http_proxy'] = proxy_url
                os.environ['https_proxy'] = proxy_url
                return proxy_url
        
        winreg.CloseKey(key)
    except Exception:
        pass
    
    return None


def get_proxy_url():
    """获取代理URL"""
    return os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY') or \
           os.environ.get('https_proxy') or os.environ.get('http_proxy')


def get_proxy_dict():
    """获取代理字典（用于requests等库）"""
    proxy = get_proxy_url()
    if proxy:
        return {'http': proxy, 'https': proxy}
    return None


# 启动时自动设置代理
setup_proxy()
