import os

from test_utils import TestResult, TestSet, test


class MonitoringSet(TestSet):

    @test(
        name="Is tracer attached?",
        description="Looks for a TracerPid different than 0.")
    def is_tracer_attached(self) -> TestResult:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("TracerPid"): break
        pid = int(line.split()[-1])
        additional_info = {
            'found_pid': pid
        }
        result = TestSet.TEST_PASSED if pid == 0 else TestSet.TEST_FAILED
        return result, additional_info

    @test(
        name="Is Wireshark running?",
        description="Looks for a process named 'wireshark'.")
    def wireshark_running(self) -> TestResult:
        pgrep = os.popen("pgrep wireshark")
        pids = pgrep.read()
        if not pgrep.close() is None:
            return TestSet.TEST_INCONCLUSIVE
        if pids:
            additional_info = {
                'PIDs found:': [int(pid) for pid in pids.split("\n")[:-1]]
            }
            return TestSet.TEST_FAILED, additional_info
        return TestSet.TEST_PASSED


class HooksAndInjectedLibrariesSet(TestSet):

    @test(
        name="Is LD_PRELOAD present?",
        description=
            "Checks if the process was started with the LD_PRELOAD "\
            "environment variable")
    def ld_preload_present(self) -> TestResult:
        if 'LD_PRELOAD' in os.environ:
            additional_info = {
                'found_libraries': os.environ['LD_PRELOAD']
            }
            return TestSet.TEST_FAILED, additional_info
        return TestSet.TEST_PASSED


class NetworkingSet(TestSet):

    @test(
        name="Are cached SSIDs present?",
        description=
            "Looks for a file in "\
            "'/etc/NetworkManager/system-connections/'.")
    def ssids_present(self) -> TestResult:
        path = "/etc/NetworkManager/system-connections/"
        if not os.path.isdir(path):
            return TestSet.TEST_INCONCLUSIVE
        elements = os.listdir(path)
        for e in elements:
            if os.path.isfile(os.path.join(path, e)):
                return TestSet.TEST_PASSED
        return TestSet.TEST_FAILED


class HardwareSet(TestSet):

    @test(
        name="Are there at least 2 CPU cores?",
        description="Checks how many cores the processor has through nproc.")
    def at_least_two_cores(self) -> TestResult:
        nproc = os.popen("nproc")
        cores = nproc.read()
        if not nproc.close() is None:
            return TestSet.TEST_INCONCLUSIVE
        cores = int(cores.rstrip())
        additional_info = {
            'cores': cores
        }
        result = TestSet.TEST_FAILED if cores < 2 else TestSet.TEST_PASSED
        return result, additional_info