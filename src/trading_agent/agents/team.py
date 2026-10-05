"""I ruoli del desk. Ogni funzione è un compito fine-grained con input/output tipizzati."""

from __future__ import annotations

from dataclasses import dataclass

from trading_agent.agents.base import Agent
from trading_agent.config import AgentsConfig
from trading_agent.domain import (
    AnalystReport,
    DebateArgument,
    MarketSnapshot,
    PortfolioState,
    ResearchThesis,
    RiskCommitteeView,
    RiskVerdict,
    TradeDecision,
    TradeProposal,
)
from trading_agent.llm import LLMClient

ANALYST_ROLES = ("technical_analyst", "sentiment_analyst", "fundamental_analyst", "macro_analyst")


@dataclass
class TradingTeam:
    agents: dict[str, Agent]
    debate_rounds: int
    risk_debate_rounds: int

    @classmethod
    def from_config(cls, cfg: AgentsConfig, llm: LLMClient) -> TradingTeam:
        agents = {role: Agent(role=role, config=c, llm=llm) for role, c in cfg.agents.items()}
        return cls(agents, cfg.debate_rounds, cfg.risk_debate_rounds)

    # --- Analyst team -------------------------------------------------------------------
    def analyze(self, snapshot: MarketSnapshot, lessons: list[str]) -> list[AnalystReport]:
        reports = []
        for role in ANALYST_ROLES:
            agent = self.agents.get(role)
            if agent is None:
                continue
            reports.append(
                agent.ask(
                    AnalystReport,
                    task=(
                        f"Produce your {role.replace('_', ' ')} report for {snapshot.symbol}. "
                        f"Use ONLY the data in context; anything after as_of does not exist."
                    ),
                    context={"snapshot": snapshot, "past_lessons": lessons},
                )
            )
        return reports

    # --- Research debate ----------------------------------------------------------------
    def debate(
        self, snapshot: MarketSnapshot, reports: list[AnalystReport]
    ) -> tuple[list[DebateArgument], ResearchThesis]:
        transcript: list[DebateArgument] = []
        for rnd in range(1, self.debate_rounds + 1):
            for side in ("bull", "bear"):
                agent = self.agents[f"{side}_researcher"]
                transcript.append(
                    agent.ask(
                        DebateArgument,
                        task=f"Round {rnd}: argue the {side} case and rebut the other side.",
                        context={"snapshot": snapshot, "reports": reports, "debate": transcript},
                    )
                )
        thesis = self.agents["research_manager"].ask(
            ResearchThesis,
            task="Judge the debate. Pick a direction (flat allowed) and a calibrated conviction.",
            context={"snapshot": snapshot, "reports": reports, "debate": transcript},
        )
        return transcript, thesis

    # --- Trader ------------------------------------------------------------------------
    def propose(
        self, snapshot: MarketSnapshot, thesis: ResearchThesis, portfolio: PortfolioState
    ) -> TradeProposal:
        return self.agents["trader"].ask(
            TradeProposal,
            task=(
                "Turn the thesis into a concrete trade plan: entry, ATR-based stop, target, "
                "size as % of equity. If conviction is low, propose direction=flat."
            ),
            context={"snapshot": snapshot, "thesis": thesis, "portfolio": portfolio},
        )

    # --- Risk committee (qualitativo, opzionale) ----------------------------------------
    def risk_review(
        self, proposal: TradeProposal, verdict: RiskVerdict, portfolio: PortfolioState
    ) -> RiskCommitteeView | None:
        agent = self.agents.get("risk_committee")
        if agent is None or self.risk_debate_rounds == 0 or not verdict.approved:
            return None
        return agent.ask(
            RiskCommitteeView,
            task=(
                "Simulate aggressive, neutral and conservative risk officers, then return a "
                "single size_multiplier in [0,1]. You can only reduce size, never increase it."
            ),
            context={"proposal": proposal, "hard_limits_verdict": verdict, "portfolio": portfolio},
        )

    # --- Portfolio manager -------------------------------------------------------------
    def decide(
        self,
        proposal: TradeProposal,
        verdict: RiskVerdict,
        committee: RiskCommitteeView | None,
        portfolio: PortfolioState,
    ) -> TradeDecision:
        max_size = verdict.approved_size_pct_equity * (
            committee.size_multiplier if committee else 1
        )
        decision = self.agents["portfolio_manager"].ask(
            TradeDecision,
            task=(
                f"Final call: execute, reject or hold. size_pct_equity must be <= {max_size:.4f}."
            ),
            context={
                "proposal": proposal,
                "risk_verdict": verdict,
                "risk_committee": committee,
                "portfolio": portfolio,
            },
        )
        # Clamp difensivo: anche se il PM sbaglia, la size non supera mai il limite.
        if decision.size_pct_equity > max_size:
            decision = decision.model_copy(update={"size_pct_equity": max_size})
        if not verdict.approved and decision.action == "execute":
            decision = decision.model_copy(update={"action": "reject", "size_pct_equity": 0.0})
        return decision
