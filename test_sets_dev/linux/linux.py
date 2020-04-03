from test_utils import TestResult, TestSet, test

class MonitoringSet(TestSet):

    @test(
        name="Is tracer attached?",
        description="Looks for a TracerPid different than 0.")
    def is_tracer_attached(self) -> TestResult:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("TracerPid"): break
        additional_info = {
            'found_line': line
        }
        pid = int(line.split()[-1])
        result = 1 if pid == 0 else -1
        return result, additional_info