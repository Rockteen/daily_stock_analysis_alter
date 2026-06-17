# -*- coding: utf-8 -*-
"""
可视化辅助工具

生成 Markdown 表格、ASCII 柱状图等可视化输出，
用于在终端和报告中直观展示产业链数据。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.industry_chain.models import ChainLayer, LayerScoreCard


def bar_chart(
    label_value_pairs: List[tuple],
    title: str = "",
    width: int = 40,
    sort: bool = True,
) -> str:
    """生成 ASCII 柱状图

    Args:
        label_value_pairs: [(label, value), ...]
        title: 图表标题
        width: 图表宽度（字符数）
        sort: 是否按值排序

    Returns:
        Markdown 格式的 ASCII 柱状图
    """
    if not label_value_pairs:
        return ""

    if sort:
        label_value_pairs = sorted(label_value_pairs, key=lambda x: x[1], reverse=True)

    values = [v for _, v in label_value_pairs]
    max_val = max(values) if values else 1
    min_val = min(values) if values else 0
    # 确保不全是 0
    scale = max_val if max_val > 0 else 1

    lines = [f"### {title}\n"] if title else []
    lines.append("```")

    for label, value in label_value_pairs:
        bar_len = max(1, int(value / scale * width))
        bar = "█" * bar_len
        lines.append(f"{label:20s} |{bar} {value}")

    lines.append("```")
    return "\n".join(lines)


def margin_comparison(cards: List[LayerScoreCard]) -> str:
    """链层毛利率对比图"""
    pairs = [(c.layer.display_name, c.layer.sort_order) for c in cards]
    # 按上下游顺序排列
    pairs = sorted(pairs, key=lambda x: x[1])

    # 获取毛利率
    gm_pairs: List[tuple] = []
    for card in cards:
        dim_scores = {s.dimension: s.score for s in card.dimension_scores}
        # 从维度评分中的利润率维度取值
        from src.industry_chain.models import ScoreDimension

        prof_score = dim_scores.get(ScoreDimension.PROFITABILITY, 0)
        gm_pairs.append((card.layer.display_name, prof_score))

    return bar_chart(gm_pairs, title="链层利润率对比", sort=True)


def score_radar_table(cards: List[LayerScoreCard]) -> str:
    """评分雷达表（各维度评分一览）"""
    if not cards:
        return ""

    from src.industry_chain.models import ScoreDimension

    dims = list(ScoreDimension)
    dim_labels = [d.value for d in dims]

    lines = [
        "| 链层 | " + " | ".join(d.value for d in dims) + " | 综合 |",
        "|------|" + "|".join("---" for _ in dims) + "|------|",
    ]

    for card in sorted(cards, key=lambda c: c.composite_rank or 99):
        scores = {s.dimension: s.score for s in card.dimension_scores}
        score_strs = [str(scores.get(d, "-")) for d in dims]
        lines.append(
            f"| {card.layer.display_name} | "
            + " | ".join(score_strs)
            + f" | **{card.composite_score}** |"
        )

    return "\n".join(lines)


def rank_table(cards: List[LayerScoreCard]) -> str:
    """简洁排名表"""
    lines = [
        "| 排名 | 链层 | 评分 | 竞争强度 |",
        "|------|------|------|---------|",
    ]
    for card in sorted(cards, key=lambda c: c.composite_rank or 99):
        lines.append(
            f"| {card.composite_rank}. | {card.layer.display_name} "
            f"| {card.composite_score} | {card.competitive_intensity} |"
        )
    return "\n".join(lines)
