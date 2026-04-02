from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from twin_coder_crew.tools import CodeAnalyzerTool, FileExplorerTool, TestCaseExplorerTool
from crewai_tools import FileReadTool, FileWriterTool

from pydantic import BaseModel, Field

class FunctionMissingDocstring(BaseModel):
    function_name: str = Field(..., description="The name of the function missing a docstring")
    line_range: str = Field(..., description="The line number or range where the function is defined")

class FunctionNeedingUnitTest(BaseModel):
    function_name: str = Field(..., description="The name of the function that needs unit tests")
    reasoning: str = Field(..., description="The reasoning behind why this function needs unit tests")

class CodeAnalysisResult(BaseModel):
    """Structured report of code analysis results for a single file.

    Example:
    [                                                                                                                                                                                                       │
    │    {                                                                                                                                                                                                     │
    │      "file": "/Users/soumensardar/Downloads/twin_coder/sandbox/main.py",                                                                                                                                 │
    │      "functions_missing_docstrings": [                                                                                                                                                                   │
    │        {"function_name": "factorial", "line_range": "1-38"},                                                                                                                                             │
    │        {"function_name": "fibonacci", "line_range": "1-24"},                                                                                                                                             │
    │        {"function_name": "palindrome", "line_range": "1-9"},                                                                                                                                             │
    │        {"function_name": "is_prime", "line_range": "1-20"}                                                                                                                                               │
    │      ],                                                                                                                                                                                                  │
    │      "functions_needing_unit_tests": [                                                                                                                                                                   │
    │        {"function_name": "factorial", "reasoning": "Standard mathematical algorithm for number factorization"},                                                                                          │
    │        {"function_name": "fibonacci", "reasoning": "Computes the n-th Fibonacci number recursively"},                                                                                                    │
    │        {"function_name": "palindrome", "reasoning": "Checks if a string is a palindrome using string method"},                                                                                           │
    │        {"function_name": "is_prime", "reasoning": "Determines if a natural number is prime"}                                                                                                             │
    │      ]                                                                                                                                                                                                   │
    │    }                                                                                                                                                                                                     │
    │  ] 

    """
    file: str = Field(..., description="The full python file path")
    functions_missing_docstrings: list[FunctionMissingDocstring] = Field(..., description="List of functions missing docstrings")
    functions_needing_unit_tests: list[FunctionNeedingUnitTest] = Field(..., description="List of functions needing unit tests")

@CrewBase
class TwinCoder():
    """TwinCoder crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def manager(self) -> Agent:
        return Agent(
            config=self.agents_config['manager'],
            tools=[FileExplorerTool(), Agent()],
            output_pydantic=str,
            verbose=True
        )
    
    @agent
    def code_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['code_analyzer'],
            tools=[FileExplorerTool(), CodeAnalyzerTool(), FileReadTool()],
            output_pydantic=CodeAnalysisResult,
            verbose=True
        )

    @agent
    def documentation_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['documentation_specialist'],
            tools=[FileReadTool(), FileWriterTool()],
            verbose=True
        )

    @agent
    def test_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['test_engineer'],
            tools=[FileReadTool(), FileWriterTool()],
            input_pydantic=CodeAnalysisResult,
            verbose=True
        )
        
    @agent
    def quality_assurance_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['quality_assurance_agent'],
            tools=[TestCaseExplorerTool(), FileReadTool(), FileWriterTool()],
            verbose=True
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task']
        )

    @task
    def documentation_task(self) -> Task:
        return Task(
            config=self.tasks_config['documentation_task']
        )

    @task
    def testing_task(self) -> Task:
        return Task(
            config=self.tasks_config['testing_task']
        )
    
    # @task
    # def verification_task(self) -> Task:
    #     return Task(
    #         config=self.tasks_config['verification_task']
    #     )

    @crew
    def crew(self) -> Crew:
        """Creates the Code Quality crew"""
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorators
            tasks=self.tasks,    # Automatically created by the @task decorators
            process=Process.sequential,
            verbose=True
        )
