package edu.courseflow.course.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.dto.AuthoringDtos.CourseDraftDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseReviewAuditDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseReviewQueueItemDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDiffDto;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ReviewDecisionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.RollbackVersionRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateModuleItemRequestDto;
import edu.courseflow.course.dto.AuthoringDtos.UpdateModuleRequestDto;
import edu.courseflow.course.exception.ForbiddenException;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.Course;
import edu.courseflow.course.model.CourseModule;
import edu.courseflow.course.model.CourseReviewAuditLog;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.model.ModuleItem;
import edu.courseflow.course.repository.CourseJpaRepository;
import edu.courseflow.course.repository.CourseModuleJpaRepository;
import edu.courseflow.course.repository.CourseReviewAuditLogJpaRepository;
import edu.courseflow.course.repository.CourseVersionJpaRepository;
import edu.courseflow.course.repository.ModuleItemJpaRepository;
import edu.courseflow.course.repository.ModulePrerequisiteJpaRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CourseAuthoringServiceAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID OTHER_COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000999");
    private static final UUID DEPARTMENT_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");
    private static final UUID OTHER_DEPARTMENT_ID = UUID.fromString("20000000-0000-0000-0000-000000000999");
    private static final UUID MODULE_ID = UUID.fromString("30000000-0000-0000-0000-000000001001");
    private static final List<String> REVIEW_CHECKLIST = List.of(
            "content-ready",
            "dependency-ready",
            "learner-preview-checked",
            "publish-risk-reviewed");

    @Mock
    private CourseJpaRepository courses;
    @Mock
    private CourseModuleJpaRepository modules;
    @Mock
    private ModuleItemJpaRepository items;
    @Mock
    private ModulePrerequisiteJpaRepository prerequisites;
    @Mock
    private CourseVersionJpaRepository versions;
    @Mock
    private CourseReviewAuditLogJpaRepository reviewAuditLogs;
    @Mock
    private CourseMapper mapper;
    @Mock
    private CourseContentReadinessClient readinessClient;

    private CourseAuthoringService service;

    @BeforeEach
    void setUp() {
        service = new CourseAuthoringService(
                courses,
                modules,
                items,
                prerequisites,
                versions,
                reviewAuditLogs,
                new ObjectMapper(),
                mapper,
                readinessClient);
    }

    @Test
    void departmentOrgAdminCanApproveCourseInOwnDepartment() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, 1, "IN_REVIEW", "2", "Initial draft");
        CourseDraftDto approved = draftDto(course, "APPROVED");
        CurrentUser orgAdmin = userWithScope(9L, "org-admin@courseflow.local", "ORG_ADMIN", "DEPARTMENT", DEPARTMENT_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 1)).thenReturn(Optional.of(version));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of());
        when(mapper.toDraftDto(course, List.of())).thenReturn(approved);

        CourseDraftDto result = service.approve(
                COURSE_ID,
                new ReviewDecisionRequestDto("ok", REVIEW_CHECKLIST),
                orgAdmin);

        assertThat(result).isSameAs(approved);
        assertThat(course.getReviewState()).isEqualTo("APPROVED");
        assertThat(version.getState()).isEqualTo("APPROVED");
        ArgumentCaptor<CourseReviewAuditLog> audit = ArgumentCaptor.forClass(CourseReviewAuditLog.class);
        verify(reviewAuditLogs).save(audit.capture());
        assertThat(audit.getValue().getAction()).isEqualTo("APPROVE");
        assertThat(audit.getValue().getFromState()).isEqualTo("IN_REVIEW");
        assertThat(audit.getValue().getToState()).isEqualTo("APPROVED");
        assertThat(audit.getValue().getNote()).isEqualTo("ok");
        assertThat(audit.getValue().getChecklist()).containsExactlyElementsOf(REVIEW_CHECKLIST);
    }

    @Test
    void approveRequiresCompleteGovernanceChecklist() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CurrentUser orgAdmin = userWithScope(9L, "org-admin@courseflow.local", "ORG_ADMIN", "DEPARTMENT", DEPARTMENT_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.approve(
                        COURSE_ID,
                        new ReviewDecisionRequestDto("ok", List.of("content-ready")),
                        orgAdmin));

        assertThat(ex.getMessage()).contains("Review checklist is incomplete");
        assertThat(ex.getMessage()).contains("dependency-ready");
        assertThat(course.getReviewState()).isEqualTo("IN_REVIEW");
    }

    @Test
    void orgAdminCannotApproveCourseOutsideDepartment() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CurrentUser orgAdmin = userWithScope(
                9L,
                "org-admin@courseflow.local",
                "ORG_ADMIN",
                "DEPARTMENT",
                OTHER_DEPARTMENT_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        assertThrows(ForbiddenException.class,
                () -> service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok", List.of()), orgAdmin));
    }

    @Test
    void courseScopedInstructorCanApproveSameCourseWhenNotOwner() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CourseDraftDto approved = draftDto(course, "APPROVED");
        CurrentUser instructor = userWithScope(9L, "reviewer@courseflow.local", "INSTRUCTOR", "COURSE", COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of());
        when(mapper.toDraftDto(course, List.of())).thenReturn(approved);

        CourseDraftDto result = service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok", REVIEW_CHECKLIST), instructor);

        assertThat(result).isSameAs(approved);
        assertThat(course.getReviewState()).isEqualTo("APPROVED");
    }

    @Test
    void courseScopedInstructorCannotApproveAnotherCourse() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CurrentUser instructor = userWithScope(
                9L,
                "reviewer@courseflow.local",
                "INSTRUCTOR",
                "COURSE",
                OTHER_COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        assertThrows(ForbiddenException.class,
                () -> service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok", List.of()), instructor));
    }

    @Test
    void ownerCannotApproveOwnCourseEvenWithScopedInstructorRole() {
        Course course = inReviewCourse("9", DEPARTMENT_ID);
        CurrentUser owner = userWithScope(9L, "owner@courseflow.local", "INSTRUCTOR", "COURSE", COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        assertThrows(ForbiddenException.class,
                () -> service.approve(COURSE_ID, new ReviewDecisionRequestDto("ok", List.of()), owner));
    }

    @Test
    void rejectRequiresReviewerNote() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CurrentUser orgAdmin = userWithScope(9L, "org-admin@courseflow.local", "ORG_ADMIN", "DEPARTMENT", DEPARTMENT_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        BadRequestException ex = assertThrows(BadRequestException.class,
                () -> service.reject(COURSE_ID, new ReviewDecisionRequestDto(" ", List.of("content-ready")), orgAdmin));

        assertThat(ex.getMessage()).contains("Reject note is required");
    }

    @Test
    void ownerCanReadReviewHistory() {
        Course course = inReviewCourse("2", DEPARTMENT_ID);
        CourseReviewAuditLog audit = new CourseReviewAuditLog(
                UUID.randomUUID(),
                COURSE_ID,
                1,
                "9",
                "ORG_ADMIN",
                "APPROVE",
                "IN_REVIEW",
                "APPROVED",
                "ok",
                List.of("content-ready"));
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(reviewAuditLogs.findByCourseIdOrderByCreatedAtDesc(COURSE_ID)).thenReturn(List.of(audit));

        List<CourseReviewAuditDto> history = service.listReviewHistory(
                COURSE_ID,
                new CurrentUser(2L, "owner@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR")));

        assertThat(history).hasSize(1);
        assertThat(history.get(0).action()).isEqualTo("APPROVE");
        assertThat(history.get(0).checklist()).containsExactly("content-ready");
    }

    @Test
    void scopedReviewerCanReadDraftForReview() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CourseDraftDto draft = draftDto(course, "IN_REVIEW");
        CurrentUser reviewer = userWithScope(9L, "reviewer@courseflow.local", "TA", "COURSE", COURSE_ID);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of());
        when(mapper.toDraftDto(any(Course.class), org.mockito.ArgumentMatchers.<List<ModuleOutlineDto>>any())).thenReturn(draft);

        CourseDraftDto result = service.getDraft(COURSE_ID, reviewer);

        assertThat(result).isSameAs(draft);
    }

    @Test
    void studentCannotPreviewAuthoringDraft() {
        Course course = inReviewCourse("owner-2", DEPARTMENT_ID);
        CurrentUser student = new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));

        assertThrows(ForbiddenException.class, () -> service.previewDraft(COURSE_ID, student));
    }

    @Test
    void reviewQueueOnlyReturnsVisibleCoursesForScopedReviewer() {
        Course visible = inReviewCourse(COURSE_ID, "owner-2", DEPARTMENT_ID);
        Course hidden = inReviewCourse(OTHER_COURSE_ID, "owner-3", OTHER_DEPARTMENT_ID);
        CourseModule module = new CourseModule(MODULE_ID, COURSE_ID, "Module 1", null, 1, "DRAFT");
        CourseReviewAuditLog submitted = new CourseReviewAuditLog(
                UUID.randomUUID(),
                COURSE_ID,
                1,
                "2",
                "INSTRUCTOR",
                "SUBMIT_REVIEW",
                "DRAFT",
                "IN_REVIEW",
                null,
                List.of());
        CurrentUser orgAdmin = userWithScope(9L, "org-admin@courseflow.local", "ORG_ADMIN", "DEPARTMENT", DEPARTMENT_ID);
        when(courses.findByReviewStateOrderByUpdatedAtDescTitleAsc("IN_REVIEW")).thenReturn(List.of(visible, hidden));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of());
        when(reviewAuditLogs.findByCourseIdOrderByCreatedAtDesc(COURSE_ID)).thenReturn(List.of(submitted));

        List<CourseReviewQueueItemDto> queue = service.listReviewQueue(orgAdmin);

        assertThat(queue).hasSize(1);
        assertThat(queue.get(0).courseId()).isEqualTo(COURSE_ID.toString());
        assertThat(queue.get(0).moduleCount()).isEqualTo(1);
        assertThat(queue.get(0).itemCount()).isZero();
        assertThat(queue.get(0).submittedBy()).isEqualTo("2");
    }

    @Test
    void ownerCanEditModuleAndItemReturningCourseToDraft() {
        UUID itemId = UUID.fromString("30000000-0000-0000-0000-000000002001");
        Course course = inReviewCourse("2", DEPARTMENT_ID);
        course.setReviewState("PUBLISHED");
        CourseVersion publishedVersion = new CourseVersion(UUID.randomUUID(), COURSE_ID, 1, "PUBLISHED", "2", "Published");
        CourseVersion draftVersion = new CourseVersion(UUID.randomUUID(), COURSE_ID, 2, "DRAFT", "2", "Draft fork");
        CourseModule module = new CourseModule(MODULE_ID, COURSE_ID, "Old module", "old", 0, "PUBLISHED");
        ModuleItem item = new ModuleItem(
                itemId,
                MODULE_ID,
                "LESSON",
                itemId.toString(),
                "Old item",
                "old",
                null,
                List.of(),
                null,
                10,
                0,
                true);
        CourseDraftDto draft = draftDto(course, "DRAFT");
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 1)).thenReturn(Optional.of(publishedVersion));
        when(versions.nextVersionNo(COURSE_ID)).thenReturn(2);
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 2))
                .thenReturn(Optional.empty(), Optional.of(draftVersion), Optional.of(draftVersion), Optional.of(draftVersion));
        when(versions.save(any(CourseVersion.class))).thenAnswer(invocation -> (CourseVersion) invocation.getArgument(0));
        when(modules.findByIdAndCourseId(MODULE_ID, COURSE_ID)).thenReturn(Optional.of(module));
        when(items.findByIdAndModuleId(itemId, MODULE_ID)).thenReturn(Optional.of(item));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of());
        when(mapper.toDraftDto(any(Course.class), org.mockito.ArgumentMatchers.<List<ModuleOutlineDto>>any())).thenReturn(draft);

        service.updateModule(COURSE_ID, MODULE_ID, new UpdateModuleRequestDto("New module", "new"), ownerUser());
        CourseDraftDto result = service.updateModuleItem(
                COURSE_ID,
                MODULE_ID,
                itemId,
                new UpdateModuleItemRequestDto("LINK", null, "New item", "new item", null, List.of(),
                        "https://example.com/lesson", 25, false),
                ownerUser());

        assertThat(result).isSameAs(draft);
        assertThat(module.getTitle()).isEqualTo("New module");
        assertThat(module.getStatus()).isEqualTo("DRAFT");
        assertThat(item.getTitle()).isEqualTo("New item");
        assertThat(item.getItemType()).isEqualTo("LINK");
        assertThat(item.getItemId()).isEqualTo("https://example.com/lesson");
        assertThat(item.isRequired()).isFalse();
        assertThat(publishedVersion.getState()).isEqualTo("PUBLISHED");
        assertThat(course.getCurrentVersionNo()).isEqualTo(2);
        assertThat(course.getReviewState()).isEqualTo("DRAFT");
    }

    @Test
    void duplicateModuleCreatesNewModuleAndItemIds() {
        UUID itemId = UUID.fromString("30000000-0000-0000-0000-000000002001");
        UUID quizId = UUID.fromString("60000000-0000-0000-0000-000000000001");
        Course course = inReviewCourse("2", DEPARTMENT_ID);
        CourseVersion draftVersion = new CourseVersion(UUID.randomUUID(), COURSE_ID, 1, "DRAFT", "2", "Draft");
        CourseModule module = new CourseModule(MODULE_ID, COURSE_ID, "Module 1", "desc", 0, "PUBLISHED");
        ModuleItem item = new ModuleItem(
                itemId,
                MODULE_ID,
                "QUIZ",
                quizId.toString(),
                "Knowledge check",
                "quiz",
                null,
                List.of(),
                null,
                15,
                0,
                true);
        CourseDraftDto draft = draftDto(course, "DRAFT");
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 1)).thenReturn(Optional.of(draftVersion));
        when(modules.findByIdAndCourseId(MODULE_ID, COURSE_ID)).thenReturn(Optional.of(module));
        when(modules.nextPosition(COURSE_ID)).thenReturn(1);
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(item));
        when(mapper.toDraftDto(any(Course.class), org.mockito.ArgumentMatchers.<List<ModuleOutlineDto>>any())).thenReturn(draft);

        service.duplicateModule(COURSE_ID, MODULE_ID, ownerUser());

        ArgumentCaptor<CourseModule> moduleCaptor = ArgumentCaptor.forClass(CourseModule.class);
        verify(modules).save(moduleCaptor.capture());
        assertThat(moduleCaptor.getValue().getId()).isNotEqualTo(MODULE_ID);
        assertThat(moduleCaptor.getValue().getTitle()).isEqualTo("Copy of Module 1");
        assertThat(moduleCaptor.getValue().getStatus()).isEqualTo("DRAFT");

        ArgumentCaptor<ModuleItem> itemCaptor = ArgumentCaptor.forClass(ModuleItem.class);
        verify(items).save(itemCaptor.capture());
        assertThat(itemCaptor.getValue().getId()).isNotEqualTo(itemId);
        assertThat(itemCaptor.getValue().getItemId()).isEqualTo(quizId.toString());
        assertThat(itemCaptor.getValue().getTitle()).isEqualTo("Copy of Knowledge check");
    }

    @Test
    void archiveModuleItemSoftDeletesAndCompactsActivePositions() {
        UUID itemId = UUID.fromString("30000000-0000-0000-0000-000000002001");
        UUID nextItemId = UUID.fromString("30000000-0000-0000-0000-000000002002");
        Course course = inReviewCourse("2", DEPARTMENT_ID);
        CourseVersion draftVersion = new CourseVersion(UUID.randomUUID(), COURSE_ID, 1, "DRAFT", "2", "Draft");
        CourseModule module = new CourseModule(MODULE_ID, COURSE_ID, "Module 1", null, 0, "PUBLISHED");
        ModuleItem archived = new ModuleItem(
                itemId,
                MODULE_ID,
                "LESSON",
                itemId.toString(),
                "First",
                null,
                null,
                List.of(),
                null,
                10,
                0,
                true);
        ModuleItem remaining = new ModuleItem(
                nextItemId,
                MODULE_ID,
                "LESSON",
                nextItemId.toString(),
                "Second",
                null,
                null,
                List.of(),
                null,
                10,
                1,
                true);
        CourseDraftDto draft = draftDto(course, "DRAFT");
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 1)).thenReturn(Optional.of(draftVersion));
        when(modules.findByIdAndCourseId(MODULE_ID, COURSE_ID)).thenReturn(Optional.of(module));
        when(items.findByIdAndModuleId(itemId, MODULE_ID)).thenReturn(Optional.of(archived));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(archived, remaining));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(module));
        ItemOutlineDto remainingDto = itemDto(nextItemId.toString(), "Second", 0, true);
        ModuleOutlineDto moduleDto = moduleDto(MODULE_ID.toString(), "Module 1", 0, remainingDto);
        when(mapper.toOutlineDto(remaining)).thenReturn(remainingDto);
        when(mapper.toOutlineDto(module, List.of(remainingDto))).thenReturn(moduleDto);
        when(mapper.toDraftDto(course, List.of(moduleDto))).thenReturn(draft);

        CourseDraftDto result = service.archiveModuleItem(COURSE_ID, MODULE_ID, itemId, ownerUser());

        assertThat(result).isSameAs(draft);
        assertThat(archived.getStatus()).isEqualTo("ARCHIVED");
        assertThat(remaining.getPosition()).isZero();
        assertThat(course.getReviewState()).isEqualTo("DRAFT");
    }

    @Test
    void diffDraftWithPublishedReportsContentAndRequiredChanges() throws Exception {
        UUID itemId = UUID.fromString("30000000-0000-0000-0000-000000002001");
        Course course = inReviewCourse("2", DEPARTMENT_ID);
        course.setCurrentVersionNo(2);
        CourseVersion published = publishedVersion(1, moduleDto(
                MODULE_ID.toString(),
                "Module 1",
                1,
                itemDto(itemId.toString(), "Read overview", 1, true)));
        CourseModule draftModule = new CourseModule(MODULE_ID, COURSE_ID, "Module 1", null, 1, "DRAFT");
        ModuleItem draftItem = new ModuleItem(
                itemId,
                MODULE_ID,
                "LESSON",
                itemId.toString(),
                "Read overview revised",
                "Updated lesson",
                null,
                List.of(),
                null,
                30,
                1,
                false);
        ItemOutlineDto draftItemDto = itemDto(itemId.toString(), "Read overview revised", 1, false);
        ModuleOutlineDto draftModuleDto = moduleDto(MODULE_ID.toString(), "Module 1", 1, draftItemDto);
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(versions.findByCourseIdAndStateOrderByVersionNoDesc(COURSE_ID, "PUBLISHED")).thenReturn(List.of(published));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(draftModule));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(draftItem));
        when(mapper.toOutlineDto(draftItem)).thenReturn(draftItemDto);
        when(mapper.toOutlineDto(draftModule, List.of(draftItemDto))).thenReturn(draftModuleDto);

        CourseVersionDiffDto diff = service.diffDraftWithPublished(
                COURSE_ID,
                null,
                new CurrentUser(2L, "owner@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR")));

        assertThat(diff.publishedVersionNo()).isEqualTo(1);
        assertThat(diff.draftVersionNo()).isEqualTo(2);
        assertThat(diff.changedItems()).isEqualTo(1);
        assertThat(diff.requiredItemsRemoved()).isEqualTo(1);
        assertThat(diff.changes()).anySatisfy(change -> {
            assertThat(change.scope()).isEqualTo("ITEM");
            assertThat(change.field()).isEqualTo("title");
        });
        assertThat(diff.warnings()).anyMatch(warning -> warning.contains("required item"));
    }

    @Test
    void rollbackPublishedVersionCreatesNewDraftAndArchivesRowsWithoutDeleting() throws Exception {
        UUID itemId = UUID.fromString("30000000-0000-0000-0000-000000002001");
        UUID extraItemId = UUID.fromString("30000000-0000-0000-0000-000000002999");
        UUID extraModuleId = UUID.fromString("30000000-0000-0000-0000-000000001999");
        Course course = inReviewCourse("2", DEPARTMENT_ID);
        course.setCurrentVersionNo(2);
        CourseVersion published = publishedVersion(1, moduleDto(
                MODULE_ID.toString(),
                "Published module",
                0,
                itemDto(itemId.toString(), "Published lesson", 0, true)));
        CourseModule existingModule = new CourseModule(MODULE_ID, COURSE_ID, "Draft module", "old", 0, "DRAFT");
        CourseModule extraModule = new CourseModule(extraModuleId, COURSE_ID, "Extra module", null, 1, "DRAFT");
        ModuleItem existingItem = new ModuleItem(
                itemId,
                MODULE_ID,
                "LESSON",
                itemId.toString(),
                "Draft lesson",
                null,
                null,
                List.of(),
                null,
                10,
                0,
                true);
        ModuleItem extraItem = new ModuleItem(
                extraItemId,
                MODULE_ID,
                "LESSON",
                extraItemId.toString(),
                "Extra lesson",
                null,
                null,
                List.of(),
                null,
                10,
                1,
                true);
        ItemOutlineDto restoredItemDto = itemDto(itemId.toString(), "Published lesson", 0, true);
        ModuleOutlineDto restoredModuleDto = moduleDto(MODULE_ID.toString(), "Published module", 0, restoredItemDto);
        CourseDraftDto restoredDraft = draftDto(course, "DRAFT");
        when(courses.findById(COURSE_ID)).thenReturn(Optional.of(course));
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 1)).thenReturn(Optional.of(published));
        when(versions.nextVersionNo(COURSE_ID)).thenReturn(3);
        when(versions.findByCourseIdAndVersionNo(COURSE_ID, 3)).thenReturn(Optional.empty());
        when(versions.save(any(CourseVersion.class))).thenAnswer(invocation -> (CourseVersion) invocation.getArgument(0));
        when(modules.saveAndFlush(any(CourseModule.class))).thenAnswer(invocation -> (CourseModule) invocation.getArgument(0));
        when(items.saveAndFlush(any(ModuleItem.class))).thenAnswer(invocation -> (ModuleItem) invocation.getArgument(0));
        when(modules.findByCourseIdOrderByPositionAsc(COURSE_ID)).thenReturn(List.of(existingModule, extraModule));
        when(items.findByModuleIdOrderByPositionAsc(MODULE_ID)).thenReturn(List.of(existingItem, extraItem));
        when(items.findByModuleIdOrderByPositionAsc(extraModuleId)).thenReturn(List.of());
        when(mapper.toOutlineDto(existingItem)).thenReturn(restoredItemDto);
        when(mapper.toOutlineDto(existingModule, List.of(restoredItemDto))).thenReturn(restoredModuleDto);
        when(mapper.toDraftDto(course, List.of(restoredModuleDto))).thenReturn(restoredDraft);

        CourseDraftDto result = service.rollbackPublishedVersionToDraft(
                COURSE_ID,
                1,
                new RollbackVersionRequestDto("restore stable content", 2),
                new CurrentUser(2L, "owner@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR")));

        assertThat(result).isSameAs(restoredDraft);
        assertThat(course.getCurrentVersionNo()).isEqualTo(3);
        assertThat(course.getReviewState()).isEqualTo("DRAFT");
        assertThat(existingModule.getTitle()).isEqualTo("Published module");
        assertThat(existingModule.getStatus()).isEqualTo("DRAFT");
        assertThat(extraModule.getStatus()).isEqualTo("ARCHIVED");
        assertThat(existingItem.getTitle()).isEqualTo("Published lesson");
        assertThat(existingItem.getStatus()).isEqualTo("ACTIVE");
        assertThat(extraItem.getStatus()).isEqualTo("ARCHIVED");

        ArgumentCaptor<CourseVersion> version = ArgumentCaptor.forClass(CourseVersion.class);
        verify(versions).save(version.capture());
        assertThat(version.getValue().getVersionNo()).isEqualTo(3);
        assertThat(version.getValue().getState()).isEqualTo("DRAFT");

        ArgumentCaptor<CourseReviewAuditLog> audit = ArgumentCaptor.forClass(CourseReviewAuditLog.class);
        verify(reviewAuditLogs).save(audit.capture());
        assertThat(audit.getValue().getAction()).isEqualTo("ROLLBACK_TO_DRAFT");
        assertThat(audit.getValue().getChecklist()).containsExactly("source:v1", "target:v3");
    }

    private static Course inReviewCourse(String ownerId, UUID departmentId) {
        return inReviewCourse(COURSE_ID, ownerId, departmentId);
    }

    private static Course inReviewCourse(UUID courseId, String ownerId, UUID departmentId) {
        Course course = new Course(
                courseId,
                "SA-101",
                "System Architecture",
                "system-architecture-" + courseId.toString().substring(0, 8),
                "Architecture foundations",
                departmentId,
                ownerId,
                "BEGINNER");
        course.setReviewState("IN_REVIEW");
        return course;
    }

    private static CourseDraftDto draftDto(Course course, String reviewState) {
        return new CourseDraftDto(
                course.getId().toString(),
                course.getTitle(),
                course.getSlug(),
                course.getSummary(),
                course.getStatus(),
                reviewState,
                course.getCurrentVersionNo(),
                course.getLastAuthoredBy(),
                List.of());
    }

    private static CourseVersion publishedVersion(int versionNo, ModuleOutlineDto... modules) throws Exception {
        CourseVersion version = new CourseVersion(UUID.randomUUID(), COURSE_ID, versionNo, "PUBLISHED", "2", "Published");
        version.publish(new ObjectMapper().writeValueAsString(List.of(modules)), Instant.now());
        return version;
    }

    private static ModuleOutlineDto moduleDto(String moduleId, String title, int position, ItemOutlineDto... items) {
        return new ModuleOutlineDto(
                moduleId,
                title,
                null,
                position,
                "PUBLISHED",
                List.of(items));
    }

    private static ItemOutlineDto itemDto(String itemId, String title, int position, boolean required) {
        return new ItemOutlineDto(
                itemId,
                "LESSON",
                itemId,
                title,
                null,
                null,
                List.of(),
                null,
                20,
                position,
                required);
    }

    private static CurrentUser ownerUser() {
        return new CurrentUser(2L, "owner@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static CurrentUser userWithScope(
            Long id,
            String email,
            String role,
            String scopeType,
            UUID scopeId) {
        return new CurrentUser(
                id,
                email,
                role,
                Set.of(role),
                Set.of(new CurrentUser.RoleAssignment(role, scopeType, scopeId == null ? null : scopeId.toString())));
    }
}
