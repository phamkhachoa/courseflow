package edu.courseflow.chat.mapper;

import edu.courseflow.chat.dto.ChatDtos.ChatAttachmentDto;
import edu.courseflow.chat.dto.ChatDtos.ChatMessageDto;
import edu.courseflow.chat.dto.ChatDtos.ChatRoomDto;
import edu.courseflow.chat.model.ChatAttachment;
import edu.courseflow.chat.model.ChatMessage;
import edu.courseflow.chat.model.ChatRoom;
import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import java.util.List;
import org.mapstruct.Mapper;

@Mapper(config = CourseFlowMapperConfig.class)
public interface ChatMapper {

    ChatRoomDto toDto(ChatRoom room);

    ChatMessageDto toDto(ChatMessage message);

    ChatAttachment toAttachment(ChatAttachmentDto attachment);

    List<ChatAttachment> toAttachments(List<ChatAttachmentDto> attachments);

    List<ChatMessageDto> toMessageDtos(List<ChatMessage> messages);
}
