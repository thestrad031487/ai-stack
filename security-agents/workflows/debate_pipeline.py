from tools.misp_context import get_misp_context
from tools.memory import get_recent_reports
from tools.web_search import get_web_context

class DebatePipeline:
    def __init__(self, agents):
        self.planner = agents["planner"]
        self.research = agents["research"]
        self.risk_a = agents["risk"]
        self.risk_b = agents["risk_b"]
        self.mitigation = agents["mitigation"]
        self.writer = agents["writer"]

    def run(self, topic: str) -> str:
        print(f"\n[debate] starting debate analysis: {topic}\n", flush=True)

        memory_context = get_recent_reports(n=3)
        if memory_context:
            print(f"[memory] injecting past report summaries", flush=True)

        plan = self.planner.run(topic, context=memory_context)
        print(f"\n[plan]\n{plan}\n", flush=True)

        research = self.research.run(topic, context=plan)
        print(f"\n[research]\n{research}\n", flush=True)

        web_context = get_web_context(topic)
        if web_context:
            print(f"[web] injecting web research context", flush=True)

        misp_context = get_misp_context(topic)
        if misp_context:
            print(f"[misp] injecting live IOC context", flush=True)

        risk_context = research
        if web_context:
            risk_context += f"\n\n{web_context}"
        if misp_context:
            risk_context += f"\n\n{misp_context}"

        print(f"\n[debate] running dual risk analysts...\n", flush=True)
        risks_a = self.risk_a.run(risk_context)
        print(f"\n[risk_analyst_a — SOC]\n{risks_a}\n", flush=True)

        risks_b = self.risk_b.run(risk_context)
        print(f"\n[risk_analyst_b — Risk Manager]\n{risks_b}\n", flush=True)

        mitigations = self.mitigation.run(
            f"TECHNICAL RISKS (SOC Analyst):\n{risks_a}\n\nBUSINESS RISKS (Risk Manager):\n{risks_b}"
        )
        print(f"\n[mitigations]\n{mitigations}\n", flush=True)

        final_report = self.writer.run(
            topic,
            context=f"""PLAN:
{plan}

RESEARCH:
{research}

WEB RESEARCH CONTEXT:
{web_context if web_context else "No web results retrieved."}

LIVE THREAT INTEL (MISP):
{misp_context if misp_context else "No live indicators found for this topic."}

TECHNICAL RISK ANALYSIS (SOC Analyst perspective):
{risks_a}

BUSINESS RISK ANALYSIS (Risk Manager perspective):
{risks_b}

MITIGATIONS:
{mitigations}

WRITER INSTRUCTION: This is a debate-format report. After the standard sections, include a "## Analyst Perspectives" section that summarizes where the two analysts agreed, where they diverged, and what the combined view suggests for prioritization."""
        )

        return final_report
