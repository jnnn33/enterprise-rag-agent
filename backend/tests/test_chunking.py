import pytest

from app.services.chunking import TextChunker


def test_short_text_stays_in_one_chunk() -> None:
    chunker = TextChunker(chunk_size=80, overlap=10)

    assert chunker.split("这是一段简短的制度说明。") == ["这是一段简短的制度说明。"]


def test_long_text_is_split_with_overlap() -> None:
    text = "第一段用于说明报销申请流程。" * 8
    chunker = TextChunker(chunk_size=60, overlap=10)

    chunks = chunker.split(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= 60 for chunk in chunks)


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError):
        TextChunker(chunk_size=50, overlap=50)

