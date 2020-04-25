import time
import socket
import statistics

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from test_utils import TestResult, TestSet


class AgnosticNetworkingSet(TestSet):

    @TestSet.test(
        name="Are fake domains resolved?",
        description=
            "Verifies wheter the fake domain 'secchiware.fake.com' gets "
            "resolved.")
    def are_fake_domains_resolved(self) -> TestResult:
        try:
            socket.gethostbyname("secchiware.fake.com")
            return TestSet.TEST_FAILED
        except socket.error:
            return TestSet.TEST_PASSED


class AgnosticAntiAnalysisSet(TestSet):

    @TestSet.test(
        name="Is sleep simulated?",
        description=
            "Runs two threads: one sleeps and the other does some "
            "timewasting. If the sleeping thread finishes first, then the "
            "system is simulating sleep.")
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

    @TestSet.test(
        name="Does execution time vary greatly?",
        description=
            "Calculates 100 times the digest of a certain long phrase. If the "
            "coefficient of variation exceeds 0.8, then the test fails.")
    def timing_test(self) -> TestResult:
        phrase = (b"Lorem ipsum dolor sit amet, consectetur adipiscing elit, "
            b"sed do eiusmod tempor incididunt ut labore et dolore magna "
            b"aliqua. Ut enim ad minim veniam, quis nostrud exercitation "
            b"ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis "
            b"aute irure dolor in reprehenderit in voluptate velit esse "
            b"cillum dolore eu  fugiat nulla pariatur. Excepteur sint "
            b"occaecat cupidatat non proident, sunt in culpa qui officia "
            b"deserunt mollit anim id est laborum.")
        execution_times = []
        for _ in range(100):
            start_time = time.process_time()
            sha256(phrase).hexdigest()
            end_time = time.process_time()
            execution_times.append(end_time - start_time)
        mean = statistics.mean(execution_times)
        sigma = statistics.stdev(execution_times, mean)
        cv = sigma / mean
        additional_info = {
            'mean': mean,
            'standard_deviation': sigma,
            'coefficient_of_variation': cv

        }
        result = TestSet.TEST_FAILED if cv > 0.8 else TestSet.TEST_PASSED
        return result, additional_info