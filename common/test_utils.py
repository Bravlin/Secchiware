import inspect
import os
import tarfile

from abc import ABC, abstractmethod
from importlib import import_module
from functools import wraps
from pkgutil import iter_modules, walk_packages
from typing import Any, BinaryIO, Callable, List, Optional, Tuple, Union

TestResult = Union[int, Tuple[int, dict]]


class InvalidTestMethod(Exception):
    pass


def test(name: str, description: str) -> Callable:
    """Decorator that marks the given method as a test."""

    def test_decorator(
            method: Callable[[TestSet], TestResult]) -> Callable:
        @wraps(method)
        def wrapper(self: TestSet) -> Callable:
            report = {}
            result = method(self)

            if isinstance(result, int):
                report['result_code'] = result
            elif not isinstance(result, tuple):
                raise InvalidTestMethod("Invalid return type.")
            elif len(result) != 2:
                raise InvalidTestMethod("Incorrect number of return values.")
            elif not isinstance(result[0], int):
                raise InvalidTestMethod("Result code is not an integer.")
            elif not isinstance(result[1], dict):
                raise InvalidTestMethod(
                    "Second return value is not a dictionary.")
            else:
                report['result_code'] = result[0]
                report['additional_info'] = result[1]

            report['test_name'] = name
            report['test_description'] = description
            return report

        wrapper.test = True
        return wrapper
    
    return test_decorator

def is_test(x: Any) -> bool:
    """Return wheter the argument is a test method.
    
    Its use is recommended when inspecting a class definition, as there is no
    instance bound to the method.
    """

    return inspect.isfunction(x) and hasattr(x, 'test')

def is_test_method(x: Any) -> bool:
    """Return wheter the argument is a test in the form a method bound to an
    object."""

    return inspect.ismethod(x) and hasattr(x, 'test')


class TestSet(ABC):
    """Base class that provides a common interface for all test sets."""

    @staticmethod
    def is_strict_subclass(x: Any) -> bool:
        return (inspect.isclass(x)
            and issubclass(x, TestSet)
            and x is not TestSet)

    def __init__(self, description: str):
        self.description = description

    def run(self) -> List[dict]:
        """Executes all given tests in the set."""
        results = []
        tests = inspect.getmembers(self, is_test_method)
        for _, method in tests:
            try:
                results.append(method())
            except InvalidTestMethod as e:
                print(str(e))
        return results


class TestSetCollection():
    """Loads all the tests found in the corresponding packages."""

    def __init__(self, test_packages: List[str]):
        self.load_test_sets(test_packages)

    def load_test_sets(self, test_packages: List[str]) -> None:
        """Recovers all test sets from the given packages."""
        self.test_sets: List[TestSet] = []
        for package in test_packages:
            self.get_package(package)

    def get_package(self, package: str) -> None:
        """Looks for all the test sets in the given package and its
        subpackages."""
        if isinstance(package, str):
            package = import_module(package)
        for _, name, is_pkg in walk_packages(
                package.__path__,
                package.__name__ + '.'):
            if not is_pkg:
                module = import_module(name)
                classes = inspect.getmembers(module, TestSet.is_strict_subclass)
                for _, c in classes:
                    self.test_sets.append(c())

    def run_all_tests(self) -> List[List[dict]]:
        results = []
        for ts in self.test_sets:
            results += ts.run()
        return results


def get_installed_package(package_name: str) -> dict:
    """Recovers information about the given package.

    The returned dictionary contains the following keys:

    1. 'name': the package base name.

    2. 'subpackages': a list of dictionaries with a recursive format
    representing the subpackages found.

    3. 'modules': a list of dictionaries representing the found modules within
    the package. They have the following keys:

    3.1 'name': the name of the module.
    
    3.2 'test_sets': a list of dictionaries representing the classes extended
    from TestSet found in the given module. They contain the following keys:
    
    3.2.1 'name': the name of the class.
    
    3.2.2 'tests': a list of the names of the test methods found within the
    class.

    Parameters
    ----------
    package_name : str
        The full name of the package to analyze.

    Returns
    -------
    dict
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
            module_info = {
                'name': name.split(".")[-1], # Basename only
                'test_sets': []
            }
            module = import_module(name)
            classes = inspect.getmembers(module, TestSet.is_strict_subclass)
            for class_name, c in classes:
                class_info = {
                    'name': class_name,
                    'tests': []
                }
                tests = inspect.getmembers(c, is_test)
                for test_name, _ in tests:
                    class_info['tests'].append(test_name)
                module_info['test_sets'].append(class_info)
            installed['modules'].append(module_info)
    return installed

def get_installed_test_sets(root_package: str) -> List[dict]:
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
    List[dict]
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

def compress_test_packages(
        file_object: BinaryIO,
        test_packages: List[str],
        tests_root: str) -> None:
    """Compress the given packages at the root directory for tests.

    Only top level packages are allowed, everything else is ignored.
    Non-existent packages are also ignored. All pycache folders are not
    included in the resulting file. The compression format used is gzip.

    Parameters
    ----------
    file_object: BinaryIO
        A file like object in which the resulting file is generated.
    test_packages: List[str]
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

def uncompress_test_packages(file_object: BinaryIO, tests_root: str) -> List[str]:
    """Uncompress the given file in the root directory for tests.

    The file must be in gzip format.

    Parameters
    ----------
    file_object: BinaryIO
        A file like object from which the tests sets are extracted.
    tests_root : str
        The root directory name where the extracted packages are going to be
        stored.
    """

    def member_is_package(tar: tarfile.TarFile, member: tarfile.TarInfo):
        try:
            tar.getmember(f"{member.name}/__init__.py")
            return True
        except KeyError:
            return False

    new_packages = []
    with tarfile.open(fileobj=file_object, mode="r:gz") as tar:
        for member in tar:
            if member.name.count("/") == 0:
                if not (member.isdir() and member_is_package(tar, member)):
                    raise ValueError(
                        f"Found top level member {member} is not a package.")
                new_packages.append(member.name)
        tar.extractall(tests_root)
    return new_packages