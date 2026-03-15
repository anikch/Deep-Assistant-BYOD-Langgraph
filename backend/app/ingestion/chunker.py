from typing import List, Tuple


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Tuple[str, int]]:
    """
    Split text into overlapping chunks.
    Returns list of (chunk_text, chunk_index) tuples.
    """
    if not text or not text.strip():
        return []

    # Split on paragraph boundaries first, then sentences, then characters
    separators = ["\n\n", "\n", ". ", " ", ""]

    chunks = _recursive_split(text, separators, chunk_size)

    # Apply overlap
    overlapped = []
    for i, chunk in enumerate(chunks):
        overlapped.append((chunk, i))

    return overlapped


def _recursive_split(text: str, separators: List[str], chunk_size: int) -> List[str]:
    """Recursively split text using separators."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    separator = ""
    for sep in separators:
        if sep and sep in text:
            separator = sep
            break

    if not separator:
        # Fall back to hard split
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    splits = text.split(separator)
    chunks = []
    current = ""

    for split in splits:
        if not split.strip():
            continue
        candidate = current + separator + split if current else split
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current.strip())
            if len(split) > chunk_size:
                # Recursively split this piece
                sub_chunks = _recursive_split(split, separators[1:], chunk_size)
                chunks.extend(sub_chunks)
                current = ""
            else:
                current = split

    if current.strip():
        chunks.append(current.strip())

    return chunks


def chunk_text_with_overlap(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Tuple[str, int]]:
    """Split text with overlap between adjacent chunks."""
    if not text or not text.strip():
        return []

    result = []
    start = 0
    idx = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            result.append((chunk, idx))
            idx += 1
        if end >= text_len:
            break
        start = end - chunk_overlap
        if start < 0:
            start = 0

    return result
