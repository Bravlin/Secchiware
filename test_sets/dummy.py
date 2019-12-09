from test_utils import TestSet

class DummySet(TestSet):

    def __init__(self):
        super().__init__("A dummy test")

    def run(self):
        print("Dummy loaded correctly!")