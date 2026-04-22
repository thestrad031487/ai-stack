import os
import sys
from datetime import datetime
from tools.llm import LLM
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.risk_analyst import RiskAgent
from agents.risk_analyst_b import RiskAgentB
from agents.mitigation import MitigationAgent
from agents.writer import WriterAgent
from workflows.security_pipeline import SecurityPipeline
from workflows.debate_pipeline import DebatePipeline

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

def build_agents(llm):
    return {
        "planner": PlannerAgent(llm),
        "research": ResearchAgent(llm),
        "risk": RiskAgent(llm),
        "risk_b": RiskAgentB(llm),
        "mitigation": MitigationAgent(llm),
        "writer": WriterAgent(llm),
    }

def main():
    args = sys.argv[1:]

    debate_mode = False
    if args and args[0] == "--debate":
        debate_mode = True
        args = args[1:]

    topic = " ".join(args) if args else "self-hosted AI platform security"

    llm = LLM(ollama_url=OLLAMA_URL)
    agents = build_agents(llm)

    if debate_mode:
        pipeline = DebatePipeline(agents)
        print(f"\n[mode] debate pipeline", flush=True)
    else:
        pipeline = SecurityPipeline(agents)
        print(f"\n[mode] standard pipeline", flush=True)

    report = pipeline.run(topic)

    print(f"\n{'='*60}")
    print("FINAL REPORT")
    print('='*60)
    print(report)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = "debate" if debate_mode else "report"
    filename = f"outputs/reports/{prefix}_{timestamp}.md"
    os.makedirs("outputs/reports", exist_ok=True)
    with open(filename, "w") as f:
        f.write(f"# Security Report: {topic}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(report)

    print(f"\n[saved] {filename}")

if __name__ == "__main__":
    main()
