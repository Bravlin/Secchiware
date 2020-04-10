import time
import socket

from concurrent.futures import ThreadPoolExecutor
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