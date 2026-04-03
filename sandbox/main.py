def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

def palindrome(s):
    return s == s[::-1]

def is_prime(num):
    if num <= 1:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True

def main():
    num = int(input("Enter a number: "))
    if is_prime(num) and palindrome(str(num)):
        print(f"{factorial(num)} and {fibonacci(num)} are the factorial and fibonacci of {num}, which is a prime palindrome.")
    else:
        print(f"{num} cannot process the number as it is not a prime palindrome.")
