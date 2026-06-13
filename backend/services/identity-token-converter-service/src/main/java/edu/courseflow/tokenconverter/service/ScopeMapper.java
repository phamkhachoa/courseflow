package edu.courseflow.tokenconverter.service;

import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import org.springframework.stereotype.Component;

@Component
public class ScopeMapper {

    public List<String> scopesFor(Collection<String> roles, String requestedScope) {
        Set<String> allowed = allowedScopes(roles);
        Set<String> requested = parseRequestedScopes(requestedScope);
        if (requested.isEmpty()) {
            return List.copyOf(allowed);
        }
        if (allowed.contains("*")) {
            return List.copyOf(requested);
        }
        requested.retainAll(allowed);
        return List.copyOf(requested);
    }

    private Set<String> allowedScopes(Collection<String> roles) {
        Set<String> scopes = new LinkedHashSet<>();
        if (roles == null) {
            return scopes;
        }
        for (String role : roles) {
            switch (normalize(role)) {
                case "ADMIN" -> scopes.add("*");
                case "ORG_ADMIN" -> scopes.addAll(List.of(
                        "org:read", "org:write", "course:read", "course:author", "learner:read",
                        "analytics:read"));
                case "INSTRUCTOR", "PROFESSOR", "TA" -> scopes.addAll(List.of(
                        "course:read", "course:author", "learner:read", "assessment:grade", "analytics:read"));
                case "STUDENT", "LEARNER" -> scopes.addAll(List.of(
                        "course:read", "learning:read", "learning:write", "assessment:submit",
                        "certificate:read"));
                default -> {
                }
            }
        }
        return scopes;
    }

    private Set<String> parseRequestedScopes(String requestedScope) {
        Set<String> scopes = new LinkedHashSet<>();
        if (requestedScope == null || requestedScope.isBlank()) {
            return scopes;
        }
        Arrays.stream(requestedScope.split("\\s+"))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .forEach(scopes::add);
        return scopes;
    }

    private String normalize(String role) {
        return role == null ? "" : role.trim().toUpperCase();
    }
}
