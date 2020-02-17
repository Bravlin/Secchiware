from typing import Any, Callable, List

class OrderedListOfDict():

    def __init__(
            self,
            sort_key: Any,
            sort_key_value_type: Callable,
            values: List[dict] = []):
        self._sort_key: Any = sort_key
        self._skvt: Callable = sort_key_value_type
        if values:
            self.content = values
        else:
            self._ordered_list: List[dict] = []

    @property
    def content(self) -> List[dict]:
        return self._ordered_list

    @content.setter
    def content(self, value: List[dict]) -> None:
        key = self._sort_key
        for d in value:
            if not isinstance(d, dict):
                raise ValueError("Found member in argument which is not a dictionary.")
            if not key in d:
                raise ValueError("The sort key is not present in one of the members of the argument.")
            if not isinstance(d[key], self._skvt):
                raise ValueError("The type of the value corresponding to the sort key is not correct in one of the members.")
        self._ordered_list = sorted(value, key=lambda x : x[key])

    def index_of(self, key_value: Any) -> int:
        if not isinstance(key_value, self._skvt):
            raise ValueError("The argument type is invalid.")
        
        key = self._sort_key
        ol = self._ordered_list
        start = 0
        end = len(ol) - 1
        middle = (start + end)//2
        while start <= end and ol[middle][key] != key_value:
            if (ol[middle][key] > key_value):
                end = middle - 1
            else:
                start = middle + 1
            middle = (start + end)//2
        if start > end:
            return -1
        return middle

    def insert(self, d: dict) -> None:
        key = self._sort_key
        if not isinstance(d, dict):
            raise ValueError("The argument is not a dictionary.")
        if not key in d:
            raise ValueError("The sort key is not present in the argument.")
        if not isinstance(d[key], self._skvt):
            raise ValueError("The type of the value corresponding to the sort key is not correct.")

        ol = self._ordered_list
        start = 0
        end = len(ol) - 1
        middle = (start + end)//2
        while start <= end and ol[middle][key] != d[key]:
            if (ol[middle][key] > d[key]):
                end = middle - 1
            else:
                start = middle + 1
            middle = (start + end)//2
        if start > end:
            ol.insert(start, d) # Inserts
        else:
            ol[middle] = d # Updates

    def batch_insert(self, values: List[dict]) -> None:
        key = self._sort_key
        appended = False
        for d in values:
            if not isinstance(d, dict):
                print("Found member in argument which is not a dictionary.")
            elif not key in d:
                print("The sort key is not present in one of the members of the argument.")
            else:
                try:
                    index = self.index_of(d[key])
                except ValueError:
                    print("The type of the value corresponding to the sort key is not correct in one of the members.")
                else:
                    if index >= 0:
                        self._ordered_list[index] = d
                    else:
                        self._ordered_list.append(d)
                        appended = True
        if appended: self._ordered_list.sort(key=lambda x : x[key])

    def delete(self, key_value: Any) -> None:
        index = self.index_of(key_value)
        if index < 0:
            raise KeyError()
        del self._ordered_list[index]