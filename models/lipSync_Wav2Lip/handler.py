import cv2
import numpy as np
import torch
import boto3
import io
import os
import requests  # To download the model from GitHub
import runpod
from moviepy.editor import VideoFileClip
from Wav2Lip.models import Wav2Lip
from Wav2Lip.utils import load_model, preprocess_mel, sync_mouth
import librosa
import subprocess

# Wav2Lip GitHub URL for model weights
MODEL_URL = "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip.pth"

def download_model(url, save_path):
    # Download model weights from the provided URL
    response = requests.get(url)
    with open(save_path, 'wb') as f:
        f.write(response.content)

def handler(job):
    job_input = job["input"]  # Access the input from the request.
    bucket_name = job_input["bucket_name"]
    video_input_key = job_input["video_input_key"]
    audio_input_key = job_input["audio_input_key"]
    output_key = job_input["output_key"]
    aws_access_key_id = job_input["aws_access_key_id"]
    aws_secret_access_key = job_input["aws_secret_access_key"]
    aws_region = job_input["aws_region"]
    endpoint = job_input.get("endpoint", None)  # Optional custom endpoint URL

    # Set AWS credentials and region
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region

    # Initialize S3 client with a custom endpoint if provided
    s3 = boto3.client('s3', endpoint_url=endpoint)

    # Load the video and audio from S3
    video_response = s3.get_object(Bucket=bucket_name, Key=video_input_key)
    audio_response = s3.get_object(Bucket=bucket_name, Key=audio_input_key)

    video_data = video_response['Body'].read()
    audio_data = audio_response['Body'].read()

    # Save video and audio to temporary files
    with open("/tmp/input_video.mp4", "wb") as f:
        f.write(video_data)

    with open("/tmp/input_audio.wav", "wb") as f:
        f.write(audio_data)

    # Download and load Wav2Lip model weights
    model_weights_path = "/tmp/wav2lip.pth"
    download_model(MODEL_URL, model_weights_path)
    
    model = load_model(model_weights_path)  # Load the downloaded model
    model = model.to('cuda').eval()

    # Process video and audio
    video_clip = VideoFileClip("/tmp/input_video.mp4")
    audio_clip, sample_rate = librosa.load("/tmp/input_audio.wav", sr=16000)

    frames = [frame for frame in video_clip.iter_frames()]
    mel_spectrogram = preprocess_mel(audio_clip, sample_rate)

    # Sync video with audio
    synced_frames = sync_mouth(frames, mel_spectrogram, model)

    # Write the synced video
    height, width, _ = synced_frames[0].shape
    out = cv2.VideoWriter('/tmp/output_video.mp4', cv2.VideoWriter_fourcc(*'mp4v'), video_clip.fps, (width, height))

    for frame in synced_frames:
        out.write(frame)

    out.release()

    # Merge audio and video using ffmpeg
    subprocess.run(['ffmpeg', '-y', '-i', '/tmp/output_video.mp4', '-i', '/tmp/input_audio.wav', '-c:v', 'copy', '-c:a', 'aac', '/tmp/final_output.mp4'])

    # Upload the final video to S3
    with open("/tmp/final_output.mp4", "rb") as f:
        s3.put_object(Bucket=bucket_name, Key=output_key, Body=f, ContentType='video/mp4')

    # Generate presigned URL for the output video
    response = s3.generate_presigned_url('get_object',
                                         Params={'Bucket': bucket_name,
                                                 'Key': output_key}, ExpiresIn=3600)
    return response

runpod.serverless.start({"handler": handler})  # Required.
