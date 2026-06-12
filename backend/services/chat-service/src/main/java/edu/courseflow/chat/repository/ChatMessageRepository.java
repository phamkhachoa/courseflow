package edu.courseflow.chat.repository;

import edu.courseflow.chat.model.ChatMessage;
import java.time.Instant;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface ChatMessageRepository extends MongoRepository<ChatMessage, String> {

    Page<ChatMessage> findByCourseIdAndDeletedAtIsNullOrderByCreatedAtDesc(String courseId, Pageable pageable);

    Page<ChatMessage> findByCourseIdAndDeletedAtIsNullAndCreatedAtBeforeOrderByCreatedAtDesc(
            String courseId, Instant before, Pageable pageable);
}
