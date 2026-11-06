"""Authentication for Zhihu.

Strategy (three-tier fallback, aligned with bilibili-cli):
1. Try loading saved credential from ~/.zhihu-cli/credential.json
2. Try extracting cookies from local browsers via browser-cookie3
3. Fallback: paste cookie manually (zhihu login --cookie "...")

QR-code login requires x-zse-96 / x-zst-81 signature reverse-engineering and
is a separate future task (see reference/zhihu-login-api.md).
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .exceptions import AuthenticationError, NetworkError

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".zhihu-cli"
CREDENTIAL_FILE = CONFIG_DIR / "credential.json"

REQUIRED_COOKIES = {"z_c0"}

CREDENTIAL_TTL_DAYS = 30
_CREDENTIAL_TTL_SECONDS = CREDENTIAL_TTL_DAYS * 86400

AuthMode = Literal["optional", "read", "write"]


@dataclass
class Credential:
    """Zhihu login credential built from browser cookies."""

    z_c0: str = ""  # 登录凭证（核心）
    q_c0: str = ""  # 登录态辅助
    d_c0: str = ""  # 设备指纹
    xsrf: str = ""  # CSRF token（写操作需要）

    @property
    def is_valid(self) -> bool:
        return bool(self.z_c0)

    def to_cookie_header(self) -> str:
        parts: list[str] = []
        if self.z_c0:
            parts.append(f"z_c0={self.z_c0}")
        if self.q_c0:
            parts.append(f"q_c0={self.q_c0}")
        if self.d_c0:
            parts.append(f"d_c0={self.d_c0}")
        if self.xsrf:
            parts.append(f"_xsrf={self.xsrf}")
        return "; ".join(parts)


def parse_cookie_string(cookie_str: str) -> Credential:
    """Parse a raw Cookie header string into a Credential."""
    cookies: dict[str, str] = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return Credential(
        z_c0=cookies.get("z_c0", ""),
        q_c0=cookies.get("q_c0", ""),
        d_c0=cookies.get("d_c0", ""),
        xsrf=cookies.get("_xsrf", ""),
    )


def get_credential(mode: AuthMode = "read") -> Credential | None:
    """Try auth methods in order and return a credential according to mode.

    - optional: only load saved credential (no network validation, no browser scan)
    - read: prefer validated credential; fall back to best effort on network issues
    - write: same as read, but require _xsrf (CSRF) capability
    """
    require_write = mode == "write"

    # 1. Saved credential file
    cred = _load_saved_credential()
    if cred:
        if mode == "optional":
            return cred
        validation = _validate_credential(cred, require_write=require_write)
        if validation is True:
            logger.info("Loaded valid credential from %s", CREDENTIAL_FILE)
            return cred
        if validation is None:
            logger.warning("Credential validation failed due to network; using saved credential as best effort")
            return cred
        if validation is False:
            logger.warning("Saved credential is expired, clearing")
            clear_credential()

    if mode == "optional":
        return None

    # 2. Browser cookie extraction
    cred = _extract_browser_credential()
    if cred:
        validation = _validate_credential(cred, require_write=require_write)
        if validation is True:
            logger.info("Extracted valid credential from local browser")
            save_credential(cred)
            return cred
        if validation is None:
            logger.warning("Skipping browser credential validation due to network; using best effort")
            return cred
        if validation is False:
            logger.warning("Browser cookies are expired/invalid")

    return None


def _validate_credential(cred: Credential, require_write: bool = False) -> bool | None:
    """Check if a credential is valid via the /api/v4/me endpoint.

    Returns:
      - True: validated by API
      - False: confirmed invalid (auth rejected) or missing required fields
      - None: indeterminate due to network/runtime issues
    """
    if not cred.z_c0:
        return False
    if require_write and not cred.xsrf:
        return False

    async def _check():
        try:
            from . import client

            info = await client.get_self_info(cred)
            return bool(info.get("url_token") or info.get("id"))
        except AuthenticationError:
            return False
        except NetworkError:
            return None
        except Exception:
            return None

    try:
        return asyncio.run(_check())
    except Exception:
        return None


def _load_saved_credential() -> Credential | None:
    """Load credential from saved file."""
    if not CREDENTIAL_FILE.exists():
        return None
    try:
        data = json.loads(CREDENTIAL_FILE.read_text())
        cred = Credential(
            z_c0=data.get("z_c0", ""),
            q_c0=data.get("q_c0", ""),
            d_c0=data.get("d_c0", ""),
            xsrf=data.get("xsrf", ""),
        )
        return cred if cred.is_valid else None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load saved credential: %s", e)
        return None


def _extract_browser_credential() -> Credential | None:
    """Extract Zhihu cookies from local browsers using browser-cookie3.

    Runs extraction in a subprocess with timeout to avoid hanging when the
    browser is running (Chrome DB lock issue).
    """
    extract_script = '''
import json, sys
try:
    import browser_cookie3 as bc3
except ImportError:
    print(json.dumps({"error": "not_installed"}))
    sys.exit(0)

browsers = [
    ("Chrome", bc3.chrome),
    ("Firefox", bc3.firefox),
    ("Edge", bc3.edge),
    ("Brave", bc3.brave),
]

for name, loader in browsers:
    try:
        cj = loader(domain_name=".zhihu.com")
        cookies = {c.name: c.value for c in cj if "zhihu.com" in (c.domain or "")}
        if "z_c0" in cookies:
            print(json.dumps({"browser": name, "cookies": cookies}))
            sys.exit(0)
    except Exception:
        pass

print(json.dumps({"error": "no_cookies"}))
'''

    try:
        result = subprocess.run(
            [sys.executable, "-c", extract_script],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Cookie extraction timed out (browser may be running). Try closing your browser.")
        return None

    if result.returncode != 0:
        logger.debug("Cookie extraction subprocess failed: %s", result.stderr)
        return None

    output = result.stdout.strip()
    if not output:
        return None

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        logger.debug("Cookie extraction returned non-JSON output")
        return None

    if "error" in data:
        logger.debug("No valid Zhihu cookies found in any browser")
        return None

    cookies = data["cookies"]
    if not REQUIRED_COOKIES.issubset(cookies):
        logger.debug("Browser cookies missing required keys: %s", REQUIRED_COOKIES)
        return None

    logger.info("Found valid cookies in %s", data["browser"])
    return Credential(
        z_c0=cookies.get("z_c0", ""),
        q_c0=cookies.get("q_c0", ""),
        d_c0=cookies.get("d_c0", ""),
        xsrf=cookies.get("_xsrf", ""),
    )


def save_credential(credential: Credential):
    """Save credential to config file with timestamp for TTL tracking."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "z_c0": credential.z_c0,
        "q_c0": credential.q_c0,
        "d_c0": credential.d_c0,
        "xsrf": credential.xsrf,
        "saved_at": time.time(),
    }
    CREDENTIAL_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    try:
        CREDENTIAL_FILE.chmod(0o600)  # Owner-only read/write
    except OSError:
        pass
    logger.info("Credential saved to %s", CREDENTIAL_FILE)


def clear_credential():
    """Remove saved credential file."""
    if CREDENTIAL_FILE.exists():
        CREDENTIAL_FILE.unlink()
        logger.info("Credential removed: %s", CREDENTIAL_FILE)


def login_with_cookie(cookie_str: str) -> Credential:
    """Validate and save a manually pasted cookie string."""
    cred = parse_cookie_string(cookie_str)
    if not cred.is_valid:
        raise AuthenticationError("Cookie 缺少 z_c0 字段，无法登录")

    validation = _validate_credential(cred)
    if validation is False:
        raise AuthenticationError("Cookie 无效或已过期，请重新获取")
    if validation is None:
        logger.warning("无法联网校验 Cookie，仍将保存（best effort）")

    save_credential(cred)
    return cred


def login_via_browser() -> Credential:
    """Extract, validate, and save a credential from the local browser."""
    cred = _extract_browser_credential()
    if not cred:
        raise AuthenticationError("未在本地浏览器中找到知乎登录 Cookie（请先在浏览器登录知乎）")

    validation = _validate_credential(cred)
    if validation is False:
        raise AuthenticationError("浏览器中的知乎 Cookie 已过期或无效")

    save_credential(cred)
    return cred


def qr_login(headless: bool = True, timeout: int = 180) -> Credential:
    """扫码登录知乎（Playwright 驱动系统浏览器，截图二维码图片并自动打开）。

    依赖 Playwright 与系统安装的 Edge/Chrome，无需下载 chromium。
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise AuthenticationError(
            "扫码登录需要 playwright，请先安装：pip install playwright"
        ) from exc

    with sync_playwright() as p:
        browser = _launch_browser(p, headless)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.zhihu.com/signin", timeout=30000)

            qr_bytes = _grab_qrcode(page)
            if qr_bytes:
                qr_path = _save_qrcode_image(qr_bytes)
                _open_image(qr_path)
                print(f"已生成二维码图片并自动打开：{qr_path}")
                print("请用「知乎 App」扫码登录...")
            else:
                print("请在打开的浏览器窗口中用「知乎 App」扫码登录...")

            cred = _poll_login(context, timeout=timeout)
            if cred is None:
                raise AuthenticationError(
                    f"扫码登录超时（{timeout} 秒），二维码可能已过期，请重试"
                )
        finally:
            browser.close()

    save_credential(cred)
    return cred


def _launch_browser(p, headless: bool):
    """优先使用系统 Edge / Chrome，避免下载 chromium。"""
    for channel in ("msedge", "chrome"):
        try:
            return p.chromium.launch(channel=channel, headless=headless)
        except Exception as exc:
            logger.debug("channel %s 启动失败: %s", channel, exc)
            continue
    return p.chromium.launch(headless=headless)


def _grab_qrcode(page) -> bytes | None:
    """截取登录页二维码 canvas 的 PNG 内容。"""
    try:
        page.wait_for_selector("canvas.Qrcode-qrcode", timeout=10000)
        return page.locator("canvas.Qrcode-qrcode").first.screenshot()
    except Exception as exc:
        logger.debug("获取二维码截图失败: %s", exc)
        return None


def _save_qrcode_image(png_bytes: bytes) -> Path:
    """保存二维码 PNG 到配置目录，返回路径。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / "qrcode.png"
    path.write_bytes(png_bytes)
    return path


def _open_image(path: Path) -> None:
    """用系统默认图片查看器打开图片（跨平台）。"""
    import os
    import platform

    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(str(path))
        elif system == "Darwin":
            os.system(f"open {path}")
        else:
            os.system(f"xdg-open {path}")
    except Exception as exc:
        logger.debug("打开图片失败: %s", exc)


def _poll_login(context, timeout: int) -> Credential | None:
    """轮询浏览器 Cookie，直到出现 z_c0 视为登录成功。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            cookies = context.cookies("https://www.zhihu.com")
        except Exception:
            cookies = []
        d = {c["name"]: c["value"] for c in cookies}
        if d.get("z_c0"):
            return Credential(
                z_c0=d.get("z_c0", ""),
                q_c0=d.get("q_c0", ""),
                d_c0=d.get("d_c0", ""),
                xsrf=d.get("_xsrf", ""),
            )
        time.sleep(2)
    return None
