package edu.courseflow.discussion.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.discussion.dto.DiscussionDtos.CreateCommentRequestDto;
import edu.courseflow.discussion.dto.DiscussionDtos.CreateThreadRequestDto;
import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionCommentDto;
import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionThreadDto;
import edu.courseflow.discussion.repository.DiscussionRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DiscussionService {

    private final DiscussionRepository discussions;
    private final ObjectMapper objectMapper;

    public DiscussionService(DiscussionRepository discussions, ObjectMapper objectMapper) {
        this.discussions = discussions;
        this.objectMapper = objectMapper;
    }

    public List<DiscussionThreadDto> listThreads(Optional<UUID> courseId, Optional<UUID> assignmentId) {
        return discussions.listThreads(courseId.orElse(null), assignmentId.orElse(null));
    }

    public DiscussionThreadDto getThread(UUID threadId) {
        return discussions.findThread(threadId)
                .orElseThrow(() -> new NotFoundException("Discussion thread not found: " + threadId));
    }

    @Transactional
    public DiscussionThreadDto createThread(CreateThreadRequestDto request) {
        return discussions.createThread(request);
    }

    @Transactional
    public DiscussionCommentDto addComment(UUID threadId, CreateCommentRequestDto request) {
        DiscussionThreadDto thread = getThread(threadId);
        DiscussionCommentDto comment = discussions.addComment(threadId, request);
        discussions.outbox(UUID.fromString(comment.id()), "discussion.comment.created", toJson(Map.of(
                "commentId", comment.id(),
                "threadId", threadId.toString(),
                "courseId", thread.courseId(),
                "authorId", request.authorId(),
                "createdAt", comment.createdAt().toString())));
        return comment;
    }

    @Transactional
    public DiscussionThreadDto acceptComment(UUID threadId, UUID commentId) {
        DiscussionCommentDto comment = discussions.findComment(commentId)
                .orElseThrow(() -> new NotFoundException("Discussion comment not found: " + commentId));
        if (!threadId.toString().equals(comment.threadId())) {
            throw new BadRequestException("Comment does not belong to thread: " + threadId);
        }
        discussions.acceptComment(commentId);
        return getThread(threadId);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
