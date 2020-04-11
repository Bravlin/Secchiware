import os

from test_utils import TestResult, TestSet, test


class WMICHardwareRecognitionSet(TestSet):

    @test(
        name="Are there at least 2 CPU cores?",
        description="Checks how many cores the processor has.")
    def at_least_two_cores(self) -> TestResult:
        process = os.popen("wmic cpu get NumberOfCores")
        output = process.read()
        if not process.close() is None:
            return TestSet.TEST_INCONCLUSIVE
        cores = int(output.rstrip().split()[1])
        additional_info = {
            'cores': cores
        }
        result = TestSet.TEST_FAILED if cores < 2 else TestSet.TEST_PASSED
        return result, additional_info

    @test(
        name="Is there a disk of believable size?",
        description="Looks for a disk with at least 20 GB of total storage.")
    def disk_with_minimum_size(self) -> TestResult:
        process = os.popen("wmic diskdrive get size")
        output = process.read()
        if not process.close() is None:
            return TestSet.TEST_INCONCLUSIVE
        sizes = [int(size) for size in output.rstrip().split()[1:]]
        additional_info = {
            'found_disks_sizes': sizes
        }
        for size in sizes:
            if size < 20000000000:
                result = TestSet.TEST_FAILED
                break
        else:
            result = TestSet.TEST_PASSED
        return result, additional_info

    @test(
        name="Can the CPU temperature be consulted?",
        description=
            "Tries to recover the CPU temperature. It needs to be run as admin.")
    def can_the_temperature_be_recovered(self) -> TestResult:
        process = os.popen("wmic /namespace:\\\\root\\wmi PATH "\
            "MSAcpi_ThermalZoneTemperature get CurrentTemperature /value")
        temperatures = []
        for line in process:
            if line.startswith("CurrentTemperature"):
                temperatures.append(int(line.split("=")[1]))
        if not process.close() is None:
            return TestSet.TEST_INCONCLUSIVE
        if not temperatures:
            return TestSet.TEST_FAILED
        additional_info = {
            'temperatures': temperatures
        }
        return TestSet.TEST_PASSED, additional_info