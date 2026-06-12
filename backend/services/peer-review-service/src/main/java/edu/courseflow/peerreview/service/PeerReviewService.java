package edu.courseflow.peerreview.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.peerreview.dto.AssignReviewRequestDto;
import edu.courseflow.peerreview.dto.FinalizePeerReviewRequestDto;
import edu.courseflow.peerreview.dto.PeerReviewResultDto;
import edu.courseflow.peerreview.dto.PeerReviewSettingDto;
import edu.courseflow.peerreview.dto.ReviewAssignmentDto;
import edu.courseflow.peerreview.dto.ReviewSubmissionDto;
import edu.courseflow.peerreview.dto.SubmitReviewRequestDto;
import edu.courseflow.peerreview.mapper.PeerReviewMapper;
import edu.courseflow.peerreview.model.OutboxEvent;
import edu.courseflow.peerreview.model.PeerReviewResult;
import edu.courseflow.peerreview.model.PeerReviewSetting;
import edu.courseflow.peerreview.model.ReviewAssignment;
import edu.courseflow.peerreview.model.ReviewSubmission;
import edu.courseflow.peerreview.repository.OutboxEventRepository;
import edu.courseflow.peerreview.repository.PeerReviewResultRepository;
import edu.courseflow.peerreview.repository.PeerReviewSettingRepository;
import edu.courseflow.peerreview.repository.ReviewAssignmentRepository;
import edu.courseflow.peerreview.repository.ReviewSubmissionRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PeerReviewService {

    /**
     * Upper bound for an individual review score. Peer-review forms do not model a per-form max in
     * this service, so scores are assumed to be on a 0..100 scale. Adjust here if a per-form max is
     * introduced later.
     */
    private static final BigDecimal MAX_REVIEW_SCORE = new BigDecimal("100");

    private final PeerReviewSettingRepository settings;
    private final ReviewAssignmentRepository assignments;
    private final ReviewSubmissionRepository submissions;
    private final PeerReviewResultRepository results;
    private final OutboxEventRepository outboxEvents;
    private final PeerReviewMapper mapper;
    private final ObjectMapper objectMapper;

    public PeerReviewService(PeerReviewSettingRepository settings,
            ReviewAssignmentRepository assignments,
            ReviewSubmissionRepository submissions,
            PeerReviewResultRepository results,
            OutboxEventRepository outboxEvents,
            PeerReviewMapper mapper,
            ObjectMapper objectMapper) {
        this.settings = settings;
        this.assignments = assignments;
        this.submissions = submissions;
        this.results = results;
        this.outboxEvents = outboxEvents;
        this.mapper = mapper;
        this.objectMapper = objectMapper;
    }

    public PeerReviewSettingDto setting(UUID assignmentId) {
        return settings.findByAssignmentId(assignmentId)
                .map(mapper::toDto)
                .orElseThrow(() -> new NotFoundException("Peer review setting not found: " + assignmentId));
    }

    @Transactional
    public ReviewAssignmentDto assign(AssignReviewRequestDto request) {
        if (request.reviewerId().equals(request.revieweeId())) {
            throw new BadRequestException("PEER_REVIEW_SELF_REVIEW_NOT_ALLOWED");
        }
        UUID id = UUID.randomUUID();
        ReviewAssignment assignment = assignments.save(new ReviewAssignment(
                id,
                parseOptionalUuid(request.courseId(), "courseId"),
                UUID.fromString(request.assignmentId()),
                UUID.fromString(request.submissionId()),
                request.reviewerId(),
                request.revieweeId()));
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("eventId", UUID.randomUUID().toString());
        payload.put("reviewAssignmentId", id.toString());
        if (request.courseId() != null && !request.courseId().isBlank()) {
            payload.put("courseId", request.courseId());
        }
        payload.put("assignmentId", request.assignmentId());
        payload.put("submissionId", request.submissionId());
        payload.put("reviewerId", request.reviewerId());
        outbox(id, "peer_review.assigned", payload);
        return mapper.toDto(assignment);
    }

    /** Reviewer (reviewer_id) of a review assignment, for controller-level ownership checks. */
    public String reviewerOf(UUID reviewAssignmentId) {
        return assignments.findById(reviewAssignmentId)
                .map(ReviewAssignment::getReviewerId)
                .orElseThrow(() -> new NotFoundException("Review assignment not found: " + reviewAssignmentId));
    }

    public List<ReviewAssignmentDto> assignedToReviewer(String reviewerId) {
        return assignments.findByReviewerIdOrderByAssignedAtDesc(reviewerId).stream()
                .map(mapper::toDto)
                .toList();
    }

    @Transactional
    public ReviewSubmissionDto submit(UUID reviewAssignmentId, SubmitReviewRequestDto request) {
        // Validate score range (0..MAX_REVIEW_SCORE).
        if (request.score() == null
                || request.score().compareTo(BigDecimal.ZERO) < 0
                || request.score().compareTo(MAX_REVIEW_SCORE) > 0) {
            throw new BadRequestException("PEER_REVIEW_SCORE_OUT_OF_RANGE");
        }

        ReviewAssignment assignment = assignments.findById(reviewAssignmentId)
                .orElseThrow(() -> new NotFoundException("Review assignment not found: " + reviewAssignmentId));

        // Enforce review due date when peer-review settings exist for the assignment.
        Instant dueAt = settings.findByAssignmentId(assignment.getAssignmentId())
                .map(PeerReviewSetting::getReviewDueAt)
                .orElse(null);
        if (dueAt != null && Instant.now().isAfter(dueAt)) {
            throw new BadRequestException("PEER_REVIEW_DUE_DATE_PASSED");
        }

        // Block duplicate submission: one reviewer submits at most once per review assignment.
        if (submissions.existsByReviewAssignmentId(reviewAssignmentId)) {
            throw new ConflictException("PEER_REVIEW_ALREADY_SUBMITTED");
        }

        ReviewSubmission submission = submissions.save(new ReviewSubmission(
                UUID.randomUUID(), reviewAssignmentId, request.score(), request.comment()));
        assignment.markReviewed();
        assignments.save(assignment);
        return mapper.toDto(submission);
    }

    /**
     * Finalizes the peer-review score for a reviewed submission. The final score is computed
     * server-side as the mean of all submitted peer reviews for that submission (never taken from the
     * client). The reviewee (studentId) and assignmentId are derived from the review assignments, so
     * the caller can only identify which submission to finalize, not whose score or what value.
     */
    @Transactional
    public PeerReviewResultDto finalizeScore(FinalizePeerReviewRequestDto request, String finalizedBy) {
        UUID submissionId = UUID.fromString(request.submissionId());

        // Derive assignmentId + reviewee from the review assignments tied to this submission.
        ReviewAssignment reviewed = assignments.findFirstBySubmissionId(submissionId)
                .orElseThrow(() -> new NotFoundException(
                        "No review assignments for submission: " + submissionId));
        PeerReviewSetting setting = settings.findByAssignmentId(reviewed.getAssignmentId())
                .orElseThrow(() -> new NotFoundException(
                        "Peer review setting not found: " + reviewed.getAssignmentId()));

        List<UUID> assignmentIds = assignments.findBySubmissionId(submissionId).stream()
                .map(ReviewAssignment::getId)
                .toList();
        List<BigDecimal> scores = submissions.findByReviewAssignmentIdIn(assignmentIds).stream()
                .map(ReviewSubmission::getScore)
                .toList();
        if (scores.isEmpty()) {
            throw new BadRequestException("PEER_REVIEW_NO_SUBMISSIONS_TO_AGGREGATE");
        }
        if (scores.size() < setting.getReviewersPerSubmission()) {
            throw new BadRequestException("PEER_REVIEW_NOT_ENOUGH_SUBMISSIONS");
        }

        // Aggregate = mean of submitted review scores (chosen over median for stability with few
        // reviewers; switch the helper if median is preferred).
        BigDecimal finalScore = mean(scores);

        PeerReviewResult result = results.findBySubmissionId(submissionId)
                .orElseGet(() -> new PeerReviewResult(submissionId, finalScore, finalizedBy));
        result.finalizeWith(finalScore, finalizedBy);
        result = results.save(result);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("eventId", UUID.randomUUID().toString());
        payload.put("resultId", result.getId().toString());
        if (reviewed.getCourseId() != null) {
            payload.put("courseId", reviewed.getCourseId().toString());
        }
        payload.put("assignmentId", reviewed.getAssignmentId().toString());
        payload.put("submissionId", request.submissionId());
        payload.put("studentId", reviewed.getRevieweeId());
        payload.put("finalScore", finalScore);
        payload.put("maxScore", MAX_REVIEW_SCORE);
        outbox(result.getId(), "peer_review.finalized", payload);
        return mapper.toDto(result);
    }

    private UUID parseOptionalUuid(String value, String field) {
        if (value == null || value.isBlank()) {
            return null;
        }
        try {
            return UUID.fromString(value);
        } catch (IllegalArgumentException ex) {
            throw new BadRequestException(field + " must be a UUID");
        }
    }

    /** Mean of the supplied scores, rounded to 2 dp. */
    static BigDecimal mean(List<BigDecimal> scores) {
        BigDecimal sum = scores.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
        return sum.divide(BigDecimal.valueOf(scores.size()), 2, RoundingMode.HALF_UP);
    }

    private void outbox(UUID aggregateId, String eventType, Map<String, ?> payload) {
        outboxEvents.save(new OutboxEvent(aggregateId, "peer-review", eventType, toJson(payload)));
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
