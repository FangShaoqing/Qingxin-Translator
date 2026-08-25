"""
Qingxin Translator - Update Manager
更新下载与安装管理

流程：
1. download_update(): 后台下载安装包到用户数据目录
2. install_update(now=True): 立即安装——启动安装程序（静默）+ 退出应用
3. install_update(now=False): 稍后安装——写待安装标志，退出应用时静默执行
"""

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from app.constants import APP_NAME, DATA_DIR
from core.logger import log

# 更新包目录（用户数据目录下，可写）
UPDATE_DIR = DATA_DIR / "updates"
PENDING_FILE = DATA_DIR / "pending_install.json"

# Inno Setup 静默安装参数（覆盖原程序：安装脚本内置 taskkill 结束旧进程）
SILENT_ARGS = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/NOCANCEL"]


def _ensure_dirs():
    """确保更新目录存在"""
    try:
        UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.warning(f"Create update dir failed: {e}")


def download_update(url: str, version: str, on_done, on_error) -> bool:
    """
    后台下载安装包（线程内调用），带自动重试。

    实测（v0.3.7 自动更新）：GitHub 安装包经代理下载易被远端重置连接
    （WinError 10054 / SSL handshake timed out）。策略：代理 → 直连 →
    代理 → 直连 最多 4 次尝试，指数退避，最后一次失败才回调 on_error。

    Args:
        url: 安装包下载地址
        version: 目标版本号（用于文件名）
        on_done: 下载成功回调 (installer_path: str)
        on_error: 下载失败回调 (error_msg: str)
    """
    def _run():
        tmp = None
        try:
            _ensure_dirs()
            # 文件名：QingxinTranslator-Setup-{version}.exe
            safe_version = "".join(c for c in str(version) if c.isalnum() or c in ".-_")
            target = UPDATE_DIR / f"QingxinTranslator-Setup-{safe_version}.exe"

            # 已存在且大于 1MB 则直接复用（避免重复下载）
            if target.exists() and target.stat().st_size > 1024 * 1024:
                log.info(f"Update package already exists: {target}")
                on_done(str(target))
                return

            import httpx
            from core.proxy_manager import get_proxy_url
            proxy = get_proxy_url()

            tmp = target.with_suffix(".part")
            # 尝试序列：(代理, 用环境变量, 超时秒), (直连, 禁环境变量, 更长超时) 交替
            # 直连较慢（实测 ~65KB/s），超时需放宽；代理快但易被重置
            attempts = [(proxy, True, 60), (None, False, 120),
                        (proxy, True, 60), (None, False, 180)]
            last_err = None
            for i, (p, use_env, timeout_s) in enumerate(attempts):
                try:
                    log.info(f"Downloading update (attempt {i + 1}/{len(attempts)}, "
                             f"proxy={p or 'direct'}) {url}")
                    with httpx.stream(
                            "GET", url, timeout=timeout_s,
                            proxy=p, trust_env=use_env,
                            follow_redirects=True) as resp:
                        resp.raise_for_status()
                        total = int(resp.headers.get("content-length", 0))
                        downloaded = 0
                        with open(tmp, "wb") as f:
                            for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                                f.write(chunk)
                                downloaded += len(chunk)
                        if total and downloaded != total:
                            raise IOError(
                                f"size mismatch: got {downloaded}, expected {total}")
                    os.replace(tmp, target)
                    log.info(f"Update downloaded: {target} ({downloaded} bytes)")
                    on_done(str(target))
                    return
                except Exception as e:
                    last_err = e
                    log.warning(f"Update download attempt {i + 1} failed: {e}")
                    try:
                        if tmp.exists():
                            tmp.unlink()
                    except Exception:
                        pass
                    time.sleep(2 * (i + 1))  # 指数退避 2s/4s/6s
            on_error(str(last_err))
        except Exception as e:
            log.error(f"Update download failed: {e}")
            try:
                if tmp and tmp.exists():
                    tmp.unlink()
            except Exception:
                pass
            on_error(str(e))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return True


def save_pending_install(installer_path: str):
    """记录"稍后安装"：退出应用后自动执行"""
    try:
        _ensure_dirs()
        PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
        PENDING_FILE.write_text(
            json.dumps({"installer": installer_path, "version": ""}),
            encoding="utf-8"
        )
        log.info(f"Pending install saved: {installer_path}")
    except Exception as e:
        log.error(f"Save pending install failed: {e}")


def _get_install_dir() -> str:
    """获取当前应用安装目录（打包版：exe 所在目录；开发版：空 = 用安装程序默认目录）"""
    try:
        import sys
        if getattr(sys, 'frozen', False):
            return str(Path(sys.executable).parent)
    except Exception:
        pass
    return ""


def run_installer(installer_path: str):
    """
    启动安装程序（静默模式，分离进程，不阻塞调用方）。

    关键：用 /DIR= 指定安装到【当前应用所在目录】，覆盖原程序，
    而不是 Inno Setup 的默认安装位置（{autopf}）。

    注意：/DIR 值【不要手动加引号】——路径含空格时 subprocess.Popen
    会自动按 Windows 命令行规则引用整个参数；手动加引号会被
    list2cmdline 转义成嵌套引号（"/DIR=\\"...\\""），Inno Setup 解析
    失败导致安装程序静默退出、什么都不装（v0.3.0 实测翻车）。
    """
    try:
        p = str(installer_path)
        args = SILENT_ARGS + [f'/DIR={_get_install_dir()}']
        log.info(f"Launching installer: {p} {' '.join(args)}")
        subprocess.Popen(
            [p] + args,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
        )
        return True
    except Exception as e:
        log.error(f"Launch installer failed: {e}")
        return False


def run_pending_install():
    """检查并执行待安装更新（应用退出时调用）"""
    try:
        if not PENDING_FILE.exists():
            return
        data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        installer = data.get("installer", "")
        if installer and Path(installer).exists():
            log.info("Running pending install on exit...")
            run_installer(installer)
        else:
            log.warning(f"Pending installer missing: {installer}")
        PENDING_FILE.unlink(missing_ok=True)
    except Exception as e:
        log.error(f"Run pending install failed: {e}")


def get_installer_path(version: str = "") -> str:
    """获取已下载安装包路径（用于"立即安装"）"""
    try:
        if UPDATE_DIR.exists():
            # 取最新的 Setup exe
            exes = sorted(UPDATE_DIR.glob("QingxinTranslator-Setup-*.exe"),
                          key=lambda p: p.stat().st_mtime, reverse=True)
            if exes:
                return str(exes[0])
    except Exception as e:
        log.warning(f"Find installer failed: {e}")
    return ""
