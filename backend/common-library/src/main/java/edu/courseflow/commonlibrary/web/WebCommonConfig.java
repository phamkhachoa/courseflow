package edu.courseflow.commonlibrary.web;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import java.util.List;
import java.util.Optional;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.domain.AuditorAware;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Registers the {@link CurrentUser} resolver and a JPA auditor so audit columns
 * ({@code createdBy}/{@code lastModifiedBy}) are filled from the gateway identity.
 * Services enable it by importing this class via component scan of the common package.
 */
@Configuration
public class WebCommonConfig implements WebMvcConfigurer {

    @Override
    public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
        resolvers.add(new CurrentUserArgumentResolver());
    }

    public static AuditorAware<String> gatewayAuditorAware() {
        return () -> {
            if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes attrs) {
                String email = attrs.getRequest().getHeader(GatewayHeaders.USER_EMAIL);
                return Optional.ofNullable(email);
            }
            return Optional.of("system");
        };
    }
}
