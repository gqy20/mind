"""显示模块

提供 UI 显示相关功能，包括引用显示和进度显示。
"""

__all__ = ["display_citations", "format_citations", "ProgressDisplay"]


def __getattr__(name: str):
    """延迟导入，避免循环依赖

    Args:
        name: 要导入的名称

    Returns:
        导入的对象
    """
    if name == "display_citations":
        from mind.display.citations import display_citations

        return display_citations
    if name == "format_citations":
        from mind.display.citations import format_citations

        return format_citations
    if name == "ProgressDisplay":
        from mind.display.progress import ProgressDisplay

        return ProgressDisplay

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
