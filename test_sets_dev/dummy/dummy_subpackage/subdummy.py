from test_utils import TestSet, test

class DummySet2(TestSet):

    def __init__(self):
        super().__init__("A dummy test")

    @test
    def dummy2(self):
        print("Dummy 2 loaded correctly!")