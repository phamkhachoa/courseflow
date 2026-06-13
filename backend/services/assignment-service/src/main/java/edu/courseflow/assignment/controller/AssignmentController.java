package edu.courseflow.assignment.controller;

import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentDto;
import edu.courseflow.assignment.dto.AssignmentDtos.AssignmentReadinessDto;
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
import edu.courseflow.assignment.service.AssignmentService;
import edu.courseflow.assignment.web.Authz;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
public class AssignmentController {

    private final AssignmentService assignments;
    private final CourseAccessClient courseAccess;
    private final String serviceToken;

    public AssignmentController(AssignmentService assignments,
            CourseAccessClient courseAccess,
            @Value("${courseflow.security.service-token:}") String serviceToken) {
        this.assignments = assignments;
        this.courseAccess = courseAccess;
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    @GetMapping("/internal/assignments")
    public List<AssignmentDto> list(@RequestParam UUID courseId, CurrentUser user) {
        Authz.callerId(user);
        if (Authz.isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, courseId);
            return assignments.listByCourse(courseId);
        }
        courseAccess.requireCourseAccess(user, courseId);
        return assignments.listVisibleByCourse(courseId);
    }

    @PostMapping("/internal/assignments")
    public AssignmentDto create(@Valid @RequestBody CreateAssignmentRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(request.courseId()));
        return assignments.create(request);
    }

    @GetMapping("/internal/assignments/{assignmentId}")
    public AssignmentDto get(@PathVariable UUID assignmentId, CurrentUser user) {
        AssignmentDto assignment = assignments.get(assignmentId);
        requireReadableAssignment(user, assignment);
        return assignment;
    }

    @GetMapping("/internal/assignments/{assignmentId}/readiness")
    public AssignmentReadinessDto readiness(@PathVariable UUID assignmentId,
            @RequestHeader(value = CourseAccessClient.SERVICE_TOKEN_HEADER, required = false) String token) {
        requireServiceToken(token);
        return assignments.readiness(assignmentId);
    }

    @PostMapping("/internal/assignments/{assignmentId}/publish")
    public AssignmentDto publish(@PathVariable UUID assignmentId, CurrentUser user) {
        Authz.requireStaff(user);
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.publish(assignmentId);
    }

    @PostMapping("/internal/assignments/{assignmentId}/draft")
    public AssignmentDto draft(@PathVariable UUID assignmentId, CurrentUser user) {
        Authz.requireStaff(user);
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.draft(assignmentId);
    }

    @PostMapping("/internal/assignments/{assignmentId}/archive")
    public AssignmentDto archive(@PathVariable UUID assignmentId, CurrentUser user) {
        Authz.requireStaff(user);
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.archive(assignmentId);
    }

    // ---- Submissions ----

    @PostMapping("/internal/assignments/{assignmentId}/submissions")
    public SubmissionDto submit(@PathVariable UUID assignmentId,
            @Valid @RequestBody SubmitAssignmentRequestDto request, CurrentUser user) {
        // studentId is the authenticated caller, never trusted from the body.
        return assignments.submit(assignmentId, Authz.callerId(user), request);
    }

    @GetMapping("/internal/assignments/{assignmentId}/submissions")
    public List<SubmissionDto> listSubmissions(@PathVariable UUID assignmentId,
            @RequestParam String studentId, CurrentUser user) {
        // A student may only list their own submissions; staff may view any student's.
        Authz.requireSelfOrStaff(user, studentId);
        AssignmentDto assignment = assignments.get(assignmentId);
        UUID courseId = UUID.fromString(assignment.courseId());
        if (Authz.isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, courseId);
        } else {
            courseAccess.requireCourseAccess(user, UUID.fromString(assignment.courseId()));
        }
        return assignments.listSubmissions(assignmentId, studentId);
    }

    @PostMapping("/internal/submissions/{submissionId}/grade")
    public SubmissionDto grade(@PathVariable UUID submissionId,
            @Valid @RequestBody GradeSubmissionRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        SubmissionDto submission = assignments.getSubmission(submissionId);
        AssignmentDto assignment = assignments.get(UUID.fromString(submission.assignmentId()));
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.grade(submissionId, Authz.callerId(user), request);
    }

    // ---- Rubric ----

    @GetMapping("/internal/assignments/{assignmentId}/rubric")
    public RubricDto getRubric(@PathVariable UUID assignmentId, CurrentUser user) {
        AssignmentDto assignment = assignments.get(assignmentId);
        requireReadableAssignment(user, assignment);
        return assignments.getRubric(assignmentId);
    }

    @PutMapping("/internal/assignments/{assignmentId}/rubric")
    public RubricDto upsertRubric(@PathVariable UUID assignmentId,
            @Valid @RequestBody UpsertRubricRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.upsertRubric(assignmentId, request);
    }

    // ---- Storage (MinIO direct upload) ----

    @PostMapping("/internal/assignments/{assignmentId}/attachments/upload-url")
    public PresignedUploadDto presignUpload(@PathVariable UUID assignmentId,
            @Valid @RequestBody RequestUploadUrlDto request, CurrentUser user) {
        String callerId = Authz.callerId(user);
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.presignUpload(assignmentId, callerId, request);
    }

    @PostMapping(value = "/internal/assignments/{assignmentId}/attachments/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public AttachmentRef proxyUpload(@PathVariable UUID assignmentId,
            @RequestPart("file") MultipartFile file, CurrentUser user) {
        String callerId = Authz.callerId(user);
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.proxyUpload(assignmentId, callerId, file);
    }

    @GetMapping("/internal/submissions/{submissionId}/attachments/download-url")
    public PresignedDownloadDto downloadUrl(@PathVariable UUID submissionId,
            @RequestParam String storageKey, CurrentUser user) {
        // Student may only download attachments on their own submission; staff may download any.
        SubmissionDto sub = assignments.getSubmission(submissionId);
        Authz.requireSelfOrStaff(user, sub.studentId());
        AssignmentDto assignment = assignments.get(UUID.fromString(sub.assignmentId()));
        UUID courseId = UUID.fromString(assignment.courseId());
        if (Authz.isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, courseId);
        } else {
            courseAccess.requireCourseAccess(user, courseId);
        }
        return assignments.presignDownloadAttachment(submissionId, storageKey);
    }

    private void requireServiceToken(String token) {
        if (serviceToken.isBlank() || token == null || !serviceToken.equals(token.trim())) {
            throw new edu.courseflow.assignment.web.ForbiddenException("Service token required");
        }
    }

    private void requireReadableAssignment(CurrentUser user, AssignmentDto assignment) {
        UUID courseId = UUID.fromString(assignment.courseId());
        if (Authz.isStaff(user)) {
            courseAccess.requireCourseStaffAccess(user, courseId);
            return;
        }
        courseAccess.requireCourseAccess(user, courseId);
        assignments.requireLearnerVisible(assignment);
    }
}
