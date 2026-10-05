"""Grafo LangGraph di un ciclo decisionale su un simbolo.

    analysts -> debate -> trader -> risk_engine -> risk_committee -> portfolio_manager
             -> execution -> journal

Nodi LLM: analysts, debate, trader, risk_committee, portfolio_manager.
Nodi deterministici: risk_engine, execution, journal (audit-truth).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from trading_agent.agents import TradingTeam
from trading_agent.domain import (
    AnalystReport,
    DebateArgument,
    Direction,
    Fill,
    MarketSnapshot,
    PortfolioState,
    ResearchThesis,
    RiskCommitteeView,
    RiskVerdict,
    TradeDecision,
    TradeProposal,
)
from trading_agent.execution import Broker, decision_to_order
from trading_agent.memory import TradeJournal
from trading_agent.risk import RiskEngine


class CycleState(TypedDict, total=False):
    snapshot: MarketSnapshot
    portfolio: PortfolioState
    lessons: list[str]
    reports: list[AnalystReport]
    debate: list[DebateArgument]
    thesis: ResearchThesis
    proposal: TradeProposal
    verdict: RiskVerdict
    committee: RiskCommitteeView | None
    decision: TradeDecision
    fill: Fill | None
    halted_reason: str | None


@dataclass
class CycleDeps:
    team: TradingTeam
    risk: RiskEngine
    broker: Broker
    journal: TradeJournal


def build_graph(deps: CycleDeps) -> Any:
    team, risk, broker, journal = deps.team, deps.risk, deps.broker, deps.journal

    def guard(state: CycleState) -> CycleState:
        if risk.kill_switch_active(state["portfolio"]):
            return {"halted_reason": "kill_switch"}
        return {"halted_reason": None}

    def analysts(state: CycleState) -> CycleState:
        return {"reports": team.analyze(state["snapshot"], state.get("lessons", []))}

    def debate(state: CycleState) -> CycleState:
        transcript, thesis = team.debate(state["snapshot"], state["reports"])
        return {"debate": transcript, "thesis": thesis}

    def trader(state: CycleState) -> CycleState:
        return {"proposal": team.propose(state["snapshot"], state["thesis"], state["portfolio"])}

    def risk_engine(state: CycleState) -> CycleState:
        return {"verdict": risk.evaluate(state["proposal"], state["portfolio"])}

    def risk_committee(state: CycleState) -> CycleState:
        return {
            "committee": team.risk_review(state["proposal"], state["verdict"], state["portfolio"])
        }

    def portfolio_manager(state: CycleState) -> CycleState:
        return {
            "decision": team.decide(
                state["proposal"], state["verdict"], state.get("committee"), state["portfolio"]
            )
        }

    def execution(state: CycleState) -> CycleState:
        snap = state["snapshot"]
        order = decision_to_order(state["decision"], state["portfolio"], snap.last_price)
        fill = broker.submit(order, snap.last_price) if order else None
        return {"fill": fill}

    def journal_node(state: CycleState) -> CycleState:
        journal.append(
            "cycle",
            {
                "symbol": state["snapshot"].symbol,
                "as_of": state["snapshot"].as_of.isoformat(),
                "halted_reason": state.get("halted_reason"),
                "thesis": _dump(state.get("thesis")),
                "proposal": _dump(state.get("proposal")),
                "verdict": _dump(state.get("verdict")),
                "committee": _dump(state.get("committee")),
                "decision": _dump(state.get("decision")),
                "fill": _dump(state.get("fill")),
            },
        )
        return {}

    def after_guard(state: CycleState) -> str:
        return "journal" if state.get("halted_reason") else "analysts"

    def after_trader(state: CycleState) -> str:
        return "journal" if state["proposal"].direction is Direction.FLAT else "risk_engine"

    g = StateGraph(CycleState)
    g.add_node("guard", guard)
    g.add_node("analysts", analysts)
    g.add_node("debate", debate)
    g.add_node("trader", trader)
    g.add_node("risk_engine", risk_engine)
    g.add_node("risk_committee", risk_committee)
    g.add_node("portfolio_manager", portfolio_manager)
    g.add_node("execution", execution)
    g.add_node("journal", journal_node)

    g.add_edge(START, "guard")
    g.add_conditional_edges("guard", after_guard, ["analysts", "journal"])
    g.add_edge("analysts", "debate")
    g.add_edge("debate", "trader")
    g.add_conditional_edges("trader", after_trader, ["risk_engine", "journal"])
    g.add_edge("risk_engine", "risk_committee")
    g.add_edge("risk_committee", "portfolio_manager")
    g.add_edge("portfolio_manager", "execution")
    g.add_edge("execution", "journal")
    g.add_edge("journal", END)
    return g.compile()


def _dump(obj: Any) -> Any:
    return obj.model_dump(mode="json") if obj is not None and hasattr(obj, "model_dump") else obj


def run_cycle(deps: CycleDeps, snapshot: MarketSnapshot) -> CycleState:
    portfolio = deps.broker.mark_to_market({snapshot.symbol: snapshot.last_price})
    lessons = deps.journal.lessons_before(snapshot.as_of, snapshot.symbol)
    graph = build_graph(deps)
    result: CycleState = graph.invoke(
        {"snapshot": snapshot, "portfolio": portfolio, "lessons": lessons}
    )
    return result
