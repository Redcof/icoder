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
            if ("tests/" in str(file_path) 
                or "tests\\" in str(file_path) 
                or os.path.basename(str(file_path)).startswith("test_")):
                continue
            yield str(file_path)

class iCoderFlow(Flow[iCoderState]):
    
    def __init__(self, *args, **kwargs):
        if "root_dir" in kwargs.keys():
            self.root_dir = kwargs.pop("root_dir", None)
        assert self.root_dir is not None, "`root_dir` must be provided to {self.__class__.__name__}"
        if "flow_test" in kwargs.keys():
            self.flow_test = kwargs.pop("flow_test", False)
        super().__init__(*args, **kwargs)
        
    @staticmethod
    def save_file(content:str, file_path: str):
        try:
            open(file_path, "w").write(content)
        except Exception as e:
            raise e
    
    @staticmethod
    def save_error_log(e, raw_output, prefix: str, file_path: str):
        os.makedirs("flow_errors", exist_ok=True)
        error_log_path = os.path.join("flow_errors", f"{os.path.basename(file_path)}.{prefix}.error")
        try:
            if raw_output and isinstance(raw_output, CrewOutput):
                open(error_log_path, "w").write(f"Error: {e}\n\n{raw_output.raw}")
            else:
                open(error_log_path, "w").write(f"Error: {e}\n\n{raw_output}")
        except Exception as e:
            raise e
    
    def update_documentation(self, documented_code: str):
        self.save_file(documented_code, self.state.current_file)
        self.state.file_state.is_documentated = True
    
    def update_unittests(self, unittests_code: str):
        """For a given source path follow the same directory 
        structure but locate the testfile under tests/ directory. 
        For example if the source file is project_root/src/module1/utils.py 
        then the test file will be located at project_root/tests/src/module1/test_utils.py"""
        
        module_path = os.path.dirname(self.state.current_file)
        project_dir = self.root_dir
        if module_path.startswith(project_dir):
            module_path = module_path[len(project_dir):].lstrip("/\\")
        test_dir = os.path.join(project_dir, "tests", module_path)
        os.makedirs(test_dir, exist_ok=True)
        test_file_path = os.path.join(test_dir, f"test_{os.path.basename(self.state.current_file)}")
        self.save_file(unittests_code, test_file_path)
        self.state.file_state.is_unittests_added = True
    
    
    def reset_filestate(self):
        self.state.file_state = FileState()
    
    @start()
    def process_project(self) -> str:
        self.generator = FileNavigator(self.root_dir, type_filter="*.py").stream_files()
    
    @router(or_(process_project, "NEXT"))
    def process_next_file(self) -> str:
        try:
            self.state.current_file = next(self.generator)
            self.reset_filestate()
            self.state.file_state.is_valid_file = os.path.isfile(self.state.current_file)
            self.state.current_file_content = open(self.state.current_file).read()
            return "SELECT"
        except StopIteration:
            return "END"

    @router("SELECT")
    def check_file(self) -> str:
        if self.state.file_state.is_valid_file:
            self.state.counter += 1
            return "CONTINUE"
        else:
            return "ERROR"
    
    @router("CONTINUE")
    def is_documentation_done(self) -> bool:
        """Using interrogate verify if the current file is already well documented, 
        if yes skip documentation task."""
        from interrogate import coverage
        doc_coverage = coverage.InterrogateCoverage(paths=[self.state.current_file])
        results = doc_coverage.get_coverage()
        if results.missing == 0:
            self.state.file_state.is_documentated = True
            return "DOCUMENTATION_DONE"
        return "GENERATE_DOCUMENTATION"
    
    @router("GENERATE_DOCUMENTATION")
    def documentation_task(self) -> str:
        raw_output = None
        try:
            if self.flow_test is False:
                raw_output = DocumentationCrew().crew().kickoff(inputs={"source_code": self.state.current_file_content})
                updated_content = raw_output.pydantic.content
            else:
                updated_content = self.state.current_file_content
            self.update_documentation(updated_content)
            return "DOCUMENTATION_DONE"
        except Exception as e:
            self.save_error_log(e, raw_output, "documentation", self.state.current_file)
            return "ERROR"
    
    @router("CONTINUE")
    def unittest_task(self) -> str:
        raw_output = None
        try:
            if self.flow_test is False:
                raw_output = UnittestCrew().crew().kickoff(inputs={
                    "source_code": self.state.current_file_content,
                    "source_path": self.state.current_file
                    })
                updated_content = raw_output.pydantic.content
            else:
                updated_content = self.state.current_file_content
            self.update_unittests(updated_content)
            return "UNITTESTS_DONE"
        except Exception as e:
            self.save_error_log(e, raw_output, "unittests", self.state.current_file)
            return "ERROR"

    @router(and_("DOCUMENTATION_DONE", "UNITTESTS_DONE"))
    def move_next(self) -> str:
        return "NEXT"

    @listen("ERROR")
    def handle_error(self) -> str:
        # restore source code if any error occurs during documentation or unittest generation
        # self.save_file(self.state.current_file_content, self.state.current_file)
        return "END"
    
    @listen("END")
    def finish(self):
        pass


def kickoff():
    flow = iCoderFlow(root_dir="sandbox", flow_test=True)
    flow.kickoff()

def plot():
    poem_flow = iCoderFlow(root_dir="sandbox", flow_test=True)
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
