package edu.courseflow.identity.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import org.springframework.stereotype.Component;

@Component
public class PasswordPolicy {

    public static final int MIN_LENGTH = 12;

    public void validate(String password) {
        if (password == null || password.length() < MIN_LENGTH) {
            throw new BadRequestException("PASSWORD_TOO_WEAK");
        }
        boolean hasLower = false;
        boolean hasUpper = false;
        boolean hasDigit = false;
        boolean hasSymbol = false;
        for (int i = 0; i < password.length(); i++) {
            char c = password.charAt(i);
            if (Character.isLowerCase(c)) {
                hasLower = true;
            } else if (Character.isUpperCase(c)) {
                hasUpper = true;
            } else if (Character.isDigit(c)) {
                hasDigit = true;
            } else {
                hasSymbol = true;
            }
        }
        if (!hasLower || !hasUpper || !hasDigit || !hasSymbol) {
            throw new BadRequestException("PASSWORD_TOO_WEAK");
        }
    }
}
