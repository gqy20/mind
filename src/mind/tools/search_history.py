"""搜索历史管理模块

管理搜索结果的持久化存储，支持保存、读取和搜索历史记录。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from loguru import logger


class SearchHistory:
    """搜索历史管理器"""

    def __init__(self, file_path: Path | str | None = None):
        """初始化搜索历史管理器

        Args:
            file_path: 历史文件路径，默认为 ~/.mind/search_history.json
        """
        if file_path is None:
            # 默认路径
            home = Path.home()
            file_path = home / ".mind" / "search_history.json"

        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载或初始化数据
        self.data = self._load_data()

        logger.debug(f"搜索历史初始化: {self.file_path}")

    def _load_data(self) -> dict[str, Any]:
        """加载历史数据

        Returns:
            历史数据字典
        """
        if self.file_path.exists():
            try:
                content = self.file_path.read_text(encoding="utf-8")
                return cast(dict[str, Any], json.loads(content))
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"历史文件损坏，创建新文件: {e}")
                return {"searches": []}
        else:
            # 创建新文件
            self.file_path.write_text(
                json.dumps({"searches": []}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return {"searches": []}

    def _save_data(self) -> None:
        """保存数据到文件"""
        try:
            self.file_path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error(f"保存历史失败: {e}")

    def save_search(self, query: str, results: list[dict]) -> None:
        """保存搜索结果到历史

        Args:
            query: 搜索查询
            results: 搜索结果列表
        """
        search_entry = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "results": results,
        }

        self.data["searches"].append(search_entry)
        self._save_data()

        logger.debug(f"搜索已保存: {query}, {len(results)} 条结果")

    def get_latest(self, limit: int = 5) -> list[dict[str, Any]]:
        """获取最新的搜索记录

        Args:
            limit: 返回数量限制

        Returns:
            最新的搜索记录列表（按时间倒序）
        """
        # 按时间倒序排序并限制数量
        searches = self.data.get("searches", [])
        sorted_searches = sorted(
            searches,
            key=lambda x: x["timestamp"],
            reverse=True,
        )
        return sorted_searches[:limit]

    def search_history(self, pattern: str) -> list[dict[str, Any]]:
        """在历史中搜索

        Args:
            pattern: 搜索模式（不区分大小写）

        Returns:
            匹配的搜索记录列表
        """
        searches = self.data.get("searches", [])

        if not pattern:
            # 空模式返回所有
            return list(searches)

        pattern_lower = pattern.lower()
        matches = []

        for entry in searches:
            # 在查询中搜索
            if pattern_lower in entry["query"].lower():
                matches.append(entry)
                continue

            # 在结果标题中搜索
            for result in entry["results"]:
                title = result.get("title", "")
                if pattern_lower in title.lower():
                    matches.append(entry)
                    break

        return matches
