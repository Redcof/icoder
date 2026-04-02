#!/usr/bin/env python
import asyncio
import os

from crewai import tasks
from crewai.flow import Flow, listen, start, router, and_, or_
from icoder.crews.poem_crew.poem_crew import PoemCrew
from pydantic import BaseModel
from pathlib import Path

class iCoderState(BaseModel):
    current_file: str = ""
    is_documentated: bool = False
    is_unittests_added: bool = False
    is_unittested: bool = False
    is_valid_file: bool = True



class FileNavigator:
    def __init__(self, root_dir, type_filter="*.py"):
        self.root_dir = root_dir
        self.type_filter = type_filter

    def stream_files(self):
        """Yields one Python file path at a time without loading the whole list."""
        path_obj = Path(self.root_dir)
        # rglob returns a generator, not a list!
        for file_path in path_obj.rglob(self.type_filter):
            yield str(file_path)

class iCoderFlow(Flow[iCoderState]):
    
    def __init__(self, *args, **kwargs):
        if "file" in kwargs.keys():
            file = kwargs.pop("file")
        super().__init__(*args, **kwargs)
        self.state.current_file = file
    
    @start()
    def process_file(self):
        self.state.is_valid_file = os.path.isfile(self.state.current_file)
        print(f"--- Processing: {self.state.current_file} ---")

    @router(process_file)
    def verify(self):
        if self.state.is_valid_file:
            return "CONTINUE"
        else:
            return "ERROR"

    
    @listen("CONTINUE")
    def documentation_task(self):
        print(f"Documenting: {self.state.current_file}")
        # Simulate documentation work here
        self.state.is_documentated = True
    
    @listen("CONTINUE")
    def unittest_task(self):
        print(f"Adding unittests: {self.state.current_file}")
        # Simulate unittest work here
        self.state.is_unittests_added = True
    
    @listen(or_(and_(documentation_task, unittest_task), "ERROR"))
    def end(self):
        # Automatically pick the next file after processing the current one
        print(f"Finished processing: {self.state.current_file}")
        return 


def kickoff():
    generator = FileNavigator("src", type_filter="*.py").stream_files()
    def process_with_flow(file):
        flow = iCoderFlow(file=file)
        return flow.kickoff()
    for file in generator:
        process_with_flow(file)

def plot():
    poem_flow = iCoderFlow(file=None)
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
