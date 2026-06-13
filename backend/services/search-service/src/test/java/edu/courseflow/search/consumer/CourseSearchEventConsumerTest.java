package edu.courseflow.search.consumer;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.search.dto.SearchDtos.IndexCourseRequestDto;
import edu.courseflow.search.model.ProcessedEventDocument;
import edu.courseflow.search.repository.ProcessedEventRepository;
import edu.courseflow.search.service.SearchService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CourseSearchEventConsumerTest {

    private SearchService search;
    private ProcessedEventRepository processedEvents;
    private CourseSearchEventConsumer consumer;

    @BeforeEach
    void setUp() {
        search = org.mockito.Mockito.mock(SearchService.class);
        processedEvents = org.mockito.Mockito.mock(ProcessedEventRepository.class);
        consumer = new CourseSearchEventConsumer(search, processedEvents, new ObjectMapper());
    }

    @Test
    void indexesPublishedCourseFromDebeziumEnvelope() throws Exception {
        when(processedEvents.existsById("search-service:course-cdc:course-cdc:course-1:c:7:100")).thenReturn(false);

        consumer.onCourseRowChanged("""
                {
                  "op": "c",
                  "source": { "txId": 7, "lsn": 100 },
                  "before": null,
                  "after": {
                    "id": "course-1",
                    "code": "SE401",
                    "title": "Production Microservices",
                    "slug": "production-microservices",
                    "summary": "Build production systems",
                    "department_id": "dept-1",
                    "level": "ADVANCED",
                    "status": "PUBLISHED"
                  }
                }
                """);

        verify(search).indexCourse(new IndexCourseRequestDto(
                "course-1",
                "SE401",
                "Production Microservices",
                "production-microservices",
                "Build production systems",
                "dept-1",
                "ADVANCED",
                "PUBLISHED"));
        verify(processedEvents).save(any(ProcessedEventDocument.class));
    }

    @Test
    void deletesArchivedCourseFromDebeziumEnvelope() throws Exception {
        when(processedEvents.existsById("search-service:course-cdc:course-cdc:course-1:u:8:101")).thenReturn(false);

        consumer.onCourseRowChanged("""
                {
                  "op": "u",
                  "source": { "txId": 8, "lsn": 101 },
                  "before": {
                    "id": "course-1",
                    "status": "PUBLISHED"
                  },
                  "after": {
                    "id": "course-1",
                    "code": "SE401",
                    "title": "Production Microservices",
                    "slug": "production-microservices",
                    "summary": "Build production systems",
                    "department_id": "dept-1",
                    "level": "ADVANCED",
                    "status": "ARCHIVED"
                  }
                }
                """);

        verify(search).deleteCourse("course-1");
        verify(processedEvents).save(any(ProcessedEventDocument.class));
    }

    @Test
    void skipsAlreadyProcessedEvent() throws Exception {
        when(processedEvents.existsById("search-service:course-cdc:course-cdc:course-1:r:9:102")).thenReturn(true);

        consumer.onCourseRowChanged("""
                {
                  "op": "r",
                  "source": { "txId": 9, "lsn": 102 },
                  "before": null,
                  "after": {
                    "id": "course-1",
                    "code": "SE401",
                    "title": "Production Microservices",
                    "slug": "production-microservices",
                    "summary": "Build production systems",
                    "department_id": "dept-1",
                    "level": "ADVANCED",
                    "status": "PUBLISHED"
                  }
                }
                """);

        verify(search, never()).indexCourse(any());
        verify(processedEvents, never()).save(any());
    }
}
