import os
import re

from test_utils import TestResult, TestSet, test

class ContainerSet(TestSet):

    @test(
        name="Read kallsyms",
        description="Verifies that if the user is root, then addresses in '/proc/kallsyms' should all not be 0.")
    def read_kallsyms(self) -> TestResult:
        process = os.popen("whoami")
        user = process.read().rstrip()
        process.close()
        if not user:
            additional_info = {
                'error': "User name could not be queried."
            }
            return 0, additional_info
        if user != "root":
            additional_info = {
                'error': "User name is not root."
            }
            return 0, additional_info
        with open("/proc/kallsyms", "r") as f:
            for line in f:
                if re.match("0+ ", line) is None:
                    return 1
        return -1

class DockerSet(TestSet):

    @test(
        name="Is '.dockerenv' present?",
        description="Looks for a file named .dockerenv in directory '/'.")
    def dockerenv_present(self) -> TestResult:
        return -1 if os.path.isfile("/.dockerenv") else 1