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
        """Looks for all the test sets in the given package and its
        subpackages."""
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


def get_installed_package(package_name):
    """Recovers information about the given package.

    The returned dictionary contains the following keys:

    'name': the package base name.

    'subpackages': a list of dictionaries with a recursive format representing
    the subpackages found.

    'modules': a list of dictionaries representing the found modules within the
    package. They have the following keys:
        'name': the name of the module.
        'test_sets': a list with the names of the classes extended from TestSet
        found in the given module.

    Parameters
    ----------
    package_name : str
        The full name of the package to analyze.

    Returns
    -------
    dictionary
        a dictionary representing the structure of the given package. 
    """

    installed = {
        'name': package_name.split(".")[-1], # Basename only
        'subpackages': [],
        'modules': [],
    }
    package = import_module(package_name)
    for _, name, is_pkg in iter_modules(
            package.__path__,
            package.__name__ + '.'):
        if is_pkg:
            # Recursive call with the found subpackage
            sub = get_installed_package(name)
            installed['subpackages'].append(sub)
        else:
            sub = {
                'name': name.split(".")[-1], # Basename only
                'test_sets': []
            }
            module = import_module(name)
            classes = inspect.getmembers(module, inspect.isclass)
            for class_name, c in classes:
                # Only adds a class if it extended from TestSet and it is not
                # TestSet itself
                if issubclass(c, TestSet) and c is not TestSet:
                    sub['test_sets'].append(class_name)
            installed['modules'].append(sub)
    return installed

def get_installed_test_sets(root_package):
    """Recovers information about the installed test sets at the given root
    package.

    Each component of the returned list is a dictionary of the form returned by
    the function get_installed_package().

    Parameters
    ----------
    root_package : str
        The name of the test sets root package.

    Returns
    -------
    lists
        a list whose components are dictionaries representing each of the found
        packages. 
    """

    package = import_module(root_package)
    installed = []
    for _, name, is_pkg in iter_modules(
            package.__path__,
            package.__name__ + '.'):
        if is_pkg:
            installed.append(get_installed_package(name))
    return installed

def compress_test_packages(file_object, test_packages, tests_root):
    """Compress the given packages at the root directory for tests.

    Only top level packages are allowed, everything else is ignored.
    Non-existent packages are also ignored. All pycache folders are not
    included in the resulting file. The compression format used is gzip.

    Parameters
    ----------
    file_object
        A file like object in which the resulting file is generated.
    test_packages
        A list of packages names.
    tests_root : str
        The root directory name where the tests sets packages are stored.
    """

    def filter_pycache(x):
        """Excludes x if it's a pycache directory."""
        if os.path.basename(x.name) == "__pycache__":
            return None
        else:
            return x

    with tarfile.open(fileobj=file_object, mode="w:gz") as tar:
        for tp in test_packages:
            if len(tp.split(".")) > 1:
                print(tp + "ignored. Only top level packages allowed.")
            else:
                tp_path = os.path.join(tests_root, tp)
                if os.path.isdir(tp_path):
                    tar.add(tp_path, tp, filter=filter_pycache)
                else:
                    print("No package found with name " + tp + ".")

def uncompress_test_packages(file_object, tests_root):
    """Uncompress the given file in the root directory for tests.

    The file must be in gzip format.

    Parameters
    ----------
    file_object
        A file like object from which the tests sets are extracted.
    tests_root : str
        The root directory name where the extracted packages are going to be
        stored.
    """

    with tarfile.open(fileobj=file_object, mode="r:gz") as tar:
        tar.extractall(tests_root)