import socket

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