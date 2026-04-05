# docstring_agent.py
from crewai import Agent, Task

def make_docstring_agent():
    return Agent(
        role="Python Documentation Specialist",
        goal="Generate accurate, Google-style docstrings for undocumented Python functions",
        backstory=(
            "You are an expert Python developer who writes clear, concise docstrings. "
            "You analyze function signatures and bodies to produce accurate documentation. "
            "You never modify existing docstrings. You output only the docstring text itself."
        ),
        verbose=True,
        allow_delegation=False,
    )

def make_docstring_task(agent, func_info) -> Task:
    context = f"""
Function name: {func_info.name}
Class: {func_info.class_name or 'N/A (top-level)'}
Is async: {func_info.is_async}
Decorators: {', '.join(func_info.decorators) or 'none'}
Source code:
{func_info.source}
"""
    return Task(
        description=f"""
Generate a Google-style docstring for the following Python function.
Rules:
- Output ONLY the docstring content (the text between triple quotes, not the quotes themselves)
- Include Args, Returns, Raises sections if applicable
- Be concise but accurate
- Do NOT include the function definition itself

{context}
""",
        agent=agent,
        expected_output="A complete Google-style docstring body (no triple quotes)"
    )
