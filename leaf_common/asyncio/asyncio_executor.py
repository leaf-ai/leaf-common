
# Copyright (C) 2019-2025 Cognizant Digital Business, Evolutionary AI.
# All Rights Reserved.
# Issued under the Academic Public License.
#
# You can be released from the terms, and requirements of the Academic Public
# License by purchasing a commercial license.
# Purchase of a commercial license is mandatory for any use of the
# leaf-common SDK Software in commercial settings.
#
# END COPYRIGHT
"""
See class comment for details.
"""
from typing import Any
from typing import Awaitable
from typing import Dict
from typing import List

import asyncio
import functools
import inspect
import threading
import traceback

from asyncio import AbstractEventLoop
from asyncio import Future
from concurrent.futures import Executor


# A global containing a some kind of reference to asyncio tasks running in the background.
# Some documentation has recommended this practice as some coroutines
# reportedly operate under weak references.
BACKGROUND_TASKS: Dict[Future, Dict[str, Any]] = {}

EXECUTOR_START_TIMEOUT_SECONDS: int = 5


class AsyncioExecutor(Executor):
    """
    Class for managing asynchronous background tasks in a single thread
    Riffed from:
    https://stackoverflow.com/questions/38387443/how-to-implement-a-async-grpc-python-server/63020796#63020796
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self._shutdown: bool = False
        self._thread: threading.Thread = None
        # We are going to start new thread for this Executor,
        # so we need a new event loop bound to this particular thread:
        self._loop: AbstractEventLoop = asyncio.new_event_loop()
        self._loop.set_exception_handler(AsyncioExecutor.loop_exception_handler)
        self._loop_ready = threading.Event()

        # Use the global
        self._background_tasks: Dict[Future, Dict[str, Any]] = BACKGROUND_TASKS

    def get_event_loop(self) -> AbstractEventLoop:
        """
        :return: The AbstractEventLoop associated with this instance
        """
        return self._loop

    def start(self):
        """
        Starts the background thread.
        Do this separately from constructor for more control.
        """
        # Don't start twice
        if self._thread is not None:
            return

        self._thread = threading.Thread(target=self.loop_manager,
                                        args=(self._loop, self._loop_ready),
                                        daemon=True)
        self._thread.start()
        timeout: int = EXECUTOR_START_TIMEOUT_SECONDS
        was_set: bool = self._loop_ready.wait(timeout=timeout)
        if not was_set:
            raise ValueError(f"FAILED to start executor event loop in {timeout} sec")

    @staticmethod
    def notify_loop_ready(loop_ready: threading.Event):
        """
        Function will be called once the event loop starts
        """
        loop_ready.set()

    @staticmethod
    def loop_manager(loop: AbstractEventLoop, loop_ready: threading.Event):
        """
        Entry point static method for the background thread.

        :param loop: The AbstractEventLoop to use to run the event loop.
        :param loop_ready: event notifying that loop is ready for execution.
        """
        asyncio.set_event_loop(loop)
        loop.call_soon(AsyncioExecutor.notify_loop_ready, loop_ready)
        loop.run_forever()

        # If we reach here, the loop was stopped.
        # We should gather any remaining tasks and finish them.
        pending = asyncio.all_tasks(loop=loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=False))

    @staticmethod
    def loop_exception_handler(loop: AbstractEventLoop, context: Dict[str, Any]):
        """
        Handles exceptions for the asyncio event loop

        DEF - I believe this exception handler is for exceptions that happen in
              the event loop itself, *not* the submit()-ed coroutines.
              Exceptions from the coroutines are handled by submission_done() below.

        :param loop: The asyncio event loop
        :param context: A context dictionary described here:
                https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.loop.call_exception_handler
        """
        # Call the default exception handler first
        loop.default_exception_handler(context)

        message = context.get("message", None)
        print(f"Got exception message {message}")

        exception = context.get("exception", None)
        formatted_exception = traceback.format_exception(exception)
        print(f"Traceback:\n{formatted_exception}")

    def submit(self, submitter_id: str, function, /, *args, **kwargs) -> Future:
        """
        Submit a function to be run in the asyncio event loop.

        :param submitter_id: A string id denoting who is doing the submitting.
        :param function: The function handle to run
        :param /: Positional or keyword arguments.
            See https://realpython.com/python-asterisk-and-slash-special-parameters/
        :param args: args for the function
        :param kwargs: keyword args for the function
        :return: An asyncio.Future that corresponds to the submitted task
        """

        if self._shutdown:
            raise RuntimeError('Cannot schedule new futures after shutdown')

        if not self._loop.is_running():
            raise RuntimeError("Loop must be started before any function can "
                               "be submitted")

        future: Future = None
        if inspect.iscoroutinefunction(function):
            coro = function(*args, **kwargs)
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        else:
            func = functools.partial(function, *args, **kwargs)
            future = self._loop.run_in_executor(None, func)

        self.track_future(future, submitter_id, function)

        return future

    def create_task(self, awaitable: Awaitable, submitter_id: str, raise_exception: bool = False) -> Future:
        """
        Creates a task for the event loop given an Awaitable
        :param awaitable: The Awaitable to create and schedule a task for
        :param submitter_id: A string id denoting who is doing the submitting.
        :param raise_exception: True if exceptions are to be raised in the executor.
                    Default is False.
        :return: The Future corresponding to the results of the scheduled task
        """
        future: Future = self._loop.create_task(awaitable)
        self.track_future(future, submitter_id, awaitable, raise_exception)
        return future

    def track_future(self, future: Future, submitter_id: str, function, raise_exception: bool = False):
        """
        :param future: The Future to track
        :param submitter_id: A string id denoting who is doing the submitting.
        :param function: The function handle to be run in the future
        :param raise_exception: True if exceptions are to be raised in the executor.
                    Default is False.
        """

        # Weak references in the asyncio system can cause tasks to disappear
        # before they execute.  Hold a reference in a global as per
        # https://docs.python.org/3/library/asyncio-task.html#creating-tasks

        function_name: str = None
        try:
            function_name = function.__qualname__   # Fully qualified name of function
        except AttributeError:
            # Just get the class name
            function_name = function.__class__.__name__

        self._background_tasks[future] = {
            "submitter_id": submitter_id,
            "function": function_name,
            "future": future,
            "raise_exception": raise_exception
        }
        future.add_done_callback(self.submission_done)

        return future

    def submission_done(self, future: Future):
        """
        Intended as a "done_callback" method on futures created by submit() above.
        Does some processing on a future that has been marked as done
        (for whatever reason).

        :param future: The Future which has completed
        """

        # Get a dictionary entry describing some metadata about the future itself.
        future_info: Dict[str, Any] = {}
        future_info = self._background_tasks.get(future, future_info)

        origination: str = f"{future_info.get('submitter_id')} of {future_info.get('function')}"

        if future.done():
            try:
                # First see if there was any exception
                exception = future.exception()
                if exception is not None and future_info.get("raise_exception"):
                    raise exception

                result = future.result()
                _ = result

            except StopAsyncIteration:
                # StopAsyncIteration is OK
                pass

            except TimeoutError:
                print(f"Coroutine from {origination} took too long()")

            # pylint: disable=broad-exception-caught
            except Exception as exception:
                print(f"Coroutine from {origination} raised an exception:")
                formatted_exception: List[str] = traceback.format_exception(exception)
                for line in formatted_exception:
                    if line.endswith("\n"):
                        line = line[:-1]
                    print(line)
        else:
            print("Not sure why submission_done() got called on future "
                  f"from {origination} that wasn't done")

        # As a last gesture, remove the background task from the map
        # we use to keep its reference around.
        del self._background_tasks[future]

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False):
        """
        Shuts down the event loop.

        :param wait: True if we should wait for the background thread to join up.
                     False otherwise.  Default is True.
        :param cancel_futures: Ignored? Default is False.
        """
        self._shutdown = True
        self._loop.call_soon_threadsafe(self._loop.stop)
        if wait:
            self._thread.join()
        self._thread = None
