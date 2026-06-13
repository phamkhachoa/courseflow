package edu.courseflow.commonlibrary.web;

import java.util.List;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * Registers the {@link CurrentUser} resolver. JPA auditing lives in {@link JpaAuditorConfig} so
 * non-JPA services can use the web helpers without requiring Spring Data on their runtime classpath.
 */
@Configuration
public class WebCommonConfig implements WebMvcConfigurer {

    @Override
    public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
        resolvers.add(new CurrentUserArgumentResolver());
    }
}
