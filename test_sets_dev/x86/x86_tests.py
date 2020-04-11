import ctypes
import os

from test_utils import TestResult, TestSet, test


class X86VirtualizationSet(TestSet):

    def __init__(self):
        package_dir = os.path.dirname(os.path.abspath(__file__))
        shared_bin_dir = os.path.join(package_dir, "shared", "bin")
        self.dll = ctypes.CDLL(os.path.join(shared_bin_dir, "x86_shared.so"))

    @test(
        name="Is CPUID hypervisor bit on?",
        description=
            "Calls the x86 instruction CPUID and checks the value of the ECX "\
            "register's 31th bit.")
    def cpuid_hypervisor_bit_on(self) -> TestResult:
        return self.dll.CPUID_HypervisorBitTest()