"""Edit these domain profiles to make the project your own."""

DOMAIN_PROFILES = {
    "hyperspectral": {
        "name": "高光谱图像分类",
        "instructions": (
            "重点分析高光谱图像分类任务，特别是光谱-空间建模、CNN、Transformer、"
            "图神经网络和动态建图。比较常用数据集，如 Indian Pines、Pavia University、"
            "Salinas、Houston、Berlin。指出论文中 OA/AA/Kappa 的具体来源；"
            "没有可靠证据的指标不得编造，区分不同数据集、划分设置和训练样本比例。"
        ),
    },
    "general": {
        "name": "通用科研",
        "instructions": (
            "引用可核实的来源，清楚区分事实与推测；明确研究方法、局限及未来方向。"
            "不要编造实验指标和论文引用。"
        ),
    },
}


def build_research_query(topic: str, domain: str, language: str) -> str:
    profile = DOMAIN_PROFILES[domain]
    return (
        f"研究主题：{topic}\n"
        f"领域：{profile['name']}\n"
        f"分析要求：{profile['instructions']}\n"
        f"请用{'中文' if language == 'zh' else '英文'}撰写带来源的研究报告。"
        "报告包含研究问题、代表方法、关键差异、局限、未来研究方向。"
    )
