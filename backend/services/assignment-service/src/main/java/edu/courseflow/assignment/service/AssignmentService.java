package edu.courseflow.assignment.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentReadinessDto;
import edu.courseflow.assignment.dto.AssignmentDtos.AttachmentRef;
import edu.courseflow.assignment.dto.AssignmentDtos.CreateAssignmentRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.GradeSubmissionRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.GradingQueueItemDto;
import edu.courseflow.assignment.dto.AssignmentDtos.LearnerSourceStatusDto;
import edu.courseflow.assignment.dto.AssignmentDtos.PresignedDownloadDto;
import edu.courseflow.assignment.dto.AssignmentDtos.PresignedUploadDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RequestUploadUrlDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricCriterionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmitAssignmentRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.UpsertRubricRequestDto;
import edu.courseflow.assignment.model.AttachmentUploadGrant;
import edu.courseflow.assignment.repository.AssignmentRepository;
import edu.courseflow.assignment.repository.AttachmentUploadGrantJpaRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient.PresignedUrl;
import java.io.IOException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.time.Instant;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

@Service
public class AssignmentService {

    private static final String STORAGE_PREFIX = "submissions";
    private static final BigDecimal ONE_HUNDRED = new BigDecimal("100");

    private final AssignmentRepository assignments;
    private final ObjectStorageClient storage;
    private final ObjectMapper objectMapper;
    private final CourseAccessClient courseAccess;
    private final LearningAccessClient learningAccess;
    private final AttachmentUploadGrantJpaRepository uploadGrants;

    public AssignmentService(AssignmentRepository assignments,
            ObjectStorageClient storage,
            ObjectMapper objectMapper,
            CourseAccessClient courseAccess,
            LearningAccessClient learningAccess,
            AttachmentUploadGrantJpaRepository uploadGrants) {
        this.assignments = assignments;
        this.storage = storage;
        this.objectMapper = objectMapper;
        this.courseAccess = courseAccess;
        this.learningAccess = learningAccess;
        this.uploadGrants = uploadGrants;
    }

    // ---------- Reads ----------

    public List<AssignmentDto> listByCourse(UUID courseId) {
        return assignments.listByCourse(courseId);
    }

    public List<AssignmentDto> listVisibleByCourse(UUID courseId) {
        Instant now = Instant.now();
        return assignments.listByCourse(courseId).stream()
                .filter(assignment -> isLearnerVisible(assignment, now))
                .toList();
    }

    public List<LearnerSourceStatusDto> learnerStatuses(UUID courseId, String studentId, List<UUID> sourceIds) {
        if (studentId == null || studentId.isBlank()) {
            throw new BadRequestException("studentId is required");
        }
        Set<UUID> requestedSourceIds = sourceIds == null ? Set.of() : new HashSet<>(sourceIds);
        List<AssignmentDto> courseAssignments = assignments.listByCourse(courseId).stream()
                .filter(assignment -> requestedSourceIds.isEmpty()
                        || requestedSourceIds.contains(UUID.fromString(assignment.id())))
                .toList();
        if (courseAssignments.isEmpty()) {
            return List.of();
        }
        List<UUID> assignmentIds = courseAssignments.stream()
                .map(assignment -> UUID.fromString(assignment.id()))
                .toList();
        Map<String, List<SubmissionDto>> submissionsByAssignment = assignments
                .listSubmissionAttemptsForStudent(assignmentIds, studentId.trim()).stream()
                .collect(java.util.stream.Collectors.groupingBy(SubmissionDto::assignmentId));
        Instant now = Instant.now();
        return courseAssignments.stream()
                .map(assignment -> learnerStatus(
                        assignment,
                        submissionsByAssignment.getOrDefault(assignment.id(), List.of()),
                        now))
                .toList();
    }

    public AssignmentDto get(UUID assignmentId) {
        return assignments.find(assignmentId)
                .orElseThrow(() -> new NotFoundException("Assignment not found: " + assignmentId));
    }

    public AssignmentReadinessDto readiness(UUID assignmentId) {
        AssignmentDto assignment = get(assignmentId);
        return new AssignmentReadinessDto(assignment.id(), assignment.courseId(), assignment.status());
    }

    public List<SubmissionDto> listSubmissions(UUID assignmentId, String studentId) {
        get(assignmentId);
        return assignments.listSubmissionsForStudent(assignmentId, studentId);
    }

    public List<GradingQueueItemDto> gradingQueue(UUID courseId, UUID assignmentId, String status, int requestedLimit) {
        int limit = Math.max(1, Math.min(requestedLimit, 200));
        List<AssignmentDto> courseAssignments = assignments.listByCourse(courseId);
        if (assignmentId != null) {
            courseAssignments = courseAssignments.stream()
                    .filter(assignment -> assignment.id().equals(assignmentId.toString()))
                    .toList();
            if (courseAssignments.isEmpty()) {
                throw new BadRequestException("ASSIGNMENT_NOT_IN_COURSE");
            }
        }
        return assignments.listGradingQueue(courseAssignments, gradingQueueStatuses(status), limit);
    }

    public SubmissionDto getSubmission(UUID submissionId) {
        return assignments.findSubmissionById(submissionId)
                .orElseThrow(() -> new NotFoundException("Submission not found: " + submissionId));
    }

    // ---------- Writes ----------

    @Transactional
    public AssignmentDto create(CreateAssignmentRequestDto request) {
        return assignments.create(request);
    }

    @Transactional
    public AssignmentDto publish(UUID assignmentId) {
        get(assignmentId);
        return assignments.updateStatus(assignmentId, "PUBLISHED");
    }

    @Transactional
    public AssignmentDto draft(UUID assignmentId) {
        get(assignmentId);
        return assignments.updateStatus(assignmentId, "DRAFT");
    }

    @Transactional
    public AssignmentDto archive(UUID assignmentId) {
        get(assignmentId);
        return assignments.updateStatus(assignmentId, "ARCHIVED");
    }

    @Transactional
    public SubmissionDto submit(UUID assignmentId, String studentId, SubmitAssignmentRequestDto request) {
        AssignmentDto assignment = get(assignmentId);
        UUID courseId = UUID.fromString(assignment.courseId());
        courseAccess.requireStudentCourseAccess(studentId, courseId);
        Instant now = Instant.now();
        requireLearnerOpen(assignment, now);
        learningAccess.requireSourceAccess(courseId, studentId, "ASSIGNMENT", assignmentId);
        List<AttachmentRef> trustedAttachments = validateSubmissionPayload(assignment, studentId, request);

        int nextAttempt = assignments.nextAttemptNo(assignmentId, studentId);
        if (nextAttempt > 1 && !assignment.allowResubmission()) {
            throw new BadRequestException("RESUBMISSION_NOT_ALLOWED");
        }
        if (assignment.maxAttempts() > 0 && nextAttempt > assignment.maxAttempts()) {
            throw new BadRequestException("MAX_ATTEMPTS_REACHED");
        }

        boolean isLate = now.isAfter(assignment.dueAt());
        int minutesLate = isLate
                ? (int) Math.max(0, Duration.between(assignment.dueAt(), now).toMinutes())
                : 0;

        SubmissionDto submission = assignments.insertSubmission(assignmentId, studentId, nextAttempt,
                request.submissionText(), request.submissionUrl(),
                isLate, minutesLate,
                trustedAttachments);
        consumeAttachmentGrants(assignmentId, studentId, trustedAttachments, UUID.fromString(submission.id()), now);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("eventId", UUID.randomUUID().toString());
        payload.put("submissionId", submission.id());
        payload.put("assignmentId", assignmentId.toString());
        payload.put("courseId", assignment.courseId());
        payload.put("studentId", studentId);
        payload.put("attemptNo", submission.attemptNo());
        payload.put("isLate", isLate);
        payload.put("submittedAt", submission.submittedAt().toString());
        assignments.outbox(UUID.fromString(submission.id()), "submission", "submission.created", toJson(payload));
        return submission;
    }

    private void requireLearnerOpen(AssignmentDto assignment, Instant now) {
        if (!isPublishedOrActive(assignment.status())) {
            throw new BadRequestException("ASSIGNMENT_NOT_PUBLISHED");
        }
        if (assignment.availableAt() != null && now.isBefore(assignment.availableAt())) {
            throw new BadRequestException("ASSIGNMENT_NOT_AVAILABLE_YET");
        }
        if (assignment.lockAt() != null && now.isAfter(assignment.lockAt())) {
            throw new BadRequestException("ASSIGNMENT_LOCKED");
        }
    }

    public void requireLearnerVisible(AssignmentDto assignment) {
        if (!isLearnerVisible(assignment, Instant.now())) {
            throw new BadRequestException("ASSIGNMENT_NOT_AVAILABLE");
        }
    }

    private boolean isLearnerVisible(AssignmentDto assignment, Instant now) {
        return isPublishedOrActive(assignment.status())
                && (assignment.availableAt() == null || !now.isBefore(assignment.availableAt()))
                && (assignment.lockAt() == null || !now.isAfter(assignment.lockAt()));
    }

    private boolean isPublishedOrActive(String status) {
        return "PUBLISHED".equalsIgnoreCase(status) || "ACTIVE".equalsIgnoreCase(status);
    }

    private LearnerSourceStatusDto learnerStatus(AssignmentDto assignment,
                                                 List<SubmissionDto> learnerSubmissions,
                                                 Instant now) {
        SubmissionDto latest = learnerSubmissions.isEmpty() ? null : learnerSubmissions.getFirst();
        boolean completed = learnerSubmissions.stream()
                .anyMatch(submission -> "GRADED".equalsIgnoreCase(submission.status()));
        boolean hasSubmission = latest != null;
        boolean overdue = !completed
                && !hasSubmission
                && assignment.dueAt() != null
                && now.isAfter(assignment.dueAt());
        String sourceStatus = assignmentSourceStatus(assignment, latest, completed, overdue, now);
        return new LearnerSourceStatusDto(
                "ASSIGNMENT",
                assignment.id(),
                assignment.courseId(),
                assignment.title(),
                sourceStatus,
                assignment.availableAt(),
                assignment.dueAt(),
                assignment.lockAt(),
                latest == null ? null : latest.status(),
                latest == null ? null : latest.id(),
                learnerSubmissions.size(),
                assignment.maxAttempts(),
                completed,
                overdue);
    }

    private String assignmentSourceStatus(AssignmentDto assignment,
                                          SubmissionDto latest,
                                          boolean completed,
                                          boolean overdue,
                                          Instant now) {
        if (!isPublishedOrActive(assignment.status())) {
            return "UNAVAILABLE";
        }
        if (completed) {
            return "COMPLETED";
        }
        if (latest != null && latest.status() != null && !latest.status().isBlank()) {
            return latest.status().trim().toUpperCase();
        }
        if (assignment.availableAt() != null && now.isBefore(assignment.availableAt())) {
            return "NOT_AVAILABLE";
        }
        if (assignment.lockAt() != null && now.isAfter(assignment.lockAt())) {
            return "LOCKED";
        }
        if (overdue) {
            return "OVERDUE";
        }
        return "READY";
    }

    private List<String> gradingQueueStatuses(String status) {
        if (status == null || status.isBlank()) {
            return List.of("SUBMITTED", "RESUBMITTED");
        }
        String normalized = status.trim().toUpperCase(Locale.ROOT);
        if ("ALL".equals(normalized)) {
            return List.of();
        }
        return List.of(normalized);
    }

    @Transactional
    public SubmissionDto grade(UUID submissionId, String graderId, GradeSubmissionRequestDto request) {
        SubmissionDto submission = getSubmission(submissionId);
        AssignmentDto assignment = get(UUID.fromString(submission.assignmentId()));

        BigDecimal rawScore = resolveRawScore(assignment, submission, request);
        BigDecimal penaltyPct = computeLatePenaltyPercent(assignment, submission);
        BigDecimal finalScore = rawScore
                .subtract(rawScore.multiply(penaltyPct).divide(ONE_HUNDRED, 4, RoundingMode.HALF_UP));
        if (finalScore.compareTo(BigDecimal.ZERO) < 0) {
            finalScore = BigDecimal.ZERO;
        }
        finalScore = finalScore.setScale(2, RoundingMode.HALF_UP);

        if (request.rubricScores() != null && !request.rubricScores().isEmpty()) {
            assignments.replaceRubricScores(submissionId, request.rubricScores());
        }
        assignments.recordGrade(submissionId, graderId, rawScore, penaltyPct, finalScore, request.feedback());

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("eventId", UUID.randomUUID().toString());
        payload.put("submissionId", submissionId.toString());
        payload.put("assignmentId", submission.assignmentId());
        payload.put("courseId", assignment.courseId());
        payload.put("studentId", submission.studentId());
        payload.put("attemptNo", submission.attemptNo());
        payload.put("rawScore", rawScore);
        payload.put("latePenaltyPercent", penaltyPct);
        payload.put("finalScore", finalScore);
        payload.put("maxScore", assignment.maxScore());
        payload.put("gradedAt", Instant.now().toString());
        assignments.outbox(submissionId, "submission", "submission.graded", toJson(payload));

        return getSubmission(submissionId);
    }

    // ---------- Rubric ----------

    public RubricDto getRubric(UUID assignmentId) {
        get(assignmentId);
        return assignments.findRubricByAssignment(assignmentId)
                .orElseThrow(() -> new NotFoundException("Rubric not set for assignment: " + assignmentId));
    }

    @Transactional
    public RubricDto upsertRubric(UUID assignmentId, UpsertRubricRequestDto request) {
        get(assignmentId);
        return assignments.upsertRubric(assignmentId, request);
    }

    // ---------- Storage (MinIO direct upload) ----------

    public PresignedUploadDto presignUpload(UUID assignmentId, String studentId, RequestUploadUrlDto req) {
        AssignmentDto assignment = get(assignmentId);
        requireLearnerOpen(assignment, Instant.now());
        learningAccess.requireSourceAccess(UUID.fromString(assignment.courseId()), studentId, "ASSIGNMENT", assignmentId);
        String fileName = safeFileName(req.fileName());
        String contentType = normalizeContentType(req.contentType());
        String key = storage.buildKey(STORAGE_PREFIX + "/" + assignmentId + "/" + studentId, fileName);
        PresignedUrl presigned = storage.presignPut(key, contentType);
        uploadGrants.save(new AttachmentUploadGrant(
                assignmentId,
                studentId,
                presigned.storageKey(),
                fileName,
                contentType,
                null,
                presigned.expiresAt()));
        return new PresignedUploadDto(presigned.storageKey(), presigned.url(), presigned.expiresAt());
    }

    public AttachmentRef proxyUpload(UUID assignmentId, String studentId, MultipartFile file) {
        AssignmentDto assignment = get(assignmentId);
        requireLearnerOpen(assignment, Instant.now());
        learningAccess.requireSourceAccess(UUID.fromString(assignment.courseId()), studentId, "ASSIGNMENT", assignmentId);
        if (file == null || file.isEmpty()) {
            throw new BadRequestException("Uploaded file is empty");
        }
        String fileName = safeFileName(file.getOriginalFilename());
        String contentType = normalizeContentType(file.getContentType());
        String key = storage.buildKey(STORAGE_PREFIX + "/" + assignmentId + "/" + studentId, fileName);
        try {
            storage.put(key, file.getInputStream(), file.getSize(), contentType);
        } catch (IOException ex) {
            throw new BadRequestException("Failed to read uploaded file: " + ex.getMessage());
        }
        uploadGrants.save(new AttachmentUploadGrant(
                assignmentId,
                studentId,
                key,
                fileName,
                contentType,
                file.getSize(),
                null));
        return new AttachmentRef(null, fileName, key, contentType, file.getSize());
    }

    public PresignedDownloadDto presignDownloadAttachment(UUID submissionId, String storageKey) {
        SubmissionDto sub = getSubmission(submissionId);
        boolean ours = sub.attachments().stream().anyMatch(a -> a.storageKey().equals(storageKey));
        if (!ours) {
            throw new NotFoundException("Attachment not found on submission: " + submissionId);
        }
        PresignedUrl presigned = storage.presignGet(storageKey);
        return new PresignedDownloadDto(presigned.storageKey(), presigned.url(), presigned.expiresAt());
    }

    // ---------- Helpers ----------

    private List<AttachmentRef> validateSubmissionPayload(AssignmentDto assignment, String studentId,
            SubmitAssignmentRequestDto request) {
        List<String> allowed = List.of(assignment.submissionTypes().split(","));
        boolean hasFile = request.attachments() != null && !request.attachments().isEmpty();
        boolean hasText = request.submissionText() != null && !request.submissionText().isBlank();
        boolean hasUrl = request.submissionUrl() != null && !request.submissionUrl().isBlank();

        if (!hasFile && !hasText && !hasUrl) {
            throw new BadRequestException("EMPTY_SUBMISSION");
        }
        if (hasFile && allowed.stream().noneMatch(t -> t.trim().equalsIgnoreCase("FILE"))) {
            throw new BadRequestException("FILE_SUBMISSION_NOT_ALLOWED");
        }
        if (hasText && allowed.stream().noneMatch(t -> t.trim().equalsIgnoreCase("TEXT"))) {
            throw new BadRequestException("TEXT_SUBMISSION_NOT_ALLOWED");
        }
        if (hasUrl && allowed.stream().noneMatch(t -> t.trim().equalsIgnoreCase("URL"))) {
            throw new BadRequestException("URL_SUBMISSION_NOT_ALLOWED");
        }
        return hasFile
                ? authorizeSubmissionAttachments(UUID.fromString(assignment.id()), studentId, request.attachments())
                : List.of();
    }

    private List<AttachmentRef> authorizeSubmissionAttachments(UUID assignmentId, String studentId,
            List<AttachmentRef> attachments) {
        return attachments.stream()
                .map(ref -> {
                    if (ref == null || ref.storageKey() == null || ref.storageKey().isBlank()) {
                        throw new BadRequestException("ATTACHMENT_STORAGE_KEY_REQUIRED");
                    }
                    AttachmentUploadGrant grant = uploadGrants
                            .findByAssignmentIdAndStudentIdAndStorageKey(assignmentId, studentId, ref.storageKey())
                            .orElseThrow(() -> new BadRequestException("ATTACHMENT_UPLOAD_NOT_OWNED"));
                    if (grant.isConsumed()) {
                        throw new BadRequestException("ATTACHMENT_UPLOAD_ALREADY_USED");
                    }
                    if (!storage.exists(grant.getStorageKey())) {
                        throw new BadRequestException("ATTACHMENT_UPLOAD_NOT_FOUND");
                    }
                    return new AttachmentRef(
                            ref.mediaAssetId(),
                            grant.getFileName(),
                            grant.getStorageKey(),
                            grant.getContentType(),
                            grant.getSizeBytes() == null ? ref.sizeBytes() : grant.getSizeBytes());
                })
                .toList();
    }

    private void consumeAttachmentGrants(UUID assignmentId, String studentId, List<AttachmentRef> attachments,
            UUID submissionId, Instant consumedAt) {
        for (AttachmentRef ref : attachments) {
            uploadGrants.findByAssignmentIdAndStudentIdAndStorageKey(assignmentId, studentId, ref.storageKey())
                    .ifPresent(grant -> {
                        grant.consume(submissionId, consumedAt);
                        uploadGrants.save(grant);
                    });
        }
    }

    private String safeFileName(String fileName) {
        String safe = fileName == null ? "" : fileName.trim();
        if (safe.isBlank()) {
            return "file";
        }
        return safe.replaceAll("[\\\\/]+", "_");
    }

    private String normalizeContentType(String contentType) {
        return contentType == null || contentType.isBlank()
                ? "application/octet-stream"
                : contentType.trim();
    }

    private BigDecimal resolveRawScore(AssignmentDto assignment, SubmissionDto submission,
            GradeSubmissionRequestDto req) {
        BigDecimal score;
        if (req.rubricScores() != null && !req.rubricScores().isEmpty()) {
            validateRubricScores(assignment, req);
            score = req.rubricScores().stream()
                    .map(s -> s.points() == null ? BigDecimal.ZERO : s.points())
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
        } else if (req.rawScore() != null) {
            score = req.rawScore();
        } else {
            throw new BadRequestException("GRADE_PAYLOAD_REQUIRED");
        }
        if (score.compareTo(BigDecimal.ZERO) < 0) {
            throw new BadRequestException("NEGATIVE_SCORE");
        }
        BigDecimal cap = assignment.maxScore();
        if (score.compareTo(cap) > 0) {
            throw new BadRequestException("SCORE_EXCEEDS_MAX");
        }
        return score;
    }

    private void validateRubricScores(AssignmentDto assignment, GradeSubmissionRequestDto req) {
        RubricDto rubric = assignments.findRubricByAssignment(UUID.fromString(assignment.id()))
                .orElseThrow(() -> new BadRequestException("RUBRIC_NOT_SET"));
        List<RubricCriterionDto> criteria = rubric.criteria() == null ? List.of() : rubric.criteria();
        Map<String, BigDecimal> maxPointsByCriterion = criteria.stream()
                .collect(java.util.stream.Collectors.toMap(
                        criterion -> criterion.id(),
                        criterion -> criterion.maxPoints()));
        Set<String> seenCriterionIds = new HashSet<>();
        for (var score : req.rubricScores()) {
            if (!seenCriterionIds.add(score.criterionId())) {
                throw new BadRequestException("DUPLICATE_RUBRIC_CRITERION_SCORE");
            }
            BigDecimal maxPoints = maxPointsByCriterion.get(score.criterionId());
            if (maxPoints == null) {
                throw new BadRequestException("RUBRIC_CRITERION_NOT_ON_ASSIGNMENT");
            }
            BigDecimal points = score.points() == null ? BigDecimal.ZERO : score.points();
            if (points.compareTo(maxPoints) > 0) {
                throw new BadRequestException("RUBRIC_SCORE_EXCEEDS_CRITERION_MAX");
            }
        }
    }

    private BigDecimal computeLatePenaltyPercent(AssignmentDto assignment, SubmissionDto submission) {
        if (!submission.isLate() || assignment.latePenaltyPercent().compareTo(BigDecimal.ZERO) == 0) {
            return BigDecimal.ZERO;
        }
        int intervalMinutes = "HOUR".equalsIgnoreCase(assignment.latePenaltyInterval()) ? 60 : 24 * 60;
        int intervalsLate = Math.max(1, (int) Math.ceil((double) submission.minutesLate() / intervalMinutes));
        BigDecimal pct = assignment.latePenaltyPercent().multiply(BigDecimal.valueOf(intervalsLate));
        BigDecimal cap = assignment.latePenaltyMaxPercent() == null ? ONE_HUNDRED : assignment.latePenaltyMaxPercent();
        return pct.min(cap).setScale(2, RoundingMode.HALF_UP);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
