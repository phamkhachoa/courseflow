package edu.courseflow.notification.web;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import edu.courseflow.commonlibrary.web.CurrentUser;
import org.junit.jupiter.api.Test;

class AuthzTest {

    @Test
    void adminCanInspectAnotherUsersNotificationStream() {
        CurrentUser admin = new CurrentUser(1L, "admin@example.com", "ADMIN");

        assertThatCode(() -> Authz.requireSelfOrAdmin(admin, "42")).doesNotThrowAnyException();
    }

    @Test
    void orgAdminCanInspectAnotherUsersNotificationStream() {
        CurrentUser orgAdmin = new CurrentUser(2L, "org@example.com", "ORG_ADMIN");

        assertThatCode(() -> Authz.requireSelfOrAdmin(orgAdmin, "42")).doesNotThrowAnyException();
    }

    @Test
    void learnerCannotInspectAnotherUsersNotificationStream() {
        CurrentUser learner = new CurrentUser(4L, "student@example.com", "STUDENT");

        assertThatThrownBy(() -> Authz.requireSelfOrAdmin(learner, "42"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("FORBIDDEN_NOT_OWNER");
    }
}
