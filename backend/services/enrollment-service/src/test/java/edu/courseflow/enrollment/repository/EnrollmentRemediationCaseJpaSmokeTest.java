package edu.courseflow.enrollment.repository;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.enrollment.model.EnrollmentRemediationCase;
import edu.courseflow.enrollment.model.EnrollmentRemediationCaseAction;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.domain.PageRequest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest(properties = {
        "courseflow.enrollment.promotion-commit-retry.enabled=false",
        "eureka.client.enabled=false",
        "spring.kafka.listener.auto-startup=false"
})
@Testcontainers(disabledWithoutDocker = true)
class EnrollmentRemediationCaseJpaSmokeTest {

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("cf_enrollment")
            .withUsername("courseflow")
            .withPassword("courseflow");

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.liquibase.contexts", () -> "prod");
    }

    @Autowired
    EnrollmentRemediationCaseJpaRepository remediationCases;

    @Autowired
    EnrollmentRemediationCaseActionJpaRepository remediationActions;

    @Test
    void operationsQueueFiltersCorrelationIdFromActionJsonbPayload() {
        UUID courseId = UUID.randomUUID();
        EnrollmentRemediationCase matching = remediationCases.saveAndFlush(remediationCase(
                courseId,
                "student-matching",
                "Matching remediation"));
        EnrollmentRemediationCase unrelated = remediationCases.saveAndFlush(remediationCase(
                courseId,
                "student-unrelated",
                "Unrelated remediation"));
        remediationActions.save(new EnrollmentRemediationCaseAction(
                matching.getId(),
                "CASE_OPENED",
                "system",
                "Created for smoke test",
                null,
                "OPEN",
                "{\"correlationId\":\"checkout-correlation-123\",\"reasonCode\":\"COMMIT_FAILED\"}"));
        remediationActions.save(new EnrollmentRemediationCaseAction(
                unrelated.getId(),
                "CASE_OPENED",
                "system",
                "Created for smoke test",
                null,
                "OPEN",
                "{\"correlationId\":\"different-correlation\",\"reasonCode\":\"COMMIT_FAILED\"}"));

        var result = remediationCases.findOperationsQueue(
                null,
                courseId,
                null,
                null,
                null,
                null,
                null,
                null,
                "CHECKOUT-CORRELATION",
                null,
                PageRequest.of(0, 10));

        assertThat(result).singleElement()
                .extracting(EnrollmentRemediationCase::getId)
                .isEqualTo(matching.getId());
    }

    private EnrollmentRemediationCase remediationCase(UUID courseId, String studentId, String note) {
        return new EnrollmentRemediationCase(
                "PROMOTION_RESERVATION",
                "HIGH",
                null,
                null,
                null,
                null,
                studentId,
                courseId,
                "ops-unassigned",
                note,
                "COMMIT_FAILED",
                Instant.now().plusSeconds(900));
    }
}
