"""Dummy MCP server with three medical research tools."""

import asyncio
from fastmcp import FastMCP
from loguru import logger

# Initialize FastMCP server
mcp = FastMCP("Medical Research Tools")


def _web_search_impl(query: str) -> dict:
    """
    Search the web for medical information.

    Args:
        query: Search query string

    Returns:
        Dictionary containing search results with titles, URLs, and snippets
    """
    logger.info(f"web_search called with query: {query}")

    # Mock search results
    results = [
        {
            "title": f"Clinical Guidelines for {query}",
            "url": f"https://medical-journal.com/articles/{query.replace(' ', '-').lower()}",
            "snippet": f"Comprehensive clinical guidelines for managing {query}. "
                      f"Evidence-based recommendations from leading medical experts.",
        },
        {
            "title": f"Recent Research on {query}",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/research-{query.replace(' ', '-').lower()}",
            "snippet": f"Latest peer-reviewed research findings on {query}. "
                      f"Meta-analysis of randomized controlled trials.",
        },
        {
            "title": f"{query}: Patient Education Guide",
            "url": f"https://healthinfo.org/guides/{query.replace(' ', '-').lower()}",
            "snippet": f"Patient-friendly overview of {query}, including symptoms, "
                      f"treatment options, and lifestyle recommendations.",
        },
        {
            "title": f"Clinical Trials for {query}",
            "url": f"https://clinicaltrials.gov/{query.replace(' ', '-').lower()}",
            "snippet": f"Current clinical trials investigating new treatments for {query}. "
                      f"Find ongoing studies and enrollment information.",
        },
    ]

    logger.debug(f"Returning {len(results)} search results")
    return {
        "query": query,
        "result_count": len(results),
        "results": results,
    }


@mcp.tool()
def web_search(query: str) -> dict:
    """Search the web for medical information."""
    return _web_search_impl(query)


def _medical_knowledge_impl(topic: str) -> dict:
    """
    Retrieve structured medical knowledge about a specific topic.

    Args:
        topic: Medical topic to research

    Returns:
        Dictionary containing definition, key points, and related terms
    """
    logger.info(f"medical_knowledge called with topic: {topic}")

    # Mock medical knowledge
    knowledge = {
        "topic": topic,
        "definition": f"{topic} is a medical condition characterized by specific "
                     f"physiological changes affecting patient health and wellbeing.",
        "key_points": [
            f"Prevalence: {topic} affects approximately 5-10% of the population",
            f"Risk Factors: Genetic predisposition, lifestyle factors, and environmental triggers",
            f"Diagnosis: Clinical examination, laboratory tests, and imaging studies",
            f"Treatment: Pharmacological interventions, lifestyle modifications, and monitoring",
            f"Prognosis: Generally favorable with early detection and appropriate management",
        ],
        "related_terms": [
            f"{topic} syndrome",
            f"Acute {topic}",
            f"Chronic {topic}",
            f"{topic} complications",
            f"{topic} prevention",
        ],
        "icd_10_code": "E11.9",  # Generic code for example
        "specialty": "Internal Medicine",
    }

    logger.debug(f"Returning knowledge data for: {topic}")
    return knowledge


@mcp.tool()
def medical_knowledge(topic: str) -> dict:
    """Retrieve structured medical knowledge about a specific topic."""
    return _medical_knowledge_impl(topic)


def _citation_generator_impl(topic: str, num_citations: int = 3) -> dict:
    """
    Generate formatted medical citations for a topic.

    Args:
        topic: Medical topic to generate citations for
        num_citations: Number of citations to generate (default: 3)

    Returns:
        Dictionary containing formatted citations
    """
    logger.info(f"citation_generator called for topic: {topic}, num_citations: {num_citations}")

    # Ensure we don't generate too many citations
    num_citations = min(num_citations, 10)

    # Mock citations
    citations = []
    authors = [
        ["Smith J", "Johnson M", "Williams R"],
        ["Brown A", "Davis K", "Miller L"],
        ["Wilson C", "Moore T", "Taylor S"],
        ["Anderson P", "Thomas H", "Jackson D"],
        ["White M", "Harris E", "Martin N"],
        ["Thompson G", "Garcia C", "Martinez A"],
        ["Robinson K", "Clark L", "Rodriguez M"],
        ["Lewis W", "Lee S", "Walker P"],
        ["Hall A", "Allen B", "Young C"],
        ["Hernandez D", "King E", "Wright F"],
    ]

    journals = [
        "New England Journal of Medicine",
        "The Lancet",
        "JAMA",
        "British Medical Journal",
        "Nature Medicine",
        "Annals of Internal Medicine",
        "Circulation",
        "Journal of Clinical Oncology",
        "American Journal of Respiratory and Critical Care Medicine",
        "Diabetes Care",
    ]

    for i in range(num_citations):
        year = 2020 + (i % 5)  # Years from 2020-2024
        author_set = authors[i % len(authors)]

        citation = {
            "id": i + 1,
            "authors": author_set,
            "year": year,
            "title": f"Clinical Management and Outcomes of {topic}: A Systematic Review",
            "journal": journals[i % len(journals)],
            "volume": 350 + i,
            "issue": (i % 12) + 1,
            "pages": f"{1000 + i * 10}-{1010 + i * 10}",
            "doi": f"10.1001/jama.{year}.{10000 + i}",
            "formatted_apa": None,  # Will be filled below
        }

        # Generate APA-style formatted citation
        authors_str = ", ".join(citation["authors"][:-1])
        if len(citation["authors"]) > 1:
            authors_str += f", & {citation['authors'][-1]}"
        else:
            authors_str = citation["authors"][0]

        citation["formatted_apa"] = (
            f"{authors_str}. ({citation['year']}). {citation['title']}. "
            f"{citation['journal']}, {citation['volume']}({citation['issue']}), "
            f"{citation['pages']}. https://doi.org/{citation['doi']}"
        )

        citations.append(citation)

    logger.debug(f"Generated {len(citations)} citations")
    return {
        "topic": topic,
        "citation_count": len(citations),
        "citations": citations,
    }


@mcp.tool()
def citation_generator(topic: str, num_citations: int = 3) -> dict:
    """Generate formatted medical citations for a topic."""
    return _citation_generator_impl(topic, num_citations)


def run_server(port: int = 8000):
    """
    Run the MCP server.

    Args:
        port: Port to run the server on
    """
    logger.info(f"Starting MCP server on port {port}")
    try:
        # Run the FastMCP server
        mcp.run(transport="http", port=port)
    except Exception as e:
        logger.error(f"Error running MCP server: {e}")
        raise


if __name__ == "__main__":
    # Import settings to get port configuration
    from src.config.settings import settings

    # Ensure logs directory exists
    from pathlib import Path
    Path("logs").mkdir(exist_ok=True)

    # Configure basic logging
    logger.add(
        "logs/mcp_server.log",
        rotation="10 MB",
        retention="3 days",
        level="DEBUG",
    )

    run_server(port=settings.mcp_server_port)
