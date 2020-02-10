from test_utils import TestSet, test

class DummySet(TestSet):

    def __init__(self):
        super().__init__("A dummy test")

    @test
    def dummy(self):
        print("Dummy loaded correctly!")