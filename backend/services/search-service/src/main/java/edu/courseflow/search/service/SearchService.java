package edu.courseflow.search.service;

import co.elastic.clients.elasticsearch._types.query_dsl.Query;
import co.elastic.clients.elasticsearch._types.query_dsl.TextQueryType;
import edu.courseflow.search.dto.SearchDtos.CourseRecommendationDto;
import edu.courseflow.search.dto.SearchDtos.CourseSearchDto;
import edu.courseflow.search.dto.SearchDtos.CourseSearchPageDto;
import edu.courseflow.search.dto.SearchDtos.IndexCourseRequestDto;
import edu.courseflow.search.mapper.SearchMapper;
import edu.courseflow.search.model.CourseSearchDocument;
import edu.courseflow.search.repository.CourseSearchRepository;
import java.util.List;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.elasticsearch.client.elc.NativeQuery;
import org.springframework.data.elasticsearch.client.elc.NativeQueryBuilder;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.SearchHits;
import org.springframework.stereotype.Service;

/**
 * Public course search and indexing.
 *
 * <p>Search is executed by Elasticsearch via a {@link NativeQuery}: a {@code multi_match} across the
 * analyzed text fields, wrapped in a {@code bool} query whose {@code filter} clause restricts results
 * to {@code status = PUBLISHED}. This replaces the previous approach of loading every PUBLISHED course
 * and filtering with Java {@code String.contains()}, which defeated Elasticsearch, did no real
 * relevance ranking, and could not paginate.
 */
@Service
public class SearchService {

    /** Bound the page size so a caller cannot ask Elasticsearch for an unbounded result window. */
    static final int MAX_PAGE_SIZE = 100;
    static final int DEFAULT_PAGE_SIZE = 20;
    static final int MAX_SUGGESTION_SIZE = 10;
    static final int DEFAULT_SUGGESTION_SIZE = 6;
    private static final String STATUS_PUBLISHED = "PUBLISHED";

    private final CourseSearchRepository courses;
    private final ElasticsearchOperations elasticsearch;
    private final SearchMapper mapper;

    public SearchService(CourseSearchRepository courses, ElasticsearchOperations elasticsearch, SearchMapper mapper) {
        this.courses = courses;
        this.elasticsearch = elasticsearch;
        this.mapper = mapper;
    }

    public CourseSearchPageDto searchPublicCourses(String query, int page, int size) {
        Pageable pageable = toPageable(page, size);
        NativeQuery nativeQuery = buildPublicQuery(query, pageable);
        SearchHits<CourseSearchDocument> hits = elasticsearch.search(nativeQuery, CourseSearchDocument.class);
        List<CourseSearchDto> content = hits.getSearchHits().stream()
                .map(hit -> mapper.toDto(hit.getContent()))
                .toList();
        return new CourseSearchPageDto(content, hits.getTotalHits(), pageable.getPageNumber(), pageable.getPageSize());
    }

    public List<CourseSearchDto> suggestPublicCourses(String query, int limit) {
        NativeQuery nativeQuery = buildSuggestQuery(query, toSuggestionPageable(limit));
        SearchHits<CourseSearchDocument> hits = elasticsearch.search(nativeQuery, CourseSearchDocument.class);
        return hits.getSearchHits().stream()
                .map(hit -> mapper.toDto(hit.getContent()))
                .toList();
    }

    public List<CourseRecommendationDto> recommendPublicCourses(String query, String level, String departmentId,
            int limit) {
        NativeQuery nativeQuery = buildRecommendationQuery(query, level, departmentId, toSuggestionPageable(limit));
        SearchHits<CourseSearchDocument> hits = elasticsearch.search(nativeQuery, CourseSearchDocument.class);
        String reason = recommendationReason(query, level, departmentId);
        return hits.getSearchHits().stream()
                .map(hit -> new CourseRecommendationDto(mapper.toDto(hit.getContent()), reason))
                .toList();
    }

    /**
     * Builds the Elasticsearch query for public course search. Extracted (package-private, static) so
     * the query shape can be asserted in a unit test without a running cluster.
     *
     * <p>Behaviour:
     * <ul>
     *   <li>Always filters to {@code status = PUBLISHED} (a non-scoring {@code filter} clause).</li>
     *   <li>A blank query returns all published courses; a non-blank query adds a
     *       {@code multi_match} (best_fields) over title^4 / summary so learners search by course
     *       name or course description/content.</li>
     * </ul>
     */
    static NativeQuery buildPublicQuery(String query, Pageable pageable) {
        Query boolQuery = Query.of(q -> q.bool(b -> {
            b.filter(publishedFilter());
            if (query != null && !query.isBlank()) {
                b.must(m -> m.multiMatch(mm -> mm
                        .query(query)
                        .type(TextQueryType.BestFields)
                        .fields("title^4", "summary")));
            }
            return b;
        }));

        NativeQueryBuilder builder = NativeQuery.builder()
                .withQuery(boolQuery)
                .withPageable(pageable);
        return builder.build();
    }

    static NativeQuery buildSuggestQuery(String query, Pageable pageable) {
        Query boolQuery = Query.of(q -> q.bool(b -> {
            b.filter(publishedFilter());
            if (query != null && !query.isBlank()) {
                b.must(m -> m.multiMatch(mm -> mm
                        .query(query)
                        .type(TextQueryType.BoolPrefix)
                        .fields("title^5", "summary")));
            }
            return b;
        }));

        return NativeQuery.builder()
                .withQuery(boolQuery)
                .withPageable(pageable)
                .build();
    }

    static NativeQuery buildRecommendationQuery(String query, String level, String departmentId, Pageable pageable) {
        boolean hasKeyword = query != null && !query.isBlank();
        boolean hasLevel = level != null && !level.isBlank();
        boolean hasDepartment = departmentId != null && !departmentId.isBlank();

        Query boolQuery = Query.of(q -> q.bool(b -> {
            b.filter(publishedFilter());
            if (hasKeyword) {
                b.should(s -> s.multiMatch(mm -> mm
                        .query(query)
                        .type(TextQueryType.BestFields)
                        .fields("title^4", "summary")));
            }
            if (hasLevel) {
                b.should(s -> s.term(t -> t.field("level").value(level).boost(1.8f)));
            }
            if (hasDepartment) {
                b.should(s -> s.term(t -> t.field("departmentId").value(departmentId).boost(1.5f)));
            }
            if (hasKeyword || hasLevel || hasDepartment) {
                b.minimumShouldMatch("1");
            }
            return b;
        }));

        return NativeQuery.builder()
                .withQuery(boolQuery)
                .withPageable(pageable)
                .build();
    }

    static Pageable toPageable(int page, int size) {
        int safePage = Math.max(page, 0);
        int safeSize = size <= 0 ? DEFAULT_PAGE_SIZE : Math.min(size, MAX_PAGE_SIZE);
        return PageRequest.of(safePage, safeSize);
    }

    static Pageable toSuggestionPageable(int limit) {
        int safeLimit = limit <= 0 ? DEFAULT_SUGGESTION_SIZE : Math.min(limit, MAX_SUGGESTION_SIZE);
        return PageRequest.of(0, safeLimit);
    }

    private static Query publishedFilter() {
        return Query.of(q -> q.term(t -> t.field("status").value(STATUS_PUBLISHED)));
    }

    private static String recommendationReason(String query, String level, String departmentId) {
        if (query != null && !query.isBlank()) {
            return "Phù hợp với từ khóa \"" + query.trim() + "\"";
        }
        if (level != null && !level.isBlank()) {
            return "Cùng trình độ " + level;
        }
        if (departmentId != null && !departmentId.isBlank()) {
            return "Cùng nhóm kiến thức";
        }
        return "Đề xuất từ catalog đang mở";
    }

    public CourseSearchDto indexCourse(IndexCourseRequestDto request) {
        CourseSearchDocument document = mapper.toDocument(request);
        return mapper.toDto(courses.save(document));
    }

    public void deleteCourse(String courseId) {
        courses.deleteById(courseId);
    }
}
