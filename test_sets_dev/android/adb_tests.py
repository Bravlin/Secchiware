import os

from test_utils import TestResult, TestSet, test


class ADBEmulatorSet(TestSet):

    @test(
        name="Does the brand correspond to an emulator?",
        description="Verifies the brand property against 'generic'.")
    def brand_from_emulator(self) -> TestResult:
        process = os.popen("getprop ro.product.brand")
        brand = process.read().rstrip()
        if not process.close() is None:
            additional_info = {
                'error': "The test could not be fulfilled."
            }
            return TestSet.TEST_INCONCLUSIVE, additional_info
        if brand == "generic":
            return TestSet.TEST_FAILED
        return TestSet.TEST_PASSED

    @test(
        name="Does the manufacturer correspond to an emulator?",
        description="Verifies the manufacturer property against 'unknown'.")
    def manufacturer_from_emulator(self) -> TestResult:
        process = os.popen("getprop ro.product.manufacturer")
        brand = process.read().rstrip()
        if not process.close() is None:
            additional_info = {
                'error': "The test could not be fulfilled."
            }
            return TestSet.TEST_INCONCLUSIVE, additional_info
        if brand == "unknown":
            return TestSet.TEST_FAILED
        return TestSet.TEST_PASSED