package edu.courseflow.search.repository;

import edu.courseflow.search.model.ProcessedEventDocument;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;

public interface ProcessedEventRepository extends ElasticsearchRepository<ProcessedEventDocument, String> {
}
