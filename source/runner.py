from cgi import test
import importlib

from ast import Module
from typing import Tuple
from source.utils import get_time
from multiprocess import Semaphore
from source.process import S_Process
from source.searcher import create_tree
from source.testcase import Results, Status


class Runner(object):
    """
    Class responsible for creating processes in which
    each test is executed separately and independently.
    """

    def __init__(self) -> None:
        """
        Initialization of processes list
        and generating tests' hierarchy.
        """
        self.processes: list = []
        self.test_tree: list[dict] = create_tree()
        self.test_results = Results()

    def collect_tests(self) -> None:
        """
        Method for future test selection.
        """
        pass

    def importer(self, module: dict) -> Tuple[Module, str, str]:
        """
        Imports given module name.

        Args:
            module (dict): Module in form of dictionary
            with name and its class members.

        Raises:
            ModuleNotFoundError: When module was not found.

        Returns:
            Tuple[Module, str, str]: Imported module,
            its name and members.
        """
        mod_name = next(iter(module.keys()))
        mod_members = next(iter(module.values()))

        try:
            mod = importlib.import_module(mod_name)
        except ModuleNotFoundError as Error:
            raise Error

        return mod, mod_name, mod_members

    def run_tests(self) -> None:
        """
        Creates independent processes and appends
        them into the pool of processes.
        """
        # Create a pool of processes by defined number
        # ? NO_SYSTEM_CPU = multiprocess.cpu_count()
        concurrency = 2
        semaphore = Semaphore(concurrency)
        start_time = get_time()

        # For each module in test hierarchy.
        for module in self.test_tree:
            module, mod_name, mod_members = self.importer(module)

            # For each TestSuite in module.
            for test_class in mod_members:
                _class = getattr(module, next(iter(test_class.keys())))

                # For each test in given TestSuite.
                for test_name in test_class[next(iter(test_class.keys()))]:
                    _test_instance = _class(test_name)

                    semaphore.acquire()

                    process = S_Process(
                            target=getattr(_class, test_name),
                            args=(_test_instance,),
                            test_name=test_name,
                            start_time=start_time,
                            semaphore=semaphore
                    )
                    process.start()
                    self.processes.append((process, _test_instance))

        self.get_results()

    def get_results(self) -> None:
        """
        Wait untill all processes are finished
        and get the test session results.
        """
        for process, instance in self.processes:
            process.join()

            instance.message = process.exception
            instance.duration = process.duration

            if process.exception:
                if isinstance(process.exception[0], AssertionError):
                    instance.status = Status.FAIL
                else:
                    instance.status = Status.ERROR

            self.test_results.add(instance)

    def show_results(self) -> None:
        for test in self.test_results.tests:
            print(test.name, test.status, test.duration)


if __name__ == "__main__":
    runner = Runner()
    # runner.collect_tests()
    runner.run_tests()
    runner.show_results()


# TODO Make result creation on the side of process and send it back by pipe to parent process.
