package edu.courseflow.enrollment.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
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
import edu.courseflow.enrollment.repository.EnrollmentRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class EnrollmentService {

    /**
     * Allowed enrollment status transitions.
     * <ul>
     *   <li>ACTIVE    -> DROPPED, COMPLETED</li>
     *   <li>DROPPED   -> ACTIVE (re-enroll)</li>
     *   <li>COMPLETED -> (terminal: no transitions)</li>
     * </ul>
     * A no-op transition to the same status is rejected as a bad request.
     */
    private static final Map<String, Set<String>> ALLOWED_TRANSITIONS = Map.of(
            "ACTIVE", Set.of("DROPPED", "COMPLETED"),
            "DROPPED", Set.of("ACTIVE"),
            "COMPLETED", Set.of());

    private final EnrollmentRepository enrollments;
    private final ObjectMapper objectMapper;
    private final CourseAccessClient courseAccess;

    public EnrollmentService(EnrollmentRepository enrollments, ObjectMapper objectMapper, CourseAccessClient courseAccess) {
        this.enrollments = enrollments;
        this.objectMapper = objectMapper;
        this.courseAccess = courseAccess;
    }

    public List<EnrollmentDto> list(Optional<UUID> courseId, Optional<String> studentId, CurrentUser user) {
        if (isPlatformAdmin(user)) {
            return enrollments.list(courseId.orElse(null), studentId.orElse(null));
        }
        if (isStaff(user)) {
            UUID scopedCourse = courseId.orElseThrow(() ->
                    new ForbiddenException("Staff roster reads must be scoped to a course"));
            courseAccess.requireCourseStaffAccess(user, scopedCourse);
            return enrollments.list(scopedCourse, studentId.orElse(null));
        }
        String caller = callerId(user);
        if (studentId.isPresent() && !studentId.get().equals(caller)) {
            throw new ForbiddenException("Students may only read their own enrollment");
        }
        return enrollments.list(courseId.orElse(null), caller);
    }

    public List<EnrollmentDto> learnerMemberships(String studentId) {
        if (studentId == null || studentId.isBlank()) {
            throw new BadRequestException("studentId is required");
        }
        return enrollments.list(null, studentId.trim());
    }

    /**
     * Enroll a student. A STUDENT caller always enrolls themselves; the studentId in the body is
     * ignored. Only INSTRUCTOR/ADMIN may enroll someone else. Capacity is enforced inside the
     * transaction by locking the capacity row and counting active seats; a full course is rejected
     * with 409 so the caller can fall back to the waitlist.
     */
    @Transactional
    public EnrollmentDto enroll(EnrollRequestDto request, CurrentUser user) {
        UUID courseId = parseUuid(request.courseId(), "courseId");
        courseAccess.requirePublishedCourse(courseId);
        String studentId = resolveTargetStudent(request.studentId(), user, courseId);

        enrollments.find(studentId, courseId).ifPresent(existing -> {
            if ("ACTIVE".equals(existing.status())) {
                throw new ConflictException("Student already actively enrolled");
            }
            if ("COMPLETED".equals(existing.status())) {
                throw new ConflictException("Enrollment already completed; cannot re-enroll");
            }
        });

        enforceCapacity(courseId);

        EnrollmentDto dto = enrollments.enroll(studentId, courseId);
        // Outbox write stays in the same transaction: if it fails, the enrollment rolls back too.
        enrollments.outbox(UUID.fromString(dto.id()), "enrollment", "enrollment.created", toJson(Map.of(
                "eventId", UUID.randomUUID().toString(),
                "enrollmentId", dto.id(),
                "studentId", dto.studentId(),
                "courseId", dto.courseId(),
                "enrolledAt", dto.enrolledAt().toString()
        )));
        return dto;
    }

    public Optional<EnrollmentDto> get(UUID id) {
        return enrollments.findById(id);
    }

    public EnrollmentDto get(UUID id, CurrentUser user) {
        EnrollmentDto enrollment = enrollments.findById(id)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment not found: " + id));
        requireSelfOrCourseStaff(enrollment, user);
        return enrollment;
    }

    public CourseAccessDto courseAccess(UUID courseId, String studentId) {
        Optional<EnrollmentDto> found = enrollments.findCourseAccess(studentId, courseId);
        return new CourseAccessDto(
                courseId.toString(),
                studentId,
                found.isPresent(),
                found.map(EnrollmentDto::status).orElse(null));
    }

    public List<EnrollmentDto> activeRoster(UUID courseId, Optional<UUID> cohortId) {
        return enrollments.listActiveRoster(courseId, cohortId.orElse(null));
    }

    /**
     * Drive an enrollment through its state machine.
     * <ul>
     *   <li>DROPPED: a STUDENT may only drop their own enrollment; INSTRUCTOR/ADMIN may drop anyone.</li>
     *   <li>COMPLETED: INSTRUCTOR/ADMIN only.</li>
     *   <li>ACTIVE (re-enroll from DROPPED): a STUDENT may re-enroll themselves; INSTRUCTOR/ADMIN anyone.
     *       Capacity is re-checked.</li>
     * </ul>
     */
    @Transactional
    public EnrollmentDto changeStatus(UUID id, ChangeStatusRequestDto req, CurrentUser user) {
        String newStatus = req.newStatus();
        if (!ALLOWED_TRANSITIONS.containsKey(newStatus)) {
            throw new BadRequestException("Invalid status: " + newStatus);
        }
        EnrollmentDto existing = enrollments.findById(id)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment not found: " + id));
        String oldStatus = existing.status();

        Set<String> allowedFrom = ALLOWED_TRANSITIONS.getOrDefault(oldStatus, Set.of());
        if (!allowedFrom.contains(newStatus)) {
            throw new BadRequestException(
                    "Illegal transition " + oldStatus + " -> " + newStatus);
        }

        authorizeTransition(existing, newStatus, user);

        if ("ACTIVE".equals(newStatus)) {
            UUID courseId = parseUuid(existing.courseId(), "courseId");
            courseAccess.requirePublishedCourse(courseId);
            enforceCapacity(courseId);
        }

        String actorId = String.valueOf(user.id());
        EnrollmentDto updated = enrollments.changeStatus(id, actorId, newStatus, req.reason());

        if ("DROPPED".equals(newStatus)) {
            enrollments.outbox(id, "enrollment", "enrollment.dropped", toJson(Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "enrollmentId", updated.id(),
                    "studentId", updated.studentId(),
                    "courseId", updated.courseId(),
                    "actorId", actorId,
                    "reason", req.reason() == null ? "" : req.reason())));
            promoteWaitlist(UUID.fromString(updated.courseId()));
        } else if ("COMPLETED".equals(newStatus)) {
            enrollments.outbox(id, "enrollment", "enrollment.completed", toJson(Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "enrollmentId", updated.id(),
                    "studentId", updated.studentId(),
                    "courseId", updated.courseId(),
                    "actorId", actorId)));
            promoteWaitlist(UUID.fromString(updated.courseId()));
        } else if ("ACTIVE".equals(newStatus)) {
            enrollments.outbox(id, "enrollment", "enrollment.created", toJson(Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "enrollmentId", updated.id(),
                    "studentId", updated.studentId(),
                    "courseId", updated.courseId(),
                    "enrolledAt", updated.enrolledAt().toString())));
        }
        return updated;
    }

    /**
     * System-driven completion triggered by a {@code course.completed} event. Transitions the
     * student's ACTIVE enrollment to COMPLETED (no human actor) and emits an
     * {@code enrollment.completed} outbox event. A missing enrollment, or one not currently ACTIVE
     * (already completed/dropped), is a no-op so the consumer stays idempotent and tolerant of
     * out-of-order events. Returns the updated enrollment when a transition occurred.
     */
    @Transactional
    public Optional<EnrollmentDto> completeForCourseCompletion(String studentId, UUID courseId) {
        Optional<EnrollmentDto> found = enrollments.find(studentId, courseId);
        if (found.isEmpty() || !"ACTIVE".equals(found.get().status())) {
            return Optional.empty();
        }
        UUID id = UUID.fromString(found.get().id());
        EnrollmentDto updated = enrollments.changeStatus(id, "system", "COMPLETED",
                "Auto-completed on course completion");
        enrollments.outbox(id, "enrollment", "enrollment.completed", toJson(Map.of(
                "eventId", UUID.randomUUID().toString(),
                "enrollmentId", updated.id(),
                "studentId", updated.studentId(),
                "courseId", updated.courseId(),
                "actorId", "system")));
        promoteWaitlist(courseId);
        return Optional.of(updated);
    }

    /** Batch enroll on behalf of other students: INSTRUCTOR/ADMIN only. */
    public BatchEnrollResultDto batchEnroll(BatchEnrollRequestDto req, CurrentUser user) {
        requireAuthenticated(user);
        for (BatchEnrollRequestDto.SingleEnrollDto entry : req.entries()) {
            UUID courseId = parseUuid(entry.courseId(), "courseId");
            courseAccess.requirePublishedCourse(courseId);
            courseAccess.requireCourseStaffAccess(user, courseId);
        }
        return enrollments.batchEnroll(req.entries(), String.valueOf(user.id()));
    }

    public EnrollmentStatsDto stats(UUID courseId) {
        return enrollments.stats(courseId);
    }

    public EnrollmentStatsDto stats(UUID courseId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        return enrollments.stats(courseId);
    }

    public List<AuditLogEntryDto> auditLog(UUID id) {
        return enrollments.auditLog(id);
    }

    public List<AuditLogEntryDto> auditLog(UUID id, CurrentUser user) {
        EnrollmentDto enrollment = enrollments.findById(id)
                .orElseThrow(() -> new edu.courseflow.commonlibrary.exception.NotFoundException(
                        "Enrollment not found: " + id));
        requireSelfOrCourseStaff(enrollment, user);
        return enrollments.auditLog(id);
    }

    public List<WaitlistEntryDto> listWaitlist(UUID courseId) {
        return enrollments.listWaitlist(courseId);
    }

    public List<WaitlistEntryDto> listWaitlist(UUID courseId, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        return enrollments.listWaitlist(courseId);
    }

    /**
     * Join the waitlist. Only allowed when the course is actually full; if seats are free the caller
     * should enroll directly (we reject with 409 to make the misuse explicit). A STUDENT joins for
     * themselves; INSTRUCTOR/ADMIN may add someone else.
     */
    @Transactional
    public WaitlistEntryDto waitlist(WaitlistRequestDto request, CurrentUser user) {
        UUID courseId = parseUuid(request.courseId(), "courseId");
        courseAccess.requirePublishedCourse(courseId);
        String studentId = resolveTargetStudent(request.studentId(), user, courseId);
        if (!isFull(courseId)) {
            throw new ConflictException("Course is not full; enroll directly instead of waitlisting");
        }
        return enrollments.addToWaitlist(studentId, courseId);
    }

    /** Set or clear (null = unlimited) per-course capacity. ADMIN/INSTRUCTOR only. */
    @Transactional
    public void setCapacity(UUID courseId, SetCapacityRequestDto request, CurrentUser user) {
        courseAccess.requireCourseStaffAccess(user, courseId);
        if (request.capacity() != null && request.capacity() < 0) {
            throw new BadRequestException("Capacity must be zero or positive");
        }
        enrollments.setCapacity(courseId, request.capacity());
    }

    @Transactional
    public void initializePublishedCourse(UUID courseId, Integer defaultCapacity) {
        if (courseId == null || enrollments.hasCapacityRow(courseId)) {
            return;
        }
        enrollments.setCapacity(courseId, defaultCapacity);
    }

    @Transactional
    public void archiveCourse(UUID courseId) {
        if (courseId != null) {
            enrollments.setCapacity(courseId, 0);
        }
    }

    // ---- internals ----

    /**
     * Enforce capacity inside the current transaction. Locks the capacity row so concurrent enrolls
     * for the same course serialize on the seat check. No capacity row, or a NULL capacity, means
     * unlimited.
     */
    private void enforceCapacity(UUID courseId) {
        if (courseId == null) {
            return;
        }
        Optional<Integer> capacity = enrollments.lockCapacity(courseId);
        if (capacity.isEmpty()) {
            return; // unlimited
        }
        int active = enrollments.countActive(courseId);
        if (active >= capacity.get()) {
            throw new ConflictException("Course is full (capacity " + capacity.get() + ")");
        }
    }

    private boolean isFull(UUID courseId) {
        Optional<Integer> capacity = enrollments.lockCapacity(courseId);
        if (capacity.isEmpty()) {
            return false; // unlimited is never full
        }
        return enrollments.countActive(courseId) >= capacity.get();
    }

    /**
     * On a drop, promote the first FIFO-waiting student into an active enrollment, provided the
     * course now has a free seat. Runs in the same transaction as the drop.
     */
    private void promoteWaitlist(UUID courseId) {
        while (!isFull(courseId)) {
            Optional<WaitlistEntryDto> next = enrollments.firstWaiting(courseId);
            if (next.isEmpty()) {
                return;
            }
            WaitlistEntryDto entry = next.get();
            Optional<EnrollmentDto> existingEnrollment = enrollments.find(entry.studentId(), courseId);
            if (existingEnrollment.isPresent()) {
                String status = existingEnrollment.get().status();
                if ("ACTIVE".equals(status) || "COMPLETED".equals(status)) {
                    enrollments.markWaitlistSkipped(UUID.fromString(entry.id()));
                    enrollments.compactWaitlist(courseId);
                    continue;
                }
            }

            EnrollmentDto promoted = enrollments.enroll(entry.studentId(), courseId);
            enrollments.markWaitlistPromoted(UUID.fromString(entry.id()));
            // Close the FIFO gap left at the head so remaining positions stay a gapless 1..n sequence.
            enrollments.compactWaitlist(courseId);
            enrollments.outbox(UUID.fromString(promoted.id()), "enrollment", "enrollment.created",
                    toJson(Map.of(
                            "eventId", UUID.randomUUID().toString(),
                            "enrollmentId", promoted.id(),
                            "studentId", promoted.studentId(),
                            "courseId", promoted.courseId(),
                            "enrolledAt", promoted.enrolledAt().toString(),
                            "promotedFromWaitlist", true)));
            return;
        }
    }

    /**
     * Resolve who an action targets: a non-privileged caller always acts on themselves, so any
     * studentId supplied in the body is ignored. Only INSTRUCTOR/ADMIN may target a different student.
     */
    private String resolveTargetStudent(String requestedStudentId, CurrentUser user, UUID courseId) {
        requireAuthenticated(user);
        String self = String.valueOf(user.id());
        if (requestedStudentId == null || requestedStudentId.isBlank() || requestedStudentId.equals(self)) {
            return self;
        }
        courseAccess.requireCourseStaffAccess(user, courseId);
        return requestedStudentId;
    }

    private void authorizeTransition(EnrollmentDto enrollment, String newStatus, CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
        UUID courseId = parseUuid(enrollment.courseId(), "courseId");
        boolean privileged = isStaff(user);
        boolean self = String.valueOf(user.id()).equals(enrollment.studentId());
        switch (newStatus) {
            case "DROPPED", "ACTIVE" -> {
                // Student may drop / re-enroll their own enrollment; privileged roles may act on anyone.
                if (!self && !privileged) {
                    throw new ForbiddenException("Students may only change their own enrollment");
                }
                if (!self) {
                    courseAccess.requireCourseStaffAccess(user, courseId);
                }
            }
            case "COMPLETED" -> {
                if (!privileged) {
                    throw new ForbiddenException("Only INSTRUCTOR or ADMIN may complete an enrollment");
                }
                courseAccess.requireCourseStaffAccess(user, courseId);
            }
            default -> throw new BadRequestException("Invalid status: " + newStatus);
        }
    }

    private void requireSelfOrCourseStaff(EnrollmentDto enrollment, CurrentUser user) {
        String self = callerId(user);
        if (self.equals(enrollment.studentId())) {
            return;
        }
        if (!isStaff(user)) {
            throw new ForbiddenException("Students may only read their own enrollment");
        }
        courseAccess.requireCourseStaffAccess(user, parseUuid(enrollment.courseId(), "courseId"));
    }

    private void requireInstructorOrAdmin(CurrentUser user) {
        requireAuthenticated(user);
        if (!isStaff(user)) {
            throw new ForbiddenException("Requires INSTRUCTOR or ADMIN role");
        }
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
    }

    private String callerId(CurrentUser user) {
        requireAuthenticated(user);
        return String.valueOf(user.id());
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole("INSTRUCTOR", "PROFESSOR", "TA", "ORG_ADMIN", "ADMIN");
    }

    private boolean isPlatformAdmin(CurrentUser user) {
        return user != null && user.hasRole("ADMIN");
    }

    private UUID parseUuid(String raw, String field) {
        try {
            return UUID.fromString(raw);
        } catch (RuntimeException ex) {
            throw new BadRequestException("Invalid " + field + ": " + raw);
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
