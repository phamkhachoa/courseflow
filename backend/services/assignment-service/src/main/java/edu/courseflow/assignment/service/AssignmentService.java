package edu.courseflow.assignment.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.AttachmentRef;
import edu.courseflow.assignment.dto.AssignmentDtos.CreateAssignmentRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.GradeSubmissionRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.PresignedDownloadDto;
import edu.courseflow.assignment.dto.AssignmentDtos.PresignedUploadDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RequestUploadUrlDto;
import edu.courseflow.assignment.dto.AssignmentDtos.RubricDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmissionDto;
import edu.courseflow.assignment.dto.AssignmentDtos.SubmitAssignmentRequestDto;
import edu.courseflow.assignment.dto.AssignmentDtos.UpsertRubricRequestDto;
import edu.courseflow.assignment.repository.AssignmentRepository;
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
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
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

    public AssignmentService(AssignmentRepository assignments,
            ObjectStorageClient storage,
            ObjectMapper objectMapper,
            CourseAccessClient courseAccess) {
        this.assignments = assignments;
        this.storage = storage;
        this.objectMapper = objectMapper;
        this.courseAccess = courseAccess;
    }

    // ---------- Reads ----------

    public List<AssignmentDto> listByCourse(UUID courseId) {
        return assignments.listByCourse(courseId);
    }

    public AssignmentDto get(UUID assignmentId) {
        return assignments.find(assignmentId)
                .orElseThrow(() -> new NotFoundException("Assignment not found: " + assignmentId));
    }

    public List<SubmissionDto> listSubmissions(UUID assignmentId, String studentId) {
        get(assignmentId);
        return assignments.listSubmissionsForStudent(assignmentId, studentId);
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
    public SubmissionDto submit(UUID assignmentId, String studentId, SubmitAssignmentRequestDto request) {
        AssignmentDto assignment = get(assignmentId);
        courseAccess.requireStudentCourseAccess(studentId, UUID.fromString(assignment.courseId()));
        Instant now = Instant.now();

        if (assignment.availableAt() != null && now.isBefore(assignment.availableAt())) {
            throw new BadRequestException("ASSIGNMENT_NOT_AVAILABLE_YET");
        }
        if (assignment.lockAt() != null && now.isAfter(assignment.lockAt())) {
            throw new BadRequestException("ASSIGNMENT_LOCKED");
        }
        validateSubmissionPayload(assignment, request);

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
                request.attachments());

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

    public PresignedUploadDto presignUpload(UUID assignmentId, RequestUploadUrlDto req) {
        get(assignmentId);
        String key = storage.buildKey(STORAGE_PREFIX + "/" + assignmentId, req.fileName());
        PresignedUrl presigned = storage.presignPut(key, req.contentType());
        return new PresignedUploadDto(presigned.storageKey(), presigned.url(), presigned.expiresAt());
    }

    public AttachmentRef proxyUpload(UUID assignmentId, MultipartFile file) {
        get(assignmentId);
        if (file == null || file.isEmpty()) {
            throw new BadRequestException("Uploaded file is empty");
        }
        String fileName = file.getOriginalFilename() == null ? "file" : file.getOriginalFilename();
        String contentType = file.getContentType() == null ? "application/octet-stream" : file.getContentType();
        String key = storage.buildKey(STORAGE_PREFIX + "/" + assignmentId, fileName);
        try {
            storage.put(key, file.getInputStream(), file.getSize(), contentType);
        } catch (IOException ex) {
            throw new BadRequestException("Failed to read uploaded file: " + ex.getMessage());
        }
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

    private void validateSubmissionPayload(AssignmentDto assignment, SubmitAssignmentRequestDto request) {
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
    }

    private BigDecimal resolveRawScore(AssignmentDto assignment, SubmissionDto submission,
            GradeSubmissionRequestDto req) {
        BigDecimal score;
        if (req.rubricScores() != null && !req.rubricScores().isEmpty()) {
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
