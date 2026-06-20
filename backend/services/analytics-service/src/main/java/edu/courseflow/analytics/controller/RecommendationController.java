package edu.courseflow.analytics.controller;

import edu.courseflow.analytics.dto.RecommendationDtos.ManualRelatedCourseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.MaterializeRecommendationArtifactRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationBatchRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationBatchResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationEventIngestResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecommendationMlTrainingJobResponseDto;
import edu.courseflow.analytics.dto.RecommendationDtos.RecordRecommendationEventRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.ReorderManualRelatedCoursesRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.UpdateManualRelatedCourseRequestDto;
import edu.courseflow.analytics.dto.RecommendationDtos.UpsertManualRelatedCourseRequestDto;
import edu.courseflow.analytics.service.RecommendationService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.validation.Valid;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class RecommendationController {

    private final RecommendationService recommendations;
    private final CourseAccessClient courseAccess;
    private final InternalJwtService internalJwtService;

    public RecommendationController(
            RecommendationService recommendations,
            CourseAccessClient courseAccess,
            InternalJwtService internalJwtService) {
        this.recommendations = recommendations;
        this.courseAccess = courseAccess;
        this.internalJwtService = internalJwtService;
    }

    @GetMapping("/internal/analytics/admin/courses/{courseId}/related")
    public List<ManualRelatedCourseDto> manualRelatedCourses(@PathVariable UUID courseId,
                                                             @RequestParam(defaultValue = "false")
                                                             boolean includeArchived,
                                                             CurrentUser user) {
        requirePlatformAdmin(user);
        return recommendations.manualRelatedCourses(courseId, includeArchived);
    }

    @PostMapping("/internal/analytics/admin/courses/{courseId}/related")
    @ResponseStatus(HttpStatus.CREATED)
    public ManualRelatedCourseDto createManualRelatedCourse(
            @PathVariable UUID courseId,
            @Valid @RequestBody UpsertManualRelatedCourseRequestDto request,
            CurrentUser user) {
        requirePlatformAdmin(user);
        if (request.relatedCourseId() != null) {
            courseAccess.requirePublishedCourse(request.relatedCourseId());
        }
        return recommendations.createManualRelatedCourse(courseId, request, actorId(user));
    }

    @PutMapping("/internal/analytics/admin/courses/{courseId}/related/{relatedCourseId}")
    public ManualRelatedCourseDto updateManualRelatedCourse(
            @PathVariable UUID courseId,
            @PathVariable UUID relatedCourseId,
            @Valid @RequestBody UpdateManualRelatedCourseRequestDto request,
            CurrentUser user) {
        requirePlatformAdmin(user);
        courseAccess.requirePublishedCourse(relatedCourseId);
        return recommendations.updateManualRelatedCourse(courseId, relatedCourseId, request, actorId(user));
    }

    @PostMapping("/internal/analytics/admin/courses/{courseId}/related/{relatedCourseId}/archive")
    public ManualRelatedCourseDto archiveManualRelatedCourse(@PathVariable UUID courseId,
                                                             @PathVariable UUID relatedCourseId,
                                                             CurrentUser user) {
        requirePlatformAdmin(user);
        return recommendations.archiveManualRelatedCourse(courseId, relatedCourseId, actorId(user));
    }

    @DeleteMapping("/internal/analytics/admin/courses/{courseId}/related/{relatedCourseId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteManualRelatedCourse(@PathVariable UUID courseId,
                                          @PathVariable UUID relatedCourseId,
                                          CurrentUser user) {
        requirePlatformAdmin(user);
        recommendations.deleteManualRelatedCourse(courseId, relatedCourseId);
    }

    @PostMapping("/internal/analytics/admin/courses/{courseId}/related/reorder")
    public List<ManualRelatedCourseDto> reorderManualRelatedCourses(
            @PathVariable UUID courseId,
            @Valid @RequestBody ReorderManualRelatedCoursesRequestDto request,
            CurrentUser user) {
        requirePlatformAdmin(user);
        return recommendations.reorderManualRelatedCourses(courseId, request, actorId(user));
    }

    @PostMapping("/public/analytics/recommendations/events")
    public RecommendationEventIngestResponseDto recordPublicRecommendationEvent(
            @Valid @RequestBody RecordRecommendationEventRequestDto request,
            CurrentUser user) {
        return recordRecommendationEvent(request, user, true);
    }

    @PostMapping("/internal/analytics/recommendations/events")
    public RecommendationEventIngestResponseDto recordInternalRecommendationEvent(
            @Valid @RequestBody RecordRecommendationEventRequestDto request,
            CurrentUser user) {
        return recordRecommendationEvent(request, user, false);
    }

    @PostMapping("/internal/analytics/recommendations/batch/related-course-pairs")
    public RecommendationBatchResponseDto recomputeRelatedCoursePairs(
            @RequestBody(required = false) RecommendationBatchRequestDto request,
            CurrentUser user) {
        requirePlatformAdminOrServiceScope(
                user,
                InternalScopes.ANALYTICS_MODEL_WRITE,
                "Requires platform admin or analytics model service access");
        return recommendations.recomputeRelatedCoursePairs(request);
    }

    @PostMapping("/internal/analytics/recommendations/batch/related-course-pairs/async")
    public RecommendationMlTrainingJobResponseDto enqueueMlRelatedCourseTraining(
            @RequestBody(required = false) RecommendationBatchRequestDto request,
            CurrentUser user) {
        requirePlatformAdminOrServiceScope(
                user,
                InternalScopes.ANALYTICS_MODEL_WRITE,
                "Requires platform admin or analytics model service access");
        return recommendations.enqueueMlRelatedCourseTraining(request);
    }

    @PostMapping("/internal/analytics/recommendations/batch/related-course-pairs/async/{trainingRunId}/materialize")
    public RecommendationMlTrainingJobResponseDto materializeMlTrainingRun(
            @PathVariable UUID trainingRunId,
            CurrentUser user) {
        requirePlatformAdminOrServiceScope(
                user,
                InternalScopes.ANALYTICS_MODEL_WRITE,
                "Requires platform admin or analytics model service access");
        return recommendations.materializeMlTrainingRun(trainingRunId);
    }

    @PostMapping("/internal/analytics/recommendations/batch/related-course-pairs/active-model/materialize")
    public RecommendationMlTrainingJobResponseDto materializeActiveMlModel(CurrentUser user) {
        requirePlatformAdminOrServiceScope(
                user,
                InternalScopes.ANALYTICS_MODEL_WRITE,
                "Requires platform admin or analytics model service access");
        return recommendations.syncActiveMlModelReadModel();
    }

    @PostMapping("/internal/analytics/recommendations/batch/related-course-pairs/artifact/materialize")
    public RecommendationMlTrainingJobResponseDto materializeRecommendationArtifact(
            @Valid @RequestBody MaterializeRecommendationArtifactRequestDto request,
            CurrentUser user) {
        requirePlatformAdminOrServiceScope(
                user,
                InternalScopes.ANALYTICS_MODEL_WRITE,
                "Requires platform admin or analytics model service access");
        return recommendations.materializeRecommendationArtifact(request);
    }

    private RecommendationEventIngestResponseDto recordRecommendationEvent(
            RecordRecommendationEventRequestDto request,
            CurrentUser user,
            boolean allowAnonymous) {
        if (isPlatformAdmin(user)) {
            return recommendations.recordRecommendationEvent(request, request.studentId(), actorId(user));
        }
        if (hasVerifiedServiceScope(user, InternalScopes.ANALYTICS_EVENT_WRITE)) {
            return recommendations.recordRecommendationEvent(request, request.studentId(), "service");
        }
        if (user != null && user.id() != null) {
            return recommendations.recordRecommendationEvent(request, String.valueOf(user.id()), actorId(user));
        }
        if (!allowAnonymous) {
            callerId(user);
        }
        if (request.studentId() != null && !request.studentId().isBlank()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Anonymous tracking cannot set studentId");
        }
        return recommendations.recordRecommendationEvent(request, null, null);
    }

    private void requirePlatformAdmin(CurrentUser user) {
        if (isPlatformAdmin(user)) {
            return;
        }
        callerId(user);
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires platform admin access");
    }

    private void requirePlatformAdminOrServiceScope(CurrentUser user, String scope, String message) {
        if (isPlatformAdmin(user)) {
            return;
        }
        if (hasVerifiedServiceScope(user, scope)) {
            return;
        }
        callerId(user);
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, message);
    }

    private boolean isPlatformAdmin(CurrentUser user) {
        return user != null && user.hasPlatformRole("ADMIN");
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Authentication required");
        }
        return String.valueOf(user.id());
    }

    private String actorId(CurrentUser user) {
        return "user:" + callerId(user);
    }

    private boolean hasVerifiedServiceScope(CurrentUser user, String requiredScope) {
        if (user == null || user.id() != null || user.internalToken() == null) {
            return false;
        }
        try {
            Claims claims = internalJwtService.verify(user.internalToken());
            if (!"service".equals(claims.get("actor_type", String.class))) {
                return false;
            }
            Set<String> scopes = extractScopes(claims);
            return scopes.contains("*") || scopes.contains(requiredScope);
        } catch (JwtException | IllegalArgumentException | IllegalStateException ex) {
            return false;
        }
    }

    @SuppressWarnings("unchecked")
    private Set<String> extractScopes(Claims claims) {
        Set<String> scopes = new LinkedHashSet<>();
        Object rawScope = claims.get("scope");
        if (rawScope != null) {
            Arrays.stream(rawScope.toString().split("\\s+"))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(scopes::add);
        }
        Object rawScp = claims.get("scp");
        if (rawScp instanceof List<?> list) {
            for (Object scope : list) {
                if (scope != null && !scope.toString().isBlank()) {
                    scopes.add(scope.toString().trim());
                }
            }
        }
        return scopes;
    }
}
