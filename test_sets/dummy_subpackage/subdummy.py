from test_utils import TestSet

class DummySet2(TestSet):

    def __init__(self):
        super().__init__("A dummy test")

    def run(self):
        print("Dummy 2 loaded correctly!")