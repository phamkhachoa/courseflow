package edu.courseflow.tokenconverter;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = "edu.courseflow")
public class IdentityTokenConverterApplication {

    public static void main(String[] args) {
        SpringApplication.run(IdentityTokenConverterApplication.class, args);
    }
}
