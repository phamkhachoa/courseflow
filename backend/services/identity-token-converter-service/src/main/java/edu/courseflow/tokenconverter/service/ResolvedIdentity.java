package edu.courseflow.tokenconverter.service;

import java.util.List;

public record ResolvedIdentity(
        String userId,
        String externalIssuer,
        String externalSubject,
        String email,
        String status,
        List<RoleAssignment> roleAssignments) {

    public record RoleAssignment(String code, String scopeType, String scopeId) {
    }
}
