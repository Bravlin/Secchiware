from test_utils import TestSet, test

class DummySet2(TestSet):

    def __init__(self):
        super().__init__("A dummy test")

    @test(name="Dummy 2", description="Dummier")
    def dummy2(self):
        return 0