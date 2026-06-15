package edu.courseflow.enrollment.repository;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.enrollment.dto.EnrollmentDtos.AuditLogEntryDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.BatchEnrollRequestDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.BatchEnrollResultDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentStatsDto;
import edu.courseflow.enrollment.dto.EnrollmentDtos.WaitlistEntryDto;
import edu.courseflow.enrollment.mapper.EnrollmentMapper;
import edu.courseflow.enrollment.model.CourseCapacity;
import edu.courseflow.enrollment.model.Enrollment;
import edu.courseflow.enrollment.model.EnrollmentAuditLog;
import edu.courseflow.enrollment.model.OutboxEvent;
import edu.courseflow.enrollment.model.WaitlistEntry;
import edu.courseflow.enrollment.repository.EnrollmentJpaRepository.EnrollmentBenefitReconciliationRow;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.support.TransactionTemplate;

@Repository
public class EnrollmentRepository {

    private final EnrollmentJpaRepository enrollments;
    private final CourseCapacityJpaRepository capacities;
    private final WaitlistEntryJpaRepository waitlist;
    private final EnrollmentAuditLogJpaRepository auditLog;
    private final OutboxEventJpaRepository outbox;
    private final ObjectMapper objectMapper;
    private final EnrollmentMapper mapper;
    private final TransactionTemplate transactionTemplate;

    public EnrollmentRepository(EnrollmentJpaRepository enrollments,
            CourseCapacityJpaRepository capacities,
            WaitlistEntryJpaRepository waitlist,
            EnrollmentAuditLogJpaRepository auditLog,
            OutboxEventJpaRepository outbox,
            ObjectMapper objectMapper,
            EnrollmentMapper mapper,
            TransactionTemplate transactionTemplate) {
        this.enrollments = enrollments;
        this.capacities = capacities;
        this.waitlist = waitlist;
        this.auditLog = auditLog;
        this.outbox = outbox;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
        this.transactionTemplate = transactionTemplate;
    }

    public List<EnrollmentDto> list(UUID courseId, String studentId) {
        List<Enrollment> rows;
        if (courseId != null && studentId != null) {
            rows = enrollments.findByCourseIdAndStudentIdOrderByEnrolledAtDesc(courseId, studentId);
        } else if (courseId != null) {
            rows = enrollments.findByCourseIdOrderByEnrolledAtDesc(courseId);
        } else if (studentId != null) {
            rows = enrollments.findByStudentIdOrderByEnrolledAtDesc(studentId);
        } else {
            rows = enrollments.findAll(Sort.by(Sort.Direction.DESC, "enrolledAt"));
        }
        return rows.stream().map(this::toEnrollmentDto).toList();
    }

    public List<EnrollmentDto> listActiveRoster(UUID courseId, UUID cohortId) {
        List<Enrollment> rows = cohortId == null
                ? enrollments.findByCourseIdAndStatusOrderByEnrolledAtDesc(courseId, "ACTIVE")
                : enrollments.findByCourseIdAndSectionIdAndStatusOrderByEnrolledAtDesc(courseId, cohortId, "ACTIVE");
        return rows.stream().map(this::toEnrollmentDto).toList();
    }

    public List<EnrollmentBenefitReconciliationRow> benefitReconciliationRows(
            UUID enrollmentId,
            UUID courseId,
            String studentId,
            int limit) {
        return enrollments.benefitReconciliationRows(
                enrollmentId,
                courseId,
                studentId,
                PageRequest.of(0, Math.max(1, limit)));
    }

    public Optional<EnrollmentDto> find(String studentId, UUID courseId) {
        return enrollments.findByStudentIdAndCourseId(studentId, courseId).map(this::toEnrollmentDto);
    }

    public Optional<EnrollmentDto> findCourseAccess(String studentId, UUID courseId) {
        return enrollments.findFirstByStudentIdAndCourseIdAndStatusIn(
                        studentId, courseId, List.of("ACTIVE", "COMPLETED"))
                .map(this::toEnrollmentDto);
    }

    public Optional<EnrollmentDto> findById(UUID id) {
        return enrollments.findById(id).map(this::toEnrollmentDto);
    }

    /**
     * Insert a fresh ACTIVE enrollment or, when one already exists (a previously DROPPED row being
     * re-enrolled), reset it back to a clean ACTIVE state.
     */
    public EnrollmentDto enroll(String studentId, UUID courseId) {
        Enrollment enrollment = enrollments.findByStudentIdAndCourseId(studentId, courseId)
                .map(existing -> {
                    if ("COMPLETED".equals(existing.getStatus())) {
                        throw new ConflictException("Enrollment already completed; cannot re-enroll");
                    }
                    existing.activate();
                    return existing;
                })
                .orElseGet(() -> new Enrollment(UUID.randomUUID(), studentId, courseId, null));
        return toEnrollmentDto(enrollments.save(enrollment));
    }

    public EnrollmentDto enrollPendingPayment(String studentId, UUID courseId, String actorId, String reason) {
        Enrollment enrollment = enrollments.findByStudentIdAndCourseId(studentId, courseId)
                .map(existing -> {
                    if ("ACTIVE".equals(existing.getStatus())) {
                        throw new ConflictException("Student already actively enrolled");
                    }
                    if ("COMPLETED".equals(existing.getStatus())) {
                        throw new ConflictException("Enrollment already completed; cannot re-enroll");
                    }
                    existing.pendingPayment();
                    return existing;
                })
                .orElseGet(() -> {
                    Enrollment created = new Enrollment(UUID.randomUUID(), studentId, courseId, null);
                    created.pendingPayment();
                    return created;
                });
        Enrollment saved = enrollments.save(enrollment);
        insertAudit(saved.getId(), actorId, "CHECKOUT_PENDING_PAYMENT", null, "PENDING_PAYMENT", reason);
        return toEnrollmentDto(saved);
    }

    /** Active-enrollment seat count for a course. */
    public int countActive(UUID courseId) {
        return enrollments.countByCourseIdAndStatus(courseId, "ACTIVE");
    }

    /** Seat holds include payment-pending checkout rows so paid learners cannot oversell a course. */
    public int countOccupiedSeats(UUID courseId) {
        return enrollments.countByCourseIdAndStatusIn(courseId, List.of("ACTIVE", "PENDING_PAYMENT"));
    }

    /**
     * Configured capacity for a course. Empty optional means "no limit configured" (unlimited).
     * Locks the capacity row with a pessimistic JPA lock so concurrent enrolls serialize on the
     * seat check and cannot both slip past a full course.
     */
    public Optional<Integer> lockCapacity(UUID courseId) {
        return capacities.lockByCourseId(courseId)
                .map(CourseCapacity::getCapacity)
                .flatMap(Optional::ofNullable);
    }

    public boolean hasCapacityRow(UUID courseId) {
        return capacities.existsById(courseId);
    }

    public void setCapacity(UUID courseId, Integer capacity) {
        CourseCapacity row = capacities.findById(courseId)
                .orElseGet(() -> new CourseCapacity(courseId, capacity));
        row.setCapacity(capacity);
        capacities.save(row);
    }

    /** First WAITING entry for a course in FIFO (position) order. */
    public Optional<WaitlistEntryDto> firstWaiting(UUID courseId) {
        return waitlist.findFirstByCourseIdAndStatusOrderByPositionAsc(courseId, "WAITING")
                .map(this::toWaitlistEntryDto);
    }

    public void markWaitlistPromoted(UUID waitlistId) {
        waitlist.findById(waitlistId).ifPresent(entry -> {
            entry.markPromoted();
            waitlist.save(entry);
        });
    }

    public void markWaitlistSkipped(UUID waitlistId) {
        waitlist.findById(waitlistId).ifPresent(entry -> {
            entry.markSkipped();
            waitlist.save(entry);
        });
    }

    /**
     * Renumber the remaining WAITING entries for a course into a gapless 1..n FIFO sequence after a
     * promotion/removal. This keeps the previous two-phase behavior but does it through managed JPA
     * entities rather than a window-function native update.
     */
    public void compactWaitlist(UUID courseId) {
        List<WaitlistEntry> waiting = waitlist.findByCourseIdAndStatusOrderByPositionAsc(courseId, "WAITING");
        for (WaitlistEntry entry : waiting) {
            entry.setPosition(-Math.abs(entry.getPosition()));
        }
        waitlist.saveAllAndFlush(waiting);

        int position = 1;
        for (WaitlistEntry entry : waiting) {
            entry.setPosition(position++);
        }
        waitlist.saveAll(waiting);
    }

    public EnrollmentDto changeStatus(UUID id, String actorId, String newStatus, String reason) {
        Enrollment existing = enrollments.findById(id).orElseThrow(
                () -> new RuntimeException("Enrollment not found: " + id));
        String oldStatus = existing.getStatus();
        existing.changeStatus(actorId, newStatus, reason);
        insertAudit(id, actorId, "STATUS_CHANGE", oldStatus, newStatus, reason);
        return toEnrollmentDto(enrollments.save(existing));
    }

    /**
     * Capacity-aware batch enroll. Each entry is checked against capacity before a seat is taken.
     * Existing enrollments are skipped to preserve the old DO NOTHING semantics.
     */
    public BatchEnrollResultDto batchEnroll(List<BatchEnrollRequestDto.SingleEnrollDto> entries, String actorId) {
        int enrolled = 0;
        int skipped = 0;
        List<String> errors = new ArrayList<>();

        for (BatchEnrollRequestDto.SingleEnrollDto entry : entries) {
            try {
                BatchEnrollEntryResult result = transactionTemplate.execute(
                        ignored -> batchEnrollOne(entry, actorId));
                if (result == null) {
                    errors.add(errorPrefix(entry) + ": transaction did not return a result");
                } else if (result.error() != null) {
                    errors.add(result.error());
                } else if (result.skipped()) {
                    skipped++;
                } else if (result.enrolled()) {
                    enrolled++;
                }
            } catch (Exception e) {
                errors.add(errorPrefix(entry) + ": " + e.getMessage());
            }
        }

        return new BatchEnrollResultDto(enrolled, skipped, errors);
    }

    private BatchEnrollEntryResult batchEnrollOne(BatchEnrollRequestDto.SingleEnrollDto entry, String actorId) {
        UUID courseId = UUID.fromString(entry.courseId());
        UUID sectionId = entry.sectionId() != null ? UUID.fromString(entry.sectionId()) : null;

        Optional<Integer> capacity = lockCapacity(courseId);
        if (capacity.isPresent() && countActive(courseId) >= capacity.get()) {
            return BatchEnrollEntryResult.error(errorPrefix(entry)
                    + ": course is full (capacity " + capacity.get() + ")");
        }

        if (enrollments.findByStudentIdAndCourseId(entry.studentId(), courseId).isPresent()) {
            return BatchEnrollEntryResult.skippedResult();
        }

        Enrollment enrollment = enrollments.save(new Enrollment(
                UUID.randomUUID(), entry.studentId(), courseId, sectionId));
        EnrollmentDto dto = toEnrollmentDto(enrollment);
        outbox(UUID.fromString(dto.id()), "enrollment", "enrollment.created", toJson(Map.of(
                "eventId", UUID.randomUUID().toString(),
                "enrollmentId", dto.id(),
                "studentId", dto.studentId(),
                "courseId", dto.courseId(),
                "actorId", actorId,
                "enrolledAt", dto.enrolledAt().toString())));
        return BatchEnrollEntryResult.enrolledResult();
    }

    public EnrollmentStatsDto stats(UUID courseId) {
        return new EnrollmentStatsDto(
                courseId.toString(),
                enrollments.countByCourseIdAndStatus(courseId, "ACTIVE"),
                enrollments.countByCourseIdAndStatus(courseId, "DROPPED"),
                enrollments.countByCourseIdAndStatus(courseId, "COMPLETED"),
                waitlist.countByCourseId(courseId));
    }

    public List<AuditLogEntryDto> auditLog(UUID enrollmentId) {
        return auditLog.findByEnrollmentIdOrderByCreatedAtDesc(enrollmentId).stream()
                .map(mapper::toDto)
                .toList();
    }

    public List<AuditLogEntryDto> auditLog(
            UUID enrollmentId,
            UUID courseId,
            String studentId,
            String correlationId,
            int limit) {
        return auditLog.queryOperationsAudit(
                        enrollmentId,
                        courseId,
                        studentId,
                        correlationId,
                        PageRequest.of(0, Math.max(1, limit)))
                .stream()
                .map(mapper::toDto)
                .toList();
    }

    public void outbox(UUID aggregateId, String aggregateType, String eventType, String payload) {
        outbox.save(new OutboxEvent(aggregateId, aggregateType, eventType, payload));
    }

    public void recordAudit(UUID enrollmentId, String actorId, String action,
                             String oldStatus, String newStatus, String reason) {
        insertAudit(enrollmentId, actorId == null ? "system" : actorId, action, oldStatus, newStatus, reason);
    }

    private void insertAudit(UUID enrollmentId, String actorId, String action,
                              String oldStatus, String newStatus, String reason) {
        auditLog.save(new EnrollmentAuditLog(enrollmentId, actorId, action, oldStatus, newStatus, reason));
    }

    public List<WaitlistEntryDto> listWaitlist(UUID courseId) {
        return waitlist.findByCourseIdOrderByPositionAsc(courseId).stream()
                .map(this::toWaitlistEntryDto)
                .toList();
    }

    public WaitlistEntryDto addToWaitlist(String studentId, UUID courseId) {
        enrollments.findByStudentIdAndCourseId(studentId, courseId).ifPresent(existing -> {
            if ("ACTIVE".equals(existing.getStatus())) {
                throw new ConflictException("Student already actively enrolled");
            }
            if ("COMPLETED".equals(existing.getStatus())) {
                throw new ConflictException("Enrollment already completed; cannot join waitlist");
            }
        });

        WaitlistEntry entry = waitlist.findByStudentIdAndCourseId(studentId, courseId)
                .map(existing -> {
                    if ("WAITING".equals(existing.getStatus())) {
                        return existing;
                    }
                    existing.requeue(waitlist.nextPosition(courseId));
                    return existing;
                })
                .orElseGet(() -> new WaitlistEntry(UUID.randomUUID(), studentId, courseId, waitlist.nextPosition(courseId)));
        return toWaitlistEntryDto(waitlist.save(entry));
    }

    private String errorPrefix(BatchEnrollRequestDto.SingleEnrollDto entry) {
        return "studentId=" + entry.studentId() + " courseId=" + entry.courseId();
    }

    private record BatchEnrollEntryResult(boolean enrolled, boolean skipped, String error) {
        static BatchEnrollEntryResult enrolledResult() {
            return new BatchEnrollEntryResult(true, false, null);
        }

        static BatchEnrollEntryResult skippedResult() {
            return new BatchEnrollEntryResult(false, true, null);
        }

        static BatchEnrollEntryResult error(String error) {
            return new BatchEnrollEntryResult(false, false, error);
        }
    }

    private EnrollmentDto toEnrollmentDto(Enrollment enrollment) {
        return mapper.toDto(enrollment);
    }

    private WaitlistEntryDto toWaitlistEntryDto(WaitlistEntry entry) {
        return mapper.toDto(entry);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (com.fasterxml.jackson.core.JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
