package edu.courseflow.common.web;

import edu.courseflow.common.api.ApiResponse;
import edu.courseflow.common.model.ServiceInfo;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.env.Environment;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Arrays;

@RestController
@RequestMapping("/internal")
public class ServiceInfoController {
    private final String serviceName;
    private final String version;
    private final Environment environment;

    public ServiceInfoController(
            @Value("${spring.application.name:courseflow-service}") String serviceName,
            @Value("${courseflow.version:2.0.0}") String version,
            Environment environment
    ) {
        this.serviceName = serviceName;
        this.version = version;
        this.environment = environment;
    }

    @GetMapping("/service-info")
    public ApiResponse<ServiceInfo> serviceInfo(@RequestHeader(value = "X-Correlation-Id", required = false) String traceId) {
        String profiles = String.join(",", Arrays.asList(environment.getActiveProfiles()));
        return ApiResponse.ok(new ServiceInfo(serviceName, version, profiles), traceId);
    }
}
