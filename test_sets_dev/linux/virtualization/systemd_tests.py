import os

from test_utils import TestResult, TestSet, test


class SystemdSet(TestSet):

    @test(
        name="Looks for virtualization with systemd",
        description="Executes systemd-detect-virt and examines the result.")
    def systemd_detect_virt_test(self) -> TestResult:
        process = os.popen("systemd-detect-virt")
        virt = process.read().rstrip()
        process.close()
        if not virt:
            return TestSet.TEST_INCONCLUSIVE
        if virt == "none":
            return TestSet.TEST_PASSED
        additional_info = {
            'virtualization_type': virt
        }
        return TestSet.TEST_FAILED, additional_info