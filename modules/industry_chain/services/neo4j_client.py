from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from neo4j import GraphDatabase

from modules.industry_chain.config import NEO4J_DATABASE, NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_read_query(cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with get_driver().session(database=NEO4J_DATABASE) as session:
        result = session.run(cypher, parameters or {})
        return [dict(record) for record in result]


def verify_connectivity() -> None:
    get_driver().verify_connectivity()


def first_text(value: Any, fallback: str = '') -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes, bytearray)):
        for item in value:
            text = first_text(item, '')
            if text:
                return text
        return fallback
    return str(value)
