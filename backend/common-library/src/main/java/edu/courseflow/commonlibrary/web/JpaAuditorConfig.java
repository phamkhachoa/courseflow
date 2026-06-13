package edu.courseflow.commonlibrary.web;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.domain.AuditorAware;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

@Configuration(proxyBeanMethods = false)
@ConditionalOnClass(name = "org.springframework.data.domain.AuditorAware")
public class JpaAuditorConfig {

    @Bean
    @ConditionalOnMissingBean
    public AuditorAware<String> gatewayAuditorAware() {
        return auditorAware();
    }

    public static AuditorAware<String> auditorAware() {
        return () -> {
            if (RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes attrs) {
                String email = attrs.getRequest().getHeader(GatewayHeaders.USER_EMAIL);
                return Optional.ofNullable(email);
            }
            return Optional.of("system");
        };
    }
}
