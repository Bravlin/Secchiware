import time
import socket
import statistics

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from test_utils import TestResult, TestSet, test


class AgnosticNetworkingSet(TestSet):

    @test(
        name="Are fake domains resolved?",
        description=
            "Verifies wheter the fake domain 'secchiware.fake.com' gets "\
            "resolved.")
    def are_fake_domains_resolved(self) -> TestResult:
        try:
            socket.gethostbyname("secchiware.fake.com")
            return TestSet.TEST_FAILED
        except socket.error:
            return TestSet.TEST_PASSED


class AgnosticAntiAnalysisSet(TestSet):

    @test(
        name="Is sleep simulated?",
        description=
            "Runs two threads: one sleeps and the other does some timewasting. "\
            "If the sleeping thread finishes first, then the system is "\
            "simulating sleep.")
    def sleep_emulated(self) -> TestResult:
        def sleeper():
            time.sleep(3)
            return time.time()
        
        def timewaster():
            aux = 0
            for i in range(1, 100000):
                aux += i
                if i % 2 == 0:
                    aux += 1
            return time.time()

        with ThreadPoolExecutor(max_workers=2) as executor:
            sleeper_finish_time = executor.submit(sleeper)
            timewaster_finish_time = executor.submit(timewaster)
        if sleeper_finish_time.result() > timewaster_finish_time.result():
            return TestSet.TEST_PASSED
        return TestSet.TEST_FAILED

    @test(
        name="Does execution time vary greatly?",
        description=
            "Calculates 50 times the digest of a certain long phrase. If any "\
            "measured value is out of the bounds established by adding or "\
            "substracting three times the standard deviation to the mean, "\
            "then the test fails.")
    def timing_test(self) -> TestResult:
        phrase = b"Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed "\
            b"do eiusmod tempor incididunt ut labore et dolore magna aliqua. "\
            b"Ut enim ad minim veniam, quis nostrud exercitation ullamco "\
            b"laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure "\
            b"dolor in reprehenderit in voluptate velit esse cillum dolore eu "\
            b"fugiat nulla pariatur. Excepteur sint occaecat cupidatat non "\
            b"proident, sunt in culpa qui officia deserunt mollit anim id est "\
            b"laborum."
        execution_times = []
        for _ in range(50):
            start_time = time.time()
            sha256(phrase).hexdigest()
            end_time = time.time()
            execution_times.append(end_time - start_time)
        mean = statistics.mean(execution_times)
        sigma = statistics.stdev(execution_times)
        additional_info = {
            'mean': mean,
            'standard_deviation': sigma
        }
        max_tolerable = mean + 3. * sigma
        min_tolerable = mean - 3. * sigma
        out_of_bounds = [x for x in execution_times\
            if x > max_tolerable and x < min_tolerable]
        if out_of_bounds:
            additional_info['out_of_bounds_measurements'] = out_of_bounds
            result = TestSet.TEST_FAILED
        else:
            result = TestSet.TEST_PASSED
        return result, additional_info