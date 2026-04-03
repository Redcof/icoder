#!/usr/bin/env python
import os
from crewai import CrewOutput
from crewai.flow import Flow, listen, start, router, and_, or_
from pydantic import BaseModel
from pathlib import Path

from icoder.crews.unittest_crew.unittest_crew import UnittestCrew
from icoder.crews.documentation_crew.documentation_crew import DocumentationCrew

class FileState(BaseModel):
    is_valid_file: bool = False
    is_documentated: bool = False
    is_unittests_added: bool = False

class iCoderState(BaseModel):
    current_file: str = ""
    current_file_content: str = ""
    file_state: FileState = FileState()
    counter: int = 0
    

class iCoderFlowState:
    START: str = "START"
    SELECT: str = "SELECT"
    CONTINUE: str = "CONTINUE"
    NEXT: str = "NEXT"
    ERROR: str = "ERROR"
    END: str = "END"

class FileNavigator:
    def __init__(self, root_dir, type_filter="*.py"):
        self.root_dir = root_dir
        self.type_filter = type_filter

    def stream_files(self):
        """Yields one Python file path at a time without loading the whole list."""
        path_obj = Path(self.root_dir)
        # rglob returns a generator, not a list!
        for file_path in path_obj.rglob(self.type_filter):
            # skip test files and files in unittest directories
            if "unittests" in str(file_path) or os.path.basename(str(file_path)).startswith("test_"):
                continue
            yield str(file_path)

class iCoderFlow(Flow[iCoderState]):
    
    def __init__(self, *args, **kwargs):
        if "root_dir" in kwargs.keys():
            root_dir = kwargs.pop("root_dir", None)
        super().__init__(*args, **kwargs)
        self.generator = FileNavigator(root_dir, type_filter="*.py").stream_files()
    
    def reset_filestate(self):
        self.state.file_state = FileState()
    
    @start()
    def process_project(self) -> str:
        self.state.file_state.is_valid_file = os.path.isfile(self.state.current_file)
    
    @router(or_(process_project, iCoderFlowState.NEXT))
    def process_next_file(self) -> str:
        try:
            self.state.current_file = next(self.generator)
            self.reset_filestate()
            self.state.file_state.is_valid_file = os.path.isfile(self.state.current_file)
            self.state.current_file_content = open(self.state.current_file).read()
            return iCoderFlowState.SELECT
        except StopIteration:
            return iCoderFlowState.END

    @router(iCoderFlowState.SELECT)
    def verify(self) -> str:
        if self.state.file_state.is_valid_file:
            self.state.counter += 1
            return iCoderFlowState.CONTINUE
        else:
            return iCoderFlowState.ERROR

    def save_file(content:str, file_path: str):
        try:
            open(file_path, "w").write(content)
        except Exception as e:
            raise e
    
    def update_documentation(self, documented_code: str):
        self.save_file(documented_code, self.state.current_file)
        self.state.file_state.is_documentated = True
    
    def update_unittests(self, unittests_code: str):
        module_path = os.path.dirname(self.state.current_file)
        test_dir = os.path.join(module_path, "unittests")
        os.makedirs(test_dir, exist_ok=True)
        test_file_path = os.path.join(test_dir, f"test_{os.path.basename(self.state.current_file)}")
        self.save_file(unittests_code, test_file_path)
        self.state.file_state.is_unittests_added = True
    
    @listen(iCoderFlowState.CONTINUE)
    def documentation_task(self):
        raw_output = None
        try:
            raw_output = DocumentationCrew().crew().kickoff(inputs={"source_code": self.state.current_file_content})
            self.update_documentation(raw_output.pydantic.content)
        except Exception:
            open(self.state.current_file+".documentation.error", "w").write(f"{type(raw_output)}\n\n{raw_output.raw}")
            return iCoderFlowState.ERROR
    
    @listen(iCoderFlowState.CONTINUE)
    def unittest_task(self):
        raw_output = None
        try:
            raw_output = UnittestCrew().crew().kickoff(inputs={"source_code": self.state.current_file_content})
            self.update_unittests(raw_output.pydantic.content)
        except Exception:
            open(self.state.current_file+".unittests.error", "w").write(f"{type(raw_output)}\n\n{raw_output.raw}")
            return iCoderFlowState.ERROR

    @router(or_(and_(documentation_task, unittest_task)))
    def move_next(self) -> str:
        return iCoderFlowState.NEXT

    @router(iCoderFlowState.ERROR)
    def handle_error(self) -> str:
        # restore source code if any error occurs during documentation or unittest generation
        self.save_file(self.state.current_file_content, self.state.current_file)
        return iCoderFlowState.END
    
    @listen(iCoderFlowState.END)
    def finish(self):
        pass


def kickoff():
    flow = iCoderFlow(root_dir="sandbox")
    flow.kickoff()

def plot():
    poem_flow = iCoderFlow(root_dir="sandbox")
    poem_flow.plot()


def run_with_trigger():
    """
    Run the flow with trigger payload.
    """
    import json
    import sys

    # Get trigger payload from command line argument
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    # Create flow and kickoff with trigger payload
    # The @start() methods will automatically receive crewai_trigger_payload parameter
    poem_flow = iCoderFlow()

    try:
        result = poem_flow.kickoff({"crewai_trigger_payload": trigger_payload})
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the flow with trigger: {e}")


if __name__ == "__main__":
    kickoff()
