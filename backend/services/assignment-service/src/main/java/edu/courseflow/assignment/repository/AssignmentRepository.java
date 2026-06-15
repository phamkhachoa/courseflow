package edu.courseflow.assignment.repository;

import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.AttachmentRef;
import edu.courseflow.assignment.dto.AssignmentDtos.CreateAssignmentRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.GradingQueueItemDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricCriterionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionAttachmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.UpsertRubricRequestDto;
import edu.courseflow.assignment.mapper.AssignmentMapper;
import edu.courseflow.assignment.model.Assignment;
import edu.courseflow.assignment.model.AssignmentRubric;
import edu.courseflow.assignment.model.AssignmentRubricCriterion;
import edu.courseflow.assignment.model.OutboxEvent;
import edu.courseflow.assignment.model.Submission;
import edu.courseflow.assignment.model.SubmissionAttachment;
import edu.courseflow.assignment.model.SubmissionRubricScore;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import java.math.BigDecimal;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Repository;

@Repository
public class AssignmentRepository {

    private final AssignmentJpaRepository assignments;
    private final SubmissionJpaRepository submissions;
    private final SubmissionAttachmentJpaRepository attachments;
    private final AssignmentRubricJpaRepository rubrics;
    private final AssignmentRubricCriterionJpaRepository criteria;
    private final SubmissionRubricScoreJpaRepository rubricScores;
    private final OutboxEventJpaRepository outbox;
    private final AssignmentMapper mapper;

    public AssignmentRepository(AssignmentJpaRepository assignments,
            SubmissionJpaRepository submissions,
            SubmissionAttachmentJpaRepository attachments,
            AssignmentRubricJpaRepository rubrics,
            AssignmentRubricCriterionJpaRepository criteria,
            SubmissionRubricScoreJpaRepository rubricScores,
            OutboxEventJpaRepository outbox,
            AssignmentMapper mapper) {
        this.assignments = assignments;
        this.submissions = submissions;
        this.attachments = attachments;
        this.rubrics = rubrics;
        this.criteria = criteria;
        this.rubricScores = rubricScores;
        this.outbox = outbox;
        this.mapper = mapper;
    }

    // ---------- Assignments ----------

    public List<AssignmentDto> listByCourse(UUID courseId) {
        return assignments.findByCourseIdOrderByDueAtAscTitleAsc(courseId).stream()
                .map(this::toAssignmentDto)
                .toList();
    }

    public Optional<AssignmentDto> find(UUID assignmentId) {
        return assignments.findById(assignmentId).map(this::toAssignmentDto);
    }

    public AssignmentDto updateStatus(UUID assignmentId, String status) {
        Assignment assignment = assignments.findById(assignmentId)
                .orElseThrow(() -> new NotFoundException("Assignment not found: " + assignmentId));
        assignment.setStatus(status);
        return toAssignmentDto(assignments.save(assignment));
    }

    public AssignmentDto create(CreateAssignmentRequestDto request) {
        Assignment assignment = new Assignment(
                UUID.randomUUID(),
                UUID.fromString(request.courseId()),
                request.title(),
                request.assignmentType(),
                request.instructions(),
                request.availableAt(),
                request.dueAt(),
                request.lockAt(),
                request.maxScore(),
                request.submissionTypes() == null ? "FILE" : request.submissionTypes(),
                request.maxAttempts() == null ? 1 : request.maxAttempts(),
                request.allowResubmission() != null && request.allowResubmission(),
                request.latePenaltyPercent() == null ? BigDecimal.ZERO : request.latePenaltyPercent(),
                request.latePenaltyInterval() == null ? "DAY" : request.latePenaltyInterval(),
                request.latePenaltyMaxPercent() == null ? new BigDecimal("100") : request.latePenaltyMaxPercent());
        return toAssignmentDto(assignments.save(assignment));
    }

    // ---------- Submissions ----------

    public int nextAttemptNo(UUID assignmentId, String studentId) {
        return submissions.nextAttemptNo(assignmentId, studentId);
    }

    public SubmissionDto insertSubmission(UUID assignmentId, String studentId, int attemptNo,
            String submissionText, String submissionUrl,
            boolean isLate, int minutesLate,
            List<AttachmentRef> refs) {
        Submission submission = submissions.save(new Submission(
                UUID.randomUUID(),
                assignmentId,
                studentId,
                attemptNo,
                submissionText,
                submissionUrl,
                isLate,
                minutesLate));
        insertAttachments(submission.getId(), refs == null ? List.of() : refs);
        return toSubmissionDto(submission);
    }

    private void insertAttachments(UUID submissionId, List<AttachmentRef> refs) {
        attachments.saveAll(refs.stream()
                .map(ref -> new SubmissionAttachment(
                        submissionId,
                        ref.mediaAssetId(),
                        ref.fileName(),
                        ref.storageKey(),
                        ref.contentType(),
                        ref.sizeBytes()))
                .toList());
    }

    public List<SubmissionDto> listSubmissionsForStudent(UUID assignmentId, String studentId) {
        return submissions.findByAssignmentIdAndStudentIdOrderByAttemptNoAsc(assignmentId, studentId).stream()
                .map(this::toSubmissionDto)
                .toList();
    }

    public List<SubmissionDto> listSubmissionAttemptsForStudent(List<UUID> assignmentIds, String studentId) {
        if (assignmentIds == null || assignmentIds.isEmpty()) {
            return List.of();
        }
        return submissions.findByAssignmentIdInAndStudentIdOrderBySubmittedAtDesc(assignmentIds, studentId).stream()
                .map(submission -> mapper.toDto(submission, List.of()))
                .toList();
    }

    public Optional<SubmissionDto> findSubmissionById(UUID submissionId) {
        return submissions.findById(submissionId).map(this::toSubmissionDto);
    }

    public List<GradingQueueItemDto> listGradingQueue(List<AssignmentDto> assignmentRows,
            Collection<String> statuses,
            int limit) {
        if (assignmentRows == null || assignmentRows.isEmpty()) {
            return List.of();
        }
        List<UUID> assignmentIds = assignmentRows.stream()
                .map(assignment -> UUID.fromString(assignment.id()))
                .toList();
        PageRequest page = PageRequest.of(0, limit);
        List<Submission> rows = statuses == null || statuses.isEmpty()
                ? submissions.findByAssignmentIdInOrderBySubmittedAtAsc(assignmentIds, page)
                : submissions.findByAssignmentIdInAndStatusInOrderBySubmittedAtAsc(assignmentIds, statuses, page);
        java.util.Map<String, AssignmentDto> assignmentById = assignmentRows.stream()
                .collect(java.util.stream.Collectors.toMap(AssignmentDto::id, assignment -> assignment));
        return rows.stream()
                .map(submission -> toGradingQueueItem(submission, assignmentById.get(submission.getAssignmentId().toString())))
                .toList();
    }

    public void recordGrade(UUID submissionId, String graderId, BigDecimal rawScore,
            BigDecimal latePenaltyApplied, BigDecimal finalScore, String feedback) {
        Submission submission = submissions.findById(submissionId).orElseThrow();
        submission.grade(graderId, rawScore, latePenaltyApplied, finalScore, feedback);
        submissions.save(submission);
    }

    public void replaceRubricScores(UUID submissionId,
            List<edu.courseflow.assignment.dto.AssignmentDtos.RubricScoreDto> scores) {
        rubricScores.deleteBySubmissionId(submissionId);
        if (scores == null) {
            return;
        }
        rubricScores.saveAll(scores.stream()
                .map(score -> new SubmissionRubricScore(
                        submissionId,
                        UUID.fromString(score.criterionId()),
                        score.points(),
                        score.comment()))
                .toList());
    }

    // ---------- Rubric ----------

    public Optional<RubricDto> findRubricByAssignment(UUID assignmentId) {
        return rubrics.findByAssignmentId(assignmentId).map(this::toRubricDto);
    }

    public RubricDto upsertRubric(UUID assignmentId, UpsertRubricRequestDto request) {
        AssignmentRubric rubric = rubrics.findByAssignmentId(assignmentId)
                .map(existing -> {
                    existing.update(request.title(), request.maxScore());
                    return existing;
                })
                .orElseGet(() -> new AssignmentRubric(UUID.randomUUID(), assignmentId, request.title(), request.maxScore()));
        rubric = rubrics.save(rubric);
        criteria.deleteByRubricId(rubric.getId());
        if (request.criteria() != null) {
            int pos = 1;
            for (RubricCriterionDto criterion : request.criteria()) {
                criteria.save(new AssignmentRubricCriterion(
                        rubric.getId(),
                        criterion.name(),
                        criterion.description(),
                        criterion.maxPoints(),
                        pos++));
            }
        }
        Assignment assignment = assignments.findById(assignmentId).orElseThrow();
        assignment.setRubricId(rubric.getId());
        assignments.save(assignment);
        return toRubricDto(rubric);
    }

    // ---------- Outbox ----------

    public void outbox(UUID aggregateId, String aggregateType, String eventType, String payload) {
        outbox.save(new OutboxEvent(aggregateId, aggregateType, eventType, payload));
    }

    // ---------- Helpers ----------

    private AssignmentDto toAssignmentDto(Assignment assignment) {
        return mapper.toDto(assignment);
    }

    private List<SubmissionAttachmentDto> listAttachments(UUID submissionId) {
        return attachments.findBySubmissionIdOrderByCreatedAtAscFileNameAsc(submissionId).stream()
                .map(mapper::toDto)
                .toList();
    }

    private SubmissionDto toSubmissionDto(Submission submission) {
        return mapper.toDto(submission, listAttachments(submission.getId()));
    }

    private GradingQueueItemDto toGradingQueueItem(Submission submission, AssignmentDto assignment) {
        List<SubmissionAttachmentDto> submissionAttachments = listAttachments(submission.getId());
        return new GradingQueueItemDto(
                submission.getId().toString(),
                submission.getAssignmentId().toString(),
                assignment == null ? "Assignment " + submission.getAssignmentId() : assignment.title(),
                assignment == null ? null : assignment.courseId(),
                submission.getStudentId(),
                submission.getAttemptNo(),
                submission.getSubmittedAt(),
                submission.getStatus(),
                submission.isLate(),
                submission.getMinutesLate(),
                assignment == null ? null : assignment.maxScore(),
                assignment == null ? null : assignment.rubricId(),
                submissionAttachments.size());
    }

    private RubricDto toRubricDto(AssignmentRubric rubric) {
        return mapper.toDto(rubric, criteria.findByRubricIdOrderByPositionAsc(rubric.getId()).stream()
                .map(mapper::toDto)
                .toList());
    }
}
