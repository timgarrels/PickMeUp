import os
import string
from collections.abc import Iterator
from contextlib import AbstractContextManager
from typing import Iterable
from pathlib import Path
import pickle

FILENAME_PREFIX = ".abortable_list_save_"
ALLOWED_FILENAME_CHARS = set(string.ascii_letters + string.digits + "_" + "." + "-")


class PickMeUp(AbstractContextManager):
    EXISTING_INSTANCE_NAMES = set()

    def __init__(self, list_obj: Iterable, name: str):
        self._list_obj = list_obj

        valid_name = all([c in ALLOWED_FILENAME_CHARS for c in name])
        if not valid_name:
            raise ValueError("PickMeUp name can only contain letters, digits, and '-', '_', '.'")
        if name in PickMeUp.EXISTING_INSTANCE_NAMES:
            raise NotImplementedError("TODO: ABORT; MUTLIPLE ABORTABLE LSITS WITH THE SAME NAME!")
        self._name = name  # A unique identifier to indicate where to store and load state!
        PickMeUp.EXISTING_INSTANCE_NAMES.add(self._name)
        self._state_file = Path(__file__).resolve().parent / (FILENAME_PREFIX + self._name)

        self._last_element = None

    def __enter__(self) -> Iterator:
        remaining_elements = None
        if self._state_file.is_file():
            # State exists!
            with open(self._state_file, "rb") as f:
                remaining_elements = pickle.load(f)

        self._list_iterator = self.create_list_iterator(remaining_elements)
        return self._list_iterator

    def __exit__(self, exc_type, exc_value, traceback):
        if all([
            arg is None
            for arg in [exc_type, exc_value, traceback]
        ]):
            # Nothing aborted our context, we ran fine
            # using an PickMeUp was a precaution but not necessary (anymore :P)
            if self._state_file.is_file():
                os.remove(self._state_file)
            return
        # We were aborted early
        # We do not want to catch the exception, so people can debug
        # However, we do want to save state so people can debug starting right from the last thing they processed
        self.save_state()
        return False

    def save_state(self):
        elements_to_save = [self._last_element]
        elements_to_save += [e for e in self._list_iterator]
        with open(self._state_file, "wb") as f:
            pickle.dump(elements_to_save, f)

    def create_list_iterator(self, remaining_elements: Iterable = None):
        elements = self._list_obj if remaining_elements is None else remaining_elements
        for e in elements:
            self._last_element = e
            yield self._last_element
