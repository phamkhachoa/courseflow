package edu.courseflow.notification.config;

import java.util.HashMap;
import java.util.Map;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.listener.DeadLetterPublishingRecoverer;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.ExponentialBackOff;

/**
 * Wires a {@link DefaultErrorHandler} with a {@link DeadLetterPublishingRecoverer} onto the Kafka
 * listener container. Without this, an exception in a {@code @KafkaListener} is retried indefinitely
 * (or, with the default 9 attempts, the record is eventually dropped and the event is lost).
 *
 * <p>Behaviour:
 * <ul>
 *   <li>A failing record is retried with exponential backoff up to a bounded number of attempts.</li>
 *   <li>After the budget is exhausted the record is published to {@code <topic>.DLT} and the offset is
 *       committed, so one poison message can no longer block the partition forever.</li>
 * </ul>
 *
 * <p>Consumers should still parse payloads null-safely so that <em>recoverable</em> bad data is skipped
 * inline; the DLT is the backstop for genuinely unexpected failures (broker hiccups, downstream outages
 * past the retry budget).
 */
@Configuration
public class KafkaErrorHandlingConfig {

    /** Dedicated producer for dead-letter records (consumer-only service otherwise). */
    @Bean
    public ProducerFactory<Object, Object> dltProducerFactory(
            @Value("${spring.kafka.bootstrap-servers:localhost:9092}") String bootstrapServers) {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        return new DefaultKafkaProducerFactory<>(props);
    }

    @Bean
    public KafkaTemplate<Object, Object> dltKafkaTemplate(ProducerFactory<Object, Object> dltProducerFactory) {
        return new KafkaTemplate<>(dltProducerFactory);
    }

    @Bean
    public DefaultErrorHandler kafkaErrorHandler(KafkaTemplate<Object, Object> dltKafkaTemplate) {
        DeadLetterPublishingRecoverer recoverer = new DeadLetterPublishingRecoverer(dltKafkaTemplate);
        // Exponential backoff 1s -> 2s -> ... capped at 10s per attempt, giving up after ~30s total so a
        // poison record is routed to <topic>.DLT instead of blocking the partition forever.
        ExponentialBackOff backOff = new ExponentialBackOff(1000L, 2.0);
        backOff.setMaxInterval(10000L);
        backOff.setMaxElapsedTime(30000L);
        return new DefaultErrorHandler(recoverer, backOff);
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, String> kafkaListenerContainerFactory(
            ConsumerFactory<String, String> consumerFactory, DefaultErrorHandler kafkaErrorHandler) {
        ConcurrentKafkaListenerContainerFactory<String, String> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);
        factory.setCommonErrorHandler(kafkaErrorHandler);
        return factory;
    }
}
