package edu.courseflow.gradebook.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.gradebook.dto.GradebookDtos.GradePublishAuditDto;
import edu.courseflow.gradebook.dto.GradebookDtos.UpsertGradeEntryRequestDto;
import edu.courseflow.gradebook.model.FinalGrade;
import edu.courseflow.gradebook.model.GradeCategory;
import edu.courseflow.gradebook.model.GradeEntry;
import edu.courseflow.gradebook.model.GradeItem;
import edu.courseflow.gradebook.model.GradebookAuditLog;
import edu.courseflow.gradebook.repository.FinalGradeRepository;
import edu.courseflow.gradebook.repository.GradeCategoryRepository;
import edu.courseflow.gradebook.repository.GradeEntryRepository;
import edu.courseflow.gradebook.repository.GradeItemRepository;
import edu.courseflow.gradebook.repository.GradeOverrideRepository;
import edu.courseflow.gradebook.repository.GradebookAuditLogRepository;
import edu.courseflow.gradebook.repository.GradingSchemeEntryRepository;
import edu.courseflow.gradebook.repository.GradingSchemeRepository;
import edu.courseflow.gradebook.repository.OutboxEventRepository;
import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;

@ExtendWith(MockitoExtension.class)
class GradebookAuditServiceTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID CATEGORY_ID = UUID.fromString("a1000000-0000-0000-0000-000000000001");
    private static final UUID GRADE_ITEM_ID = UUID.fromString("b1000000-0000-0000-0000-000000000001");

    @Mock
    private GradeCategoryRepository categories;
    @Mock
    private GradeItemRepository items;
    @Mock
    private GradeEntryRepository entries;
    @Mock
    private GradeOverrideRepository overrides;
    @Mock
    private GradebookAuditLogRepository auditLogs;
    @Mock
    private GradingSchemeRepository schemes;
    @Mock
    private GradingSchemeEntryRepository schemeEntries;
    @Mock
    private FinalGradeRepository finalGrades;
    @Mock
    private OutboxEventRepository outbox;

    private GradebookService service;
    private GradeCategory category;
    private GradeItem item;

    @BeforeEach
    void setUp() {
        category = new GradeCategory(CATEGORY_ID, COURSE_ID, "Assignments",
                new BigDecimal("100"), 1, "WEIGHTED_MEAN", 0);
        item = new GradeItem(GRADE_ITEM_ID, COURSE_ID, CATEGORY_ID, "ASSIGNMENT", "assignment-1",
                "Capstone", new BigDecimal("100"), BigDecimal.ONE, BigDecimal.ZERO);
        service = new GradebookService(
                categories,
                items,
                entries,
                overrides,
                auditLogs,
                schemes,
                schemeEntries,
                finalGrades,
                outbox,
                new ObjectMapper(),
                null);
    }

    @Test
    void upsertEntryAuditsInitialPublish() {
        AtomicReference<GradeEntry> savedEntry = new AtomicReference<>();
        when(items.findById(GRADE_ITEM_ID)).thenReturn(Optional.of(item));
        when(entries.findByGradeItemIdAndStudentId(GRADE_ITEM_ID, "learner-1")).thenReturn(Optional.empty());
        when(entries.save(any(GradeEntry.class))).thenAnswer(invocation -> {
            GradeEntry entry = invocation.getArgument(0);
            savedEntry.set(entry);
            return entry;
        });
        when(items.findByCourseId(COURSE_ID)).thenReturn(List.of(item));
        when(categories.findByCourseIdOrderByPositionAscNameAsc(COURSE_ID)).thenReturn(List.of(category));
        when(entries.findByGradeItemIdInAndStudentIdAndStatus(any(), eq("learner-1"), eq("PUBLISHED")))
                .thenAnswer(invocation -> List.of(savedEntry.get()));
        when(schemes.findByCourseIdAndDefaultSchemeTrue(COURSE_ID)).thenReturn(Optional.empty());

        service.upsertEntry(new UpsertGradeEntryRequestDto(
                GRADE_ITEM_ID.toString(),
                "learner-1",
                new BigDecimal("86.50"),
                false,
                0,
                null), "instructor-9");

        ArgumentCaptor<GradebookAuditLog> auditCaptor = ArgumentCaptor.forClass(GradebookAuditLog.class);
        verify(auditLogs).save(auditCaptor.capture());
        GradebookAuditLog audit = auditCaptor.getValue();
        assertThat(audit.getAction()).isEqualTo("GRADE_ENTRY_PUBLISHED");
        assertThat(audit.getCourseId()).isEqualTo(COURSE_ID);
        assertThat(audit.getStudentId()).isEqualTo("learner-1");
        assertThat(audit.getGradeItemId()).isEqualTo(GRADE_ITEM_ID);
        assertThat(audit.getActorId()).isEqualTo("instructor-9");
        assertThat(audit.getReasonCodes()).contains("INITIAL_PUBLISH");
        assertThat(audit.getPayload()).contains("\"effectiveScore\":86.50");
    }

    @Test
    void listGradePublishAuditFiltersAndParsesPayload() {
        GradebookAuditLog row = new GradebookAuditLog(
                "GRADE_ENTRY_PUBLISHED",
                COURSE_ID,
                "learner-1",
                GRADE_ITEM_ID,
                UUID.randomUUID(),
                null,
                "instructor-9",
                "[\"GRADE_OVERRIDE\"]",
                "{\"reason\":\"score correction\"}");
        when(auditLogs.findByCourseIdAndStudentIdAndGradeItemIdOrderByCreatedAtDesc(
                eq(COURSE_ID), eq("learner-1"), eq(GRADE_ITEM_ID), any(Pageable.class)))
                .thenReturn(List.of(row));

        List<GradePublishAuditDto> audit = service.listGradePublishAudit(COURSE_ID, " learner-1 ", GRADE_ITEM_ID, 500);

        assertThat(audit).hasSize(1);
        assertThat(audit.getFirst().reasonCodes()).containsExactly("GRADE_OVERRIDE");
        assertThat(audit.getFirst().payload()).containsEntry("reason", "score correction");
    }

    @Test
    void gradingQueueShowsMissingGradeForSelectedLearner() {
        when(categories.findByCourseIdOrderByPositionAscNameAsc(COURSE_ID)).thenReturn(List.of(category));
        when(items.findByCourseId(COURSE_ID)).thenReturn(List.of(item));
        when(entries.findByGradeItemIdIn(List.of(GRADE_ITEM_ID))).thenReturn(List.of());
        when(finalGrades.findByCourseId(COURSE_ID)).thenReturn(List.of());

        var queue = service.gradingQueue(COURSE_ID, " learner-1 ", null, 20);

        assertThat(queue).hasSize(1);
        assertThat(queue.getFirst().status()).isEqualTo("MISSING_GRADE");
        assertThat(queue.getFirst().studentId()).isEqualTo("learner-1");
        assertThat(queue.getFirst().gradeItemId()).isEqualTo(GRADE_ITEM_ID.toString());
        assertThat(queue.getFirst().reasonCodes()).containsExactly("GRADE_ENTRY_MISSING");
    }

    @Test
    void gradingQueueShowsFinalizeReadyWhenAllPublishedItemsAreGraded() {
        GradeEntry entry = new GradeEntry(UUID.randomUUID(), GRADE_ITEM_ID, "learner-1");
        entry.publish(new BigDecimal("88.00"), null, false, 0, BigDecimal.ZERO);
        when(categories.findByCourseIdOrderByPositionAscNameAsc(COURSE_ID)).thenReturn(List.of(category));
        when(items.findByCourseId(COURSE_ID)).thenReturn(List.of(item));
        when(entries.findByGradeItemIdIn(List.of(GRADE_ITEM_ID))).thenReturn(List.of(entry));
        when(finalGrades.findByCourseId(COURSE_ID)).thenReturn(List.of());

        var queue = service.gradingQueue(COURSE_ID, "learner-1", "final_grade_ready", 20);

        assertThat(queue).hasSize(1);
        assertThat(queue.getFirst().status()).isEqualTo("FINAL_GRADE_READY");
        assertThat(queue.getFirst().studentId()).isEqualTo("learner-1");
        assertThat(queue.getFirst().reasonCodes()).containsExactly("FINAL_GRADE_NOT_FINALIZED");
    }

    @Test
    void gradingQueueHidesFinalizedRowsUnlessExplicitlyRequested() {
        GradeEntry entry = new GradeEntry(UUID.randomUUID(), GRADE_ITEM_ID, "learner-1");
        entry.publish(new BigDecimal("88.00"), null, false, 0, BigDecimal.ZERO);
        FinalGrade finalGrade = new FinalGrade(UUID.randomUUID(), COURSE_ID, "learner-1");
        finalGrade.finalizeAs(new BigDecimal("88.00"), "B", true, "instructor-9");
        when(categories.findByCourseIdOrderByPositionAscNameAsc(COURSE_ID)).thenReturn(List.of(category));
        when(items.findByCourseId(COURSE_ID)).thenReturn(List.of(item));
        when(entries.findByGradeItemIdIn(List.of(GRADE_ITEM_ID))).thenReturn(List.of(entry));
        when(finalGrades.findByCourseId(COURSE_ID)).thenReturn(List.of(finalGrade));

        var openQueue = service.gradingQueue(COURSE_ID, "learner-1", null, 20);
        var finalizedQueue = service.gradingQueue(COURSE_ID, "learner-1", "FINALIZED", 20);

        assertThat(openQueue).isEmpty();
        assertThat(finalizedQueue).hasSize(1);
        assertThat(finalizedQueue.getFirst().status()).isEqualTo("FINALIZED");
    }
}
