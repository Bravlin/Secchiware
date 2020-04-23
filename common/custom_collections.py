from typing import Any, Callable, List

class OrderedListOfDict():
    """
    A wrapper that keeps a list of dictionaries ordered by a specific key that
    must be present in all of them. Also, the values associated to that key
    must all be of the same type.

    Attributes
    ----------
    content: List[dict]
        The list wrapped by a instance of this class. It should not be
        directly manipulated. You can set this attribute with a list of
        dictionaries that fulfills the instance conditions for the sorting key
        and its value.
        
    Methods
    -------
    index_of(key_value: Any) -> int
        Looks for the index of the element associated to the given key.
    insert(d: dict) -> None
        Inserts (or updates) d in the collection.
    batch_insert(values: List[dict]) -> None:
        Inserts (or updates) the elements present in the argument.
    delete(self, key_value: Any) -> None:
        Removes the element associated to the given key from the collection.
    """

    def __init__(
            self,
            sort_key: Any,
            sort_key_value_type: Callable,
            values: List[dict] = []):
        """
        Parameters
        ----------
        sort_key: Any
            The key associated to the values used to sort the collection.
        sort_key_value_type: Callable
            The type of the values used to sort the collection.
        values: List[dict], optional
            A list of dictionaries used to initialize the instance. If it is
            not given, the instance is initialized with an empty list.
        """
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
                raise TypeError(
                    "Found member in argument which is not a dictionary.")
            if not key in d:
                raise ValueError(
                    "The sort key is not present in one of the members of "
                    "the argument.")
            if not isinstance(d[key], self._skvt):
                raise TypeError(
                    "The type of the value corresponding to the sort key is "
                    "not correct in one of the members.")
        self._ordered_list = sorted(value, key=lambda x : x[key])

    def index_of(self, key_value: Any) -> int:
        """Looks for the index of the element associated to the given key.
        
        Parameters
        ----------
        key_value: Any
            The key to look for in the collection.

        Raises
        ------
        TypeError
            The given key's type is not valid for this collection.

        Returns
        -------
        int
            The index of the element associated to the given key. Returns -1 in
            the case where there was no match.
        """

        if not isinstance(key_value, self._skvt):
            raise TypeError("The argument type is invalid.")
        
        key = self._sort_key
        ol = self._ordered_list
        # Binary search.
        start = 0
        end = len(ol) - 1
        middle = (start + end)//2
        while start <= end and ol[middle][key] != key_value:
            if (ol[middle][key] > key_value):
                end = middle - 1
            else:
                start = middle + 1
            middle = (start + end)//2
        if start > end: # No match.
            return -1
        return middle

    def insert(self, d: dict) -> None:
        """Inserts (or updates) d in the collection.

        If d has a key that alredy exists in the collection, it replaces the
        associated element.

        Parameters
        ----------
        d: dict
            The element to insert or update in the collection.
        
        Raises
        ------
        ValueError
            d does not contain the needed sort key.
        TypeError
            d is not a dictionary or its element associated to the sort key has
            a wrong type.
        """

        key = self._sort_key
        if not isinstance(d, dict):
            raise TypeError("The argument is not a dictionary.")
        if not key in d:
            raise ValueError("The sort key is not present in the argument.")
        if not isinstance(d[key], self._skvt):
            raise TypeError(
                "The type of the value corresponding to the sort key is not "
                "correct.")

        ol = self._ordered_list
        # Binary search.
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
            ol.insert(start, d) # Inserts if there was no match.
        else:
            ol[middle] = d # Updates if there was a match.

    def batch_insert(self, values: List[dict]) -> None:
        """Inserts (or updates) the elements present in the argument.
        It ignores any incompatible members.

        Parameters
        ----------
        values: List[dict]
            A list containing the elements to insert or update in the
            collection.
        """

        key = self._sort_key
        appended = False

        for d in values:
            if not isinstance(d, dict):
                print("Found member in argument which is not a dictionary.")
            elif not key in d:
                print(
                    "The sort key is not present in one of the members of "
                    "the argument.")
            else:
                try:
                    index = self.index_of(d[key])
                except TypeError:
                    print("The type of the value corresponding to the sort "
                        "key is not correct in one of the members.")
                else:
                    if index >= 0:
                        # Updates if there was no match.
                        self._ordered_list[index] = d
                    else:
                        # Appends if there was a match.
                        self._ordered_list.append(d)
                        appended = True
        # It's faster to order the list after appending various elements
        # than inserting them keeping the list's order.
        if appended: self._ordered_list.sort(key=lambda x : x[key])

    def delete(self, key_value: Any) -> None:
        """Removes the element associated to the given key from the collection.

        Parameters
        ----------
        key_value: Any
            The key to look for in the collection.

        Raises
        ------
        KeyError
            The given key was not found in the collection.
        TypeError
            The given key's type is not valid for this collection.
        """

        index = self.index_of(key_value) # Can throw TypeError.
        if index < 0:
            raise KeyError()
        del self._ordered_list[index]