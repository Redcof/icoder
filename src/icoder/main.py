#!/usr/bin/env python
import os
import shutil
import sys

import coverage
import pytest
from crewai import CrewOutput
from crewai.flow import Flow, listen, start, router, and_, or_
from pydantic import BaseModel

from icoder.crews.documentation_crew.documentation_crew import DocumentationCrew
from icoder.crews.unittest_crew.unittest_crew import UnittestCrew
from icoder.crews.utils import FileNavigator

FLOW_ERROR_DIR = "errors"


class FileFlags(BaseModel):
    is_valid_file: bool = False
    is_documented: bool = False
    is_unittests_added: bool = False


class iCoderState(BaseModel):
    current_file: str = ""
    current_file_content: str = ""
    file_flags: FileFlags = FileFlags()
    counter: int = 0
    error_counter: int = 0


class iCoderFlow(Flow[iCoderState]):

    def __init__(self, *args, **kwargs):
        if "root_dir" in kwargs.keys():
            self.root_dir = kwargs.pop("root_dir", None)
        assert self.root_dir is not None, f"`root_dir` must be provided to {self.__class__.__name__}"
        if "flow_test" in kwargs.keys():
            self.flow_test = kwargs.pop("flow_test", False)
        super().__init__(*args, **kwargs)
        self.generator = None

    @staticmethod
    def save_file(content: str, file_path: str):
        try:
            open(file_path, "w").write(content)
        except Exception as e:
            raise e

    def save_error_log(self, e, raw_output, prefix: str, file_path: str):
        self.state.error_counter += 1
        dest = self.get_module_structured_path(destination=FLOW_ERROR_DIR)
        os.makedirs(dest, exist_ok=True)
        error_log_path = os.path.join(dest, f"{os.path.basename(file_path)}.{prefix}.error")
        try:
            if raw_output and isinstance(raw_output, CrewOutput):
                open(error_log_path, "w").write(f"Error: {e}\n\n{raw_output.raw}")
            else:
                open(error_log_path, "w").write(f"Error: {e}\n\n{raw_output}")
        except Exception as e:
            raise e

    def update_documentation(self, documented_code: str):
        self.save_file(documented_code, self.state.current_file)
        self.state.file_flags.is_documented = True

    def get_unitest_path(self) -> str:
        """For a given source path follow the same directory 
        structure but locate the testfile under tests/ directory. 
        For example if the source file is project_root/src/module1/utils.py 
        then the test file will be located at project_root/tests/src/module1/test_utils.py"""
        test_dir = self.get_module_structured_path(destination="tests")
        os.makedirs(test_dir, exist_ok=True)
        test_file_path = os.path.join(test_dir, f"test_{os.path.basename(self.state.current_file)}")
        return test_file_path

    def get_module_structured_path(self, destination: str) -> str:
        """For a given source path follow the same directory 
        structure but locate the testfile under destination/ directory. 
        For example if the source file is project_root/src/module1/utils.py 
        then the test file will be located at project_root/destination/src/module1/test_utils.py"""

        module_path = os.path.dirname(self.state.current_file)
        project_dir = self.root_dir
        if module_path.startswith(project_dir):
            module_path = module_path[len(project_dir):].lstrip("/\\")
        test_dir = os.path.join(project_dir, destination, module_path)
        os.makedirs(test_dir, exist_ok=True)
        return test_dir

    def update_unittests(self, unittests_code: str, module_imports: str):
        """For a given source path follow the same directory 
        structure but locate the testfile under tests/ directory. 
        For example if the source file is project_root/src/module1/utils.py 
        then the test file will be located at project_root/tests/src/module1/test_utils.py"""

        test_file_path = self.get_unitest_path()
        self.save_file(module_imports + "\n\n" + unittests_code, test_file_path)
        self.state.file_flags.is_unittests_added = True

    def reset_file_flags(self):
        self.state.file_flags = FileFlags()

    @start()
    def process_project(self) -> str:
        self.generator = FileNavigator(self.root_dir, type_filter="*.py").stream_files()
        # remove previous error logs if any before starting the flow
        error_dir = self.get_module_structured_path(
            destination=FLOW_ERROR_DIR)  # ensure flow_errors directory structure is created
        shutil.rmtree(error_dir) if os.path.exists(error_dir) else None

    @router(or_(process_project, "NEXT"))
    def process_next_file(self) -> str:
        try:
            self.state.current_file = next(self.generator)
            self.reset_file_flags()
            self.state.file_flags.is_valid_file = os.path.isfile(self.state.current_file)
            self.state.current_file_content = open(self.state.current_file).read()
            return "SELECT"
        except StopIteration:
            return "END"

    @router("SELECT")
    def check_file(self) -> str:
        if self.state.file_flags.is_valid_file:
            self.state.counter += 1
            return "CONTINUE"
        else:
            return "ERROR"

    @listen("CONTINUE")
    def is_documentation_done(self):
        """Using interrogate verify if the current file is already well documented, 
        if yes skip documentation task."""
        from interrogate import coverage
        try:
            doc_coverage = coverage.InterrogateCoverage(paths=[self.state.current_file])
            results = doc_coverage.get_coverage()
            if results.missing == 0:
                self.state.file_flags.is_documented = True
        except Exception as e:
            self.state.file_flags.is_documented = False
            self.save_error_log(e, None, "documentation_check", self.state.current_file)

    @router(is_documentation_done)
    def documentation_task(self) -> str:
        raw_output = None
        try:
            if self.flow_test is False:
                if not self.state.file_flags.is_documented:
                    raw_output = DocumentationCrew().crew().kickoff(
                        inputs={"source_code": self.state.current_file_content})
                    updated_content = raw_output.pydantic.content
                    self.update_documentation(updated_content)
            return "DOC_DONE"
        except Exception as e:
            self.save_error_log(e, raw_output, "documentation", self.state.current_file)
            return "ERROR"

    @listen("CONTINUE")
    def is_unittests_done(self) -> str:
        """Check if unittest already exists for the current file, if yes skip unittest task."""
        source_file = self.state.current_file
        test_file = self.get_unitest_path()

        try:
            # 1. Initialize coverage, specifying which file to monitor
            # We use 'include' to ensure we only care about the target file
            cov = coverage.Coverage(include=[source_file])

            # 2. Start measuring
            cov.start()

            # 3. Run the tests via pytest
            # We pass the test_file path to pytest.main
            sys.path.insert(0, os.path.dirname(source_file))  # Ensure the test file's directory is in the path
            exit_code = pytest.main([test_file, "-q"])
            if exit_code != 0:
                self.state.file_flags.is_unittests_added = False

            # 4. Stop measuring
            cov.stop()
            cov.save()

            if exit_code == 0:
                # 5. Extract results
                # This generates a summary of the coverage
                percentage = cov.report(file=sys.stdout)
                self.state.file_flags.is_unittests_added = int(percentage) == 100
        except Exception as e:
            # If any error occurs (e.g., test file doesn't exist, pytest error), we consider unittests not done
            self.state.file_flags.is_unittests_added = False
            self.save_error_log(e, None, "unittests_check", self.state.current_file)

    @router(is_unittests_done)
    def unittest_task(self) -> str:
        raw_output = None
        try:
            if self.flow_test is False:
                if not self.state.file_flags.is_unittests_added:
                    raw_output = UnittestCrew().crew().kickoff(inputs={
                        "source_code": self.state.current_file_content,
                        "source_path": self.state.current_file.replace(self.root_dir, "").strip("/").strip("\\"),
                    })
                    updated_content = raw_output.pydantic.content
                    module_imports = raw_output.pydantic.imports
                    self.update_unittests(updated_content, module_imports)
            return "TEST_DONE"
        except Exception as e:
            self.save_error_log(e, raw_output, "unittests", self.state.current_file)
            return "ERROR"

    @router(and_("DOC_DONE", "TEST_DONE"))
    def move_next(self) -> str:
        return "NEXT"

    @router("ERROR")
    def handle_error(self) -> str:
        # restore source code if any error occurs during documentation or unittest generation
        # self.save_file(self.state.current_file_content, self.state.current_file)
        return "END"

    @listen("END")
    def finish(self):
        return dict(
            root_dir=self.root_dir,
            processed_files=self.state.counter,
            error_count=self.state.error_counter,
            error_dir=os.path.join(self.root_dir, FLOW_ERROR_DIR),
            unittest_cmd=f"""
            cd '{self.root_dir}'
            pytest
            """
        )


def kickoff():
    flow = iCoderFlow(root_dir="sandbox", flow_test=False)
    r = flow.kickoff()
    print(r)
    print(r['unittest_cmd'])


def plot():
    poem_flow = iCoderFlow(root_dir="sandbox", flow_test=True)
    r = poem_flow.plot()
    print(r)


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
