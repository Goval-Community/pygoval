ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def encode(number: int | float) -> str:
    result = ""
    number = abs(int(number))

    while number:
        number, remainder = divmod(number, 36)
        result = ALPHABET[remainder] + result

    return result or "0"
