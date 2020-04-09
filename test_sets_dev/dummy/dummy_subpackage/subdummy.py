from test_utils import TestSet, test

class DummySet2(TestSet):

    @test(name="Dummy 2", description="Dummier")
    def dummy2(self):
        return TestSet.TEST_INCONCLUSIVE