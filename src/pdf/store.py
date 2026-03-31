"""ChromaDB-based document store with hybrid BM25 + vector retrieval."""

from uuid import UUID

import chromadb
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.chroma import ChromaVectorStore


COLLECTION_NAME = "pdf_chunks"


class DocumentStore:
    """Stores and retrieves PDF chunks using ChromaDB with hybrid search."""

    def __init__(self, persist_dir: str = "/app/data/chromadb"):
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
        )
        self._vector_store = ChromaVectorStore(chroma_collection=self._collection)
        self._storage_context = StorageContext.from_defaults(
            vector_store=self._vector_store
        )
        self._index = VectorStoreIndex.from_vector_store(
            vector_store=self._vector_store,
        )

    def add_chunks(
        self, conv_id: UUID, chunks: list[str], filename: str
    ) -> None:
        """Add text chunks to the store with conversation and file metadata."""
        if not chunks:
            return

        nodes = [
            TextNode(
                text=chunk,
                metadata={"conv_id": str(conv_id), "filename": filename},
            )
            for chunk in chunks
        ]

        self._index.insert_nodes(nodes)

    def query(
        self, conv_id: UUID, query_text: str, top_k: int = 5
    ) -> list[str]:
        """Hybrid retrieval: BM25 + vector via QueryFusionRetriever with RRF."""
        if not self.has_documents(conv_id):
            return []

        filters = MetadataFilters(
            filters=[MetadataFilter(key="conv_id", value=str(conv_id))]
        )

        vector_retriever = self._index.as_retriever(
            similarity_top_k=top_k, filters=filters
        )

        # BM25 retriever on nodes for this conversation
        conv_nodes = self._get_nodes(conv_id)
        bm25_retriever = BM25Retriever.from_defaults(
            nodes=conv_nodes, similarity_top_k=top_k
        )

        fusion_retriever = QueryFusionRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            mode=FUSION_MODES.RECIPROCAL_RANK,
            similarity_top_k=top_k,
            num_queries=1,
        )

        results = fusion_retriever.retrieve(query_text)
        return [node.text for node in results]

    def delete_by_conv_id(self, conv_id: UUID) -> None:
        """Delete all chunks belonging to a conversation."""
        self._collection.delete(where={"conv_id": str(conv_id)})

    def has_documents(self, conv_id: UUID) -> bool:
        """Check if any documents exist for a conversation."""
        results = self._collection.get(
            where={"conv_id": str(conv_id)}, limit=1
        )
        return len(results["ids"]) > 0

    def _get_nodes(self, conv_id: UUID) -> list[TextNode]:
        """Load all nodes for a conversation from ChromaDB."""
        results = self._collection.get(where={"conv_id": str(conv_id)})
        return [
            TextNode(text=doc, metadata=meta)
            for doc, meta in zip(
                results["documents"] or [],
                results["metadatas"] or [],
            )
        ]
