package edu.courseflow.chat.security;

import edu.courseflow.commonlibrary.web.CurrentUser;
import java.security.Principal;
import java.util.Set;

public record ChatPrincipal(Long id, String email, String role, Set<String> roles) implements Principal {

    @Override
    public String getName() {
        return String.valueOf(id);
    }

    public CurrentUser toCurrentUser() {
        return new CurrentUser(id, email, role, roles);
    }
}
