from test_utils import TestSet

class DebugSet(TestSet):

    def __init__(self):
        super().__init__("Debug")

    def run(self):
        f = open("/proc/self/status", "r")
        for line in f:
            if line.startswith("TracerPid"):
                print(line)
                break