import redis
import time

from abc import ABC, abstractmethod
from typing import Optional, Union


class UnavailableLockError(Exception):
    """Expresses that a lock could not be obtained."""

    pass


class ReaderWriterLock(ABC):
    """Base abstract class to work with a custom implementation of a
    reader/writer locking mechanism.
    
    Its derived classes can be used as context managers.

    Instance attributes
    -------------------
    connection: redis.StrictRedis
        A connection to a Redis instance.
    resource: str
        The name that represents the resource for which a lock is desired.
    timeout: Union[int, float]
        The time to live for the lock once acquired.
    sleep: Union[int, float]
        The amount of time that the thread will be suspended between tries to
        acquire the lock.
        
    Instance methods
    ----------------
    acquire(self, blocking: bool) -> bool
        Tries to acquire the lock for the resource specified by the attribute
        "resource".
    release(self) -> None
        Releases the held lock.
    get_mutex_key(self) -> str
        Composes the key associated to the mutex of the resource specified by
        attribute "resource".
    get_readers_key(self) -> str
        Composes the key associated to the set of active readers of the
        resource specified by attribute "resource".
    """

    def __init__(
            self,
            connection: redis.StrictRedis,
            resource: str,
            timeout: Union[int, float] = 5,
            sleep: Union[int, float] = 0.1):
        """
        Parameters
        ----------
        connection: redis.StrictRedis
            The connection to the desired Redis instance.
        resource: str
            The name that represents the resource for which a lock is seeked.
        timeout: Union[int, float], optional
            The time to live for the lock once acquired. Its default value is
            5 seconds.
        sleep: Union[int, float], optional
            The amount of time that the thread will be suspended between tries
            to acquire the lock. Its default value is 0.1 seconds.
        """

        self.connection: redis.StrictRedis = connection
        self.resource: str = resource
        self.timeout: Union[int, float] = timeout
        self.sleep: Union[int, float] = sleep

    @abstractmethod
    def acquire(self, blocking: bool = True) -> bool:
        """Tries to acquire the lock for the resource specified by the
        attribute "resource".

        Parameters
        ----------
        blocking: bool
            Specifies wheter the thread should keep trying to acquire the lock
            if the first time it fails to do so.

        Returns
        -------
        bool
            Wheter the lock was acquired or not.
        """

        pass

    @abstractmethod
    def release(self) -> None:
        """Releases the held lock."""

        pass

    def get_mutex_key(self) -> str:
        """Composes the key associated to the mutex of the resource specified
        by attribute "resource".

        Returns
        -------
        str
            The key for the resource's mutex.
        """

        return f"{self.resource}:mutex"

    def get_readers_key(self) -> str:
        """Composes the key associated to the set of active readers of the
        resource specified by attribute "resource".

        Returns
        -------
        str
            The key for the resource's set of active readers.
        """

        return f"{self.resource}:readers"

    def __enter__(self):
        if not self.acquire(blocking=True):
            raise UnavailableLockError(
                "The specified lock could not be acquired.")

    def __exit__(self, type, value, traceback):
        self.release()


class ReaderLock(ReaderWriterLock):
    """Class to handle a reader lock over a given resource. Its companion
    class is WriterLock.
    
    This implementation prefers readers.
    
    For information about methods and attributes inherited from
    ReaderWriteLock, please refer to that class documentation.

    Instance attributes
    -------------------
    reading_timeout: Union[int, float]
        The maximum amount of time that the thread can hold the shared lock
        between readers.
    """

    def __init__(
            self,
            connection: redis.StrictRedis,
            resource: str,
            timeout: Union[int, float] = 5,
            reading_timeout: Union[int, float] = 5,
            sleep: Union[int, float] = 0.1):
        """The documentation for the shared parameters with the init method of
        ReaderWriterLock can be found in that same method.

        Parameters
        ----------
        reading_timeout: Union[int, float], optional
            The maximum amount of time that the thread can hold the shared
            lock between readers.
        """

        super().__init__(connection, resource, timeout, sleep)
        self.reading_timeout: Union[int, float] = timeout
        self.reader_id: str = ''

    def acquire(self, blocking: bool = True) -> bool:
        """Documented in ReaderWriterLock.acquire()."""

        self.reader_id = self.connection.incr(
            f"{self.resource}:readers:next_id")
        lock = self.connection.lock(
            self.get_mutex_key(),
            timeout=self.timeout,
            sleep=self.sleep)
        registered = 0

        if blocking:
            with lock:
                registered = self.connection.zadd(
                    self.get_readers_key(),
                    {self.reader_id: time.time() + self.reading_timeout})
        elif lock.acquire(blocking=False):
            registered = self.connection.zadd(
                self.get_readers_key(),
                {self.reader_id: time.time() + self.reading_timeout})
            lock.release()

        return registered == 1

    def release(self):
        """Documented in ReaderWriterLock.release()."""

        self.connection.zrem(self.get_readers_key(), self.reader_id)


class WriterLock(ReaderWriterLock):
    """Class to handle a writer lock over a given resource. Its companion
    class is ReaderLock.
    
    This implementation prefers readers.
    
    For information about its methods and attributes, please refer to the
    documentation for its base class: ReaderWriteLock.
    """

    def __init__(
            self,
            connection: redis.StrictRedis,
            resource: str,
            timeout: Union[int, float] = 5,
            sleep: Union[int, float] = 0.1):
        """Parameters are described in the documentation for
        ReaderWriterLock."""

        super().__init__(connection, resource, timeout, sleep)
        self.lock = self.connection.lock(
            self.get_mutex_key(),
            timeout=self.timeout)

    def acquire(self, blocking: bool = True) -> bool:
        """Documented in ReaderWriterLock.acquire()."""

        readers_key = self.get_readers_key()
        # Clears all expired readers.
        self.connection.zremrangebyscore(readers_key, "-inf", time.time())

        if blocking:
            while (self.connection.zcard(readers_key) != 0
                    or not self.lock.acquire(blocking=False)):
                time.sleep(self.sleep)
                # Clears all expired readers and tries again.
                self.connection.zremrangebyscore(
                    readers_key,
                    "-inf",
                    time.time())
            return True

        return (self.connection.zcard(readers_key) == 0
            and self.lock.acquire(blocking=False))

    def release(self) -> None:
        """Documented in ReaderWriterLock.release()."""

        self.lock.release()
