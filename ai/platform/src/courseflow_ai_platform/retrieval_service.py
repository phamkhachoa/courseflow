from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from courseflow_ai_platform.registry import (
    RegistryValidationError,
    load_yaml,
    require_list,
    require_str,
)
from courseflow_ai_platform.vector_index import (
    VectorIndexArtifact,
    build_vector_index,
    hybrid_rank_ids,
    tokenize,
    vector_rank,
)

RETRIEVAL_CATALOG_SCOPE = "internal:ai-platform:retrieval:catalog"
RETRIEVAL_SEARCH_SCOPE = "internal:ai-platform:retrieval:search"
RETRIEVAL_OPS_SCOPE = "internal:ai-platform:retrieval:ops"
RETRIEVAL_ROUTE_SCOPES = {
    ("GET", "/v1/retrieval/collections"): RETRIEVAL_CATALOG_SCOPE,
    ("POST", "/v1/retrieval/search"): RETRIEVAL_SEARCH_SCOPE,
    ("GET", "/v1/retrieval/health"): RETRIEVAL_OPS_SCOPE,
    ("GET", "/v1/retrieval/metrics"): RETRIEVAL_OPS_SCOPE,
}
RETRIEVAL_MODES = {"lexical", "vector", "hybrid"}


class RetrievalServiceError(ValueError):
    """Raised when retrieval service input or policy is invalid."""


@dataclass(frozen=True, slots=True)
class RetrievalPrincipal:
    principal_id: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...] = ()
    allowed_collection_ids: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> RetrievalPrincipal:
        return cls(
            principal_id=required_non_empty_str(row, "principal_id", "principalId"),
            scopes=normalize_string_tuple(row.get("scopes", row.get("scope"))),
            tenant_ids=normalize_string_tuple(row.get("tenant_ids", row.get("tenantIds"))),
            allowed_collection_ids=normalize_string_tuple(
                row.get(
                    "allowed_collection_ids",
                    row.get("allowedCollectionIds", row.get("collectionIds")),
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class RetrievalPrincipalGrant:
    principal_id: str
    owner_role: str
    product: str
    scopes: tuple[str, ...]
    tenant_ids: tuple[str, ...]
    allowed_collection_ids: tuple[str, ...]

    def resolve(self, requested_scopes: object | None = None) -> RetrievalPrincipal:
        scopes = (
            self.scopes
            if requested_scopes is None
            else normalize_string_tuple(requested_scopes)
        )
        missing_scopes = sorted(set(scopes) - set(self.scopes))
        if missing_scopes:
            raise RetrievalServiceError(
                f"principal {self.principal_id} requested ungranted scopes: "
                + ", ".join(missing_scopes)
            )
        return RetrievalPrincipal(
            principal_id=self.principal_id,
            scopes=scopes,
            tenant_ids=self.tenant_ids,
            allowed_collection_ids=self.allowed_collection_ids,
        )


@dataclass(frozen=True, slots=True)
class RetrievalAccessPolicy:
    policy_id: str
    principals: Mapping[str, RetrievalPrincipalGrant]
    wildcard_scopes_allowed: bool = False
    tenant_isolation_required: bool = True

    def resolve_principal(
        self,
        principal_id: str,
        requested_scopes: object | None = None,
    ) -> RetrievalPrincipal:
        grant = self.principals.get(principal_id)
        if grant is None:
            raise RetrievalServiceError(f"retrieval principal is not registered: {principal_id}")
        return grant.resolve(requested_scopes)


@dataclass(frozen=True, slots=True)
class RetrievalCollection:
    collection_id: str
    product: str
    use_case_id: str
    model_id: str
    index_id: str
    corpus_path: str
    collection_schema_path: str
    artifact_manifest_path: str
    top_k_default: int
    top_k_max: int
    min_similarity_for_rag: float
    artifact: VectorIndexArtifact
    chunks: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifactManifestPath": self.artifact_manifest_path,
            "chunkCount": len(self.chunks),
            "collectionId": self.collection_id,
            "collectionSchemaPath": self.collection_schema_path,
            "corpusPath": self.corpus_path,
            "embeddingDimensions": self.artifact.embedding_dimensions,
            "indexId": self.index_id,
            "minSimilarityForRag": self.min_similarity_for_rag,
            "modelId": self.model_id,
            "product": self.product,
            "topKDefault": self.top_k_default,
            "topKMax": self.top_k_max,
            "useCaseId": self.use_case_id,
        }


@dataclass(frozen=True, slots=True)
class RetrievalSearchRequest:
    collection_id: str
    tenant_id: str
    query: str
    mode: str = "hybrid"
    top_k: int | None = None
    lexical_weight: float = 0.60
    vector_weight: float = 0.40

    @classmethod
    def from_dict(cls, row: Mapping[str, Any]) -> RetrievalSearchRequest:
        return cls(
            collection_id=required_non_empty_str(row, "collection_id", "collectionId"),
            tenant_id=required_non_empty_str(row, "tenant_id", "tenantId"),
            query=required_non_empty_str(row, "query", "query"),
            mode=optional_str(row, "mode", "hybrid"),
            top_k=optional_positive_int(row, "top_k", "topK"),
            lexical_weight=optional_number(row, "lexical_weight", "lexicalWeight", 0.60),
            vector_weight=optional_number(row, "vector_weight", "vectorWeight", 0.40),
        )


@dataclass(frozen=True, slots=True)
class RetrievalSearchResult:
    chunk_id: str
    score: float
    lexical_score: float
    vector_score: float
    source_ref: str
    title: str
    text_snippet: str
    tenant_id: str
    access_scope: str
    pii_class: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accessScope": self.access_scope,
            "chunkId": self.chunk_id,
            "lexicalScore": self.lexical_score,
            "piiClass": self.pii_class,
            "score": self.score,
            "sourceRef": self.source_ref,
            "tenantId": self.tenant_id,
            "textSnippet": self.text_snippet,
            "title": self.title,
            "vectorScore": self.vector_score,
        }


@dataclass(frozen=True, slots=True)
class RetrievalSearchResponse:
    collection_id: str
    tenant_id: str
    query: str
    mode: str
    top_k: int
    result_count: int
    results: tuple[RetrievalSearchResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "collectionId": self.collection_id,
            "mode": self.mode,
            "query": self.query,
            "resultCount": self.result_count,
            "results": [result.to_dict() for result in self.results],
            "tenantId": self.tenant_id,
            "topK": self.top_k,
        }


@dataclass(frozen=True, slots=True)
class RetrievalMetricsSnapshot:
    request_count: int
    search_count: int
    error_count: int
    by_collection: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "byCollection": self.by_collection,
            "errorCount": self.error_count,
            "requestCount": self.request_count,
            "searchCount": self.search_count,
        }


class RetrievalMetrics:
    def __init__(self) -> None:
        self.request_count = 0
        self.search_count = 0
        self.error_count = 0
        self.by_collection: dict[str, int] = {}

    def record_search(self, collection_id: str) -> None:
        self.request_count += 1
        self.search_count += 1
        self.by_collection[collection_id] = self.by_collection.get(collection_id, 0) + 1

    def record_error(self) -> None:
        self.request_count += 1
        self.error_count += 1

    def snapshot(self) -> RetrievalMetricsSnapshot:
        return RetrievalMetricsSnapshot(
            request_count=self.request_count,
            search_count=self.search_count,
            error_count=self.error_count,
            by_collection=dict(sorted(self.by_collection.items())),
        )


class RetrievalRuntime:
    """Tenant-scoped lexical/vector/hybrid retrieval over registered vector artifacts."""

    def __init__(self, ai_root: Path | str) -> None:
        self.ai_root = Path(ai_root)
        self.collections = load_retrieval_collections(self.ai_root)
        self.metrics = RetrievalMetrics()

    def catalog(self) -> tuple[RetrievalCollection, ...]:
        return tuple(self.collections.values())

    def search(
        self,
        request: RetrievalSearchRequest | Mapping[str, Any],
        principal: RetrievalPrincipal | Mapping[str, Any] | None = None,
    ) -> RetrievalSearchResponse:
        search_request = (
            request
            if isinstance(request, RetrievalSearchRequest)
            else RetrievalSearchRequest.from_dict(request)
        )
        try:
            response = self._search(search_request, normalize_principal(principal))
        except Exception:
            self.metrics.record_error()
            raise
        self.metrics.record_search(search_request.collection_id)
        return response

    def health(self) -> dict[str, Any]:
        return {
            "collectionCount": len(self.collections),
            "chunkCount": sum(len(collection.chunks) for collection in self.collections.values()),
            "serviceStatus": "healthy" if self.collections else "no_collections",
        }

    def snapshot_metrics(self) -> RetrievalMetricsSnapshot:
        return self.metrics.snapshot()

    def _search(
        self,
        request: RetrievalSearchRequest,
        principal: RetrievalPrincipal | None,
    ) -> RetrievalSearchResponse:
        if request.mode not in RETRIEVAL_MODES:
            raise RetrievalServiceError(
                "retrieval mode must be one of: " + ", ".join(sorted(RETRIEVAL_MODES))
            )
        collection = self.collections.get(request.collection_id)
        if collection is None:
            raise RetrievalServiceError(f"unknown retrieval collection: {request.collection_id}")
        authorize_retrieval_search(principal, request)
        top_k = request.top_k or collection.top_k_default
        if top_k <= 0 or top_k > collection.top_k_max:
            raise RetrievalServiceError(
                f"top_k must be between 1 and {collection.top_k_max} for {collection.collection_id}"
            )

        lexical_ranked = lexical_rank(
            request.query,
            list(collection.chunks),
            request.tenant_id,
            top_k,
        )
        lexical_scores = {chunk_id: score for score, chunk_id, _ in lexical_ranked}
        vector_ranked = vector_rank(request.query, collection.artifact, request.tenant_id, top_k)
        vector_scores = {result.chunk_id: result.score for result in vector_ranked}

        if request.mode == "lexical":
            ranked_ids = tuple(chunk_id for _, chunk_id, _ in lexical_ranked)
        elif request.mode == "vector":
            ranked_ids = tuple(result.chunk_id for result in vector_ranked)
        else:
            ranked_ids = hybrid_rank_ids(
                lexical_scores,
                vector_ranked,
                k=top_k,
                lexical_weight=request.lexical_weight,
                vector_weight=request.vector_weight,
            )

        chunk_by_id = {
            require_str(chunk, "chunk_id", "retrieval chunk"): chunk
            for chunk in collection.chunks
        }
        results = tuple(
            build_search_result(
                chunk_by_id[chunk_id],
                lexical_score=lexical_scores.get(chunk_id, 0.0),
                vector_score=vector_scores.get(chunk_id, 0.0),
                mode=request.mode,
                lexical_weight=request.lexical_weight,
                vector_weight=request.vector_weight,
            )
            for chunk_id in ranked_ids
            if chunk_id in chunk_by_id
            and is_chunk_allowed_for_tenant(chunk_by_id[chunk_id], request.tenant_id)
        )
        return RetrievalSearchResponse(
            collection_id=request.collection_id,
            tenant_id=request.tenant_id,
            query=request.query,
            mode=request.mode,
            top_k=top_k,
            result_count=len(results),
            results=results,
        )


def load_retrieval_collections(root: Path) -> dict[str, RetrievalCollection]:
    result: dict[str, RetrievalCollection] = {}
    manifest_dir = root / "platform" / "artifacts" / "manifests"
    for manifest_path in sorted(manifest_dir.glob("*-vector-index-baseline-v1.yaml")):
        manifest = load_yaml(manifest_path)
        if manifest.get("artifact_type") != "vector_index_snapshot":
            continue
        lineage = require_mapping(manifest, "lineage", str(manifest_path))
        corpus_path = require_str(lineage, "corpus", f"{manifest_path} lineage")
        collection_schema_path = require_str(
            lineage,
            "collection_schema",
            f"{manifest_path} lineage",
        )
        corpus = load_yaml(root / corpus_path)
        schema = load_yaml(root / collection_schema_path)
        collection_id = require_str(corpus, "collection", "retrieval corpus")
        model_id = require_str(manifest, "model_id", str(manifest_path))
        artifact = build_vector_index(
            corpus,
            schema,
            index_id=model_id,
            model_id=model_id,
            algorithm=require_str(manifest, "algorithm", str(manifest_path)),
        )
        serving = require_mapping(schema, "serving", f"{collection_schema_path} schema")
        result[collection_id] = RetrievalCollection(
            collection_id=collection_id,
            product=require_str(manifest, "product", str(manifest_path)),
            use_case_id=require_str(manifest, "use_case_id", str(manifest_path)),
            model_id=model_id,
            index_id=artifact.index_id,
            corpus_path=corpus_path,
            collection_schema_path=collection_schema_path,
            artifact_manifest_path=str(manifest_path.relative_to(root)),
            top_k_default=require_positive_int(serving, "top_k_default", "retrieval serving"),
            top_k_max=require_positive_int(serving, "top_k_max", "retrieval serving"),
            min_similarity_for_rag=require_float(
                serving,
                "min_similarity_for_rag",
                "retrieval serving",
            ),
            artifact=artifact,
            chunks=tuple(require_list(corpus, "chunks", "retrieval corpus")),
        )
    return dict(sorted(result.items()))


def load_retrieval_access_policy(ai_root: Path | str) -> RetrievalAccessPolicy:
    root = Path(ai_root)
    policy_path = root / "platform" / "governance" / "policies" / "retrieval-access-policy.yaml"
    policy = load_yaml(policy_path)
    raw_scope_aliases = policy.get("scope_aliases", {})
    if not isinstance(raw_scope_aliases, dict):
        raise RegistryValidationError(f"{policy_path} must define mapping field scope_aliases")
    scope_aliases = {
        "catalog": RETRIEVAL_CATALOG_SCOPE,
        "search": RETRIEVAL_SEARCH_SCOPE,
        "ops": RETRIEVAL_OPS_SCOPE,
        **raw_scope_aliases,
    }
    grants: dict[str, RetrievalPrincipalGrant] = {}
    for row in require_mapping_list(policy, "principals", policy_path):
        principal_id = require_str(row, "principal_id", str(policy_path))
        if principal_id in grants:
            raise RegistryValidationError(f"{policy_path} duplicates principal: {principal_id}")
        grants[principal_id] = RetrievalPrincipalGrant(
            principal_id=principal_id,
            owner_role=require_str(row, "owner_role", str(policy_path)),
            product=require_str(row, "product", str(policy_path)),
            scopes=tuple(
                sorted(
                    {
                        expand_scope_alias(scope, scope_aliases, policy_path)
                        for scope in normalize_string_tuple(row.get("scopes", []))
                    }
                )
            ),
            tenant_ids=tuple(sorted(normalize_string_tuple(row.get("tenant_ids", [])))),
            allowed_collection_ids=tuple(
                sorted(normalize_string_tuple(row.get("collection_ids", [])))
            ),
        )
    return RetrievalAccessPolicy(
        policy_id=require_str(policy, "policy_id", str(policy_path)),
        principals=dict(sorted(grants.items())),
        wildcard_scopes_allowed=bool(
            policy.get("defaults", {}).get("wildcard_scopes_allowed", False)
        ),
        tenant_isolation_required=bool(
            policy.get("defaults", {}).get("tenant_isolation_required", True)
        ),
    )


def authorize_retrieval_search(
    principal: RetrievalPrincipal | None,
    request: RetrievalSearchRequest,
) -> None:
    if principal is None:
        return
    if "*" in principal.scopes:
        raise RetrievalServiceError("wildcard retrieval scopes are forbidden")
    if RETRIEVAL_SEARCH_SCOPE not in principal.scopes:
        raise RetrievalServiceError("retrieval search scope is required")
    if principal.tenant_ids and request.tenant_id not in principal.tenant_ids:
        raise RetrievalServiceError("retrieval tenant is not granted to principal")
    if (
        principal.allowed_collection_ids
        and request.collection_id not in principal.allowed_collection_ids
    ):
        raise RetrievalServiceError("retrieval collection is not granted to principal")


def build_search_result(
    chunk: Mapping[str, Any],
    *,
    lexical_score: float,
    vector_score: float,
    mode: str,
    lexical_weight: float,
    vector_weight: float,
) -> RetrievalSearchResult:
    if mode == "lexical":
        score = lexical_score
    elif mode == "vector":
        score = vector_score
    else:
        score = lexical_weight * lexical_score + vector_weight * vector_score
    return RetrievalSearchResult(
        chunk_id=require_str(chunk, "chunk_id", "retrieval chunk"),
        score=round(score, 8),
        lexical_score=round(lexical_score, 8),
        vector_score=round(vector_score, 8),
        source_ref=require_str(chunk, "source_ref", "retrieval chunk"),
        title=require_str(chunk, "title", "retrieval chunk"),
        text_snippet=truncate_text(require_str(chunk, "text", "retrieval chunk")),
        tenant_id=require_str(chunk, "tenant_id", "retrieval chunk"),
        access_scope=require_str(chunk, "access_scope", "retrieval chunk"),
        pii_class=require_str(chunk, "pii_class", "retrieval chunk"),
    )


def lexical_rank(
    query_text: str,
    chunks: list[dict[str, Any]],
    tenant_id: str,
    k: int,
) -> list[tuple[float, str, dict[str, Any]]]:
    query_tokens = set(tokenize(query_text))
    scored: list[tuple[float, str, dict[str, Any]]] = []
    for chunk in chunks:
        if not is_chunk_allowed_for_tenant(chunk, tenant_id):
            continue
        chunk_id = require_str(chunk, "chunk_id", "retrieval chunk")
        document_tokens = set(
            tokenize(
                " ".join(
                    [
                        require_str(chunk, "title", "retrieval chunk"),
                        require_str(chunk, "text", "retrieval chunk"),
                        " ".join(normalize_string_tuple(chunk.get("tags", []))),
                    ]
                )
            )
        )
        score = lexical_score(query_tokens, document_tokens)
        if score > 0:
            scored.append((score, chunk_id, chunk))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return scored[:k]


def lexical_score(query_tokens: set[str], document_tokens: set[str]) -> float:
    if not query_tokens or not document_tokens:
        return 0.0
    return len(query_tokens & document_tokens) / len(query_tokens)


def is_chunk_allowed_for_tenant(chunk: Mapping[str, Any], tenant_id: str) -> bool:
    access_scope = require_str(chunk, "access_scope", "retrieval chunk")
    chunk_tenant_id = require_str(chunk, "tenant_id", "retrieval chunk")
    if access_scope == "public" and chunk_tenant_id == "global":
        return True
    return chunk_tenant_id == tenant_id


def normalize_principal(
    principal: RetrievalPrincipal | Mapping[str, Any] | None,
) -> RetrievalPrincipal | None:
    if principal is None or isinstance(principal, RetrievalPrincipal):
        return principal
    return RetrievalPrincipal.from_dict(principal)


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise RetrievalServiceError("retrieval policy values must be strings or lists")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RetrievalServiceError("retrieval policy list values must be non-empty strings")
        result.append(item.strip())
    return tuple(result)


def expand_scope_alias(
    scope: str,
    scope_aliases: Mapping[str, str],
    policy_path: Path,
) -> str:
    expanded = scope_aliases.get(scope, scope)
    if not expanded.startswith("internal:ai-platform:retrieval:"):
        raise RegistryValidationError(f"{policy_path} has unsupported retrieval scope: {scope}")
    return expanded


def required_non_empty_str(row: Mapping[str, Any], snake_key: str, camel_key: str) -> str:
    value = row.get(snake_key, row.get(camel_key))
    if not isinstance(value, str) or not value.strip():
        raise RetrievalServiceError(f"retrieval request must define {snake_key} or {camel_key}")
    return value.strip()


def optional_str(row: Mapping[str, Any], key: str, default: str) -> str:
    value = row.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise RetrievalServiceError(f"retrieval request field {key} must be a string")
    return value.strip()


def optional_positive_int(row: Mapping[str, Any], snake_key: str, camel_key: str) -> int | None:
    value = row.get(snake_key, row.get(camel_key))
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RetrievalServiceError(f"retrieval request field {snake_key} must be positive")
    return value


def optional_number(
    row: Mapping[str, Any],
    snake_key: str,
    camel_key: str,
    default: float,
) -> float:
    value = row.get(snake_key, row.get(camel_key, default))
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise RetrievalServiceError(f"retrieval request field {snake_key} must be numeric")
    return float(value)


def require_mapping(row: Mapping[str, Any], key: str, owner: str) -> dict[str, Any]:
    value = row.get(key)
    if not isinstance(value, dict):
        raise RegistryValidationError(f"{owner} must define mapping field {key}")
    return value


def require_mapping_list(row: Mapping[str, Any], key: str, path: Path) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{path} must define list field {key}")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{path} {key} must contain mappings")
        result.append(item)
    return result


def require_positive_int(row: Mapping[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise RegistryValidationError(f"{owner} must define positive integer {key}")
    return value


def require_float(row: Mapping[str, Any], key: str, owner: str) -> float:
    value = row.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise RegistryValidationError(f"{owner} must define numeric field {key}")
    return float(value)


def truncate_text(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
