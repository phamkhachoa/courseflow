package edu.courseflow.chat.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import edu.courseflow.chat.security.ChatJwtVerifier;
import edu.courseflow.chat.security.ChatPrincipal;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessagingException;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.MessageBuilder;

class ChatStompAuthInterceptorTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");

    private final ChatJwtVerifier jwtVerifier = mock(ChatJwtVerifier.class);
    private final CourseAccessClient courseAccess = mock(CourseAccessClient.class);
    private final ChatStompAuthInterceptor interceptor = new ChatStompAuthInterceptor(jwtVerifier, courseAccess);

    @Test
    void connectVerifiesBearerAndStoresPrincipal() {
        ChatPrincipal principal = principal();
        when(jwtVerifier.verify("Bearer external-token")).thenReturn(principal);
        StompHeaderAccessor accessor = StompHeaderAccessor.create(StompCommand.CONNECT);
        accessor.setNativeHeader("Authorization", "Bearer external-token");
        accessor.setLeaveMutable(true);
        Message<byte[]> message = MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());

        Message<?> result = interceptor.preSend(message, null);
        StompHeaderAccessor resultAccessor = StompHeaderAccessor.wrap(result);

        assertThat(resultAccessor.getUser()).isEqualTo(principal);
    }

    @Test
    void subscribeRequiresAuthenticatedPrincipal() {
        StompHeaderAccessor accessor = StompHeaderAccessor.create(StompCommand.SUBSCRIBE);
        accessor.setDestination("/topic/courses/" + COURSE_ID + "/chat");
        Message<byte[]> message = MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());

        assertThatThrownBy(() -> interceptor.preSend(message, null))
                .isInstanceOf(MessagingException.class)
                .hasMessageContaining("Authenticated STOMP user required");
    }

    @Test
    void subscribeRejectsUnknownDestinationInsteadOfDefaultAllowing() {
        StompHeaderAccessor accessor = StompHeaderAccessor.create(StompCommand.SUBSCRIBE);
        accessor.setUser(principal());
        accessor.setDestination("/topic/system/broadcast");
        Message<byte[]> message = MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());

        assertThatThrownBy(() -> interceptor.preSend(message, null))
                .isInstanceOf(MessagingException.class)
                .hasMessageContaining("Unsupported STOMP destination");
        verifyNoInteractions(courseAccess);
    }

    @Test
    void sendChecksCourseAccessForAllowedDestination() {
        ChatPrincipal principal = principal();
        StompHeaderAccessor accessor = StompHeaderAccessor.create(StompCommand.SEND);
        accessor.setUser(principal);
        accessor.setDestination("/app/courses/" + COURSE_ID + "/send");
        Message<byte[]> message = MessageBuilder.createMessage(new byte[0], accessor.getMessageHeaders());

        Message<?> result = interceptor.preSend(message, null);

        assertThat(result).isSameAs(message);
        verify(courseAccess).requireCourseAccess(principal.toCurrentUser(), COURSE_ID);
    }

    private ChatPrincipal principal() {
        return new ChatPrincipal(42L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));
    }
}
