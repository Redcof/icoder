from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from pydantic import BaseModel, Field

class UnittestCode(BaseModel):
    """Represents a unittest for the input source code content formated as a plain ASCII string."""
    content: str = Field(..., description="The generated unittest code")

@CrewBase
class UnittestCrew():
    """Unittest crew"""

    agents: list[BaseAgent]
    tasks: list[Task]
    
    @agent
    def test_engineer(self) -> Agent:
        return Agent(
            config=self.agents_config['test_engineer'],
            output_pydantic=UnittestCode,
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
    def testing_task(self) -> Task:
        return Task(
            config=self.tasks_config['testing_task'],
            output_pydantic=UnittestCode,
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
            tasks=self.tasks,    # Automatically created by the @task decorators
            process=Process.sequential,
            verbose=True
        )
