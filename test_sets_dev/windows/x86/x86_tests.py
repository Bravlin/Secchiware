import os

from test_utils import TestResult, TestSet, test

class DebuggerSet(TestSet):

    def __init__(self):
        self.package_dir = os.path.dirname(os.path.abspath(__file__))
        self.bin_dir = os.path.join(self.package_dir, "bin")

    @test(
        name="Execute INT 2Dh instruction.",
        description="Verifies if a debugger is attached to the process by observing the handling of a breakpoint.")
    def int2dh(self) -> TestResult:
        exe_path = os.path.join(self.bin_dir, "int2dh.exe")
        process = os.popen(exe_path)
        if process.close() is None:
            # There was no error, so a debugger was detected
            return TestSet.TEST_FAILED
        # It crashed, so there was no debugger
        return TestSet.TEST_PASSED