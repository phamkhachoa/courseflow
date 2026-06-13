package edu.courseflow.usermanagement.service;

import java.util.List;
import java.util.Map;

public interface KeycloakAdminClient {

    String issuer();

    KeycloakUser createUser(String email, String fullName);

    void setCourseFlowUserId(String keycloakUserId, String courseflowUserId);

    void sendSetupEmail(String keycloakUserId);

    KeycloakUser getUser(String keycloakUserId);

    void disableUser(String keycloakUserId);

    void logoutUser(String keycloakUserId);

    void deleteUser(String keycloakUserId);

    record KeycloakUser(
            String id,
            String username,
            String email,
            String firstName,
            String lastName,
            boolean enabled,
            boolean emailVerified,
            List<String> requiredActions,
            Map<String, List<String>> attributes) {
    }
}
