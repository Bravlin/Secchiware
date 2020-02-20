from test_utils import TestSetCollection

def main():
    tests = TestSetCollection("test_sets_dev", packages=["debug"], test_sets=["dummy.dummy.DummySet"])
    print(tests.run_all_tests())

if __name__ == '__main__':
    main()