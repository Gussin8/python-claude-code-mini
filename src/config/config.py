"""Configuration management"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os


@dataclass
class AuthConfig:
    """认证配置
    
    Attributes:
        api_key: Anthropic API 密钥
        oauth_tokens: OAuth 令牌字典
    """

    api_key: Optional[str] = None
    oauth_tokens: dict = field(default_factory=dict)

    def __post_init__(self):
        # 从环境变量读取 API key
        if self.api_key is None:
            self.api_key = os.getenv("ANTHROPIC_API_KEY")


@dataclass
class ModelConfig:
    """模型配置
    
    Attributes:
        default: 默认使用的模型
        fallback: 备用模型（当默认模型不可用时）
        max_tokens: 最大生成 token 数
    """

    default: str = "claude-sonnet-4-20250514"
    fallback: str = "claude-haiku-4-20250514"
    max_tokens: int = 4096


@dataclass
class PermissionConfig:
    """权限配置
    
    Attributes:
        mode: 权限模式 (default, auto, bypass, dontAsk)
        always_allow_rules: 总是允许的规则列表
        always_deny_rules: 总是拒绝的规则列表
        always_ask_rules: 总是询问的规则列表
    """

    mode: str = "default"
    always_allow_rules: list[str] = field(default_factory=list)
    always_deny_rules: list[str] = field(default_factory=list)
    always_ask_rules: list[str] = field(default_factory=list)


@dataclass
class GlobalConfig:
    """全局配置
    
    这是配置系统的核心类，负责加载、保存和管理所有配置项。
    
    Attributes:
        auth: 认证配置
        model: 模型配置
        permissions: 权限配置
        mcp_servers: MCP 服务器配置
        features: 功能开关
    
    示例:
        # 加载配置
        config = GlobalConfig.load()
        
        # 访问配置
        print(config.model.default)
        print(config.auth.api_key)
        
        # 保存配置
        config.save()
    """

    auth: AuthConfig = field(default_factory=AuthConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    permissions: PermissionConfig = field(default_factory=PermissionConfig)
    mcp_servers: dict = field(default_factory=dict)
    features: dict = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "GlobalConfig":
        """加载配置
        
        Args:
            config_path: 配置文件路径，如果为 None 则使用默认路径
        
        Returns:
            加载的配置对象
        
        默认配置路径:
            - ~/.python-claude-code/config.yaml
            - ~/.python-claude-code/config.yml
        """
        if config_path is None:
            config_path = cls._get_default_config_path()

        if not config_path.exists():
            return cls()

        content = config_path.read_text(encoding="utf-8")
        data = cls._parse_content(content, config_path.suffix)

        return cls._from_dict(data)

    @classmethod
    def _parse_content(cls, content: str, suffix: str) -> dict:
        """解析配置文件内容
        
        Args:
            content: 文件内容
            suffix: 文件扩展名
        
        Returns:
            解析后的字典
        """
        if suffix in (".yaml", ".yml"):
            try:
                import yaml

                return yaml.safe_load(content) or {}
            except ImportError:
                raise ImportError("PyYAML is required for YAML config files")
        elif suffix == ".toml":
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError:
                    raise ImportError(
                        "tomli is required for TOML config files on Python < 3.11"
                    )
            return tomllib.loads(content)
        elif suffix == ".json":
            import json

            return json.loads(content)
        else:
            raise ValueError(f"Unsupported config format: {suffix}")

    @classmethod
    def _from_dict(cls, data: dict) -> "GlobalConfig":
        """从字典创建配置对象
        
        Args:
            data: 配置字典
        
        Returns:
            配置对象
        """
        return cls(
            auth=AuthConfig(**data.get("auth", {})),
            model=ModelConfig(**data.get("model", {})),
            permissions=PermissionConfig(**data.get("permissions", {})),
            mcp_servers=data.get("mcp_servers", {}),
            features=data.get("features", {}),
        )

    @staticmethod
    def _get_default_config_path() -> Path:
        """获取默认配置路径
        
        Returns:
            默认配置文件路径
        """
        home = Path.home()
        config_dir = home / ".python-claude-code"
        return config_dir / "config.yaml"

    def save(self, path: Optional[Path] = None):
        """保存配置到文件
        
        Args:
            path: 保存路径，如果为 None 则保存到默认路径
        """
        if path is None:
            path = self._get_default_config_path()

        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "auth": {k: v for k, v in self.auth.__dict__.items() if v},
            "model": self.model.__dict__,
            "permissions": self.permissions.__dict__,
            "mcp_servers": self.mcp_servers,
            "features": self.features,
        }

        # 过滤空值
        data = {k: v for k, v in data.items() if v}

        with open(path, "w", encoding="utf-8") as f:
            import yaml

            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def to_dict(self) -> dict:
        """将配置转换为字典
        
        Returns:
            配置字典
        """
        return {
            "auth": self.auth.__dict__,
            "model": self.model.__dict__,
            "permissions": self.permissions.__dict__,
            "mcp_servers": self.mcp_servers,
            "features": self.features,
        }
