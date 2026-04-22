from tools.misp_context import get_misp_context
from tools.memory import get_recent_reports
from tools.web_search import get_web_context

class SecurityPipeline:
    def __init__(self, agents):
        self.planner = agents["planner"]
        self.research = agents["research"]
        self.risk = agents["risk"]
        self.mitigation = agents["mitigation"]
        self.writer = agents["writer"]

    def run(self, topic: str) -> str:
        print(f"\n[pipeline] starting security analysis: {topic}\n", flush=True)

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

        risks = self.risk.run(risk_context)
        print(f"\n[risks]\n{risks}\n", flush=True)

        mitigations = self.mitigation.run(risks)
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

RISKS:
{risks}

MITIGATIONS:
{mitigations}"""
        )

        return final_report

    def run_with_stages(self, topic: str) -> dict:
        memory_context = get_recent_reports(n=3)
        plan = self.planner.run(topic, context=memory_context)
        research = self.research.run(topic, context=plan)

        web_context = get_web_context(topic)
        misp_context = get_misp_context(topic)

        risk_context = research
        if web_context:
            risk_context += f"\n\n{web_context}"
        if misp_context:
            risk_context += f"\n\n{misp_context}"

        risks = self.risk.run(risk_context)
        mitigations = self.mitigation.run(risks)
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

RISKS:
{risks}

MITIGATIONS:
{mitigations}"""
        )
        return {
            "plan": plan,
            "research": research,
            "web_context": web_context,
            "misp_context": misp_context,
            "risks": risks,
            "mitigations": mitigations,
            "report": final_report
        }
