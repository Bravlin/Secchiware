from test_utils import TestSet, test

class DummySet(TestSet):

    @test(name="Dummy", description="Dummy")
    def dummy(self):
        return 0