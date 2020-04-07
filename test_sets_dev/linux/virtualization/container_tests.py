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

    @test(
        name="Is the first process an init?",
        description="Verifies that the name of the process with PID 1 corresponds to a well known init.")
    def is_first_process_an_init(self) -> TestSet:
        known_inits = {"systemd", "upstart", "sysv-init"}
        with open("/proc/1/sched", "r") as f:
            process_name = f.readline().split(" ")[0]
        additional_info = {
            'found_process_name': process_name
        }
        result = 1 if process_name in known_inits else -1
        return result, additional_info


class DockerSet(TestSet):

    @test(
        name="Is '.dockerenv' present?",
        description="Looks for a file named .dockerenv in directory '/'.")
    def dockerenv_present(self) -> TestResult:
        return -1 if os.path.isfile("/.dockerenv") else 1