#!/usr/bin/env python3
'''
Iyke Movie Studio — Runpod GPU Worker Handler
Main entry point for AI movie production pipeline.

Pipeline stages:
  1. Validate inputs
  2. Generate screenplay via Gemini Pro (if not provided)
  3. Generate video scenes via Veo 3 API
  4. Synthesize voice via ElevenLabs
  5. Stitch scenes with FFmpeg
  6. Upscale to target resolution
  7. Burn subtitles
  8. Generate thumbnail
  9. Upload to storage
  10. Return completed URLs to portal
'''
import os, time, json, logging, traceback
import runpod
from pipeline.screenplay import generate_screenplay
from pipeline.video import generate_scenes
from pipeline.audio import generate_voice
from pipeline.editor import stitch_and_edit
from pipeline.uploader import upload_outputs

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger('iyke-worker')

def validate_input(job_input: dict) -> tuple[bool, str]:
    '''Validate job input fields.'''
    required = ['projectId', 'idea']
    for field in required:
        if not job_input.get(field):
            return False, f'Missing required field: {field}'
    return True, ''

    logger.info(f'[{job_id}] Project: {job_input.get("projectId")} | Title: {job_input.get("title", "Untitled")}')
    '''
    Main Runpod job handler.
    Receives movie production job and returns completed video URLs.
    '''
    job_id = job.get('id', 'unknown')
    job_input = job.get('input', {})
    start_time = time.time()

    logger.info(f'[{job_id}] Starting movie production pipeline')
    logger.info(f'[{job_id}] Project: {job_input.get(" projectId\)} | Title: {job_input.get(\title\, \Untitled\)}')

 try:
 # 1. Validate
 valid, err = validate_input(job_input)
 if not valid:
 return {'error': err, 'status': 'FAILED'}

 project_id = job_input['projectId']
 title = job_input.get('title', 'Untitled Movie')
 idea = job_input['idea']
 genre = job_input.get('genre', 'Drama')
 duration = job_input.get('duration', '1 minute')
 language = job_input.get('language', 'English')
 audience = job_input.get('audience', 'General Audience')
 style = job_input.get('style', 'Cinematic Realism')
 aspect_ratio = job_input.get('aspectRatio', '16:9')
 resolution = job_input.get('resolution', '1080p')
 voice_enabled = job_input.get('voiceEnabled', True)
 subtitles_enabled = job_input.get('subtitlesEnabled', True)

 output_dir = os.path.join(os.getenv('OUTPUT_DIR', '/app/output'), project_id)
 os.makedirs(output_dir, exist_ok=True)

 logger.info(f'[{job_id}] Stage 1/7: Screenplay generation')
 screenplay = job_input.get('script') or []
 characters = job_input.get('characters') or []

 if not screenplay:
 screenplay, characters = generate_screenplay(
 idea=idea, genre=genre, audience=audience,
 duration=duration, style=style, language=language,
 gemini_key=os.getenv('GEMINI_API_KEY', '')
 )
 logger.info(f'[{job_id}] Generated {len(screenplay)} scenes, {len(characters)} characters')
 else:
 logger.info(f'[{job_id}] Using provided screenplay: {len(screenplay)} scenes')

 logger.info(f'[{job_id}] Stage 2/7: Scene video generation (Veo 3)')
 scene_videos = generate_scenes(
 scenes=screenplay,
 style=style,
 aspect_ratio=aspect_ratio,
 output_dir=output_dir,
 veo_key=os.getenv('VEO_API_KEY', '') or os.getenv('GEMINI_API_KEY', ''),
 job_id=job_id
 )

 voice_tracks = []
 if voice_enabled:
 logger.info(f'[{job_id}] Stage 3/7: Voice synthesis (ElevenLabs)')
 voice_tracks = generate_voice(
 scenes=screenplay,
 output_dir=output_dir,
 elevenlabs_key=os.getenv('ELEVENLABS_API_KEY', ''),
 job_id=job_id
 )

 logger.info(f'[{job_id}] Stage 4/7: Stitching + editing')
 edited_output = stitch_and_edit(
 scene_videos=scene_videos,
 voice_tracks=voice_tracks,
 screenplay=screenplay,
 output_dir=output_dir,
 resolution=resolution,
 aspect_ratio=aspect_ratio,
 add_subtitles=subtitles_enabled,
 title=title,
 job_id=job_id
 )

 logger.info(f'[{job_id}] Stage 5/7: Uploading to storage')
 upload_result = upload_outputs(
 edited_output=edited_output,
 project_id=project_id,
 job_id=job_id,
 s3_bucket=os.getenv('S3_BUCKET', ''),
 s3_key=os.getenv('AWS_ACCESS_KEY_ID', ''),
 s3_secret=os.getenv('AWS_SECRET_ACCESS_KEY', ''),
 s3_region=os.getenv('AWS_REGION', 'us-east-1'),
 s3_endpoint=os.getenv('S3_ENDPOINT_URL', '')
 )

 processing_time = round(time.time() - start_time, 2)
 gpu_used = os.getenv('RUNPOD_GPU_ID', 'Unknown GPU')

 # Cost estimation (.001/sec on H100, varies by GPU)
 gpu_cost_per_sec = float(os.getenv('GPU_COST_PER_SEC', '0.001'))
 estimated_cost = round(processing_time * gpu_cost_per_sec, 4)

 logger.info(f'[{job_id}] Pipeline complete in {processing_time}s. Cost: ')

 return {
 'projectId': project_id,
 'jobId': job_id,
 'status': 'COMPLETED',
 'videoUrl': upload_result.get('videoUrl', ''),
 'streamingUrl': upload_result.get('streamingUrl', ''),
 'downloadUrl': upload_result.get('downloadUrl', ''),
 'thumbnailUrl': upload_result.get('thumbnailUrl', ''),
 'subtitleUrl': upload_result.get('subtitleUrl', ''),
 'resolution': resolution,
 'durationSecs': edited_output.get('duration_secs', 0),
 'gpuUsed': gpu_used,
 'processingTimeSecs': processing_time,
 'estimatedCost': estimated_cost,
 'scenesGenerated': len(screenplay),
 'charactersGenerated': len(characters)
 }

 except Exception as e:
 processing_time = round(time.time() - start_time, 2)
 logger.error(f'[{job_id}] Pipeline FAILED after {processing_time}s: {e}')
 logger.error(traceback.format_exc())
 return {
 'status': 'FAILED',
 'error': str(e),
 'errorLogs': traceback.format_exc(),
 'processingTimeSecs': processing_time
 }

# Start Runpod serverless worker
runpod.serverless.start({'handler': handler})
