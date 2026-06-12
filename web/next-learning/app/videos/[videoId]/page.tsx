import { VideoWatchPage } from "@/features/video-player/VideoWatchPage";

type Props = { params: Promise<{ videoId: string }> };

export default async function VideoPage({ params }: Props) {
  const { videoId } = await params;
  return <VideoWatchPage videoId={videoId} />;
}
