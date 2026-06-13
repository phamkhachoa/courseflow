package edu.courseflow.accesscontrol.service;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzCheckRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.CreateRoleRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ResolveIdentityRequest;
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
        registry.add("courseflow.access-control.allow-legacy-bootstrap", () -> "true");
        registry.add("courseflow.security.internal-jwt.secret",
                () -> "test-internal-jwt-secret-32-byte-value-001");
    }

    @Autowired
    AccessControlService accessControl;

    @Test
    void bootsWithJpaAndManagesRoleDefinitions() {
        var resolved = accessControl.resolveIdentity(new ResolveIdentityRequest(
                "legacy-courseflow",
                "admin@example.com",
                "admin@example.com",
                true,
                "1",
                List.of(new RoleAssignmentHint("ADMIN", "PLATFORM", null))));

        assertThat(resolved.userId()).isEqualTo("1");
        assertThat(accessControl.permissions()).extracting("code").contains("role:manage", "user:assign-role");
        assertThat(accessControl.roles()).extracting("code").contains("ADMIN", "STUDENT");

        var admin = new CurrentUser(1L, "admin@example.com", "ADMIN", Set.of("ADMIN"));
        var created = accessControl.createRole(new CreateRoleRequestDto(
                "CONTENT_REVIEWER",
                "Content Reviewer",
                "Reviews course content before publishing",
                null,
                true,
                60), admin);

        assertThat(created.code()).isEqualTo("CONTENT_REVIEWER");
        assertThat(accessControl.check(new AuthzCheckRequestDto("1", "role:manage", "PLATFORM", null)).allowed())
                .isTrue();
        assertThat(accessControl.userDirectory("admin", 10)).singleElement()
                .satisfies(user -> {
                    assertThat(user.userId()).isEqualTo("1");
                    assertThat(user.email()).isEqualTo("admin@example.com");
                    assertThat(user.primaryRole()).isEqualTo("ADMIN");
                    assertThat(user.status()).isEqualTo("ACTIVE");
                });
    }
}
