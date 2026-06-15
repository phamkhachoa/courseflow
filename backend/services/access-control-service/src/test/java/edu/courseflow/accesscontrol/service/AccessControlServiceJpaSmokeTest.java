package edu.courseflow.accesscontrol.service;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.accesscontrol.dto.AccessControlDtos.AssignRoleRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzCheckRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.CreateRoleRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ProvisionKeycloakUserRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.RoleAssignmentHint;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class AccessControlServiceJpaSmokeTest {

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("cf_access_control")
            .withUsername("courseflow")
            .withPassword("courseflow");

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.liquibase.contexts", () -> "prod");
        registry.add("courseflow.security.internal-jwt.secret",
                () -> "test-internal-jwt-secret-32-byte-value-001");
    }

    @Autowired
    AccessControlService accessControl;

    @Test
    void bootsWithJpaAndManagesRoleDefinitions() {
        var resolved = accessControl.provisionKeycloakUser(new ProvisionKeycloakUserRequest(
                "https://auth.example.com/realms/courseflow",
                "kc-admin",
                "admin@example.com",
                true,
                List.of(new RoleAssignmentHint("ADMIN", "PLATFORM", null))),
                new CurrentUser(null, null, null, Set.of(), Set.of(), "service-token"));
        long adminUserId = Long.parseLong(resolved.userId());

        assertThat(accessControl.permissions()).extracting("code")
                .contains(
                        "role:manage",
                        "user:assign-role",
                        "incentive:read",
                        "incentive:campaign:review",
                        "incentive:coupon:import:read",
                        "incentive:coupon:import:manage",
                        "incentive:coupon:import:review");
        assertThat(accessControl.permissions())
                .filteredOn(permission -> "user:assign-role".equals(permission.code()))
                .singleElement()
                .satisfies(permission -> assertThat(permission.scopeType()).isEqualTo("ANY"));
        assertThat(accessControl.roles()).extracting("code")
                .contains("ADMIN", "STUDENT", "INCENTIVE_ADMIN", "INCENTIVE_REVIEWER", "INCENTIVE_OPERATOR");

        var admin = new CurrentUser(adminUserId, "admin@example.com", "ADMIN", Set.of("ADMIN"));
        var target = accessControl.provisionKeycloakUser(new ProvisionKeycloakUserRequest(
                "https://auth.example.com/realms/courseflow",
                "kc-incentive-reviewer",
                "reviewer@example.com",
                true,
                List.of()),
                new CurrentUser(null, null, null, Set.of(), Set.of(), "service-token"));
        long reviewerUserId = Long.parseLong(target.userId());
        var incentiveReviewerRole = accessControl.roles().stream()
                .filter(role -> "INCENTIVE_REVIEWER".equals(role.code()))
                .findFirst()
                .orElseThrow();
        var incentiveOperatorRole = accessControl.roles().stream()
                .filter(role -> "INCENTIVE_OPERATOR".equals(role.code()))
                .findFirst()
                .orElseThrow();

        var assigned = accessControl.assignRole(
                reviewerUserId,
                new AssignRoleRequestDto(incentiveReviewerRole.id(), "APPLICATION", "courseflow:lms", null, null),
                admin);

        assertThat(assigned.roleCode()).isEqualTo("INCENTIVE_REVIEWER");
        assertThat(assigned.scopeType()).isEqualTo("APPLICATION");
        assertThat(assigned.scopeId()).isEqualTo("courseflow:lms");
        assertThat(accessControl.check(new AuthzCheckRequestDto(
                String.valueOf(reviewerUserId),
                "incentive:campaign:review",
                "APPLICATION",
                "courseflow:lms")).allowed())
                .isTrue();
        assertThat(accessControl.check(new AuthzCheckRequestDto(
                String.valueOf(reviewerUserId),
                "incentive:coupon:import:review",
                "APPLICATION",
                "courseflow:lms")).allowed())
                .isTrue();
        assertThat(accessControl.check(new AuthzCheckRequestDto(
                String.valueOf(reviewerUserId),
                "incentive:coupon:import:manage",
                "APPLICATION",
                "courseflow:lms")).allowed())
                .isFalse();

        var operator = accessControl.provisionKeycloakUser(new ProvisionKeycloakUserRequest(
                "https://auth.example.com/realms/courseflow",
                "kc-incentive-operator",
                "operator@example.com",
                true,
                List.of()),
                new CurrentUser(null, null, null, Set.of(), Set.of(), "service-token"));
        long operatorUserId = Long.parseLong(operator.userId());
        accessControl.assignRole(
                operatorUserId,
                new AssignRoleRequestDto(incentiveOperatorRole.id(), "APPLICATION", "courseflow:lms", null, null),
                admin);

        assertThat(accessControl.check(new AuthzCheckRequestDto(
                String.valueOf(operatorUserId),
                "incentive:coupon:import:manage",
                "APPLICATION",
                "courseflow:lms")).allowed())
                .isTrue();
        assertThat(accessControl.check(new AuthzCheckRequestDto(
                String.valueOf(operatorUserId),
                "incentive:coupon:import:review",
                "APPLICATION",
                "courseflow:lms")).allowed())
                .isFalse();
        assertThat(accessControl.check(new AuthzCheckRequestDto(
                String.valueOf(operatorUserId),
                "incentive:coupon:manage",
                "APPLICATION",
                "courseflow:lms")).allowed())
                .isFalse();

        var created = accessControl.createRole(new CreateRoleRequestDto(
                "CONTENT_REVIEWER",
                "Content Reviewer",
                "Reviews course content before publishing",
                null,
                true,
                60), admin);

        assertThat(created.code()).isEqualTo("CONTENT_REVIEWER");
        assertThat(accessControl.check(new AuthzCheckRequestDto(
                String.valueOf(adminUserId), "role:manage", "PLATFORM", null)).allowed())
                .isTrue();
        assertThat(accessControl.userDirectory("admin", 10)).singleElement()
                .satisfies(user -> {
                    assertThat(user.userId()).isEqualTo(String.valueOf(adminUserId));
                    assertThat(user.email()).isEqualTo("admin@example.com");
                    assertThat(user.primaryRole()).isEqualTo("ADMIN");
                    assertThat(user.status()).isEqualTo("ACTIVE");
                });
    }
}
