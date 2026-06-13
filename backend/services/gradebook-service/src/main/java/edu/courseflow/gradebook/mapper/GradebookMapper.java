package edu.courseflow.gradebook.mapper;

import edu.courseflow.gradebook.dto.GradebookDtos.FinalGradeDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeCategoryDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeItemDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradingSchemeDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradingSchemeEntryDto;
import edu.courseflow.gradebook.model.FinalGrade;
import edu.courseflow.gradebook.model.GradeCategory;
import edu.courseflow.gradebook.model.GradeItem;
import edu.courseflow.gradebook.model.GradingScheme;
import edu.courseflow.gradebook.model.GradingSchemeEntry;
import java.util.List;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface GradebookMapper {

    @Mapping(target = "categoryName", source = "category.name")
    @Mapping(target = "id", source = "item.id")
    @Mapping(target = "courseId", source = "item.courseId")
    @Mapping(target = "sourceType", source = "item.sourceType")
    @Mapping(target = "sourceId", source = "item.sourceId")
    @Mapping(target = "title", source = "item.title")
    @Mapping(target = "maxScore", source = "item.maxScore")
    @Mapping(target = "itemWeightPercent", source = "item.weightPercent")
    @Mapping(target = "categoryWeightPercent", source = "category.weightPercent")
    @Mapping(target = "aggregationMethod", source = "category.aggregationMethod")
    @Mapping(target = "dropLowest", source = "category.dropLowest")
    @Mapping(target = "latePenaltyPercent", source = "item.latePenaltyPercent")
    @Mapping(target = "published", source = "item.published")
    GradeItemDto toDto(GradeItem item, GradeCategory category);

    GradeCategoryDto toDto(GradeCategory category);

    @Mapping(target = "passThreshold", ignore = true)
    FinalGradeDto toDto(FinalGrade grade);

    GradingSchemeEntryDto toDto(GradingSchemeEntry entry);

    @Mapping(target = "isDefault", expression = "java(scheme.isDefaultScheme())")
    @Mapping(target = "entries", source = "entries")
    GradingSchemeDto toDto(GradingScheme scheme, List<GradingSchemeEntryDto> entries);
}
