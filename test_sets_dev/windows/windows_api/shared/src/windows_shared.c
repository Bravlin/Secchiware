#include <unistd.h>
#include <string.h>
#include <windows.h>

#define TEST_PASSED 1
#define TEST_FAILED -1
#define TEST_INCONCLUSIVE 0

#define TITLE_MAX_SIZE 256

int WindowsAPI_IsDebuggerPresent()
{
    return IsDebuggerPresent() ? TEST_FAILED : TEST_PASSED;
}

int WindowsAPI_DoesForegroundWindowChange()
{
    char actual_title[TITLE_MAX_SIZE], first_title[TITLE_MAX_SIZE];
    int i;
    HWND window;

    window = GetForegroundWindow();
    if (window != NULL)
        GetWindowText(window, first_title, TITLE_MAX_SIZE);
    else
        strcpy(first_title, "\0");

    i = 0;
    do
    {
        sleep(1);
        window = GetForegroundWindow();
        if (window != NULL)
            GetWindowText(window, actual_title, TITLE_MAX_SIZE);
        else
            strcpy(actual_title, "\0");
        i++;
    } while(i < 10 && strcmp(first_title, actual_title) == 0);

    return i < 10 || strcmp(first_title, actual_title) != 0 ? TEST_PASSED : TEST_FAILED;
}

int WindowsAPI_VirtualDeviceDriversPresent()
{
    HKEY hk;
    LPCSTR subkey = TEXT("SYSTEM\\CurrentControlSet\\Control\\VirtualDeviceDrivers");
    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, subkey, 0, KEY_QUERY_VALUE, &hk) == ERROR_SUCCESS)
    {
        RegCloseKey(hk);
        return TEST_FAILED;
    }
    return TEST_PASSED;
}

int WindowsAPI_WordWheelQueryHasContent()
{
    HKEY hk;
    DWORD numValues;
    LSTATUS status;
    LPCSTR subkey = TEXT("SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\WordWheelQuery");
    if (RegOpenKeyExA(HKEY_CURRENT_USER, subkey, 0, KEY_QUERY_VALUE, &hk) != ERROR_SUCCESS)
        return TEST_FAILED;
    status = RegQueryInfoKeyA(
        hk,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        &numValues,
        NULL,
        NULL,
        NULL,
        NULL
    );
    RegCloseKey(hk);
    if (status != ERROR_SUCCESS)
        return TEST_INCONCLUSIVE;
    if (numValues < 2)
        return TEST_FAILED;
    return TEST_PASSED;
}
