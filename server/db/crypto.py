"""API Key 加密/解密工具"""
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet

from server.config import get_settings

logger = logging.getLogger("server.db.crypto")

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    settings = get_settings()
    key = settings.encryption_key

    if not key:
        key = Fernet.generate_key().decode()
        # 追加到 .env 文件
        env_path = Path(".env")
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nENCRYPTION_KEY={key}\n")
        logger.info("已生成加密密钥并写入 .env")

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_api_key(plain: str) -> str:
    if not plain:
        return ""
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    if not encrypted:
        return ""
    try:
        return _get_fernet().decrypt(encrypted.encode()).decode()
    except Exception:
        # 可能是未加密的旧数据，直接返回
        return encrypted
