#!/usr/bin/env python3
'''Upload finished assets to S3/R2/Cloudflare storage.'''
import os, logging, mimetypes
logger = logging.getLogger('pipeline.uploader')

def upload_outputs(edited_output, project_id, job_id, s3_bucket, s3_key, s3_secret, s3_region, s3_endpoint):
    '''Upload video, subtitle, and thumbnail to cloud storage.'''
    video_path = edited_output.get('videoPath', '')
    subtitle_path = edited_output.get('subtitlePath')
    thumbnail_path = edited_output.get('thumbnailPath')

    if not s3_bucket or not s3_key or not s3_secret:
        logger.warning(f'[{job_id}] S3 not configured - returning local paths')
        return {
            'videoUrl': _local_url(video_path),
            'downloadUrl': _local_url(video_path),
            'subtitleUrl': _local_url(subtitle_path) if subtitle_path else None,
            'thumbnailUrl': _local_url(thumbnail_path) if thumbnail_path else 'https://picsum.photos/1280/720'
        }

    try:
        import boto3
        from botocore.config import Config

        client_args = {
            'aws_access_key_id': s3_key,
            'aws_secret_access_key': s3_secret,
            'region_name': s3_region,
            'config': Config(signature_version='s3v4')
        }
        if s3_endpoint:
            client_args['endpoint_url'] = s3_endpoint

        s3 = boto3.client('s3', **client_args)
        base_key = f'movies/{project_id}/{job_id}'

        # Upload video
        video_url = _upload_file(s3, video_path, s3_bucket, f'{base_key}/movie.mp4', job_id, s3_endpoint)

        # Upload subtitle
        subtitle_url = None
        if subtitle_path and os.path.exists(subtitle_path):
            subtitle_url = _upload_file(s3, subtitle_path, s3_bucket, f'{base_key}/subtitles.srt', job_id, s3_endpoint)

        # Upload thumbnail
        thumbnail_url = 'https://picsum.photos/1280/720'
        if thumbnail_path and os.path.exists(thumbnail_path):
            thumbnail_url = _upload_file(s3, thumbnail_path, s3_bucket, f'{base_key}/thumbnail.jpg', job_id, s3_endpoint)

        return {
            'videoUrl': video_url,
            'streamingUrl': video_url,
            'downloadUrl': video_url,
            'subtitleUrl': subtitle_url,
            'thumbnailUrl': thumbnail_url
        }

    except ImportError:
        logger.error(f'[{job_id}] boto3 not installed')
    except Exception as e:
        logger.error(f'[{job_id}] Upload failed: {e}')

    return {
        'videoUrl': _local_url(video_path),
        'downloadUrl': _local_url(video_path),
        'thumbnailUrl': 'https://picsum.photos/1280/720'
    }

def _upload_file(s3, file_path, bucket, key, job_id, endpoint):
    if not file_path or not os.path.exists(file_path):
        return None
    content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    s3.upload_file(file_path, bucket, key, ExtraArgs={'ContentType': content_type, 'ACL': 'public-read'})
    if endpoint:
        return f'{endpoint}/{bucket}/{key}'
    return f'https://{bucket}.s3.amazonaws.com/{key}'

def _local_url(path):
    if not path:
        return None
    return f'/output/{os.path.basename(path)}'
