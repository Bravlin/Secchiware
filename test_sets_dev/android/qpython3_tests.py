from test_utils import TestResult, TestSet, test
from time import sleep


class QPython3CommunicationSet(TestSet):

    def __init__(self):
        # It can break the command and control server if the import is not here
        from androidhelper import Android
        self.droid = Android()

    @test(
        name="How many contacts are registered?",
        description="Looks for at least 5 registered contacts.")
    def contacts_registered(self) -> TestResult:
        count = len(self.droid.contactsGetIds().result)
        additional_info = {
            'found_contacts': count
        }
        result = 1 if count >= 5 else -1
        return result, additional_info

    @test(
        name="How many SMS are stored?",
        description="Looks for at least 10 stored messages.")
    def sms_stored(self) -> TestResult:
        count = len(self.droid.smsGetMessageIds(False).result)
        additional_info = {
            'found_messages': count
        }
        result = 1 if count >= 5 else -1
        return result, additional_info
        
    @test(
        name="Is the phone participating in calls?",
        description="Waits for a phone call during 10 seconds.")
    def detect_call(self) -> TestResult:
        self.droid.startTrackingPhoneState()
        i = 0
        while i <= 9 and self.droid.readPhoneState().result['state'] == "idle":
            sleep(1)
            i += 1
        if i <= 9 or self.droid.readPhoneState().result['state'] != "idle":
            result = 1
        else:
            result = -1
        self.droid.stopTrackingPhoneState()
        return result


class QPython3EmulatorSet(TestSet):

    def __init__(self):
        # It can break the command and control server if the import is not here
        from androidhelper import Android
        self.droid = Android()

    @test(
        name="Does the IMEI correspond to an emulator?",
        description="Checks the device's IMEI against '000000000000000'.")
    def imei_from_emulator(self) -> TestResult:
        if self.droid.getDeviceId().result == "000000000000000":
            return -1
        return 1

    @test(
        name="Does the network operator name correspond to an emulator?",
        description="Checks the device's network operator's name against 'Android'.")
    def network_operator_name_from_emulator(self) -> TestResult:
        name = self.droid.getNetworkOperatorName().result
        additional_info = {
            'found_network_operator': name
        }
        if name == "Android":
            return -1, additional_info
        return 1, additional_info

    @test(
        name="Does the device have a bluetooth adapter?",
        description="Looks for a not null local bluetooth address.")
    def has_bluetooth(self) -> TestResult:
        address = self.droid.bluetoothGetLocalAddress().result
        if address:
            return 1
        return -1