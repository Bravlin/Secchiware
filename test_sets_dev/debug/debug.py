from test_utils import TestSet, test

class DebugSet(TestSet):

    def __init__(self):
        super().__init__("Debug")

    @test
    def is_tracer_attached(self):
        f = open("/proc/self/status", "r")
        for line in f:
            if line.startswith("TracerPid"):
                print(line)
                break