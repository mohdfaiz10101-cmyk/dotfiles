"""
social_intelligence.py — 微信社交智能工作流
LangGraph StateGraph: Ingest → Analyze → BuildRelations → GenerateInsights → Report

Usage:
    cd ~/agi && python3 -m flows.social_intelligence
    # 或从 macg.py 调用: macg_run_flow("social_intelligence")
"""

import json
import re
from datetime import datetime
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flows.safe_tools import bash_safe

FLOW_NAME = "social_intelligence"
MAX_RETRIES = 2


class SocialState(TypedDict):
    """社交智能工作流状态"""

    raw_messages: list[dict]  # 原始消息
    analyzed: list[dict]  # 分析后消息(含intent/sentiment)
    contacts_updated: list[str]  # 更新的联系人
    relations_found: list[dict]  # 发现的关系
    insights: list[dict]  # 智能洞察
    alerts: list[str]  # 预警信息
    report: str  # 最终报告
    retry_count: int
    success: bool


# ── Node: Ingest ──────────────────────────────────────────


def node_ingest(state: SocialState) -> dict:
    """
    从消息DB获取最近未处理的消息。
    用 sqlite3 读取 /mnt/ai/data/wechat-merged/messages.db
    获取最近200条消息
    """
    import sqlite3

    db_path = "/mnt/ai/data/wechat-merged/messages.db"
    messages = []
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM messages ORDER BY create_time DESC LIMIT 200"
            ).fetchall()
            messages = [dict(r) for r in rows]
    except Exception:
        # DB不存在或为空，返回空列表不报错
        pass
    return {"raw_messages": messages, "retry_count": 0, "success": False}


# ── Node: Analyze ─────────────────────────────────────────


def node_analyze(state: SocialState) -> dict:
    """
    分析每条消息的意图和情感。
    使用规则匹配（零成本）+ 可选 LLM 增强。

    意图分类: inquiry(询价), support(技术支持), after_sales(售后),
              logistics(物流), complaint(投诉), greeting(问候),
              scheduling(约见), business(商务), social(社交闲聊)

    情感: positive, neutral, negative, urgent
    """
    INTENT_KEYWORDS = {
        "inquiry": [
            "价格",
            "多少钱",
            "报价",
            "费用",
            "采购",
            "询价",
            "批量",
            "单价",
            "报价单",
        ],
        "support": ["问题", "报错", "故障", "无法", "不能", "失败", "崩溃", "bug"],
        "after_sales": ["退款", "退货", "换货", "维修", "售后", "质量问题"],
        "logistics": ["快递", "物流", "发货", "到货", "配送", "运费", "签收"],
        "complaint": ["投诉", "差评", "不满", "欺骗", "骗", "欺诈"],
        "scheduling": ["见面", "约", "拜访", "会议", "几点", "什么时候"],
        "business": ["合作", "合同", "签约", "代理", "经销", "渠道", "项目"],
        "greeting": ["你好", "在吗", "嗨", "早上好", "晚上好", "周末好"],
    }

    analyzed = []
    for msg in state.get("raw_messages", []):
        content = msg.get("message_content", "") or ""
        entry = dict(msg)

        # 意图匹配
        entry["intent"] = "social"
        entry["confidence"] = 0.3
        for intent, keywords in INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in content:
                    entry["intent"] = intent
                    entry["confidence"] = 0.85
                    break
            if entry["intent"] != "social":
                break

        # 情感（简单规则）
        urgent_words = ["紧急", "急", "马上", "立刻", "赶紧", "尽快"]
        negative_words = ["不满", "差", "烂", "骗", "垃圾"]
        if any(w in content for w in urgent_words):
            entry["sentiment"] = "urgent"
        elif any(w in content for w in negative_words):
            entry["sentiment"] = "negative"
        else:
            entry["sentiment"] = "neutral"

        # 提取 @mentions
        mentions = re.findall(r"@(\S+)", content)
        entry["mentions"] = mentions

        analyzed.append(entry)

    return {"analyzed": analyzed}


# ── Node: BuildRelations ──────────────────────────────────


def node_build_relations(state: SocialState) -> dict:
    """
    从分析结果中提取关系信息，更新 CRM DB。
    检测: @互动关系
    """
    import sqlite3

    crm_path = "/mnt/ai/apps/wechat-agent/data/crm.db"
    relations = []
    updated_contacts = set()

    try:
        with sqlite3.connect(crm_path) as conn:
            # 确保表存在
            conn.execute("""CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wxid_a TEXT NOT NULL, wxid_b TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 0.0,
                interaction_count INTEGER DEFAULT 0,
                last_interaction DATETIME,
                metadata TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(wxid_a, wxid_b, relation_type)
            )""")

            # 从分析结果提取@互动关系
            for msg in state.get("analyzed", []):
                talker = msg.get("talker", "")
                mentions = msg.get("mentions", [])
                for mentioned in mentions:
                    if talker and mentioned and talker != mentioned:
                        relations.append(
                            {
                                "source": talker,
                                "target": mentioned,
                                "type": "at_interaction",
                                "strength": 0.6,
                            }
                        )

            # 写入 DB (UPSERT)
            for rel in relations:
                try:
                    conn.execute(
                        """
                        INSERT INTO relations (wxid_a, wxid_b, relation_type,
                                               strength, interaction_count)
                        VALUES (?, ?, ?, ?, 1)
                        ON CONFLICT(wxid_a, wxid_b, relation_type)
                        DO UPDATE SET interaction_count = interaction_count + 1,
                                      strength = ?,
                                      updated_at = CURRENT_TIMESTAMP
                    """,
                        (
                            rel["source"],
                            rel["target"],
                            rel["type"],
                            rel["strength"],
                            rel["strength"],
                        ),
                    )
                except Exception:
                    pass
            conn.commit()
    except Exception:
        pass

    return {"relations_found": relations, "contacts_updated": list(updated_contacts)}


# ── Node: GenerateInsights ────────────────────────────────


def node_insights(state: SocialState) -> dict:
    """
    生成智能洞察和预警:
    - 商机识别（多个询价意图 → 潜在客户群）
    - 异常检测（投诉集中爆发）
    - 紧急消息标记
    """
    insights = []
    alerts = []

    analyzed = state.get("analyzed", [])

    # 意图统计
    intent_counts: dict[str, int] = {}
    urgent_msgs = []
    for msg in analyzed:
        intent = msg.get("intent", "social")
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
        if msg.get("sentiment") == "urgent":
            urgent_msgs.append(msg)

    # 商机检测
    if intent_counts.get("inquiry", 0) >= 2:
        insights.append(
            {
                "type": "opportunity",
                "message": f"检测到 {intent_counts['inquiry']} 次询价，可能存在商机",
                "priority": "high",
            }
        )

    # 投诉预警
    if intent_counts.get("complaint", 0) >= 1:
        alerts.append(f"[预警] 检测到 {intent_counts['complaint']} 条投诉信息，需关注")

    # 紧急消息
    for msg in urgent_msgs:
        content = (msg.get("message_content", "") or "")[:50]
        alerts.append(f"[紧急] {msg.get('talker', '未知')}: {content}")

    return {"insights": insights, "alerts": alerts}


# ── Node: Report ──────────────────────────────────────────


def node_report(state: SocialState) -> dict:
    """生成最终报告并写入文件"""
    analyzed = state.get("analyzed", [])
    relations = state.get("relations_found", [])
    insights = state.get("insights", [])
    alerts = state.get("alerts", [])

    # 意图汇总
    intent_summary: dict[str, int] = {}
    for msg in analyzed:
        intent = msg.get("intent", "social")
        intent_summary[intent] = intent_summary.get(intent, 0) + 1

    report_lines = [
        f"📊 社交智能报告 ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        f"消息分析: {len(analyzed)} 条",
        f"关系更新: {len(relations)} 条",
    ]

    if intent_summary:
        top_intents = sorted(intent_summary.items(), key=lambda x: -x[1])[:5]
        report_lines.append(
            "意图分布: " + ", ".join(f"{k}({v})" for k, v in top_intents)
        )

    if insights:
        report_lines.append("💡 洞察:")
        for ins in insights:
            report_lines.append(f"  [{ins['priority']}] {ins['message']}")

    if alerts:
        report_lines.append("⚠️ 预警:")
        for a in alerts:
            report_lines.append(f"  {a}")

    report = "\n".join(report_lines)

    # 写入报告到文件
    report_path = Path.home() / ".local/share/macg/social-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "report": report,
                "stats": {
                    "messages": len(analyzed),
                    "relations": len(relations),
                    "insights": len(insights),
                    "alerts": len(alerts),
                },
                "timestamp": datetime.now().isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return {"report": report, "success": True}


# ── Build Graph ───────────────────────────────────────────


def _route_after_ingest(state: SocialState) -> str:
    """无消息时跳过分析直接出报告"""
    if not state.get("raw_messages"):
        return "report"
    return "analyze"


def build_graph() -> StateGraph:
    """构建社交智能 StateGraph"""
    g = StateGraph(SocialState)
    g.add_node("ingest", node_ingest)
    g.add_node("analyze", node_analyze)
    g.add_node("build_relations", node_build_relations)
    g.add_node("insights", node_insights)
    g.add_node("report", node_report)

    g.add_edge(START, "ingest")
    g.add_conditional_edges(
        "ingest", _route_after_ingest, {"report": "report", "analyze": "analyze"}
    )
    g.add_edge("analyze", "build_relations")
    g.add_edge("build_relations", "insights")
    g.add_edge("insights", "report")
    g.add_edge("report", END)
    return g


def run(spec: str = ""):
    """外部调用入口"""
    graph = build_graph().compile()
    result = graph.invoke(
        {
            "raw_messages": [],
            "analyzed": [],
            "contacts_updated": [],
            "relations_found": [],
            "insights": [],
            "alerts": [],
            "report": "",
            "retry_count": 0,
            "success": False,
        }
    )
    return result.get("report", "No report generated")


if __name__ == "__main__":
    print(run())
