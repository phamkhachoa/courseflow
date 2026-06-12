package edu.courseflow.gradebook.controller;

import edu.courseflow.gradebook.dto.GradebookDtos.CreateGradingSchemeRequestDto;
import edu.courseflow.gradebook.dto.GradebookDtos.FinalGradeDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeCategoryDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeItemDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradingSchemeDto;
import edu.courseflow.gradebook.dto.GradebookDtos.StudentGradebookDto;
import edu.courseflow.gradebook.dto.GradebookDtos.UpsertCategoryRequestDto;
import edu.courseflow.gradebook.dto.GradebookDtos.UpsertGradeEntryRequestDto;
import edu.courseflow.gradebook.service.GradebookService;
import edu.courseflow.gradebook.web.Authz;
import edu.courseflow.commonlibrary.web.CurrentUser;
import jakarta.validation.Valid;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/gradebook")
public class GradebookController {

    private final GradebookService gradebook;

    public GradebookController(GradebookService gradebook) {
        this.gradebook = gradebook;
    }

    @GetMapping("/courses/{courseId}/items")
    public List<GradeItemDto> listItems(@PathVariable UUID courseId, CurrentUser user) {
        // Listing the course's grade items (structure, not per-student scores) is staff-only.
        Authz.requireStaff(user);
        return gradebook.listItems(courseId);
    }

    @GetMapping("/courses/{courseId}/students/{studentId}")
    public StudentGradebookDto studentGradebook(@PathVariable UUID courseId, @PathVariable String studentId,
            CurrentUser user) {
        // A student may only read their own gradebook; staff may read any student's.
        Authz.requireSelfOrStaff(user, studentId);
        return gradebook.studentGradebook(courseId, studentId);
    }

    @PostMapping("/entries")
    public StudentGradebookDto upsertEntry(@Valid @RequestBody UpsertGradeEntryRequestDto request,
            CurrentUser user) {
        Authz.requireStaff(user);
        return gradebook.upsertEntry(request);
    }

    // ---- Grade categories (weights) ----

    @GetMapping("/courses/{courseId}/categories")
    public List<GradeCategoryDto> listCategories(@PathVariable UUID courseId, CurrentUser user) {
        Authz.requireStaff(user);
        return gradebook.listCategories(courseId);
    }

    @PostMapping("/courses/{courseId}/categories")
    public GradeCategoryDto createCategory(@PathVariable UUID courseId,
            @Valid @RequestBody UpsertCategoryRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        return gradebook.createCategory(courseId, request);
    }

    @PutMapping("/courses/{courseId}/categories/{categoryId}")
    public GradeCategoryDto updateCategory(@PathVariable UUID courseId, @PathVariable UUID categoryId,
            @Valid @RequestBody UpsertCategoryRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        return gradebook.updateCategory(courseId, categoryId, request);
    }

    // ---- Grading schemes ----

    @PostMapping("/courses/{courseId}/grading-schemes")
    public GradingSchemeDto createScheme(@PathVariable UUID courseId,
            @Valid @RequestBody CreateGradingSchemeRequestDto request, CurrentUser user) {
        Authz.requireStaff(user);
        return gradebook.createScheme(courseId, request);
    }

    @GetMapping("/courses/{courseId}/grading-schemes")
    public List<GradingSchemeDto> listSchemes(@PathVariable UUID courseId, CurrentUser user) {
        Authz.requireStaff(user);
        return gradebook.listSchemes(courseId);
    }

    // ---- Final grades ----

    @PostMapping("/courses/{courseId}/students/{studentId}/finalize")
    public FinalGradeDto finalizeGrade(@PathVariable UUID courseId, @PathVariable String studentId,
            CurrentUser user) {
        // Finalizing is staff-only; the actor is the authenticated caller, never trusted from the body.
        Authz.requireStaff(user);
        return gradebook.finalizeGrade(courseId, studentId, Authz.callerId(user));
    }

    @GetMapping("/courses/{courseId}/students/{studentId}/final-grade")
    public FinalGradeDto finalGrade(@PathVariable UUID courseId, @PathVariable String studentId,
            CurrentUser user) {
        // A student may only read their own final grade; staff may read any.
        Authz.requireSelfOrStaff(user, studentId);
        return gradebook.getFinalGrade(courseId, studentId);
    }

    // ---- CSV export ----

    @GetMapping(value = "/courses/{courseId}/export.csv", produces = "text/csv")
    public ResponseEntity<byte[]> exportCsv(@PathVariable UUID courseId, CurrentUser user) {
        // Whole-class export is staff-only.
        Authz.requireStaff(user);
        byte[] body = gradebook.exportCsv(courseId).getBytes(StandardCharsets.UTF_8);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("text/csv; charset=UTF-8"))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"gradebook-" + courseId + ".csv\"")
                .body(body);
    }
}
