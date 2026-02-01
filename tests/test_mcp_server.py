"""Tests for MCP server tools."""

import pytest

# Import the implementation functions directly
from src.mcp_server.server import (
    _web_search_impl as web_search,
    _medical_knowledge_impl as medical_knowledge,
    _citation_generator_impl as citation_generator,
)


def test_web_search():
    """Test web_search tool."""
    query = "diabetes management"
    result = web_search(query)

    assert result["query"] == query
    assert result["result_count"] == 4
    assert len(result["results"]) == 4

    # Check first result structure
    first_result = result["results"][0]
    assert "title" in first_result
    assert "url" in first_result
    assert "snippet" in first_result
    assert "diabetes management" in first_result["title"].lower()


def test_web_search_different_query():
    """Test web_search with different query."""
    query = "hypertension treatment"
    result = web_search(query)

    assert result["query"] == query
    assert result["result_count"] > 0

    for item in result["results"]:
        assert isinstance(item["title"], str)
        assert isinstance(item["url"], str)
        assert isinstance(item["snippet"], str)


def test_medical_knowledge():
    """Test medical_knowledge tool."""
    topic = "diabetes"
    result = medical_knowledge(topic)

    assert result["topic"] == topic
    assert "definition" in result
    assert "key_points" in result
    assert "related_terms" in result
    assert "icd_10_code" in result
    assert "specialty" in result

    # Check key points is a list
    assert isinstance(result["key_points"], list)
    assert len(result["key_points"]) > 0

    # Check related terms is a list
    assert isinstance(result["related_terms"], list)
    assert len(result["related_terms"]) > 0


def test_medical_knowledge_different_topic():
    """Test medical_knowledge with different topic."""
    topic = "heart disease"
    result = medical_knowledge(topic)

    assert result["topic"] == topic
    assert len(result["key_points"]) >= 5
    assert len(result["related_terms"]) >= 5


def test_citation_generator_default():
    """Test citation_generator with default number of citations."""
    topic = "cancer research"
    result = citation_generator(topic)

    assert result["topic"] == topic
    assert result["citation_count"] == 3
    assert len(result["citations"]) == 3


def test_citation_generator_custom_count():
    """Test citation_generator with custom citation count."""
    topic = "alzheimer's disease"
    num_citations = 5
    result = citation_generator(topic, num_citations)

    assert result["topic"] == topic
    assert result["citation_count"] == num_citations
    assert len(result["citations"]) == num_citations


def test_citation_generator_max_limit():
    """Test citation_generator respects maximum limit."""
    topic = "covid-19"
    num_citations = 15  # Request more than max (10)
    result = citation_generator(topic, num_citations)

    assert result["citation_count"] <= 10
    assert len(result["citations"]) <= 10


def test_citation_structure():
    """Test structure of generated citations."""
    result = citation_generator("medical topic", 2)

    for citation in result["citations"]:
        assert "id" in citation
        assert "authors" in citation
        assert isinstance(citation["authors"], list)
        assert len(citation["authors"]) > 0
        assert "year" in citation
        assert "title" in citation
        assert "journal" in citation
        assert "volume" in citation
        assert "issue" in citation
        assert "pages" in citation
        assert "doi" in citation
        assert "formatted_apa" in citation
        assert isinstance(citation["formatted_apa"], str)


def test_citation_apa_format():
    """Test APA formatting of citations."""
    result = citation_generator("test topic", 1)
    citation = result["citations"][0]

    apa = citation["formatted_apa"]

    # Check APA format contains required elements
    assert str(citation["year"]) in apa
    assert citation["title"] in apa
    assert citation["journal"] in apa
    assert str(citation["volume"]) in apa
    assert str(citation["issue"]) in apa
    assert citation["doi"] in apa


def test_citation_different_years():
    """Test that citations have different years."""
    result = citation_generator("test", 5)

    years = [c["year"] for c in result["citations"]]
    # Should have at least some variation (not all same year)
    assert len(set(years)) > 1


def test_citation_different_journals():
    """Test that citations reference different journals."""
    result = citation_generator("test", 5)

    journals = [c["journal"] for c in result["citations"]]
    # Should have at least some variation
    assert len(set(journals)) > 1
