import pytest

def test_add_edge_cases():
    # Test case 1: a=0, b=0
    assert add(0, 0) == 0
    # Test case 2: a=1, b=-1
    assert add(1, -1) == 0
    # Test case 3: a=10, b=20
    assert add(10, 20) == 30

def test_add_edge_cases_types():
    # Test case 1: a=str(1), b=int(1)
    with pytest.raises(TypeError):
        add('1', 1)
    # Test case 2: a=int(-10), b=float(0.5)
    with pytest.raises(TypeError):
        add(-10, 0.5)

def test_add_invalid_input():
    # Test case 1: a is None
    with pytest.raises(TypeError):
        add(None, 1)
    # Test case 2: b is None
    with pytest.raises(TypeError):
        add(1, None)

def test_add_functionality():
    # Test case 1: a=5, b=5
    assert add(5, 5) == 10
    # Test case 2: a=-5, b=-5
    assert add(-5, -5) == -10
    # Test case 3: a=0.5, b=5
    assert add(0.5, 5) == 5.5

# Test case: a or b is not int or float
def test_add_invalid_input_type():
    with pytest.raises(TypeError):
        add('hello', 'world')