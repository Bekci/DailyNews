def _chunk_by_word(sentence_to_chunk: str) -> list[str]:
    """
    Divides the sentence into without dividing any word
    """
    result = []
    current_sentence = ""
    words = sentence_to_chunk.split(" ")
    current_length = 0
    for word in words:
    # Still below the limit
        if current_length + len(word) < 226:
            current_sentence += word + " "
            current_length += len(word) + 1
        # Cannot add more word
        else:
            result.append(current_sentence.strip())
            current_length = 0
    return result

def _chunk_sentence(sentence: str) -> list[str]:
    """
    Divides the sentence into chunks of at most 225 characters.
    The main goal is to keep sentence as whole as possible but not
    add more words to make the sentence longer.
    While dividing into chunks first commas will be used if availabe
    then words will be used.
    """
    # Check if dividing by a comma will resolve
    chunks = []
    comma_split_sentence = sentence.split(',')

    for sentence_part in comma_split_sentence:
        if len(sentence_part) < 226:
            chunks.append(sentence_part.strip())
        else:
            chunks.extend(_chunk_by_word(sentence_part))
    
    return _combine_short_chunks(chunks)

def _combine_short_chunks(chunks: list[str]) -> list[str]:
    """
    Combines the chunks that are shorter than 225 characters
    with the next chunk to make them longer but still under 225 characters.
    """
    result = []
    current_chunk = ""
    for chunk in chunks:
        if len(current_chunk) + len(chunk) + 1 < 226:
            current_chunk += " " + chunk
        else:
            if current_chunk:
                result.append(current_chunk.strip())
            current_chunk = chunk
    if current_chunk:
        result.append(current_chunk.strip())
    return result

def chunk_text(text: str) -> list[str]:
    """
    Divides the text into chunks of at most 225 characters.
    The main goal is to  keep sentences as whole as possible
    Therefore first commas will be used to divide sentences, 
    then words will be used if necessary to not exceed the limit.
    """
    result = []
    sentences = text.split('.')
    for sentence in sentences:
        if len(sentence) < 226 and len(sentence) > 1:
            result.append(sentence.strip())
        elif len(sentence) > 1:
            result.extend(_chunk_sentence(sentence))
    return result