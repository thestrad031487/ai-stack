class BaseAgent:
    def __init__(self, name: str, system_prompt: str, llm):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm

    def run(self, task: str, context: str = "") -> str:
        prompt = f"""SYSTEM:
{self.system_prompt}

CONTEXT:
{context}

TASK:
{task}

Respond concisely and in plain text only."""
        print(f"[{self.name}] running...")
        result = self.llm.generate(prompt)
        print(f"[{self.name}] done.")
        return result
