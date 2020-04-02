from importlib import import_module
from test_utils import TestResult, TestSet, test

class CommunicationSet(TestSet):

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
        count = len(self.droid.smsGetMessageIds().result)
        additional_info = {
            'found_messages': count
        }
        result = 1 if count >= 5 else -1
        return result, additional_info
        