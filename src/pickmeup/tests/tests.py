# list which is a generator
# Make sure state is saved, or faults with missing permissions
# Make sure state is saved to one space only, regardless of execution directory (PATH issues)
import os
import unittest

from pickmeup import PickMeUp


def _clear_existing_instance_name_log():
    PickMeUp.EXISTING_INSTANCE_NAMES = set()


def make_generator(iterable):
    for e in iterable:
        yield e


class TestListProcessing(unittest.TestCase):

    NAME = "test_list_processing_state"

    def tearDown(self):
        """Remove created state file, clear the log of existing instance names"""
        _clear_existing_instance_name_log()

        context = PickMeUp([], TestListProcessing.NAME)
        try:
            os.remove(context._state_file)
        except FileNotFoundError:
            pass

        _clear_existing_instance_name_log()

    def test_good_processing(self):
        """"Make sure a valid processing for all elements actually can process all elements,
        and does not create a state file"""
        iterable = [1, 2, 3, 4]

        context = PickMeUp(iterable, TestListProcessing.NAME)
        retrieved_elements = []
        with context as redo_iterable:
            for e in redo_iterable:
                retrieved_elements.append(e)

        self.assertEqual(iterable, retrieved_elements)
        self.assertFalse(context._state_file.is_file())

    def test_abort(self):
        """Make sure a processing that fails on an element results in a correct state dump"""
        def _get_state_dump(iterable):
            """Inserts `None` on fail_index and checks the resulting state file"""
            _clear_existing_instance_name_log()

            if iterable.count(None) != 1:
                raise ValueError("Only one `None` value allowed!")

            with self.assertRaises(TypeError):
                with PickMeUp(iterable, TestListProcessing.NAME) as redo_iterable:
                    for e in redo_iterable:
                        _ = e * 42

            _clear_existing_instance_name_log()
            with PickMeUp(iterable, TestListProcessing.NAME) as redo_iterable:
                elements = list(redo_iterable)
            return elements

        self.assertEqual(
            _get_state_dump([None, 1, 2, 3, 4]),
            [None, 1, 2, 3, 4],
        )
        self.assertEqual(
            _get_state_dump([1, None, 2, 3, 4]),
            [None, 2, 3, 4],
        )
        self.assertEqual(
            _get_state_dump([1, 2, 3, 4, None]),
            [None],
        )

    def test_successive_abort(self):
        """Make sure successive aborts still lead to the full list being processed"""
        iterable = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        processed_elements = []
        for i, _ in enumerate(iterable):
            # Progress through the list, one element succeeding, one failing
            _clear_existing_instance_name_log()
            try:
                context = PickMeUp(iterable, TestListProcessing.NAME)
                with context as redo_iterable:
                    for e in redo_iterable:
                        # Succeed
                        processed_elements.append(e)
                        break
                    for _ in redo_iterable:
                        # Fail
                        raise ValueError("Some Error to stop processing")
            except ValueError:
                pass
            self.assertEqual(iterable[:i + 1], processed_elements)

    def test_pickup_and_success(self):
        """Make sure a fail and pickup results in the whole list being processed"""
        iterable = [1, None, 2, 3, 4, 5]

        processed_elements = []
        buggy_process = lambda x: x * 2
        try:
            with PickMeUp(iterable, TestListProcessing.NAME) as redo_iterable:
                for e in redo_iterable:
                    buggy_process(e)
                    processed_elements.append(e)
        except TypeError:
            pass

        _clear_existing_instance_name_log()

        correct_process = lambda x: x * 2 if x is not None else None
        with PickMeUp(iterable, TestListProcessing.NAME) as redo_iterable:
            for e in redo_iterable:
                correct_process(e)
                processed_elements.append(e)

        self.assertEqual(iterable, processed_elements)


class TestInitialization(unittest.TestCase):
    def test_invalid_name_rejection(self):
        """Make sure only names that can be a filename are accepted"""
        invalid_chars = " /\\\n:"
        for c in invalid_chars:
            with self.assertRaises(ValueError):
                PickMeUp([], f"invalid{c}name")


class TestGeneratorsProcessing(unittest.TestCase):

    NAME = "test_generators_processing_state"

    def tearDown(self):
        """Remove created state file, clear the log of existing instance names"""
        _clear_existing_instance_name_log()

        context = PickMeUp([], TestGeneratorsProcessing.NAME)
        try:
            os.remove(context._state_file)
        except FileNotFoundError:
            pass

        _clear_existing_instance_name_log()

    def test_with_faulty_generator(self):
        def _faulty_generator():
            for i in range(100):
                if i == 42:
                    raise ValueError("Arbitrary fault in generator")
                yield i

        with self.assertRaises(ValueError):
            with PickMeUp(_faulty_generator(), TestGeneratorsProcessing.NAME) as redo_iterable:
                for _ in redo_iterable:
                    pass

    def test_good_processing(self):
        """"Make sure a valid processing for all elements actually can process all elements,
        and does not create a state file"""
        iterable = make_generator([1, 2, 3, 4])

        context = PickMeUp(iterable, TestListProcessing.NAME)
        retrieved_elements = []
        with context as redo_iterable:
            for e in redo_iterable:
                retrieved_elements.append(e)

        self.assertEqual([1, 2, 3, 4], retrieved_elements)
        self.assertFalse(context._state_file.is_file())

    def test_abort(self):
        """Make sure a processing that fails on an element results in a correct state dump"""
        def _get_state_dump(elements):
            _clear_existing_instance_name_log()

            with self.assertRaises(TypeError):
                with PickMeUp(elements, TestListProcessing.NAME) as redo_iterable:
                    for e in redo_iterable:
                        _ = e * 42

            _clear_existing_instance_name_log()
            with PickMeUp(elements, TestListProcessing.NAME) as redo_iterable:
                elements = list(redo_iterable)
            return elements

        self.assertEqual(
            _get_state_dump(make_generator([None, 1, 2, 3, 4])),
            [None, 1, 2, 3, 4],
        )
        self.assertEqual(
            _get_state_dump(make_generator([1, None, 2, 3, 4])),
            [None, 2, 3, 4],
        )
        self.assertEqual(
            _get_state_dump(make_generator([1, 2, 3, 4, None])),
            [None],
        )

    def test_successive_abort(self):
        """Make sure successive aborts still lead to the full list being processed"""
        iterable = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        g = make_generator(iterable)

        processed_elements = []
        for i, _ in enumerate(iterable):
            # Progress through the list, one element succeeding, one failing
            _clear_existing_instance_name_log()
            try:
                with PickMeUp(g, TestGeneratorsProcessing.NAME) as redo_iterable:
                    for e in redo_iterable:
                        # Succeed
                        processed_elements.append(e)
                        break
                    for _ in redo_iterable:
                        # Fail
                        raise ValueError("Some Error to stop processing")
            except ValueError:
                pass
            except StopIteration:
                pass
            self.assertEqual(iterable[:i + 1], processed_elements)

    def test_pickup_and_success(self):
        """Make sure a fail and pickup results in the whole list being processed"""
        iterable = [1, None, 2, 3, 4, 5]
        g = make_generator(iterable)

        processed_elements = []
        buggy_process = lambda x: x * 2
        try:
            with PickMeUp(g, TestListProcessing.NAME) as redo_iterable:
                for e in redo_iterable:
                    buggy_process(e)
                    processed_elements.append(e)
        except TypeError:
            pass

        _clear_existing_instance_name_log()

        correct_process = lambda x: x * 2 if x is not None else None
        with PickMeUp(g, TestListProcessing.NAME) as redo_iterable:
            for e in redo_iterable:
                correct_process(e)
                processed_elements.append(e)

        self.assertEqual(iterable, processed_elements)


if __name__ == "__main__":
    unittest.main()
