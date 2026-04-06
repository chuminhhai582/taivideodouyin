from fastapi import APIRouter, HTTPException, Query
from ..services import ytdlp_service
from ..models.schemas import ChannelVideosResponse

router = APIRouter(prefix="/channel", tags=["channel"])


@router.get("/videos", response_model=ChannelVideosResponse)
async def get_channel_videos(url: str = Query(..., description="URL kênh Douyin")):
    """Lấy danh sách tất cả video của kênh Douyin"""
    try:
        result = await ytdlp_service.get_channel_videos(url)
        return ChannelVideosResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
