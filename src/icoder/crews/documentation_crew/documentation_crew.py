from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task

from icoder.types import DocumentedCode


@CrewBase
class DocumentationCrew():
    """Documentation crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def documentation_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['documentation_specialist'],
            # llm=get_llm(),
            verbose=True
        )

    # @agent
    # def quality_assurance_agent(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config['quality_assurance_agent'],
    #         tools=[TestCaseExplorerTool(), FileReadTool(), FileWriterTool()],
    #         verbose=True
    #     )

    @task
    def documentation_task(self) -> Task:
        return Task(
            config=self.tasks_config['documentation_task'],
            output_pydantic=DocumentedCode,
            verbose=True
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
            tasks=self.tasks,  # Automatically created by the @task decorators
            process=Process.sequential,
            verbose=True
        )
