import os
import pathlib

from crewai import LLM


def get_llm():
    return LLM(
        model=os.environ.get('MODEL'),
        temperature=float(os.getenv("LLM_TEMPERATURE", 0.5)),
        top_p=float(os.getenv("LLM_TOP_P", 0.5)),
        top_k=float(os.getenv("LLM_TOP_K", 100)),
        seed=int(os.getenv("LLM_SEED", 1))
    )


class FileNavigator:
    def __init__(self, root_dir, type_filter="*.py"):
        self.root_dir = root_dir
        self.type_filter = type_filter

    def stream_files(self):
        """Yields one Python file path at a time without loading the whole list."""
        path_obj = pathlib.Path(self.root_dir)
        # rglob returns a generator, not a list!
        for file_path in path_obj.rglob(self.type_filter):
            # skip test files and files in unittest directories
            if ("tests/" in str(file_path)
                    or "tests\\" in str(file_path)
                    or os.path.basename(str(file_path)).startswith("test_")):
                continue
            yield str(file_path)
