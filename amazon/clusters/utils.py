import string
from typing import Iterable


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


def _validate_char(i: int, char: str, text: str) -> str:
    replaceable_chars = ".,+:;'-"
    removable_chars = replaceable_chars + '_%"/&'
    has_no_spaces_around = i != 0 and i != len(text) - 1 and text[i - 1] != ' ' and text[i + 1] != ' '

    if char in replaceable_chars and has_no_spaces_around:
        return ' '
    if char not in removable_chars:
        return char
    return ''


def article_filter(text: list) -> list:
    articles = ['a', 'are', 'the']
    words = ''.join(text).split()
    return [word for word in words if word.strip() not in articles]


def normalize_text(text: str) -> str:
    valid_text_chars = [_validate_char(i, c, text) for i, c in enumerate(text)]
    no_article_words = article_filter(valid_text_chars)
    return ' '.join(no_article_words).replace('  ', ' ')
