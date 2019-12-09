import inspect
import os

from abc import ABC, abstractmethod
from importlib import import_module
from pkgutil import iter_modules

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
        self.visited_paths = []
        for package in test_packages:
            self.get_package(package)

    def get_package(self, package):
        """
        Looks for all the test sets in the given package and its subpackages.
        """
        imported_package = import_module(package)
        # Searches for modules inside the imported package
        for _, module_name, is_package in iter_modules(
                imported_package.__path__,
                imported_package.__name__ + '.'):
            if not is_package:
                module = import_module(module_name)
                classes = inspect.getmembers(module, inspect.isclass)
                for (_, c) in classes:
                    if issubclass(c, TestSet) and c is not TestSet:
                        self.test_sets.append(c())

        # Recovers additional paths from the current package path
        current_paths = []
        if isinstance(imported_package.__path__, str):
            current_paths.append(imported_package.__path__)
        else:
            current_paths.extend([path for path in imported_package.__path__])

        for package_path in current_paths:
            if package_path not in self.visited_paths:
                self.visited_paths.append(package_path)

                # Gets all subdirectories in the current package path
                subpackages = [subpackage for subpackage
                    in os.listdir(package_path)
                    if os.path.isdir(os.path.join(package_path, subpackage))]
                
                # Repeats the process recursively for the given subpackage
                for subpackage in subpackages:
                    self.get_package(package + '.' + subpackage)

    def run_all_tests(self):
        for ts in self.test_sets:
            ts.run()