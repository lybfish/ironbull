"""
Config - 统一配置加载

职责：
- 从环境变量 / 配置文件加载配置
- 提供类型安全的配置访问
- 支持默认值

不负责：
- 业务配置（由各 service 自行定义）
- 敏感信息加密（由部署层处理）
"""

import os
from typing import Any, Optional, Dict, List
from pathlib import Path
from ast import literal_eval

from .exceptions import ConfigError


class Config:
    """
    配置管理器
    
    优先级：环境变量 > 配置文件 > 默认值
    """
    
    _instance: Optional["Config"] = None
    _data: Dict[str, Any]
    
    def __init__(self):
        self._data = {}
        self._load_from_file()
        self._load_from_env()

    def _root_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _default_yaml_path(self) -> Path:
        return self._root_dir() / "config" / "default.yaml"

    def _load_from_file(self) -> None:
        """从 YAML 文件加载配置（默认 config/default.yaml）"""
        env_path = os.environ.get("IRONBULL_CONFIG_PATH")
        path = Path(env_path) if env_path else self._default_yaml_path()
        if not path.exists():
            return
        data = self._load_yaml(path)
        if data:
            self._deep_merge(self._data, data)

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return {}
        try:
            import yaml  # type: ignore
        except Exception:
            return self._simple_yaml_parse(content, path)
        try:
            data = yaml.safe_load(content) or {}
        except Exception as exc:
            raise ConfigError(
                message=f"Failed to parse YAML: {path}",
                details={"error": str(exc)}
            )
        if not isinstance(data, dict):
            raise ConfigError(
                message=f"Config root must be a mapping: {path}"
            )
        return data

    def _simple_yaml_parse(self, content: str, path: Path) -> Dict[str, Any]:
        """极简 YAML 解析器（仅支持 key: value，避免外部依赖）"""
        data: Dict[str, Any] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ConfigError(
                    message=f"Invalid YAML line: {line}",
                    details={"path": str(path)}
                )
            key, value = line.split(":", 1)
            data[key.strip()] = self._parse_scalar(value.strip())
        return data

    def _parse_scalar(self, value: str) -> Any:
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        if value.lower() == "null":
            return None
        try:
            return literal_eval(value)
        except Exception:
            return value
    
    def _load_from_env(self) -> None:
        """从环境变量加载配置（IRONBULL_ 前缀）"""
        prefix = "IRONBULL_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self._set_by_path(config_key, value)

    def _set_by_path(self, key: str, value: Any) -> None:
        parts = [p for p in key.split("__") if p]
        if not parts:
            return
        target = self._data
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    def _deep_merge(self, base: Dict[str, Any], new: Dict[str, Any]) -> None:
        for key, value in new.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._get_by_path(key.lower(), default)

    def _get_by_path(self, key: str, default: Any = None) -> Any:
        parts = [p for p in key.split(".") if p]
        target: Any = self._data
        for part in parts:
            if not isinstance(target, dict) or part not in target:
                return default
            target = target[part]
        return target
    
    def get_str(self, key: str, default: str = "") -> str:
        """获取字符串配置"""
        value = self.get(key, default)
        return str(value) if value is not None else default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = self.get(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "on")

    def get_list(self, key: str, default: Any = None) -> list:
        """获取列表配置。支持 YAML list 或逗号分隔字符串"""
        value = self.get(key)
        if value is None:
            return default if default is not None else []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        return default if default is not None else []

    def set(self, key: str, value: Any) -> None:
        """设置配置值（运行时）"""
        self._set_by_path(key.lower(), value)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        return self.get(key, None) is not None
    
    @classmethod
    def instance(cls) -> "Config":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_config() -> Config:
    """获取全局配置实例"""
    return Config.instance()
