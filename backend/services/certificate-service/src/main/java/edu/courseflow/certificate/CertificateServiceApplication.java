package edu.courseflow.certificate;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class CertificateServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(CertificateServiceApplication.class, args);
    }
}
