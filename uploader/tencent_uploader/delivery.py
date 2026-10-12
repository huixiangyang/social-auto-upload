"""视频号码率适配：只生成上传缓存，永不覆盖来源成片。"""
import asyncio
import hashlib
import json
import os
import tempfile
from pathlib import Path


async def prepare_upload_file(source, media_info):
    from conf import BASE_DIR
    from uploader.tencent_uploader.main import _probe_tencent_media, _validate_tencent_media_info
    from utils.log import tencent_logger

    source = Path(source)
    # 转码只处理码率超限，其他硬约束仍执行原校验。
    probe = {**media_info, 'format': {**media_info['format'], 'bit_rate': '6000000'}}
    _validate_tencent_media_info(probe, source)
    with source.open('rb') as stream:
        origin_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    cache = Path(BASE_DIR) / 'cache' / 'tencent-upload'
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / (origin_hash + '-h264-6m-v1.mp4')
    original_duration = float(media_info['format']['duration'])

    async def validate(path):
        result = await _probe_tencent_media(path)
        _validate_tencent_media_info(result, path)
        if abs(float(result['format']['duration']) - original_duration) > 0.15:
            raise ValueError('上传转码时长与原片不一致，拒绝使用')
        return result

    if target.exists():
        return str(target), await validate(target)
    descriptor, temporary = tempfile.mkstemp(prefix='.encoding-', suffix='.mp4', dir=cache)
    os.close(descriptor)
    process = None
    try:
        tencent_logger.info('视频号码率超限，生成6Mbps上传副本，原成片保留')
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-nostdin', '-v', 'error', '-i', str(source),
            '-map', '0:v:0', '-map', '0:a:0?', '-c:v', 'libx264', '-preset', 'fast',
            '-threads', '4', '-b:v', '6M', '-maxrate', '8M', '-bufsize', '12M',
            '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', '-y', temporary,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=900)
        if process.returncode:
            raise RuntimeError('视频号上传转码失败：' + stderr.decode(errors='replace')[-1000:])
        result = await validate(temporary)
        Path(temporary).replace(target)
        with target.open('rb') as stream:
            target_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        target.with_suffix('.json').write_text(json.dumps({'source_sha256': origin_hash,
            'upload_sha256': target_hash, 'source_bytes': source.stat().st_size,
            'upload_bytes': target.stat().st_size, 'media': result}, ensure_ascii=False, indent=2) + '\n')
        return str(target), result
    finally:
        if process and process.returncode is None:
            process.kill()
            await process.wait()
        Path(temporary).unlink(missing_ok=True)
