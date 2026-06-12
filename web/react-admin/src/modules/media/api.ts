import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type MediaAsset = {
  id: string;
  ownerId: string;
  fileName: string;
  contentType: string;
  storageKey: string;
  sizeBytes: number;
  createdAt?: string;
};

export type VideoAsset = {
  id: string;
  mediaAssetId?: string | null;
  courseId?: string | null;
  title: string;
  sourceStorageKey: string;
  durationSeconds?: number | null;
  status: string;
  createdAt?: string;
};

export async function listAssets(): Promise<MediaAsset[]> {
  const { data } = await apiClient.get("/admin/v1/media/assets");
  return unwrapList<MediaAsset>(data);
}
export async function getAsset(id: string): Promise<MediaAsset> {
  const { data } = await apiClient.get(`/admin/v1/media/assets/${id}`);
  return unwrap<MediaAsset>(data);
}
export async function registerAsset(input: {
  fileName: string;
  contentType: string;
  storageKey: string;
  sizeBytes: number;
}): Promise<MediaAsset> {
  const { data } = await apiClient.post("/admin/v1/media/assets", input);
  return unwrap<MediaAsset>(data);
}

export type PresignedUpload = {
  storageKey: string;
  uploadUrl: string;
  expiresAt: string;
};

export async function getAssetUploadUrl(fileName: string, contentType: string): Promise<PresignedUpload> {
  const { data } = await apiClient.post("/admin/v1/media/assets/upload-url", { fileName, contentType });
  return unwrap<PresignedUpload>(data);
}

export async function getVideoUploadUrl(title: string, fileName: string, contentType: string): Promise<PresignedUpload> {
  const { data } = await apiClient.post("/admin/v1/media/videos/upload-url", { title, fileName, contentType });
  return unwrap<PresignedUpload>(data);
}

export async function listVideos(courseId?: string): Promise<VideoAsset[]> {
  const { data } = await apiClient.get("/admin/v1/media/videos", {
    params: courseId ? { courseId } : undefined
  });
  return unwrapList<VideoAsset>(data);
}

export async function registerVideo(input: {
  title: string;
  sourceStorageKey: string;
  courseId?: string;
  mediaAssetId?: string;
  durationSeconds?: number;
}): Promise<VideoAsset> {
  const { data } = await apiClient.post("/admin/v1/media/videos", input);
  return unwrap<VideoAsset>(data);
}

export async function transcodeVideo(videoId: string): Promise<VideoAsset> {
  const { data } = await apiClient.post(`/admin/v1/media/videos/${videoId}/transcode`);
  return unwrap<VideoAsset>(data);
}

export async function getVideoPlaybackUrl(videoId: string): Promise<{ videoId: string; url: string; expiresAt: string }> {
  const { data } = await apiClient.get(`/admin/v1/media/videos/${videoId}/playback-url`);
  return unwrap<{ videoId: string; url: string; expiresAt: string }>(data);
}

export async function getDownloadUrl(mediaId: string): Promise<{ downloadUrl: string; expiresAt: string }> {
  const { data } = await apiClient.get(`/admin/v1/media/assets/${mediaId}/download-url`);
  return unwrap<{ downloadUrl: string; expiresAt: string }>(data);
}
