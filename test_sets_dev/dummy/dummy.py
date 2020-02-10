from test_utils import generate_test_result, TestSet, test

class DummySet(TestSet):

    def __init__(self):
        super().__init__("A dummy test")

    @test
    def dummy(self):
        return generate_test_result("Dummy", "Dummy", 0)