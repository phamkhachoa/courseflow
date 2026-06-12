package edu.courseflow.media.repository;

import edu.courseflow.media.dto.MediaDtos.MediaAssetDto;
import edu.courseflow.media.dto.MediaDtos.RegisterMediaAssetRequestDto;
import edu.courseflow.media.mapper.MediaMapper;
import edu.courseflow.media.model.MediaAsset;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class MediaRepository {

    private final MediaAssetJpaRepository assets;
    private final MediaMapper mapper;

    public MediaRepository(MediaAssetJpaRepository assets, MediaMapper mapper) {
        this.assets = assets;
        this.mapper = mapper;
    }

    public List<MediaAssetDto> list(String ownerId) {
        List<MediaAsset> rows = ownerId == null
                ? assets.findAllByOrderByCreatedAtDesc()
                : assets.findByOwnerIdOrderByCreatedAtDesc(ownerId);
        return rows.stream().map(mapper::toDto).toList();
    }

    public Optional<MediaAssetDto> find(UUID mediaId) {
        return assets.findById(mediaId).map(mapper::toDto);
    }

    public MediaAssetDto register(RegisterMediaAssetRequestDto request) {
        return create(request.ownerId(), request.fileName(), request.contentType(),
                request.storageKey(), request.sizeBytes());
    }

    /** Insert an asset row from explicit fields (used by the multipart upload path). */
    public MediaAssetDto create(String ownerId, String fileName, String contentType,
                                String storageKey, long sizeBytes) {
        return mapper.toDto(assets.save(new MediaAsset(ownerId, fileName, contentType, storageKey, sizeBytes)));
    }
}
