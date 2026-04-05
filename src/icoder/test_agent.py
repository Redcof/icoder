# test_agent.py
from crewai import Agent, Task

def make_test_agent():
    return Agent(
        role="Python Test Engineer",
        goal="Write comprehensive pytest unit tests for Python functions",
        backstory=(
            "You are a senior test engineer who writes clean, maintainable pytest tests. "
            "You test happy paths, edge cases, and error conditions. "
            "You never modify existing tests. You use pytest conventions and fixtures."
        ),
        verbose=True,
        allow_delegation=False,
    )

def make_test_task(agent, func_info) -> Task:
    async_import = "import pytest\nimport pytest_asyncio" if func_info.is_async else "import pytest"
    return Task(
        description=f"""
Generate pytest unit tests for the following Python function.
Rules:
- Use pytest conventions (no unittest classes unless the source uses them)
- Include at least: one happy path, one edge case, one error/exception test if applicable
- Use descriptive test function names (test_<function>_<scenario>)
- Add mocks/patches where external dependencies are involved
- For async functions, use @pytest.mark.asyncio
- Output only the test code, ready to paste into a test file

{async_import}

Function source:
{func_info.source}

File it lives in: {func_info.file_path}
""",
        agent=agent,
        expected_output="Complete pytest test functions as a Python code block"
    )
