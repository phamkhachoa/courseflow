package edu.courseflow.search.mapper;

import edu.courseflow.search.dto.SearchDtos.CourseSearchDto;
import edu.courseflow.search.dto.SearchDtos.IndexCourseRequestDto;
import edu.courseflow.search.model.CourseSearchDocument;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface SearchMapper {

    CourseSearchDto toDto(CourseSearchDocument document);

    @Mapping(target = "updatedAt", expression = "java(java.time.Instant.now())")
    CourseSearchDocument toDocument(IndexCourseRequestDto request);
}
