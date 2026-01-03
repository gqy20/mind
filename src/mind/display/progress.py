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

        # 计算进度条宽度
        bar_width = 30
        filled = int(bar_width * percentage)
        bar = "█" * filled + "░" * (bar_width - filled)

        # 直接输出进度条到 stderr（使用纯文本，不使用 Rich 颜色）
        import sys

        print(
            f"\rToken:[{bar}] {tokens}/{max_tokens} ({percentage:.1%})",
            end="",
            file=sys.stderr,
            flush=True,
        )
