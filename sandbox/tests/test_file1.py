from file1 import add
import pytest

class TestAdd:
    @pytest.fixture
    def add_values(self):
        return 1, 2

    def test_add_two_positive_numbers(self, add_values):
        assert add(add_values[0], add_values[1]) == add_values[0] + add_values[1]

    def test_add_two_negative_numbers(self):
        assert add(-2, -3) == -5

    def test_add_positive_and_negative_numbers(self):
        assert add(5, -7) == -2

    def test_add_zero(self):
        assert add(0, 0) == 0

    def test_add_zero_to_positive_number(self):
        assert add(0, 3) == 3

    def test_add_zero_to_negative_number(self):
        assert add(-3, 0) == -3

    def test_add_max_int(self):
        assert add(2147483647, 1) == 2147483648


    def test_add_max_uint(self):
        assert add(4294967295, 1) == 4294967296

    def test_add_float_values(self):
        assert round(add(5.0, 4.2), 2) == 9.2

    def test_add_non_int_values(self):
        assert add('a', 'b') == 'ab'
