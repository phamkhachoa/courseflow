package edu.courseflow.chat.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;

public final class ChatDtos {

    private ChatDtos() {
    }

    public record ChatRoomDto(
            String id,
            String courseId,
            String title,
            String status,
            Instant createdAt
    ) {
    }

    public record ChatMessageDto(
            String id,
            String roomId,
            String courseId,
            String senderId,
            String senderName,
            String senderEmail,
            String messageType,
            String body,
            List<ChatAttachmentDto> attachments,
            String replyToMessageId,
            Instant editedAt,
            Instant deletedAt,
            Instant createdAt
    ) {
    }

    public record ChatAttachmentDto(
            @Size(max = 80) String mediaId,
            @Size(max = 180) String fileName,
            @Size(max = 120) String contentType,
            @Size(max = 600) String url
    ) {
    }

    public record SendMessageRequestDto(
            @NotBlank @Size(max = 2000) String body,
            @Size(max = 8) List<@Valid ChatAttachmentDto> attachments,
            @Size(max = 80) String replyToMessageId
    ) {
    }
}
