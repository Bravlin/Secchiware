from test_utils import TestResult, TestSet

class DummySet2(TestSet):

    @TestSet.test(name="Dummy 2", description="Dummier")
    def dummy2(self):
        return TestSet.TEST_INCONCLUSIVE