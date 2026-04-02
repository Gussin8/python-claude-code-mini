"""Auto classifier - Automatic permission classification"""

from typing import Any


class AutoClassifier:
    """自动分类器
    
    使用启发式方法自动判断工具调用是否安全。
    
    分类策略:
        1. 基于工具类型
        2. 基于命令/操作内容
        3. 基于历史决策
    
    示例:
        classifier = AutoClassifier()
        is_safe = classifier.classify("Bash", {"command": "ls -la"})
    """

    # 安全的只读命令
    SAFE_COMMANDS = {
        # 文件浏览
        "ls", "dir", "pwd", "tree",
        # 文件内容查看
        "cat", "head", "tail", "less", "more",
        # 搜索
        "grep", "find", "locate", "which", "whereis",
        # 系统信息
        "whoami", "date", "time", "uname", "hostname",
        # Git 只读操作
        "git status", "git diff", "git log", "git branch", "git show",
        # Python
        "python --version", "python -m pip list",
        # Node.js
        "node --version", "npm list", "yarn list",
    }

    # 危险命令
    DANGEROUS_COMMANDS = {
        # 删除
        "rm", "rmdir", "del", "deltree",
        # 磁盘操作
        "dd", "mkfs", "fdisk", "format",
        # 系统控制
        "reboot", "shutdown", "halt", "poweroff",
        # 权限修改
        "chmod", "chown", "chgrp",
        # 网络下载执行
        "curl | sh", "wget | sh",
    }

    # 危险文件模式
    DANGEROUS_PATTERNS = {
        # 系统文件
        "/etc/passwd", "/etc/shadow", "/etc/sudoers",
        # 密钥文件
        ".ssh/id_rsa", ".ssh/id_ed25519",
        # 环境变量
        ".env", ".env.local", ".env.production",
    }

    def classify(self, tool_name: str, input_data: dict[str, Any]) -> str:
        """分类工具调用
        
        Args:
            tool_name: 工具名称
            input_data: 工具输入数据
        
        Returns:
            'safe' | 'risky' | 'dangerous'
        """
        if tool_name == "Bash":
            return self._classify_bash(input_data.get("command", ""))
        elif tool_name in ("FileRead", "FileEdit", "FileWrite"):
            return self._classify_file_operation(tool_name, input_data)
        elif tool_name in ("Glob", "Grep"):
            return "safe"  # 这些工具本身就是只读的
        else:
            return "risky"  # 未知工具默认视为有风险

    def _classify_bash(self, command: str) -> str:
        """分类 Bash 命令
        
        Args:
            command: Shell 命令
        
        Returns:
            'safe' | 'risky' | 'dangerous'
        """
        if not command:
            return "risky"

        # 检查是否包含危险命令
        for dangerous in self.DANGEROUS_COMMANDS:
            if command.startswith(dangerous + " ") or command == dangerous:
                return "dangerous"

        # 检查是否包含管道执行
        if "| sh" in command or "| bash" in command:
            return "dangerous"

        # 检查是否包含重定向到系统文件
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command and ">" in command:
                return "dangerous"

        # 检查是否是安全命令
        for safe in self.SAFE_COMMANDS:
            if command.startswith(safe + " ") or command == safe:
                return "safe"

        # 检查 git 只读命令
        if command.startswith("git "):
            git_subcmd = command[4:].split()[0] if len(command) > 4 else ""
            safe_git_cmds = {"status", "diff", "log", "branch", "show", "remote"}
            if git_subcmd in safe_git_cmds:
                return "safe"

        # 默认视为有风险
        return "risky"

    def _classify_file_operation(
        self,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> str:
        """分类文件操作
        
        Args:
            tool_name: 工具名称
            input_data: 输入数据
        
        Returns:
            'safe' | 'risky' | 'dangerous'
        """
        path = input_data.get("path", "")

        # 检查是否访问危险文件
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in path:
                if tool_name == "FileRead":
                    return "risky"
                else:
                    return "dangerous"

        # FileRead 是只读的，通常安全
        if tool_name == "FileRead":
            return "safe"

        # FileWrite 和 FileEdit 是写入操作
        # 检查是否是配置文件或代码文件
        safe_extensions = {".py", ".js", ".ts", ".md", ".txt", ".json", ".yaml", ".yml"}
        
        from pathlib import Path
        ext = Path(path).suffix.lower()
        
        if ext in safe_extensions:
            return "risky"  # 需要确认但不是危险的
        
        # 其他文件类型视为更危险
        return "dangerous"

    def should_auto_allow(self, tool_name: str, input_data: dict[str, Any]) -> bool:
        """判断是否应该自动允许
        
        Args:
            tool_name: 工具名称
            input_data: 输入数据
        
        Returns:
            True 如果应该自动允许
        """
        classification = self.classify(tool_name, input_data)
        return classification == "safe"

    def should_auto_deny(self, tool_name: str, input_data: dict[str, Any]) -> bool:
        """判断是否应该自动拒绝
        
        Args:
            tool_name: 工具名称
            input_data: 输入数据
        
        Returns:
            True 如果应该自动拒绝
        """
        classification = self.classify(tool_name, input_data)
        return classification == "dangerous"
