import re
import regex

def _translate_roman_numerals(text: str) -> str:
    """
    Translates Roman numerals between I and XX (1-20) in the input text
    to their corresponding integer values.
    Allows an optional '.' at the end, e.g., 'IV.' or 'XII.'
    """
    def get_order_suffix(number_text: str):
        """
        Adds the correct suffix for ordinal numbers in Turkish
        """
        last_letter = number_text[-1]
        suffix_mapping = [ [['r', 'ş', 'z'], 'inci'], ['i', 'nci'], ['ı', 'ncı'],['ç', 'ncü'], ['t', 'üncü'], ['n', 'uncu'] ]
        for letters, suffix in suffix_mapping:
            if last_letter in letters:
                return suffix

    has_order_text = False
    if text.endswith('.'):
        text = text[:-1]  # Remove the trailing dot for mapping
        has_order_text = True
    
    mapping = {
        "I": "bir",
        "II": "iki",
        "III": "üç",
        "IV": "dört",
        "V": "beş",
        "VI": "altı",
        "VII": "yedi",
        "VIII": "sekiz",
        "IX": "dokuz",
        "X": "on",
        "XI": "on bir",
        "XII": "on iki",
        "XIII": "on üç",
        "XIV": "on dört",
        "XV": "on beş",
        "XVI": "on altı",
        "XVII": "on yedi",
        "XVIII": "on sekiz",
        "XIX": "on dokuz",
        "XX": "yirmi"
    }
    number_as_text = mapping.get(text, "bir")
    
    if has_order_text:
        return number_as_text + get_order_suffix(number_as_text)

    return number_as_text

def _replace_roman_number(text: str) -> bool:
    """
    Check if the input word (only uppercase letters) is a valid
    Roman numeral between I and XX (1–20).
    Allows an optional '.' at the end, e.g., 'IV.' or 'XII.'
    """
    # Strictly match only uppercase letters (I, V, X) + optional dot
    pattern = re.compile(r'(?<!\S)[IVX]+\.?(?!\S)')
    
    matches = pattern.findall(text)

    for match in matches:
        text = text.replace(match, _translate_roman_numerals(match))

    return text

def _replace_initials_dots(text: str):
    """
    Remove dots in sequences of single uppercase letters followed by dots, e.g.:
    "A." -> "A", "A.İ." -> "Aİ"
    Does not match multi-letter groups like "AD." or "KL.".
    """
    pattern = re.compile(r'(?:\b[^\W\d_]\.)+', re.UNICODE)
    
    matches = pattern.findall(text)
    
    for match in matches:
        text.replace(match, match.replace('.', ''))
    
    return text

def _replace_decimal_commas(text: str):
    """
    Replace commas that are between digits (e.g. 45,1 or 0,56) with the word 'virgül'.
    We add spaces around 'virgül' so tokenization/reading is clearer; extra spaces are collapsed later.
    """
    return re.sub(r'(?<=\d),(?=\d)', ' virgül ', text)

def _replace_decimal_dots(text: str):
    """
    Remove dots that are between digits (e.g. 45.1 or 0.56)
    TTS engine can handle such cases without dots.
    """
    return re.sub(r'(?<=\d).(?=\d)', '', text)

def _remove_abbreviations(text: str):
    """
    Removes abbreviations like e.g., i.e., etc. from the text
    """
    # remove occurrences like (ABC) where letters are Unicode uppercase (İ,Ş,Ü,Ç,Ö,Ğ etc.)
    text = regex.sub(r'\([\p{Lu}]+\)', '', text)
    return text.strip()

def _remove_common_chars(text: str):
    return text.replace('|', '').replace('>', '').replace('<', '')

def clean_text(text: str):
    """
    Cleans the text from the characters and words not supported by the TTS engine
    """
    cleaned_text = _remove_abbreviations(text)
    cleaned_text = _replace_initials_dots(cleaned_text)
    cleaned_text = _replace_decimal_dots(cleaned_text)
    cleaned_text = _replace_decimal_commas(cleaned_text)
    clean_text = cleaned_text.replace('"', '').replace('“', '').replace('”', '')
    clean_text = clean_text.replace('’', "'")
    clean_text = _replace_roman_number(clean_text)
    clean_text = _remove_common_chars(clean_text)
    
    # Remove a common abbv.
    clean_text.replace('Çev.', '')
    
    # collapse multiple spaces into one
    clean_text = regex.sub(r'\s{2,}', ' ', clean_text)
    return clean_text.strip()

