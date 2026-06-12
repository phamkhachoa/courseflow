package edu.courseflow.search.repository;

import edu.courseflow.search.model.CourseSearchDocument;
import java.util.List;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;

public interface CourseSearchRepository extends ElasticsearchRepository<CourseSearchDocument, String> {

    List<CourseSearchDocument> findByStatus(String status);
}
