#include <stdint.h>

#define TEST_PASSED 1
#define TEST_FAILED -1
#define TEST_INCONCLUSIVE 0

int CPUID_HypervisorBitTest()
{
    // From https://github.com/a0rtega/pafish
    uint32_t ecx;
    asm volatile (
        "cpuid" \
        : "=c" (ecx) \
        : "a" (0x01));
    return (ecx >> 31) & 0x01 == 1 ? TEST_FAILED : TEST_PASSED;
}