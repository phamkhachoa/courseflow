package edu.courseflow.chat.config;

import edu.courseflow.chat.security.ChatJwtVerifier;
import edu.courseflow.chat.security.ChatPrincipal;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import java.util.List;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;
import org.springframework.stereotype.Component;

@Component
public class ChatStompAuthInterceptor implements ChannelInterceptor {

    private static final Pattern TOPIC_DESTINATION =
            Pattern.compile("^/topic/courses/([0-9a-fA-F-]{36})/chat$");
    private static final Pattern SEND_DESTINATION =
            Pattern.compile("^/app/courses/([0-9a-fA-F-]{36})/send$");

    private final ChatJwtVerifier jwtVerifier;
    private final CourseAccessClient courseAccess;

    public ChatStompAuthInterceptor(ChatJwtVerifier jwtVerifier, CourseAccessClient courseAccess) {
        this.jwtVerifier = jwtVerifier;
        this.courseAccess = courseAccess;
    }

    @Override
    public Message<?> preSend(Message<?> message, MessageChannel channel) {
        StompHeaderAccessor accessor = MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
        if (accessor == null || accessor.getCommand() == null) {
            return message;
        }

        StompCommand command = accessor.getCommand();
        if (StompCommand.CONNECT.equals(command)) {
            List<String> headers = accessor.getNativeHeader("Authorization");
            String authHeader = headers == null || headers.isEmpty() ? null : headers.get(0);
            accessor.setUser(jwtVerifier.verify(authHeader));
            return message;
        }

        if (StompCommand.SUBSCRIBE.equals(command) || StompCommand.SEND.equals(command)) {
            ChatPrincipal principal = principal(accessor);
            UUID courseId = extractCourseId(command, accessor.getDestination());
            if (courseId != null) {
                courseAccess.requireCourseAccess(principal.toCurrentUser(), courseId);
            }
        }
        return message;
    }

    private ChatPrincipal principal(StompHeaderAccessor accessor) {
        if (accessor.getUser() instanceof ChatPrincipal principal) {
            return principal;
        }
        throw new MessagingException("Authenticated STOMP user required");
    }

    private UUID extractCourseId(StompCommand command, String destination) {
        if (destination == null || destination.isBlank()) {
            return null;
        }
        Matcher matcher = StompCommand.SUBSCRIBE.equals(command)
                ? TOPIC_DESTINATION.matcher(destination)
                : SEND_DESTINATION.matcher(destination);
        if (!matcher.matches()) {
            return null;
        }
        return UUID.fromString(matcher.group(1));
    }
}
