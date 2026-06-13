package edu.courseflow.course.mapper;

import edu.courseflow.course.dto.AuthoringDtos.CourseDraftDto;
import edu.courseflow.course.dto.AuthoringDtos.CourseVersionDto;
import edu.courseflow.course.dto.AuthoringDtos.ItemOutlineDto;
import edu.courseflow.course.dto.AuthoringDtos.ModuleOutlineDto;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.dto.CourseDtos.CourseMaterialDto;
import edu.courseflow.course.dto.CourseDtos.CourseMetadataDto;
import edu.courseflow.course.dto.CourseModuleDto;
import edu.courseflow.course.dto.ModuleItemDto;
import edu.courseflow.course.dto.ModuleProgressDto;
import edu.courseflow.course.model.Course;
import edu.courseflow.course.model.CourseMaterial;
import edu.courseflow.course.model.CourseModule;
import edu.courseflow.course.model.CourseVersion;
import edu.courseflow.course.model.LearnerModuleProgress;
import edu.courseflow.course.model.ModuleItem;
import java.util.List;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface CourseMapper {

    @Mapping(target = "materials", source = "materials")
    CourseDto toDto(Course course, List<CourseMaterialDto> materials);

    CourseMetadataDto toMetadataDto(Course course);

    CourseMaterialDto toDto(CourseMaterial material);

    @Mapping(target = "courseId", source = "course.id")
    @Mapping(target = "modules", source = "modules")
    CourseDraftDto toDraftDto(Course course, List<ModuleOutlineDto> modules);

    @Mapping(target = "moduleId", source = "module.id")
    @Mapping(target = "items", source = "items")
    @Mapping(target = "prerequisites", ignore = true)
    ModuleOutlineDto toOutlineDto(CourseModule module, List<ItemOutlineDto> items);

    @Mapping(target = "itemId", source = "id")
    @Mapping(target = "refId", source = "itemId")
    ItemOutlineDto toOutlineDto(ModuleItem item);

    CourseVersionDto toDto(CourseVersion version);

    @Mapping(target = "items", source = "items")
    CourseModuleDto toDto(CourseModule module, List<ModuleItemDto> items);

    ModuleItemDto toDto(ModuleItem item);

    ModuleProgressDto toDto(LearnerModuleProgress progress);
}
