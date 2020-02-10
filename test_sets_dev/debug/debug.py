from test_utils import generate_test_result, TestSet, test

class DebugSet(TestSet):

    def __init__(self):
        super().__init__("Debug")

    @test
    def is_tracer_attached(self):
        f = open("/proc/self/status", "r")
        for line in f:
            if line.startswith("TracerPid"): break
        additional_info = {
            'found_line': line
        }
        pid = int(line.split()[-1])
        result = 1 if pid == 0 else -1
        description = "Looks for a TracerPid different than 0"
        return generate_test_result("Is tracer attached?", description, result,
            additional_info)