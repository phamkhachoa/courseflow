package edu.courseflow.commonlibrary.web;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.exception.UnauthorizedException;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.core.MethodParameter;
import org.springframework.http.HttpHeaders;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.method.support.ModelAndViewContainer;

/**
 * Lets a controller declare a {@link CurrentUser} parameter that is built from the gateway
 * identity headers. Keeps controllers free of header-parsing boilerplate.
 */
public class CurrentUserArgumentResolver implements HandlerMethodArgumentResolver {

    @Override
    public boolean supportsParameter(MethodParameter parameter) {
        return parameter.getParameterType().equals(CurrentUser.class);
    }

    @Override
    public Object resolveArgument(MethodParameter parameter, ModelAndViewContainer mavContainer,
                                  NativeWebRequest webRequest, WebDataBinderFactory binderFactory) {
        String id = webRequest.getHeader(GatewayHeaders.USER_ID);
        String email = webRequest.getHeader(GatewayHeaders.USER_EMAIL);
        String role = webRequest.getHeader(GatewayHeaders.USER_ROLE);
        String rolesHeader = webRequest.getHeader(GatewayHeaders.USER_ROLES);
        String roleScopesHeader = webRequest.getHeader(GatewayHeaders.USER_ROLE_SCOPES);
        String internalToken = firstBearerToken(
                webRequest.getHeader(GatewayHeaders.INTERNAL_AUTHORIZATION),
                webRequest.getHeader(HttpHeaders.AUTHORIZATION));
        Long userId = parseUserId(id);
        Set<String> roles = parseRoles(rolesHeader, role);
        return new CurrentUser(userId, email, role, roles, parseRoleScopes(roleScopesHeader), internalToken);
    }

    private String firstBearerToken(String... values) {
        for (String value : values) {
            if (value != null && value.regionMatches(true, 0, "Bearer ", 0, 7)) {
                return value.substring(7).trim();
            }
        }
        return null;
    }

    private Long parseUserId(String id) {
        if (id == null || id.isBlank()) {
            return null;
        }
        try {
            return Long.valueOf(id);
        } catch (NumberFormatException ex) {
            throw new UnauthorizedException("Invalid gateway user id header");
        }
    }

    private Set<String> parseRoles(String rolesHeader, String primaryRole) {
        if (rolesHeader == null || rolesHeader.isBlank()) {
            return primaryRole == null || primaryRole.isBlank() ? Set.of() : Set.of(primaryRole);
        }
        return Arrays.stream(rolesHeader.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .collect(Collectors.toCollection(LinkedHashSet::new));
    }

    private Set<CurrentUser.RoleAssignment> parseRoleScopes(String roleScopesHeader) {
        if (roleScopesHeader == null || roleScopesHeader.isBlank()) {
            return Set.of();
        }
        Set<CurrentUser.RoleAssignment> assignments = new LinkedHashSet<>();
        for (String tuple : roleScopesHeader.split(",")) {
            if (tuple.isBlank()) {
                continue;
            }
            String[] parts = tuple.split("\\.", -1);
            if (parts.length != 3) {
                throw new UnauthorizedException("Invalid gateway role scope header");
            }
            assignments.add(new CurrentUser.RoleAssignment(
                    decode(parts[0]),
                    decode(parts[1]),
                    decode(parts[2])));
        }
        return assignments;
    }

    private String decode(String encoded) {
        if (encoded == null || encoded.isBlank()) {
            return null;
        }
        try {
            return new String(Base64.getUrlDecoder().decode(encoded), java.nio.charset.StandardCharsets.UTF_8);
        } catch (IllegalArgumentException ex) {
            throw new UnauthorizedException("Invalid gateway role scope header");
        }
    }
}
