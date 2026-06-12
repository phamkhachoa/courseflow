package edu.courseflow.announcement.repository;

import edu.courseflow.announcement.dto.AnnouncementDtos.AnnouncementDto;
import edu.courseflow.announcement.dto.AnnouncementDtos.CreateAnnouncementRequestDto;
import edu.courseflow.announcement.mapper.AnnouncementMapper;
import edu.courseflow.announcement.model.Announcement;
import edu.courseflow.announcement.model.OutboxEvent;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class AnnouncementRepository {

    private final AnnouncementJpaRepository announcements;
    private final OutboxEventRepository outboxEvents;
    private final AnnouncementMapper mapper;

    public AnnouncementRepository(AnnouncementJpaRepository announcements,
            OutboxEventRepository outboxEvents,
            AnnouncementMapper mapper) {
        this.announcements = announcements;
        this.outboxEvents = outboxEvents;
        this.mapper = mapper;
    }

    public List<AnnouncementDto> list(UUID courseId, String status) {
        return announcements.listFiltered(courseId, status).stream()
                .map(mapper::toDto)
                .toList();
    }

    public Optional<AnnouncementDto> find(UUID announcementId) {
        return announcements.findById(announcementId).map(mapper::toDto);
    }

    public AnnouncementDto create(CreateAnnouncementRequestDto request) {
        return mapper.toDto(announcements.save(new Announcement(request)));
    }

    public void publish(UUID announcementId) {
        announcements.findById(announcementId).ifPresent(announcement -> {
            announcement.publish();
            announcements.save(announcement);
        });
    }

    public void outbox(UUID aggregateId, String eventType, String payload) {
        outboxEvents.save(new OutboxEvent(aggregateId, "announcement", eventType, payload));
    }

}
