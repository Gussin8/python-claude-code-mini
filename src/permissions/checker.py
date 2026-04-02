"""Permission checker - Check tool permissions"""

from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class PermissionRule:
    """权限规则
    
    Attributes:
        tool_name: 工具名称（支持 * 通配符）
        pattern: 匹配模式（可选）
        behavior: 行为 (allow, deny, ask)
        flags: 额外标志
    """

    tool_name: str
    pattern: Optional[str] = None
    behavior: str  # allow, deny, ask
    flags: str = ""


class PermissionChecker:
    """权限检查器
    
    负责根据规则检查工具调用的权限。
    
    规则优先级:
        1. always_deny_rules - 总是拒绝的规则
        2. always_ask_rules - 总是询问的规则
        3. always_allow_rules - 总是允许的规则
        4. 默认行为（根据模式决定）
    
    示例:
        checker = PermissionChecker(
            always_allow=[
                PermissionRule("FileRead"),
                PermissionRule("Bash", pattern="git status"),
            ],
            always_deny=[
                PermissionRule("Bash", pattern="rm -rf /"),
            ]
        )
        
        behavior, _ = checker.check("Bash", {"command": "ls -la"})
    """

    def __init__(
        self,
        always_allow: list[PermissionRule] = None,
        always_deny: list[PermissionRule] = None,
        always_ask: list[PermissionRule] = None,
    ):
        """初始化权限检查器
        
        Args:
            always_allow: 总是允许的规则列表
            always_deny: 总是拒绝的规则列表
            always_ask: 总是询问的规则列表
        """
        self.always_allow = always_allow or []
        self.always_deny = always_deny or []
        self.always_ask = always_ask or []

    def check(
        self,
        tool_name: str,
        input_data: dict,
        mode: str = "default",
    ) -> tuple[str, Optional[dict]]:
        """检查权限
        
        Args:
            tool_name: 工具名称
            input_data: 工具输入数据
            mode: 权限模式 (default, auto, bypass, dontAsk)
        
        Returns:
            (behavior, updated_input)
            behavior: allow | deny | ask
        """
        # 1. 检查拒绝规则
        for rule in self.always_deny:
            if self._matches_rule(rule, tool_name, input_data):
                return "deny", None

        # 2. 检查询问规则
        for rule in self.always_ask:
            if self._matches_rule(rule, tool_name, input_data):
                return "ask", None

        # 3. 检查允许规则
        for rule in self.always_allow:
            if self._matches_rule(rule, tool_name, input_data):
                return "allow", None

        # 4. 根据模式决定
        if mode == "bypass":
            return "allow", None
        elif mode == "auto":
            # 使用自动分类器
            return self._auto_classify(tool_name, input_data)
        elif mode == "dontAsk":
            # 不询问，但未明确允许的拒绝
            return "deny", None
        else:
            # 默认模式：询问用户
            return "ask", None

    def _matches_rule(
        self,
        rule: PermissionRule,
        tool_name: str,
        input_data: dict,
    ) -> bool:
        """检查是否匹配规则
        
        Args:
            rule: 规则
            tool_name: 工具名称
            input_data: 输入数据
        
        Returns:
            True 如果匹配规则
        """
        # 检查工具名称
        if rule.tool_name != tool_name and rule.tool_name != "*":
            return False

        # 如果没有模式，直接匹配
        if rule.pattern is None:
            return True

        # 提取要匹配的文本
        text_to_match = self._extract_match_text(tool_name, input_data)

        # 模式匹配
        if "*" in rule.pattern:
            regex = re.compile(rule.pattern.replace("*", ".*"))
            return bool(regex.match(text_to_match))
        else:
            return rule.pattern in text_to_match

    def _extract_match_text(self, tool_name: str, input_data: dict) -> str:
        """提取用于匹配的文本
        
        Args:
            tool_name: 工具名称
            input_data: 输入数据
        
        Returns:
            用于匹配的文本
        """
        if tool_name == "Bash":
            return input_data.get("command", "")
        elif tool_name in ("FileRead", "FileEdit", "FileWrite"):
            return input_data.get("path", "")
        elif tool_name == "Grep":
            return input_data.get("pattern", "")
        elif tool_name == "Glob":
            return input_data.get("pattern", "")
        else:
            return str(input_data)

    def _auto_classify(self, tool_name: str, input_data: dict) -> tuple[str, None]:
        """自动分类（简单启发式）
        
        Args:
            tool_name: 工具名称
            input_data: 输入数据
        
        Returns:
            (behavior, None)
        """
        safe_tools = {"FileRead", "Glob", "Grep"}
        dangerous_commands = {"rm", "del", "dd", "mkfs", "reboot", "shutdown"}

        if tool_name in safe_tools:
            return "allow", None

        if tool_name == "Bash":
            cmd = input_data.get("command", "").split()[0]
            if cmd in dangerous_commands:
                return "deny", None

        return "ask", None

    @classmethod
    def from_config(cls, config: dict) -> "PermissionChecker":
        """从配置创建权限检查器
        
        Args:
            config: 配置字典
        
        Returns:
            权限检查器实例
        """
        always_allow = [
            PermissionRule(**rule) for rule in config.get("always_allow_rules", [])
        ]
        always_deny = [
            PermissionRule(**rule) for rule in config.get("always_deny_rules", [])
        ]
        always_ask = [
            PermissionRule(**rule) for rule in config.get("always_ask_rules", [])
        ]

        return cls(
            always_allow=always_allow,
            always_deny=always_deny,
            always_ask=always_ask,
        )
