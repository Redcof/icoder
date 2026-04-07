from crewai import Crew, Process

from icoder.docstring_agent import make_docstring_agent, make_docstring_task
from icoder.test_agent import make_test_agent, make_test_task


def run_docstring_crew(missing_docstrings: list) -> dict:
    """Returns {file_path: {func_name: docstring}}"""
    agent = make_docstring_agent()
    tasks = [make_docstring_task(agent, fn) for fn in missing_docstrings]

    crew = Crew(
        agents=[agent],
        tasks=tasks,
        process=Process.sequential,  # or Process.hierarchical for large codebases
        verbose=True,
    )
    results = crew.kickoff()

    output = {}
    for fn, result in zip(missing_docstrings, results if isinstance(results, list) else [results]):
        output.setdefault(fn.file_path, {})[fn.name] = str(result)
    return output


def run_test_crew(untested_functions: list) -> dict:
    """Returns {file_path: test_code_string}"""
    agent = make_test_agent()
    tasks = [make_test_task(agent, fn) for fn in untested_functions]

    crew = Crew(
        agents=[agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    results = crew.kickoff()

    output = {}
    for fn, result in zip(untested_functions, results if isinstance(results, list) else [results]):
        output.setdefault(fn.file_path, []).append(str(result))
    return output
