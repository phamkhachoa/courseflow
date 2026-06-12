package edu.courseflow.commonlibrary.web;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.exception.UnauthorizedException;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.core.MethodParameter;
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
        Long userId = parseUserId(id);
        Set<String> roles = parseRoles(rolesHeader, role);
        return new CurrentUser(userId, email, role, roles);
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
}
