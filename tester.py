import os
import shutil
import subprocess
import sys
import tempfile
from enum import Enum

WRAPPERS_DIR = "wrappers"
TEST_DIR = "test"
TEST_INPUTS_DIR = "input"
SNAKEFILE_NAME = "Snakefile"
LOGS_DIR = "logs"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class SnakemakeConfigError(ValueError):
    pass


class SnakemakeNoLogError(ValueError):
    def __init__(self, command: str, stdout: str, stderr: str):
        message = (
            f"Running failed for command: \n{command}\n"
            + f"No log was found\n"
            + f"Stdout: \n{stdout}\n"
            + f"Stderr: \n{stderr}\n"
        )
        super().__init__(message)


class SnakemakeError(ValueError):
    def __init__(self, command: str, log: str, stdout: str, stderr: str):
        message = (
            f"Running failed for command: {command}\n"
            + f"Log output:\n{log}\n"
            + f"Stdout:\n{stdout}"
            + f"Stderr:\n{stderr}"
        )
        super().__init__(message)


class TestStatus(Enum):
    PASSED = "PASSED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"
    MISCONFIGURED = "MISCONFIGURED"
    IGNORED = "IGNORED"


class TestResult:
    status: TestStatus
    message: str | None

    def __init__(self, status: TestStatus, message: str | None = None):
        self.status = status
        self.message = message

    @property
    def has_failed(self):
        return self.status not in (TestStatus.PASSED, TestStatus.SKIPPED)


def handle_test(test_dir: str) -> TestResult:
    if not os.path.exists(test_dir):
        return TestResult(
            status=TestStatus.IGNORED,
            message=f"Test directory {test_dir} does not exist",
        )

    try:
        run_test_snake(test_dir)
    except SnakemakeConfigError as err:
        return TestResult(
            status=TestStatus.MISCONFIGURED,
            message=f"Test not configured properly - {err=}",
        )
    except (SnakemakeNoLogError, SnakemakeError) as err:
        return TestResult(status=TestStatus.FAILED, message=f"Test failed - {err=}")
    return TestResult(status=TestStatus.PASSED)


def run_test_snake(test_dir: str):
    snakefile = get_snake_file(test_dir)
    input_dir = get_input_dir(test_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copytree(input_dir, tmpdir, dirs_exist_ok=True)

        test_snakefile = os.path.join(tmpdir, "Snakefile")
        with open(snakefile, "r") as f:
            snakefile_content = f.read()

        test_snakefile_content = snakefile_content.replace(
            "https://github.com/xsitarcik/wrappers/raw/main", f"file://{BASE_DIR}"
        )
        with open(test_snakefile, "w") as f:
            f.write(test_snakefile_content)

        call_snakefile(test_snakefile, tmpdir)


def call_snakefile(snakefile: str, tmpdir: str):
    conda_prefix_dir = os.path.join(tmpdir, "tmp_conda")
    command = (
        f"snakemake --show-failed-logs -c1 --snakefile {snakefile} --directory {tmpdir} --printshellcmds --use-conda --conda-prefix {conda_prefix_dir}"
    )
    print("Calling command: {}".format(command))

    proc = subprocess.run(command, shell=True, capture_output=True)
    if proc.returncode == 0:
        return

    stdout = proc.stdout.decode()
    stderr = proc.stderr.decode()
    logs_dir = os.path.join(tmpdir, LOGS_DIR)
    if os.path.exists(logs_dir):
        logs = os.listdir()
        if len(logs) == 1:
            log_path = os.path.join(tmpdir, LOGS_DIR, logs[0])
            with open(log_path) as f:
                log_content = f.read()
            raise SnakemakeError(command, log_content, stdout, stderr)
    raise SnakemakeNoLogError(command, stdout, stderr)


def get_input_dir(test_dir: str) -> str:
    input_dir = os.path.join(test_dir, TEST_INPUTS_DIR)
    if not os.path.exists(input_dir):
        raise SnakemakeConfigError("Input dir does not exist: %s" % input_dir)
    return input_dir


def get_snake_file(test_dir: str) -> str:
    snakefile = os.path.join(test_dir, SNAKEFILE_NAME)
    if not os.path.exists(snakefile):
        raise SnakemakeConfigError("Snakefile does not exist: %s" % snakefile)
    return snakefile


def is_wrapper_among_changed_ones(wrapper_base_dir: str, changed_files: list[str]) -> bool:
    for change in changed_files:
        if change.startswith(wrapper_base_dir):
            return True
    return False


def run_tests_for_changed_files(changed_files: list[str]) -> dict[str, TestResult]:
    test_results: dict[str, TestResult] = {}
    for tool, tool_dir in list_dirs_in_dir(WRAPPERS_DIR):
        for command, _ in list_dirs_in_dir(tool_dir):
            wrapper_rule = os.path.join(WRAPPERS_DIR, tool, command)
            if is_wrapper_among_changed_ones(wrapper_rule, changed_files):
                test_results[f"{tool}-{command}"] = handle_test(os.path.join(wrapper_rule, TEST_DIR))
            else:
                test_results[f"{tool}-{command}"] = TestResult(status=TestStatus.SKIPPED, message="Not changed")
    return test_results


def list_dirs_in_dir(listing_dir: str) -> list[tuple[str, str]]:
    return [
        (name, full_path)
        for name in os.listdir(listing_dir)
        if os.path.isdir(full_path := os.path.join(listing_dir, name)) and not name.startswith((".", "_"))
    ]


def print_out_information_about_failed_tests(failed_tests: dict[str, TestResult]):
    failed_test_names = list(failed_tests.keys())
    print(f"The number of failed tests: {len(failed_tests)}", file=sys.stderr)
    print(f"{failed_test_names=}", file=sys.stderr)
    for wrapper_rule_name, test_result in failed_tests.items():
        concise_result = f" {wrapper_rule_name} - {test_result.status.value} "
        print(f"{concise_result:.^80}", file=sys.stderr)
        if test_result.message:
            for message in test_result.message.split("\\n"):
                print(message, file=sys.stderr)


def get_failed_tests(test_results: dict[str, TestResult]) -> dict[str, TestResult]:
    return {wrapper: result for wrapper, result in test_results.items() if result.has_failed}


if __name__ == "__main__":
    test_results = run_tests_for_changed_files(sys.argv[1:])
    print("Printing test results")
    for wrapper, result in test_results.items():
        print(wrapper, result.status)

    failed_tests = get_failed_tests(test_results)
    if len(failed_tests) > 0:
        print_out_information_about_failed_tests(failed_tests)
        exit(-1)
