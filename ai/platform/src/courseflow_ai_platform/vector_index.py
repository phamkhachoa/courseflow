from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from courseflow_ai_platform.registry import RegistryValidationError, require_str

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+-]*")
SUPPORTED_ACCESS_SCOPES = {"public", "tenant"}
DEFAULT_INDEX_ALGORITHM = "deterministic_hash_embedding_baseline_v1"


@dataclass(frozen=True, slots=True)
class VectorIndexEntry:
    chunk_id: str
    tenant_id: str
    source_ref: str
    access_scope: str
    pii_class: str
    text_hash: str
    vector: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accessScope": self.access_scope,
            "chunkId": self.chunk_id,
            "piiClass": self.pii_class,
            "sourceRef": self.source_ref,
            "tenantId": self.tenant_id,
            "textHash": self.text_hash,
            "vector": self.vector,
        }


@dataclass(frozen=True, slots=True)
class VectorIndexArtifact:
    index_id: str
    model_id: str
    collection: str
    product: str
    algorithm: str
    distance: str
    embedding_dimensions: int
    entries: tuple[VectorIndexEntry, ...]
    checksum: str

    @property
    def chunk_count(self) -> int:
        return len(self.entries)

    def to_dict(self, include_vectors: bool = False) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []
        for entry in self.entries:
            row = entry.to_dict()
            if not include_vectors:
                row = {key: value for key, value in row.items() if key != "vector"}
            entries.append(row)
        return {
            "algorithm": self.algorithm,
            "checksum": self.checksum,
            "chunkCount": self.chunk_count,
            "collection": self.collection,
            "distance": self.distance,
            "embeddingDimensions": self.embedding_dimensions,
            "entries": entries,
            "indexId": self.index_id,
            "modelId": self.model_id,
            "product": self.product,
        }


@dataclass(frozen=True, slots=True)
class VectorIndexContractMetrics:
    chunk_count: int
    indexed_chunk_count: int
    embedding_dimensions: int
    chunk_coverage_rate: float
    dimension_conformance_rate: float
    metadata_conformance_rate: float
    tenant_scope_coverage_rate: float
    checksum_stable: bool
    passed: bool

    def to_dict(self) -> dict[str, bool | float | int]:
        return {
            "checksumStable": self.checksum_stable,
            "chunkCount": self.chunk_count,
            "chunkCoverageRate": self.chunk_coverage_rate,
            "dimensionConformanceRate": self.dimension_conformance_rate,
            "embeddingDimensions": self.embedding_dimensions,
            "indexedChunkCount": self.indexed_chunk_count,
            "metadataConformanceRate": self.metadata_conformance_rate,
            "tenantScopeCoverageRate": self.tenant_scope_coverage_rate,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    chunk_id: str
    score: float
    entry: VectorIndexEntry


def build_vector_index(
    corpus: Mapping[str, Any],
    collection_schema: Mapping[str, Any],
    *,
    index_id: str,
    model_id: str,
    algorithm: str = DEFAULT_INDEX_ALGORITHM,
) -> VectorIndexArtifact:
    collection = require_str(dict(corpus), "collection", "vector index corpus")
    schema_collection = require_str(
        dict(collection_schema),
        "collection",
        "vector collection schema",
    )
    if collection != schema_collection:
        raise RegistryValidationError(
            f"vector index corpus collection {collection} does not match {schema_collection}"
        )

    product = require_str(dict(corpus), "product", "vector index corpus")
    schema_product = require_str(dict(collection_schema), "product", "vector collection schema")
    if product != schema_product:
        raise RegistryValidationError(
            f"vector index corpus product {product} does not match {schema_product}"
        )

    embedding_config = require_mapping(collection_schema, "embedding", "vector collection schema")
    dimensions = require_positive_int(embedding_config, "dimensions", "embedding config")
    distance = require_str(dict(embedding_config), "distance", "embedding config")
    chunks = require_mapping_list(corpus, "chunks", "vector index corpus")

    entries = tuple(
        build_vector_index_entry(chunk, dimensions)
        for chunk in sorted(chunks, key=lambda row: require_str(row, "chunk_id", "chunk"))
    )
    validate_unique_chunk_ids(entries)
    checksum = vector_index_checksum(
        index_id=index_id,
        model_id=model_id,
        collection=collection,
        product=product,
        algorithm=algorithm,
        distance=distance,
        embedding_dimensions=dimensions,
        entries=entries,
    )

    return VectorIndexArtifact(
        index_id=index_id,
        model_id=model_id,
        collection=collection,
        product=product,
        algorithm=algorithm,
        distance=distance,
        embedding_dimensions=dimensions,
        entries=entries,
        checksum=checksum,
    )


def build_vector_index_entry(chunk: Mapping[str, Any], dimensions: int) -> VectorIndexEntry:
    chunk_id = require_str(dict(chunk), "chunk_id", "vector index chunk")
    tenant_id = require_str(dict(chunk), "tenant_id", f"vector index chunk {chunk_id}")
    source_ref = require_str(dict(chunk), "source_ref", f"vector index chunk {chunk_id}")
    access_scope = require_str(dict(chunk), "access_scope", f"vector index chunk {chunk_id}")
    pii_class = require_str(dict(chunk), "pii_class", f"vector index chunk {chunk_id}")
    title = require_str(dict(chunk), "title", f"vector index chunk {chunk_id}")
    text = require_str(dict(chunk), "text", f"vector index chunk {chunk_id}")
    tags = require_optional_string_list(chunk, "tags", f"vector index chunk {chunk_id}")
    vector_text = " ".join([title, text, *tags])

    return VectorIndexEntry(
        chunk_id=chunk_id,
        tenant_id=tenant_id,
        source_ref=source_ref,
        access_scope=access_scope,
        pii_class=pii_class,
        text_hash=sha256_text(vector_text),
        vector=hash_embed_text(vector_text, dimensions),
    )


def validate_vector_index_contract(
    artifact: VectorIndexArtifact,
    corpus: Mapping[str, Any],
    collection_schema: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> VectorIndexContractMetrics:
    expected_chunks = require_mapping_list(corpus, "chunks", "vector index corpus")
    expected_dimensions = require_positive_int(
        require_mapping(collection_schema, "embedding", "vector collection schema"),
        "dimensions",
        "embedding config",
    )
    expected_chunk_count = len(expected_chunks)
    indexed_ids = {entry.chunk_id for entry in artifact.entries}
    expected_ids = {
        require_str(chunk, "chunk_id", "vector index corpus chunk") for chunk in expected_chunks
    }

    dimension_conforming = sum(
        1
        for entry in artifact.entries
        if len(entry.vector) == expected_dimensions and vector_has_unit_norm(entry.vector)
    )
    metadata_conforming = sum(1 for entry in artifact.entries if entry_metadata_conforms(entry))
    tenant_scope_conforming = sum(
        1
        for entry in artifact.entries
        if entry.tenant_id and entry.access_scope in SUPPORTED_ACCESS_SCOPES
    )
    stable_rebuild = build_vector_index(
        corpus,
        collection_schema,
        index_id=artifact.index_id,
        model_id=artifact.model_id,
        algorithm=artifact.algorithm,
    )

    chunk_coverage_rate = ratio(len(indexed_ids & expected_ids), expected_chunk_count)
    dimension_conformance_rate = ratio(dimension_conforming, expected_chunk_count)
    metadata_conformance_rate = ratio(metadata_conforming, expected_chunk_count)
    tenant_scope_coverage_rate = ratio(tenant_scope_conforming, expected_chunk_count)
    checksum_stable = stable_rebuild.checksum == artifact.checksum
    passed = (
        chunk_coverage_rate
        >= require_threshold(thresholds, "chunk_coverage_min", "vector index thresholds")
        and dimension_conformance_rate
        >= require_threshold(thresholds, "dimension_conformance_min", "vector index thresholds")
        and metadata_conformance_rate
        >= require_threshold(thresholds, "metadata_conformance_min", "vector index thresholds")
        and tenant_scope_coverage_rate
        >= require_threshold(thresholds, "tenant_scope_coverage_min", "vector index thresholds")
        and checksum_stable
    )

    return VectorIndexContractMetrics(
        chunk_count=expected_chunk_count,
        indexed_chunk_count=len(indexed_ids),
        embedding_dimensions=expected_dimensions,
        chunk_coverage_rate=round(chunk_coverage_rate, 6),
        dimension_conformance_rate=round(dimension_conformance_rate, 6),
        metadata_conformance_rate=round(metadata_conformance_rate, 6),
        tenant_scope_coverage_rate=round(tenant_scope_coverage_rate, 6),
        checksum_stable=checksum_stable,
        passed=passed,
    )


def hash_embed_text(text: str, dimensions: int) -> tuple[float, ...]:
    if dimensions <= 0:
        raise RegistryValidationError("hash embedding dimensions must be positive")
    tokens = tokenize(text)
    if not tokens:
        raise RegistryValidationError("hash embedding text must contain tokens")

    values = [0.0] * dimensions
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        values[bucket] += sign

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise RegistryValidationError("hash embedding produced zero vector")
    return tuple(round(value / norm, 8) for value in values)


def vector_rank(
    query_text: str,
    artifact: VectorIndexArtifact,
    tenant_id: str,
    k: int,
) -> tuple[VectorSearchResult, ...]:
    query_vector = hash_embed_text(query_text, artifact.embedding_dimensions)
    results: list[VectorSearchResult] = []
    for entry in artifact.entries:
        if not is_entry_allowed_for_tenant(entry, tenant_id):
            continue
        score = cosine_similarity(query_vector, entry.vector)
        if score > 0:
            results.append(
                VectorSearchResult(
                    chunk_id=entry.chunk_id,
                    score=round(score, 8),
                    entry=entry,
                )
            )

    results.sort(key=lambda result: (-result.score, result.chunk_id))
    return tuple(results[:k])


def hybrid_rank_ids(
    lexical_scores_by_chunk: Mapping[str, float],
    vector_results: tuple[VectorSearchResult, ...],
    *,
    k: int,
    lexical_weight: float = 0.60,
    vector_weight: float = 0.40,
) -> tuple[str, ...]:
    if k <= 0:
        raise RegistryValidationError("hybrid retrieval k must be positive")
    if lexical_weight < 0 or vector_weight < 0 or lexical_weight + vector_weight <= 0:
        raise RegistryValidationError("hybrid retrieval weights must be non-negative")

    max_lexical = max(lexical_scores_by_chunk.values(), default=0.0)
    max_vector = max((result.score for result in vector_results), default=0.0)
    chunk_ids = set(lexical_scores_by_chunk) | {result.chunk_id for result in vector_results}
    vector_scores_by_chunk = {result.chunk_id: result.score for result in vector_results}

    scored: list[tuple[float, str]] = []
    for chunk_id in chunk_ids:
        lexical_score = lexical_scores_by_chunk.get(chunk_id, 0.0)
        vector_score = vector_scores_by_chunk.get(chunk_id, 0.0)
        normalized_lexical = lexical_score / max_lexical if max_lexical > 0 else 0.0
        normalized_vector = vector_score / max_vector if max_vector > 0 else 0.0
        score = lexical_weight * normalized_lexical + vector_weight * normalized_vector
        scored.append((score, chunk_id))

    scored.sort(key=lambda row: (-row[0], row[1]))
    return tuple(chunk_id for _, chunk_id in scored[:k])


def cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise RegistryValidationError("cosine similarity vectors must have matching dimensions")
    return sum(
        left_value * right_value for left_value, right_value in zip(left, right, strict=True)
    )


def is_entry_allowed_for_tenant(entry: VectorIndexEntry, tenant_id: str) -> bool:
    if entry.access_scope == "public" and entry.tenant_id == "global":
        return True
    return entry.tenant_id == tenant_id


def vector_index_checksum(
    *,
    index_id: str,
    model_id: str,
    collection: str,
    product: str,
    algorithm: str,
    distance: str,
    embedding_dimensions: int,
    entries: tuple[VectorIndexEntry, ...],
) -> str:
    payload = {
        "algorithm": algorithm,
        "collection": collection,
        "distance": distance,
        "embeddingDimensions": embedding_dimensions,
        "entries": [entry.to_dict() for entry in entries],
        "indexId": index_id,
        "modelId": model_id,
        "product": product,
    }
    return sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def tokenize(text: str) -> tuple[str, ...]:
    return tuple(token.lower() for token in TOKEN_PATTERN.findall(text))


def vector_has_unit_norm(vector: tuple[float, ...]) -> bool:
    norm = math.sqrt(sum(value * value for value in vector))
    return 0.999999 <= norm <= 1.000001


def entry_metadata_conforms(entry: VectorIndexEntry) -> bool:
    return all(
        (
            bool(entry.chunk_id),
            bool(entry.tenant_id),
            bool(entry.source_ref),
            bool(entry.access_scope),
            bool(entry.pii_class),
            len(entry.text_hash) == 64,
        )
    )


def validate_unique_chunk_ids(entries: tuple[VectorIndexEntry, ...]) -> None:
    ids = [entry.chunk_id for entry in entries]
    if len(ids) != len(set(ids)):
        raise RegistryValidationError("vector index contains duplicate chunk_id")


def require_mapping(row: Mapping[str, Any], key: str, owner: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise RegistryValidationError(f"{owner} must define mapping field {key}")
    return value


def require_mapping_list(row: Mapping[str, Any], key: str, owner: str) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def require_optional_string_list(row: Mapping[str, Any], key: str, owner: str) -> list[str]:
    value = row.get(key, [])
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} {key} must contain strings")
        result.append(item.strip())
    return result


def require_positive_int(row: Mapping[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RegistryValidationError(f"{owner} must define positive integer field {key}")
    return value


def require_threshold(row: Mapping[str, Any], key: str, owner: str) -> float:
    value = row.get(key)
    if not isinstance(value, int | float):
        raise RegistryValidationError(f"{owner} must define numeric field {key}")
    return float(value)


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
