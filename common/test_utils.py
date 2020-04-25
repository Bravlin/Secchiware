import inspect
import os
import shutil
import sys
import tarfile

from abc import ABC
from importlib import import_module
from datetime import datetime
from functools import wraps
from pkgutil import iter_modules, walk_packages
from typing import Any, BinaryIO, Callable, List, Tuple, Union


############################ Types definitions ###############################

TestResult = Union[int, Tuple[int, dict]]


######################### Exceptions definitions #############################

class InvalidTestMethod(Exception):
    """Indicates that a method marked as a test does not fulfill the necessary
    requirements."""

    pass


############################ Test facilities #################################

def test(name: str, description: str) -> Callable:
    """Decorator that marks the given method as a test.
    
    It forces the decorated method to return just an int representing the
    result code of the test execution or an additional dictionary containing
    any extra information that the developer wishes to provide. Also, the
    following dictionary structure is now returned by the method:

    'test_name': a string filled with the given name parameter.
    
    'test_description': a string filled with the given description parameter.

    'result_code': a number that represents the success (> 0), failure (< 0)
    or unexpected condition (0) after the test execution.

    'additional_info': an optional dictionary containing extra relevant data.

    Parameters
    ----------
    name: str
        The name given to the test.
    description: str
        A brief explanation of the test.

    Returns
    -------
    Callable[[TestSet], dict]
        The decorated method.
    """

    def test_decorator(
            method: Callable) -> Callable:
        @wraps(method)
        def wrapper(self) -> Callable:
            report = {}
            report['timestamp_start'] = (datetime.utcnow()
                .strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
            result = method(self)
            report['timestamp_end'] = (datetime.utcnow()
                .strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

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
    """
    Its use is recommended when inspecting a class definition, as there is no
    instance bound to the method.

    Returns
    -------
    bool
        Wheter the argument is a test method.
    """

    return inspect.isfunction(x) and hasattr(x, 'test')

def is_test_method(x: Any) -> bool:
    """
    Returns
    -------
    bool 
        Wheter the argument is a test in the form a method bound to an object.
    """

    return inspect.ismethod(x) and hasattr(x, 'test')


######################### Classes to contain tests ###########################

class TestSet(ABC):
    """Base class that provides a common interface for all test sets. It can
    be extended to develop new tests.
    
    Class constants
    ---------------
    TEST_PASSED: int
        The test was sucessful.
    TEST_FAILED: int
        The test reached a negative conclusion.
    TEST_INCONCLUSIVE: int
        Something prevented the test to run properly or to take a definitive
        stand.
    
    Static methods
    --------------
    is_strict_subclass(x: Any) -> bool
        Wheter the argument is a subclass of TestSet but not TestSet itself.

    Instance methods
    ----------------
    run() -> List[dict]
        Executes all tests declared in the set.
    """

    # Handy constants to express a test result.
    TEST_PASSED = 1
    TEST_FAILED = -1
    TEST_INCONCLUSIVE = 0

    @staticmethod
    def is_strict_subclass(x: Any) -> bool:
        """
        Returns
        -------
        bool
            Wheter the argument is a subclass of TestSet but not TestSet
            itself.
        """

        return (inspect.isclass(x)
            and issubclass(x, TestSet)
            and x is not TestSet)

    def run(self) -> List[dict]:
        """Executes all tests declared in the set.
        
        Returns
        -------
        List[dict]
            A list containing the individual reports generated by each test.
            The structure of a report is documented in the test decorator.
            Any given test method found that is not 
        """

        reports = []
        tests = inspect.getmembers(self, is_test_method)
        for _, method in tests:
            try:
                reports.append(method())
            except InvalidTestMethod as e:
                print(str(e))
        return reports


class TestSetCollection():
    """Contains a collection of instances of classes extended from TestSet.
    
    Instance attributes
    -------------------
    tests_root: str
        The name of the root package use to resolve packages, modules and
        classes names.
    test_sets: List[TestSet]
        A list of instances of TestSet obtained through loading certain
        specified packages, modules or classes.

    Instance methods
    ----------------
    load_entities(packages: List[str], modules: List[str], 
    test_sets: List[str]) -> None
        Recovers all test sets from the given entities, instantiates them and
        refreshes the collection with them.
    load_package(package: str) -> None:
        Looks for all the test sets in the given package and its subpackages,
        instantiates them and adds them to the collection.
    load_module(module: str) -> None:
        Instantiates the classes extended from TestSet in the given module and
        adds them to the collection.
    load_test_set(module: str, test_set: str) -> None:
        Instantiates the given test set class and adds it to the collection.
    run_all_tests() -> List[dict]:
        Executes all the test sets in the collection.
    """

    def __init__(self,
            tests_root: str,
            packages: List[str] = [],
            modules: List[str] = [],
            test_sets: List[str] = []):
        """
        Parameters
        ----------
        tests_root: str
            The name of the root package from which the rest of the entities
            names must be resolved.
        packages: List[str], optional
            A list containing the canonical names of the packages to be loaded
            entirely.
        modules: List[str], optional
            A list containing the canonical names of the particular modules
            to be loaded entirely.
        test_sets: List[str], optional
            A list containing the canonical names of the particular classes
            extended from TestSet to be loaded.
        """

        self.tests_root = tests_root
        if packages or modules or test_sets:
            self.load_entities(packages, modules, test_sets)
        else:
            self.test_sets: List[TestSet] = []
            self.load_package(self.tests_root)

    def load_entities(
            self,
            packages: List[str] = [],
            modules: List[str] = [],
            test_sets: List[str] = []) -> None:
        """Recovers all test sets from the given entities, instantiates them
        and refreshes the collection with them.
        
        Parameters
        ----------
        packages: List[str], optional
            A list containing the canonical names of the packages to be loaded
            entirely.
        modules: List[str], optional
            A list containing the canonical names of the particular modules
            to be loaded entirely.
        test_sets: List[str], optional
            A list containing the canonical names of the particular classes
            extended from TestSet to be loaded.
        """

        self.test_sets: List[TestSet] = []
        
        for package in packages:
            self.load_package(f"{self.tests_root}.{package}")
        
        for module in modules:
            self.load_module(f"{self.tests_root}.{module}")

        for ts in test_sets:
            # The class name is the string after the last ".".
            module, c = ts.rsplit(".", 1)
            self.load_test_set(f"{self.tests_root}.{module}", c)

    def load_package(self, package: str) -> None:
        """Looks for all the test sets in the given package and its
        subpackages, instantiates them and adds them to the collection.
        
        Parameters
        ----------
        package: str
            The canonical name of the package to load.
        """

        package = import_module(package)
        # Looks for packages in package.__path__ and deeper recursively with
        # walk_packages.
        # All found entities are given their canonical name through inheriting
        # their parent's.
        for _, name, is_pkg in walk_packages(
                package.__path__,
                f"{package.__name__ }."):
            if not is_pkg:
                self.load_module(name)

    def load_module(self, module: str) -> None:
        """Instantiates the classes extended from TestSet in the given module
        and adds them to the collection.
        
        Parameters
        ----------
        module: str
            The canonical name of the module to load.
        """

        mod = import_module(module)
        classes = inspect.getmembers(mod, TestSet.is_strict_subclass)
        for _, c in classes:
            self.test_sets.append(c())

    def load_test_set(self, module: str, test_set: str) -> None:
        """Instantiates the given test set class and adds it to the collection.
        
        Parameters
        ----------
        module: str
            The canonical name of the module containing the test set.
        test_set: str
            The name of the class extended from TestSet contained in the given
            module.

        Raises
        ------
        ValueError
            The given class is not a valid one.
        """

        mod = import_module(module)
        c = getattr(mod, test_set)
        if TestSet.is_strict_subclass(c):
            self.test_sets.append(c())
        else:
            raise ValueError(f"{test_set} is not a valid class name.")

    def run_all_tests(self) -> List[dict]:
        """Executes all the test sets in the collection.

        Returns
        -------
        List[dict]
            A list containing the individual reports generated by each test
            contained in their respective test sets. The structure of a report
            is documented in the decorator "test".
        """

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
        The canonical name of the package to analyze.

    Returns
    -------
    dict
        A dictionary representing the structure of the given package. 
    """

    installed = {
        'name': package_name.split(".")[-1], # Basename only.
    }
    package = import_module(package_name)
    modules_list = []
    subpackages_list = []
    # Looks for packages in package.__path__.
    # All found entities are given their canonical name inheriting their
    # parent's.
    for _, name, is_pkg in iter_modules(
            package.__path__,
            package.__name__ + '.'):
        if is_pkg:
            # Recursive call with the found subpackage.
            sub = get_installed_package(name)
            subpackages_list.append(sub)
        else:
            module_info = {
                'name': name.split(".")[-1], # Basename only.
            }
            module = import_module(name)
            
            classes_list = []
            classes = inspect.getmembers(module, TestSet.is_strict_subclass)
            for class_name, c in classes:
                class_info = {
                    'name': class_name,
                }

                tests_list = []
                tests = inspect.getmembers(c, is_test)
                for test_name, _ in tests:
                    tests_list.append(test_name)
                
                if tests_list:
                    class_info['tests'] = tests_list
                classes_list.append(class_info)
            
            if classes_list:
                module_info['test_sets'] = classes_list
            modules_list.append(module_info)
    
    if modules_list:
        installed['modules'] = modules_list
    if subpackages_list:
        installed['subpackages'] = subpackages_list
    return installed

def get_installed_test_sets(root_package: str) -> List[dict]:
    """Recovers information about the installed test sets at the given root
    package.

    Each component of the returned list is a dictionary as the one described in
    the function get_installed_package().

    Parameters
    ----------
    root_package : str
        The name of the root package containing all other packages filled with
        test sets.

    Returns
    -------
    List[dict]
        A list whose components are dictionaries representing each of the found
        packages. 
    """

    package = import_module(root_package)
    installed = []
    # Looks for packages in package.__path__.
    # All found entities are given their canonical name from the root package.
    for _, name, is_pkg in iter_modules(
            package.__path__,
            package.__name__ + '.'):
        if is_pkg:
            installed.append(get_installed_package(name))
    return installed

def clean_package(package_name: str) -> None:
    """ Removes the given package and all its content from the cache.

    It ignores any package or module found that is not present in sys.modules.
    """

    if package_name in sys.modules:
        package = import_module(package_name)
        for _, name, is_pkg in iter_modules(
                package.__path__,
                package.__name__ + '.'):
            if is_pkg:
                clean_package(name)
            elif name in sys.modules:
                del sys.modules[name]
        del sys.modules[package_name]

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

    Raises
    ------
    ValueError
        One of the given packages is not a top level one or does not exist.
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
                raise ValueError(f"{tp} is not a top level package.")
            else:
                tp_path = os.path.join(tests_root, tp)
                if os.path.isdir(tp_path):
                    tar.add(tp_path, tp, filter=filter_pycache)
                else:
                    raise ValueError(f"No package found with name {tp}.")

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
    
    Raises
    ------
    ValueError
        A top level member of the tar file that is not a package was found.

    Returns
    -------
    List[str]
        A list whose components are the names of the top level packages found.
    """

    def member_is_package(
            tar: tarfile.TarFile,
            member: tarfile.TarInfo) -> bool:
        """Checks if the given member of the provided tar object contains a
        __init__.py file.

        Parameters
        ----------
        tar: tarfile.TarFile
            A tar object containing member.
        member: tarfile.TarInfo
            The member of the tar object to verify.

        Returns
        -------
        bool
            Wheter the given member is a package or not.
        """

        try:
            tar.getmember(f"{member.name}/__init__.py")
            return True
        except KeyError:
            return False

    new_packages = []
    with tarfile.open(fileobj=file_object, mode="r:gz") as tar:
        for member in tar:
            if member.name.count("/") == 0: # It's a top level member
                if not (member.isdir() and member_is_package(tar, member)):
                    raise ValueError(
                        f"Found top level member {member} is not a package.")
                new_packages.append(member.name)

        for np in new_packages:
            package_path = os.path.join(tests_root, np)
            # If the package existed beforehand, it first gets deleted
            if os.path.isdir(package_path):
                shutil.rmtree(package_path)
        tar.extractall(tests_root)

    return new_packages