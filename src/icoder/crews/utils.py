import os
from crewai import LLM


def get_llm():
    return LLM(
        model=os.environ.get('MODEL'),
        temperature=float(os.getenv("LLM_TEMPERATURE", 0.01)),
        top_p=float(os.getenv("LLM_TOP_P", 0.1)),
        top_k=float(os.getenv("LLM_TOP_K", 5)),
        seed=int(os.getenv("LLM_SEED", 1))
    )