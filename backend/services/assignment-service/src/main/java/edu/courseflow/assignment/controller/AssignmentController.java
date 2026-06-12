package edu.courseflow.assignment.controller;

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
import edu.courseflow.assignment.service.AssignmentService;
import edu.courseflow.assignment.web.Authz;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
public class AssignmentController {

    private final AssignmentService assignments;
    private final CourseAccessClient courseAccess;

    public AssignmentController(AssignmentService assignments, CourseAccessClient courseAccess) {
        this.assignments = assignments;
        this.courseAccess = courseAccess;
    }

    @GetMapping("/internal/assignments")
    public List<AssignmentDto> list(@RequestParam UUID courseId, CurrentUser user) {
        courseAccess.requireCourseAccess(user, courseId);
        return assignments.listByCourse(courseId);
    }

    @PostMapping("/internal/assignments")
    public AssignmentDto create(@Valid @RequestBody CreateAssignmentRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        return assignments.create(request);
    }

    @GetMapping("/internal/assignments/{assignmentId}")
    public AssignmentDto get(@PathVariable UUID assignmentId, CurrentUser user) {
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseAccess(user, UUID.fromString(assignment.courseId()));
        return assignment;
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
        if (!Authz.isStaff(user)) {
            courseAccess.requireCourseAccess(user, UUID.fromString(assignment.courseId()));
        }
        return assignments.listSubmissions(assignmentId, studentId);
    }

    @PostMapping("/internal/submissions/{submissionId}/grade")
    public SubmissionDto grade(@PathVariable UUID submissionId,
            @Valid @RequestBody GradeSubmissionRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        return assignments.grade(submissionId, Authz.callerId(user), request);
    }

    // ---- Rubric ----

    @GetMapping("/internal/assignments/{assignmentId}/rubric")
    public RubricDto getRubric(@PathVariable UUID assignmentId, CurrentUser user) {
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.getRubric(assignmentId);
    }

    @PutMapping("/internal/assignments/{assignmentId}/rubric")
    public RubricDto upsertRubric(@PathVariable UUID assignmentId,
            @Valid @RequestBody UpsertRubricRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        return assignments.upsertRubric(assignmentId, request);
    }

    // ---- Storage (MinIO direct upload) ----

    @PostMapping("/internal/assignments/{assignmentId}/attachments/upload-url")
    public PresignedUploadDto presignUpload(@PathVariable UUID assignmentId,
            @Valid @RequestBody RequestUploadUrlDto request, CurrentUser user) {
        Authz.callerId(user);
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.presignUpload(assignmentId, request);
    }

    @PostMapping(value = "/internal/assignments/{assignmentId}/attachments/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public AttachmentRef proxyUpload(@PathVariable UUID assignmentId,
            @RequestPart("file") MultipartFile file, CurrentUser user) {
        Authz.callerId(user);
        AssignmentDto assignment = assignments.get(assignmentId);
        courseAccess.requireCourseAccess(user, UUID.fromString(assignment.courseId()));
        return assignments.proxyUpload(assignmentId, file);
    }

    @GetMapping("/internal/submissions/{submissionId}/attachments/download-url")
    public PresignedDownloadDto downloadUrl(@PathVariable UUID submissionId,
            @RequestParam String storageKey, CurrentUser user) {
        // Student may only download attachments on their own submission; staff may download any.
        SubmissionDto sub = assignments.getSubmission(submissionId);
        Authz.requireSelfOrStaff(user, sub.studentId());
        return assignments.presignDownloadAttachment(submissionId, storageKey);
    }
}
