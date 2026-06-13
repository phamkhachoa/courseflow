package edu.courseflow.identity.config;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import java.util.Collections;
import java.util.Enumeration;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Overrides the {@code X-User-*} identity headers with values derived from a JWT that this service
 * verified itself. Any client-supplied copies are ignored, so a forged {@code X-User-Id} /
 * {@code X-User-Roles} cannot be used to impersonate a user or escalate privileges — the only trusted
 * source of identity is the signed token. Downstream code (e.g. {@code CurrentUserArgumentResolver})
 * keeps reading the same headers.
 *
 * <p>When constructed with a {@code null} identity (public endpoints), all four headers are blanked.
 */
public class VerifiedIdentityRequestWrapper extends HttpServletRequestWrapper {

    private static final Set<String> MANAGED_HEADERS = Set.of(
            GatewayHeaders.USER_ID.toLowerCase(),
            GatewayHeaders.USER_ROLE.toLowerCase(),
            GatewayHeaders.USER_ROLES.toLowerCase(),
            GatewayHeaders.USER_ROLE_SCOPES.toLowerCase(),
            GatewayHeaders.USER_EMAIL.toLowerCase());

    /** Verified values keyed by canonical (original-case) header name; null values mean "absent". */
    private final Map<String, String> overrides = new LinkedHashMap<>();

    public VerifiedIdentityRequestWrapper(HttpServletRequest request,
                                          String userId, String email, String primaryRole, String rolesCsv,
                                          String roleScopesCsv) {
        super(request);
        overrides.put(GatewayHeaders.USER_ID, userId);
        overrides.put(GatewayHeaders.USER_EMAIL, email);
        overrides.put(GatewayHeaders.USER_ROLE, primaryRole);
        overrides.put(GatewayHeaders.USER_ROLES, rolesCsv);
        overrides.put(GatewayHeaders.USER_ROLE_SCOPES, roleScopesCsv);
    }

    @Override
    public String getHeader(String name) {
        if (name != null && MANAGED_HEADERS.contains(name.toLowerCase())) {
            return canonicalValue(name);
        }
        return super.getHeader(name);
    }

    @Override
    public Enumeration<String> getHeaders(String name) {
        if (name != null && MANAGED_HEADERS.contains(name.toLowerCase())) {
            String value = canonicalValue(name);
            return value == null ? Collections.emptyEnumeration()
                    : Collections.enumeration(List.of(value));
        }
        return super.getHeaders(name);
    }

    @Override
    public Enumeration<String> getHeaderNames() {
        Set<String> names = new LinkedHashSet<>();
        Enumeration<String> original = super.getHeaderNames();
        while (original.hasMoreElements()) {
            String name = original.nextElement();
            if (name == null || !MANAGED_HEADERS.contains(name.toLowerCase())) {
                names.add(name);
            }
        }
        overrides.forEach((name, value) -> {
            if (value != null) {
                names.add(name);
            }
        });
        return Collections.enumeration(names);
    }

    private String canonicalValue(String requestedName) {
        for (Map.Entry<String, String> entry : overrides.entrySet()) {
            if (entry.getKey().equalsIgnoreCase(requestedName)) {
                return entry.getValue();
            }
        }
        return null;
    }
}
