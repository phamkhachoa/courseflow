package edu.courseflow.chat.repository;

import edu.courseflow.chat.model.ChatRoom;
import java.util.Optional;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface ChatRoomRepository extends MongoRepository<ChatRoom, String> {

    Optional<ChatRoom> findByCourseId(String courseId);
}
