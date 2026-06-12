package edu.courseflow.discussion.repository;

import edu.courseflow.discussion.dto.DiscussionDtos.CreateCommentRequestDto;
import edu.courseflow.discussion.dto.DiscussionDtos.CreateThreadRequestDto;
import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionCommentDto;
import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionThreadDto;
import edu.courseflow.discussion.mapper.DiscussionMapper;
import edu.courseflow.discussion.model.DiscussionComment;
import edu.courseflow.discussion.model.DiscussionThread;
import edu.courseflow.discussion.model.OutboxEvent;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class DiscussionRepository {

    private final DiscussionThreadJpaRepository threads;
    private final DiscussionCommentJpaRepository comments;
    private final OutboxEventRepository outboxEvents;
    private final DiscussionMapper mapper;

    public DiscussionRepository(DiscussionThreadJpaRepository threads,
            DiscussionCommentJpaRepository comments,
            OutboxEventRepository outboxEvents,
            DiscussionMapper mapper) {
        this.threads = threads;
        this.comments = comments;
        this.outboxEvents = outboxEvents;
        this.mapper = mapper;
    }

    public List<DiscussionThreadDto> listThreads(UUID courseId, UUID assignmentId) {
        return threads.listFiltered(courseId, assignmentId).stream()
                .map(this::toThreadDto)
                .toList();
    }

    public Optional<DiscussionThreadDto> findThread(UUID threadId) {
        return threads.findById(threadId).map(this::toThreadDto);
    }

    public Optional<DiscussionCommentDto> findComment(UUID commentId) {
        return comments.findById(commentId).map(mapper::toDto);
    }

    public DiscussionThreadDto createThread(CreateThreadRequestDto request) {
        return toThreadDto(threads.save(new DiscussionThread(request)));
    }

    public DiscussionCommentDto addComment(UUID threadId, CreateCommentRequestDto request) {
        return mapper.toDto(comments.save(new DiscussionComment(threadId, request)));
    }

    public void acceptComment(UUID commentId) {
        comments.findById(commentId).ifPresent(comment -> {
            comment.accept();
            comments.save(comment);
        });
    }

    public void outbox(UUID aggregateId, String eventType, String payload) {
        outboxEvents.save(new OutboxEvent(aggregateId, "discussion-comment", eventType, payload));
    }

    private DiscussionThreadDto toThreadDto(DiscussionThread thread) {
        return mapper.toDto(thread, listComments(thread.getId()));
    }

    private List<DiscussionCommentDto> listComments(UUID threadId) {
        return comments.findByThreadIdOrderByCreatedAtAsc(threadId).stream()
                .map(mapper::toDto)
                .toList();
    }
}
