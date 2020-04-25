from test_utils import TestResult, TestSet


class X86VirtualizationSet(TestSet):

    @TestSet.test(
        name="Does the product name correspond to VirtualBox or VMWare?",
        description=
            "Checks if the content of '/sys/class/dmi/id/product_name' "
            "matches against 'VirtualBox' or 'VMWare'.")
    def product_name(self) -> TestSet:
        with open("/sys/class/dmi/id/product_name", "r") as f:
            product_name = f.read().rstrip()
        additional_info = {
            'found_product_name': product_name
        }
        if product_name in {'VirtualBox', 'VMWare'}:
            result = TestSet.TEST_FAILED
        else:
            result = TestSet.TEST_PASSED
        return result, additional_info