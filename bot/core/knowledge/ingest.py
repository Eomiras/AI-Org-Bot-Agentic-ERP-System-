from langchain_text_splitters import RecursiveCharacterTextSplitter
from bot.core.knowledge.vector_db import get_vector_store
from langchain_core.documents import Document

def add_document(text: str, metadata: dict = None):
    """
    Ingests text into the vector database.

    Args:
        text (str): The text content to ingest.
        metadata (dict, optional): Metadata associated with the text. Defaults to None.
    """
    if metadata is None:
        metadata = {}

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )

    # split_text returns a list of strings
    chunks = text_splitter.split_text(text)

    # Create Document objects
    documents = [Document(page_content=chunk, metadata=metadata) for chunk in chunks]

    vector_store = get_vector_store()
    vector_store.add_documents(documents)

    return len(documents)
