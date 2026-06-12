package edu.courseflow.enrollment.controller;

import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.enrollment.dto.EnrollmentDtos.AuditLogEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.BatchEnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.BatchEnrollResultDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.ChangeStatusRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.CourseAccessDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentStatsDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.SetCapacityRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistRequestDto;
import edu.courseflow.enrollment.exception.ForbiddenException;
import edu.courseflow.enrollment.service.EnrollmentService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class EnrollmentController {

    private final EnrollmentService enrollments;
    private final String serviceToken;

    public EnrollmentController(EnrollmentService enrollments,
            @Value("${courseflow.security.service-token:}") String serviceToken) {
        this.enrollments = enrollments;
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    @GetMapping("/internal/enrollments")
    public List<EnrollmentDto> list(@RequestParam Optional<UUID> courseId,
                                    @RequestParam Optional<String> studentId,
                                    CurrentUser user) {
        return enrollments.list(courseId, visibleStudentId(studentId, user));
    }

    @PostMapping("/internal/enrollments")
    public EnrollmentDto enroll(@Valid @RequestBody EnrollRequestDto request, CurrentUser user) {
        return enrollments.enroll(request, user);
    }

    @GetMapping("/internal/enrollments/access")
    public CourseAccessDto access(@RequestParam UUID courseId,
                                  @RequestParam String studentId,
                                  @RequestHeader(value = "X-Service-Token", required = false) String token) {
        requireServiceToken(token);
        return enrollments.courseAccess(courseId, studentId);
    }

    @GetMapping("/internal/waitlist")
    public List<WaitlistEntryDto> waitlist(@RequestParam UUID courseId, CurrentUser user) {
        requireStaff(user);
        return enrollments.listWaitlist(courseId);
    }

    @PostMapping("/internal/waitlist")
    public WaitlistEntryDto joinWaitlist(@Valid @RequestBody WaitlistRequestDto request, CurrentUser user) {
        return enrollments.waitlist(request, user);
    }

    @GetMapping("/internal/enrollments/{id}")
    public EnrollmentDto get(@PathVariable UUID id, CurrentUser user) {
        EnrollmentDto enrollment = enrollments.get(id)
                .orElseThrow(() -> new NotFoundException("Enrollment not found: " + id));
        requireSelfOrStaff(user, enrollment.studentId());
        return enrollment;
    }

    @PatchMapping("/internal/enrollments/{id}/status")
    public EnrollmentDto changeStatus(@PathVariable UUID id,
                                      @Valid @RequestBody ChangeStatusRequestDto req,
                                      CurrentUser user) {
        return enrollments.changeStatus(id, req, user);
    }

    @PostMapping("/internal/enrollments/batch")
    public BatchEnrollResultDto batchEnroll(@Valid @RequestBody BatchEnrollRequestDto req, CurrentUser user) {
        return enrollments.batchEnroll(req, user);
    }

    @PutMapping("/internal/courses/{courseId}/capacity")
    public void setCapacity(@PathVariable UUID courseId,
                            @Valid @RequestBody SetCapacityRequestDto req,
                            CurrentUser user) {
        enrollments.setCapacity(courseId, req, user);
    }

    @GetMapping("/internal/enrollments/stats")
    public EnrollmentStatsDto stats(@RequestParam UUID courseId, CurrentUser user) {
        requireStaff(user);
        return enrollments.stats(courseId);
    }

    @GetMapping("/internal/enrollments/{id}/audit")
    public List<AuditLogEntryDto> auditLog(@PathVariable UUID id, CurrentUser user) {
        EnrollmentDto enrollment = enrollments.get(id)
                .orElseThrow(() -> new NotFoundException("Enrollment not found: " + id));
        requireSelfOrStaff(user, enrollment.studentId());
        return enrollments.auditLog(id);
    }

    private Optional<String> visibleStudentId(Optional<String> requestedStudentId, CurrentUser user) {
        if (isStaff(user)) {
            return requestedStudentId;
        }
        String caller = callerId(user);
        if (requestedStudentId.isPresent() && !requestedStudentId.get().equals(caller)) {
            throw new ForbiddenException("Students may only read their own enrollment");
        }
        return Optional.of(caller);
    }

    private void requireSelfOrStaff(CurrentUser user, String studentId) {
        if (isStaff(user)) {
            return;
        }
        if (!callerId(user).equals(studentId)) {
            throw new ForbiddenException("Students may only read their own enrollment");
        }
    }

    private void requireStaff(CurrentUser user) {
        callerId(user);
        if (!isStaff(user)) {
            throw new ForbiddenException("Requires INSTRUCTOR or ADMIN role");
        }
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole("INSTRUCTOR", "ADMIN");
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        return String.valueOf(user.id());
    }

    private void requireServiceToken(String token) {
        if (serviceToken.isBlank() || token == null || !serviceToken.equals(token.trim())) {
            throw new ForbiddenException("Service token required");
        }
    }
}
