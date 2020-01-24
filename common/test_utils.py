import inspect
import os
import tarfile

from abc import ABC, abstractmethod
from importlib import import_module
from pkgutil import iter_modules, walk_packages


class TestSet(ABC):
    """Base class that provides a common interface for all test sets."""

    def __init__(self, description):
        self.description = description

    @abstractmethod
    def run(self):
        """Executes all given tests in the set."""
        pass


class TestSetCollection():
    """Loads all the tests found in the corresponding package"""

    def __init__(self, test_packages):
        self.load_test_sets(test_packages)

    def load_test_sets(self, test_packages):
        """Recovers all test sets from the given packages."""
        self.test_sets = []
        for package in test_packages:
            self.get_package(package)

    def get_package(self, package):
        """
        Looks for all the test sets in the given package and its subpackages.
        """
        if isinstance(package, str):
            package = import_module(package)
        for _, name, is_pkg in walk_packages(
                package.__path__,
                package.__name__ + '.'):
            if not is_pkg:
                module = import_module(name)
                classes = inspect.getmembers(module, inspect.isclass)
                for _, c in classes:
                    if issubclass(c, TestSet) and c is not TestSet:
                        self.test_sets.append(c())

    def run_all_tests(self):
        for ts in self.test_sets:
            ts.run()


def get_installed_test_sets(package_name):
    installed = {
        'name': package_name.split(".")[-1],
        'subpackages': [],
        'modules': [],
    }
    package = import_module(package_name)
    for _, name, is_pkg in iter_modules(
            package.__path__,
            package.__name__ + '.'):
        if is_pkg:
            sub = get_installed_test_sets(name)
            installed['subpackages'].append(sub)
        else:
            sub = {
                'name': name.split(".")[-1],
                'test_sets': []
            }
            module = import_module(name)
            classes = inspect.getmembers(module, inspect.isclass)
            for class_name, c in classes:
                if issubclass(c, TestSet) and c is not TestSet:
                    sub['test_sets'].append(class_name)
            installed['modules'].append(sub)
    return installed

def compress_test_packages(test_packages, tests_root, file_name):
    def filter_pycache(x):
        if os.path.basename(x.name) == "__pycache__":
            return None
        else:
            return x

    tar = tarfile.open(file_name, mode="w:gz")

    for tp in test_packages:
        if len(tp.split(".")) > 1:
            print(tp + "ignored. Only top level packages allowed.")
        else:
            tp_path = os.path.join(tests_root, tp)
            if os.path.isdir(tp_path):
                tar.add(tp_path, tp, filter=filter_pycache)
            else:
                print("No package found with name " + tp + ".")

    tar.close()
