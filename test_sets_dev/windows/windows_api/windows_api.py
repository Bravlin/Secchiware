import ctypes
import os

from test_utils import TestResult, TestSet, test


dll = None

# Loads the DLL used by all TestSets of the module
def getWindowsAPIDLL():
    if dll is None:
        package_dir = os.path.dirname(os.path.abspath(__file__))
        shared_bin_dir = os.path.join(package_dir, "shared", "bin")
        dll = ctypes.WinDLL(os.path.join(shared_bin_dir, "windows_api.dll"))
    return dll


class WindowsAPIDebuggerSet(TestSet):

    @test(
        name="Is a debugger present?",
        description=
            "Calls the function IsDebuggerPresent from the Windows API.")
    def windows_api_is_debugger_present(self) -> TestResult:
        return getWindowsAPIDLL().IsDebuggerPresent()


class WindowsAPIVirtualizationSet(TestSet):

    @test(
        name="Is the 'VirtualDeviceDrivers' key present in the registry?",
        description=
            "Checks if "\
            "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\VirtualDeviceDrivers "\
            "exists.")
    def windows_api_virtual_device_drivers_exists(self) -> TestResult:
        return getWindowsAPIDLL().WindowsAPI_VirtualDeviceDriversPresent()


class WindowsAPIHumanUseSet(TestSet):

    @test(
        name="Does the foreground window change?",
        description=
            "Monitors for 10 seconds the name of the foreground window "\
            "looking for a change.")
    def windows_api_foreground_window_changes(self) -> TestResult:
        return getWindowsAPIDLL().WindowsAPI_DoesForegroundWindowChange()

    @test(
        name="Does WordWheelQuery has content?",
        description=
            "Checks if "\
            "HKEY_CURRENT_USER\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\WordWheelQuery "\
            "has at least two entries.")
    def windows_api_wordwheelquery_has_content(self) -> TestResult:
        return getWindowsAPIDLL().WindowsAPI_WordWheelQueryHasContent()