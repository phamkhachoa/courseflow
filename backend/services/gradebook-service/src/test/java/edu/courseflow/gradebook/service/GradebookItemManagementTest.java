package edu.courseflow.gradebook.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.gradebook.dto.GradebookDtos.FinalGradeDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeCategoryDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeItemDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradingSchemeDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradingSchemeEntryDto;
import edu.courseflow.gradebook.dto.GradebookDtos.UpsertGradeItemRequestDto;
import edu.courseflow.gradebook.mapper.GradebookMapper;
import edu.courseflow.gradebook.model.FinalGrade;
import edu.courseflow.gradebook.model.GradeCategory;
import edu.courseflow.gradebook.model.GradeItem;
import edu.courseflow.gradebook.model.GradingScheme;
import edu.courseflow.gradebook.model.GradingSchemeEntry;
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
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class GradebookItemManagementTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID CATEGORY_ID = UUID.fromString("a1000000-0000-0000-0000-000000000001");

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

    private GradeCategory category;
    private GradebookService service;

    @BeforeEach
    void setUp() {
        category = new GradeCategory(CATEGORY_ID, COURSE_ID, "Assignments",
                new BigDecimal("60"), 1, "WEIGHTED_MEAN", 0);
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
                new TestGradebookMapper());
    }

    @Test
    void createGradeItemNormalizesSourceTypeAndKeepsPublishedFlag() {
        when(categories.findById(CATEGORY_ID)).thenReturn(Optional.of(category));
        when(items.findBySourceTypeAndSourceId("ASSIGNMENT", "assignment-1")).thenReturn(Optional.empty());
        when(items.save(any(GradeItem.class))).thenAnswer(invocation -> invocation.getArgument(0));

        GradeItemDto dto = service.createGradeItem(COURSE_ID, request("assignment", "assignment-1", false));

        ArgumentCaptor<GradeItem> itemCaptor = ArgumentCaptor.forClass(GradeItem.class);
        org.mockito.Mockito.verify(items).save(itemCaptor.capture());
        GradeItem saved = itemCaptor.getValue();
        assertThat(saved.getSourceType()).isEqualTo("ASSIGNMENT");
        assertThat(saved.isPublished()).isFalse();
        assertThat(dto.sourceType()).isEqualTo("ASSIGNMENT");
        assertThat(dto.published()).isFalse();
    }

    @Test
    void createGradeItemRejectsDuplicateSource() {
        when(categories.findById(CATEGORY_ID)).thenReturn(Optional.of(category));
        when(items.findBySourceTypeAndSourceId("QUIZ", "quiz-1")).thenReturn(Optional.of(
                new GradeItem(UUID.randomUUID(), COURSE_ID, CATEGORY_ID, "QUIZ", "quiz-1",
                        "Quiz", new BigDecimal("10"), BigDecimal.ONE, BigDecimal.ZERO)));

        assertThatThrownBy(() -> service.createGradeItem(COURSE_ID, request("quiz", "quiz-1", true)))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("GRADE_ITEM_SOURCE_ALREADY_EXISTS");
    }

    @Test
    void createGradeItemRejectsCategoryFromAnotherCourse() {
        UUID otherCourse = UUID.fromString("30000000-0000-0000-0000-000000000099");
        GradeCategory foreign = new GradeCategory(CATEGORY_ID, otherCourse, "Foreign",
                new BigDecimal("40"), 1, "WEIGHTED_MEAN", 0);
        when(categories.findById(CATEGORY_ID)).thenReturn(Optional.of(foreign));

        assertThatThrownBy(() -> service.createGradeItem(COURSE_ID, request("quiz", "quiz-1", true)))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("CATEGORY_NOT_IN_COURSE");
    }

    private UpsertGradeItemRequestDto request(String sourceType, String sourceId, boolean published) {
        return new UpsertGradeItemRequestDto(
                CATEGORY_ID.toString(),
                sourceType,
                sourceId,
                "New grade item",
                new BigDecimal("100"),
                new BigDecimal("1"),
                BigDecimal.ZERO,
                published);
    }

    private static final class TestGradebookMapper implements GradebookMapper {
        @Override
        public GradeItemDto toDto(GradeItem item, GradeCategory category) {
            return new GradeItemDto(
                    item.getId().toString(),
                    item.getCourseId().toString(),
                    category.getName(),
                    item.getSourceType(),
                    item.getSourceId(),
                    item.getTitle(),
                    item.getMaxScore(),
                    item.getWeightPercent(),
                    category.getWeightPercent(),
                    category.getAggregationMethod(),
                    category.getDropLowest(),
                    item.getLatePenaltyPercent(),
                    item.isPublished());
        }

        @Override
        public GradeCategoryDto toDto(GradeCategory category) {
            throw new UnsupportedOperationException();
        }

        @Override
        public FinalGradeDto toDto(FinalGrade grade) {
            throw new UnsupportedOperationException();
        }

        @Override
        public GradingSchemeEntryDto toDto(GradingSchemeEntry entry) {
            throw new UnsupportedOperationException();
        }

        @Override
        public GradingSchemeDto toDto(GradingScheme scheme, List<GradingSchemeEntryDto> entries) {
            throw new UnsupportedOperationException();
        }
    }
}
