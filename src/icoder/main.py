import argparse
import os

from icoder.crew_runner import run_docstring_crew, run_test_crew
from icoder.scanner import scan_project, find_untested_functions
from icoder.writer import write_docstrings, write_tests


def main():
    parser = argparse.ArgumentParser(description="Auto DocString + Test Generator")
    parser.add_argument("project_root", help="Path to Python project root")
    parser.add_argument("--test-dir", metavar="<project_root>/tests", default="tests",
                        help="Test directory name (only name)")
    parser.add_argument("--skip-private", action="store_true")
    parser.add_argument("--skip-dunder", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing")
    args = parser.parse_args()

    print("🔍 Scanning project...")
    scan_result = scan_project(args.project_root, args.skip_private, args.skip_dunder)
    print(f"  Found {len(scan_result.missing_docstrings)} functions missing docstrings")

    untested = find_untested_functions(scan_result, os.path.join(args.project_root, args.test_dir))
    print(f"  Found {len(untested)} functions missing tests")

    if scan_result.missing_docstrings:
        print("\n📝 Generating docstrings...")
        docstring_results = run_docstring_crew(scan_result.missing_docstrings)
        if not args.dry_run:
            for file_path, insertions in docstring_results.items():
                write_docstrings(file_path, insertions)
                print(f"  ✅ Docstrings written to {file_path}")

    if untested:
        print("\n🧪 Generating unit tests...")
        test_results = run_test_crew(untested)
        if not args.dry_run:
            for file_path, test_codes in test_results.items():
                write_tests(file_path, test_codes, args.test_dir)
                print(f"  ✅ Tests written for {file_path}")

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
