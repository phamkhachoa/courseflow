package edu.courseflow.usermanagement.service;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.usermanagement.dto.UserProfileDtos.UpdateMyProfileRequest;
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
class UserProfileServiceJpaSmokeTest {

    @Container
    static final PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
            .withDatabaseName("cf_user_management")
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
    UserProfileService profiles;

    @Test
    void bootsWithJpaAndServesProfileSummaries() {
        CurrentUser user = new CurrentUser(42L, "learner@example.com", "STUDENT", Set.of("STUDENT"));
        var profile = profiles.updateMe(user, new UpdateMyProfileRequest(
                "Learner Forty Two",
                "Building LMS muscle memory.",
                "https://cdn.example.com/avatar-42.png",
                "vi-VN",
                "Asia/Ho_Chi_Minh",
                "PUBLIC"));

        assertThat(profile.userId()).isEqualTo("42");
        assertThat(profiles.profile(42L).displayName()).isEqualTo("Learner Forty Two");
        assertThat(profiles.summaries(List.of("42"))).singleElement()
                .extracting("displayName")
                .isEqualTo("Learner Forty Two");
    }
}
