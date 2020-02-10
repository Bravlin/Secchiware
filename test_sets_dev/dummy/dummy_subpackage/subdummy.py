from test_utils import generate_test_result, TestSet, test

class DummySet2(TestSet):

    def __init__(self):
        super().__init__("A dummy test")

    @test
    def dummy2(self):
        return generate_test_result("Dummy 2", "Dummier", 0)