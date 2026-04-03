import pytest
import sys
sys.path.insert(0, "sandbox/src")
import file2


def test_multiply_positive_number():
    result = file2.multiply(5, 5)
    assert result == 25

def test_multiply_negative_number():
    result = file2.multiply(-5, 5)
    assert result == -25

def test_multiply_zero_number():
    result = file2.multiply(5, 0)
    assert result == 0

def test_multiply_float_number():
    result = file2.multiply(5, 2.5)
    assert result == 12.5


