package edu.courseflow.media.mapper;

import edu.courseflow.media.dto.MediaDtos.MediaAssetDto;
import edu.courseflow.media.dto.VideoDtos.VideoAssetDto;
import edu.courseflow.media.dto.VideoDtos.VideoCaptionDto;
import edu.courseflow.media.dto.VideoDtos.VideoProgressDto;
import edu.courseflow.media.dto.VideoDtos.VideoRenditionDto;
import edu.courseflow.media.model.MediaAsset;
import edu.courseflow.media.model.VideoAsset;
import edu.courseflow.media.model.VideoCaption;
import edu.courseflow.media.model.VideoProgress;
import edu.courseflow.media.model.VideoRendition;
import java.util.List;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface MediaMapper {

    MediaAssetDto toDto(MediaAsset asset);

    @Mapping(target = "renditions", source = "renditions")
    @Mapping(target = "captions", source = "captions")
    VideoAssetDto toDto(VideoAsset video, List<VideoRenditionDto> renditions, List<VideoCaptionDto> captions);

    VideoRenditionDto toDto(VideoRendition rendition);

    VideoCaptionDto toDto(VideoCaption caption);

    VideoProgressDto toDto(VideoProgress progress);
}
