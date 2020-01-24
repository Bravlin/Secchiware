from test_utils import TestSetCollection

def main():
    tests = TestSetCollection(['test_sets_dev'])
    tests.run_all_tests()

if __name__ == '__main__':
    main()