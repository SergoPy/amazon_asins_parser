import string


def indexes_to_a1(i: int, j: int) -> str:
    i -= 1
    j -= 1
    letters = string.ascii_uppercase
    n_letters = len(letters)

    last_letter_column = letters[j % n_letters]
    column = ''
    while j / n_letters >= 1:
        column += letters[int(j / n_letters) - 1]
        j /= n_letters

    column += last_letter_column
    row = str(i + 1)

    return column + row
