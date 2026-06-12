package edu.courseflow.chat.controller;

import edu.courseflow.chat.dto.ChatDtos.ChatMessageDto;
import edu.courseflow.chat.dto.ChatDtos.ChatRoomDto;
import edu.courseflow.chat.dto.ChatDtos.SendMessageRequestDto;
import edu.courseflow.chat.service.ChatService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import jakarta.validation.Valid;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ChatController {

    private final ChatService chat;

    public ChatController(ChatService chat) {
        this.chat = chat;
    }

    @GetMapping("/internal/chat/courses/{courseId}/room")
    public ChatRoomDto getRoom(@PathVariable UUID courseId, CurrentUser user) {
        return chat.getRoom(courseId, user);
    }

    @GetMapping("/internal/chat/courses/{courseId}/messages")
    public List<ChatMessageDto> listMessages(@PathVariable UUID courseId,
                                             @RequestParam(required = false)
                                             @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant before,
                                             @RequestParam(required = false) Integer limit,
                                             CurrentUser user) {
        return chat.listMessages(courseId, before, limit, user);
    }

    @PostMapping("/internal/chat/courses/{courseId}/messages")
    public ChatMessageDto sendMessage(@PathVariable UUID courseId,
                                      @Valid @RequestBody SendMessageRequestDto request,
                                      CurrentUser user) {
        return chat.sendMessage(courseId, request, user);
    }
}
