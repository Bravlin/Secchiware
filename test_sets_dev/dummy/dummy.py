from test_utils import TestResult, TestSet

class DummySet(TestSet):

    @TestSet.test(name="Dummy", description="Dummy")
    def dummy(self) -> TestResult:
        return TestSet.TEST_INCONCLUSIVE