package edu.courseflow.search.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.search.dto.SearchDtos.CourseRecommendationDto;
import edu.courseflow.search.dto.SearchDtos.CourseSearchDto;
import edu.courseflow.search.dto.SearchDtos.CourseSearchPageDto;
import edu.courseflow.search.dto.SearchDtos.IndexCourseRequestDto;
import edu.courseflow.search.service.SearchService;
import edu.courseflow.search.web.Authz;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SearchController {

    private final SearchService search;

    public SearchController(SearchService search) {
        this.search = search;
    }

    /**
     * Public, unauthenticated course discovery. Executes a real Elasticsearch full-text query and
     * returns a page of hits plus the total hit count.
     */
    @GetMapping("/public/search/courses")
    public CourseSearchPageDto publicCourses(
            @RequestParam(defaultValue = "") String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return search.searchPublicCourses(q, page, size);
    }

    /**
     * Lightweight autocomplete for the learner search box. Uses an Elasticsearch bool-prefix query
     * so the UI can update as the learner types without downloading the full result page.
     */
    @GetMapping("/public/search/courses/suggest")
    public List<CourseSearchDto> suggestCourses(
            @RequestParam(defaultValue = "") String q,
            @RequestParam(defaultValue = "6") int limit) {
        return search.suggestPublicCourses(q, limit);
    }

    /**
     * Course recommendations for the learner search surface. The query is still executed in
     * Elasticsearch so keyword, level, and department signals contribute to score ordering.
     */
    @GetMapping("/public/search/courses/recommendations")
    public List<CourseRecommendationDto> recommendedCourses(
            @RequestParam(defaultValue = "") String q,
            @RequestParam(required = false) String level,
            @RequestParam(required = false) String departmentId,
            @RequestParam(defaultValue = "6") int limit) {
        return search.recommendPublicCourses(q, level, departmentId, limit);
    }

    /**
     * Manual indexing/backfill endpoint. Staff-only (INSTRUCTOR or ADMIN); identity comes from the
     * gateway via {@link CurrentUser}, never from the request body. Event-driven indexing is handled
     * by the Kafka consumer; this endpoint exists for reindex/backfill.
     */
    @PostMapping("/internal/search/courses")
    public CourseSearchDto indexCourse(@Valid @RequestBody IndexCourseRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        return search.indexCourse(request);
    }
}
