"""进度显示模块

提供 token 使用进度的显示功能。
"""

from rich.console import Console

console = Console()


class ProgressDisplay:
    """进度显示类"""

    @staticmethod
    def show_token_progress(tokens: int, max_tokens: int) -> None:
        """显示 token 使用进度条

        Args:
            tokens: 当前使用的 token 数
            max_tokens: 最大 token 数
        """
        percentage = min(tokens / max_tokens, 1.0)

        # 根据使用率选择颜色
        if percentage < 0.8:
            color = "[green]"
        elif percentage < 0.95:
            color = "[yellow]"
        else:
            color = "[red]"

        # 计算进度条宽度
        bar_width = 30
        filled = int(bar_width * percentage)
        bar = "█" * filled + "░" * (bar_width - filled)

        # 打印进度条（使用 \\r 覆盖当前行）
        progress_text = (
            f"\\r{color}Token:[{bar}] {tokens}/{max_tokens} "
            f"({percentage:.1%})[/{color}]"
        )
        console.print(progress_text, end="")
