package edu.courseflow.identity.config;

import edu.courseflow.commonlibrary.web.JpaAuditorConfig;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;
import org.springframework.data.domain.AuditorAware;

/**
 * Pulls in the shared exception handler, gateway-identity argument resolver and JPA auditor
 * from common-library. Every service imports the equivalent of this.
 */
@Configuration
@Import({
        edu.courseflow.commonlibrary.exception.ApiExceptionHandler.class,
        edu.courseflow.commonlibrary.exception.PersistenceExceptionHandler.class,
        edu.courseflow.commonlibrary.web.WebCommonConfig.class
})
public class CommonScanConfig {

    @Bean
    public AuditorAware<String> auditorAware() {
        return JpaAuditorConfig.auditorAware();
    }
}
