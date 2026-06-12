package edu.courseflow.search.model;

import java.time.Instant;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.DateFormat;
import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;

/**
 * Consumer dedup marker.
 *
 * <p>The architecture doc's standard dedup store is a relational {@code processed_events} table keyed
 * by {@code (event_id, consumer_name)}. search-service has no relational database (its only stores are
 * Elasticsearch and Kafka), so the equivalent marker is kept here as an Elasticsearch document in a
 * dedicated {@code courseflow-search-processed-events} index. The document {@code id} is
 * {@code consumerName + ":" + eventId}, which makes a re-create of an already-processed event a no-op
 * idempotent overwrite and lets the consumer cheaply check existence before acting.
 */
@Document(indexName = "courseflow-search-processed-events")
public class ProcessedEventDocument {

    @Id
    private String id;

    @Field(type = FieldType.Keyword)
    private String eventId;

    @Field(type = FieldType.Keyword)
    private String consumerName;

    @Field(type = FieldType.Date, format = DateFormat.date_time)
    private Instant processedAt;

    public ProcessedEventDocument() {
    }

    public ProcessedEventDocument(String consumerName, String eventId, Instant processedAt) {
        this.id = consumerName + ":" + eventId;
        this.consumerName = consumerName;
        this.eventId = eventId;
        this.processedAt = processedAt;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getEventId() {
        return eventId;
    }

    public void setEventId(String eventId) {
        this.eventId = eventId;
    }

    public String getConsumerName() {
        return consumerName;
    }

    public void setConsumerName(String consumerName) {
        this.consumerName = consumerName;
    }

    public Instant getProcessedAt() {
        return processedAt;
    }

    public void setProcessedAt(Instant processedAt) {
        this.processedAt = processedAt;
    }
}
