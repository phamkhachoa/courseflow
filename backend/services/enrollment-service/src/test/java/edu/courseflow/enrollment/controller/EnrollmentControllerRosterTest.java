package edu.courseflow.enrollment.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import edu.courseflow.enrollment.dto.EnrollmentDtos.EnrollmentDto;
import edu.courseflow.enrollment.exception.LocalExceptionHandler;
import edu.courseflow.enrollment.service.EnrollmentService;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

@ExtendWith(MockitoExtension.class)
class EnrollmentControllerRosterTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID COHORT_ID = UUID.fromString("30000000-0000-0000-0000-000000000101");

    @Mock
    private EnrollmentService enrollments;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        mvc = MockMvcBuilders
                .standaloneSetup(new EnrollmentController(enrollments))
                .setControllerAdvice(new LocalExceptionHandler())
                .build();
    }

    @Test
    void rosterReturnsActiveEnrollments() throws Exception {
        EnrollmentDto active = new EnrollmentDto(
                UUID.randomUUID().toString(),
                "4",
                COURSE_ID.toString(),
                COHORT_ID.toString(),
                "ACTIVE",
                Instant.parse("2026-06-13T00:00:00Z"),
                null,
                null,
                null);
        when(enrollments.activeRoster(COURSE_ID, Optional.of(COHORT_ID))).thenReturn(List.of(active));

        mvc.perform(get("/internal/enrollments/roster")
                        .param("courseId", COURSE_ID.toString())
                        .param("cohortId", COHORT_ID.toString()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].studentId").value("4"))
                .andExpect(jsonPath("$[0].courseId").value(COURSE_ID.toString()))
                .andExpect(jsonPath("$[0].sectionId").value(COHORT_ID.toString()))
                .andExpect(jsonPath("$[0].status").value("ACTIVE"));

        verify(enrollments).activeRoster(COURSE_ID, Optional.of(COHORT_ID));
    }

    @Test
    void learnerMembershipsReturnStudentEnrollments() throws Exception {
        EnrollmentDto active = new EnrollmentDto(
                UUID.randomUUID().toString(),
                "4",
                COURSE_ID.toString(),
                COHORT_ID.toString(),
                "ACTIVE",
                Instant.parse("2026-06-13T00:00:00Z"),
                null,
                null,
                null);
        when(enrollments.learnerMemberships("4")).thenReturn(List.of(active));

        mvc.perform(get("/internal/learner-memberships")
                        .param("studentId", "4"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].studentId").value("4"))
                .andExpect(jsonPath("$[0].courseId").value(COURSE_ID.toString()));

        verify(enrollments).learnerMemberships("4");
    }
}
