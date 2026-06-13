package edu.courseflow.gateway;

import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Import;

@Configuration
@Import({InternalJwtProperties.class, InternalJwtService.class})
public class GatewayInternalJwtConfig {
}
