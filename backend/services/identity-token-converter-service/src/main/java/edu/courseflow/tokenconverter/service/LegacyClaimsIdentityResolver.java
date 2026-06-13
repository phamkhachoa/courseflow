package edu.courseflow.tokenconverter.service;

import java.util.Collection;
import java.util.List;
import java.util.Map;

final class LegacyClaimsIdentityResolver implements AccessControlIdentityResolver {

    static final LegacyClaimsIdentityResolver INSTANCE = new LegacyClaimsIdentityResolver();

    private LegacyClaimsIdentityResolver() {
    }

    @Override
    public ResolvedIdentity resolve(ExternalTokenClaims externalClaims) {
        String userId = String.valueOf(externalClaims.get("uid"));
        return new ResolvedIdentity(
                userId,
                externalClaims.issuer(),
                externalClaims.subject(),
                externalClaims.subject(),
                "ACTIVE",
                roleAssignments(externalClaims.get("roles")));
    }

    @SuppressWarnings("unchecked")
    private List<ResolvedIdentity.RoleAssignment> roleAssignments(Object rawRoles) {
        if (!(rawRoles instanceof Collection<?> roles)) {
            return List.of();
        }
        return roles.stream()
                .map(raw -> {
                    if (raw instanceof Map<?, ?> map) {
                        Object code = ((Map<String, Object>) map).get("code");
                        if (code == null || code.toString().isBlank()) {
                            return null;
                        }
                        return new ResolvedIdentity.RoleAssignment(
                                code.toString(),
                                stringValue(((Map<String, Object>) map).get("scopeType"), "PLATFORM"),
                                stringValue(((Map<String, Object>) map).get("scopeId"), null));
                    }
                    if (raw != null && !raw.toString().isBlank()) {
                        return new ResolvedIdentity.RoleAssignment(raw.toString(), "PLATFORM", null);
                    }
                    return null;
                })
                .filter(java.util.Objects::nonNull)
                .toList();
    }

    private String stringValue(Object value, String fallback) {
        return value == null || value.toString().isBlank() ? fallback : value.toString();
    }
}
