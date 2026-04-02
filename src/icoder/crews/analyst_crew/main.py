#!/usr/bin/env python
import warnings


from twin_coder_crew.crew import TwinCoder

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    """
    Run the crew.
    """
    inputs = {
        'codebase_path': '/Users/soumensardar/Downloads/twin_coder/sandbox/',
        'threshold': 80
    }

    try:
        TwinCoder().crew().kickoff(inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")

