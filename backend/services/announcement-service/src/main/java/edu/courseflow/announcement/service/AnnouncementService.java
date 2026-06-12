package edu.courseflow.announcement.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.announcement.dto.AnnouncementDtos.AnnouncementDto;
import edu.courseflow.announcement.dto.AnnouncementDtos.CreateAnnouncementRequestDto;
import edu.courseflow.announcement.repository.AnnouncementRepository;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AnnouncementService {

    private final AnnouncementRepository announcements;
    private final ObjectMapper objectMapper;

    public AnnouncementService(AnnouncementRepository announcements, ObjectMapper objectMapper) {
        this.announcements = announcements;
        this.objectMapper = objectMapper;
    }

    public List<AnnouncementDto> list(Optional<UUID> courseId, Optional<String> status) {
        return announcements.list(courseId.orElse(null), status.orElse(null));
    }

    public AnnouncementDto get(UUID announcementId) {
        return announcements.find(announcementId)
                .orElseThrow(() -> new NotFoundException("Announcement not found: " + announcementId));
    }

    @Transactional
    public AnnouncementDto create(CreateAnnouncementRequestDto request) {
        return announcements.create(request);
    }

    @Transactional
    public AnnouncementDto publish(UUID announcementId) {
        announcements.publish(announcementId);
        AnnouncementDto published = get(announcementId);
        String eventId = UUID.randomUUID().toString();
        announcements.outbox(announcementId, "announcement.published", toJson(Map.of(
                "eventId", eventId,
                "announcementId", announcementId.toString(),
                "courseId", published.courseId(),
                "title", published.title(),
                "audience", published.audience(),
                "publishedAt", published.publishedAt().toString())));
        return published;
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
