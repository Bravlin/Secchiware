import redis
import time

from abc import ABC, abstractmethod
from typing import Optional, Union


class UnavailableLockError(Exception):
    pass


class ReaderWriterLock(ABC):
    def __init__(
            self,
            connection: redis.StrictRedis,
            resource: str,
            timeout: Union[int, float] = 5,
            sleep: Union[int, float] = 0.1):
        self.connection: redis.StrictRedis = connection
        self.resource: str = resource
        self.timeout: Union[int, float] = timeout
        self.sleep: Union[int, float] = sleep

    @abstractmethod
    def acquire(self, blocking=True) -> bool:
        pass

    @abstractmethod
    def release(self) -> None:
        pass

    def get_mutex_key(self) -> str:
        return f"{self.resource}:mutex"

    def get_readers_key(self) -> str:
        return f"{self.resource}:readers"

    def __enter__(self):
        if not self.acquire(blocking=True):
            raise UnavailableLockError(
                "The specified lock could not be acquired.")

    def __exit__(self, type, value, traceback):
        self.release()


class ReaderLock(ReaderWriterLock):
    def __init__(
            self,
            connection: redis.StrictRedis,
            resource: str,
            timeout: Union[int, float] = 5,
            reading_timeout: Union[int, float] = 5,
            sleep: Union[int, float] = 0.1):
        super().__init__(connection, resource, timeout, sleep)
        self.reading_timeout: Union[int, float] = timeout
        self.reader_id: str = ''
        
    def acquire(self, blocking=True) -> bool:
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
        self.connection.zrem(self.get_readers_key(), self.reader_id)


class WriterLock(ReaderWriterLock):
    def __init__(
            self,
            connection: redis.StrictRedis,
            resource: str,
            timeout: Union[int, float] = 5,
            sleep: Union[int, float] = 0.1):
        super().__init__(connection, resource, timeout, sleep)
        self.lock = self.connection.lock(
            self.get_mutex_key(),
            timeout=self.timeout)

    def acquire(self, blocking=True) -> bool:
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

    def release(self):
        self.lock.release()