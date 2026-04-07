import configparser
import os
import pathlib
import tomllib

from interrogate.config import find_project_config, parse_pyproject_toml, parse_setup_cfg, InterrogateConfig
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
    def __init__(self, root_dir, skip_test_dir: str = None):
        self.root_dir = root_dir
        self.type_filter = "*.py"
        self.test_dir_name = skip_test_dir
        self.skip_test = skip_test_dir is not None
    
    def stream_files(self):
        """Yields one Python file path at a time without loading the whole list."""
        path_obj = pathlib.Path(self.root_dir)
        # rglob returns a generator, not a list!
        for file_path in path_obj.rglob(self.type_filter):
            if self.skip_test:
                # skip test files and files in unittest directories
                if (self.test_dir_name + "/" in str(file_path)
                    or self.test_dir_name + "\\" in str(file_path)
                    or os.path.basename(str(file_path)).startswith("test_")):
                    continue
            yield str(file_path)


def get_interrogate_config(project_directory):
    # 1. Search for a config file (pyproject.toml or setup.cfg) 
    # starting from the current directory
    value = ""
    for path in (
        os.path.join(project_directory, "pyproject.toml"),
        os.path.join(project_directory, "setup.cfg"),
    ):
        if os.path.exists(path):
            value = path
            break
    
    config = None
    if value.endswith(".toml"):
        try:
            config = parse_pyproject_toml(value)
        except (tomllib.TOMLDecodeError, OSError) as e:
            raise Exception(f"Error reading configuration file: {e}\n'{value}'")
    
    elif value.endswith(".cfg"):
        try:
            config = parse_setup_cfg(value)
        except configparser.ParsingError as e:
            raise Exception(f"Error reading configuration file: {e}\n'{value}'")
    if config is None:
        config = InterrogateConfig(
            color=True,
            ignore_module=True,
            docstring_style="google",
            fail_under=100
        )
    return config
