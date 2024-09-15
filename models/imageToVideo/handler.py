import cv2
import numpy as np
from PIL import Image
from diffusers import StableVideoDiffusionPipeline
from diffusers.utils import load_image, export_to_video
import torch
import boto3
import io
import os
import runpod

def handler(job):
    # Extract inputs from the job
    job_input = job["input"]
    bucket_name = job_input["bucket_name"]
    input_key = job_input["input_key"]
    output_key = job_input["output_key"]
    aws_access_key_id = job_input["aws_access_key_id"]
    aws_secret_access_key = job_input["aws_secret_access_key"]
    aws_region = job_input["aws_region"]
    endpoint = job_input.get("endpoint", None)

    # Set AWS credentials
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region

    # Initialize S3 client
    s3 = boto3.client('s3', endpoint_url=endpoint)

    # Load the image from S3
    response = s3.get_object(Bucket=bucket_name, Key=input_key)
    image_data = response['Body'].read()
    image = Image.open(io.BytesIO(image_data))
    image = Image.open(io.BytesIO(image_data)).convert("RGB")

    # Resize image to the expected dimensions
    image = image.resize((1024, 576))

    # Load StableVideoDiffusionPipeline from Hugging Face
    pipeline = StableVideoDiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid-xt", torch_dtype=torch.float16, variant="fp16"
    )
    pipeline.enable_model_cpu_offload()

    # Set the seed for reproducibility
    generator = torch.manual_seed(42)

    # Generate video frames
    frames = pipeline(image, decode_chunk_size=8, generator=generator).frames[0]

    # Export the generated frames to a video
    video_path = "/tmp/generated_video.mp4"
    export_to_video(frames, video_path, fps=7)

    # Upload the generated video to S3
    with open(video_path, "rb") as video_file:
        s3.put_object(Bucket=bucket_name, Key=output_key, Body=video_file, ContentType='video/mp4')

    # Generate a presigned URL to access the video
    response = s3.generate_presigned_url(
        'get_object', 
        Params={'Bucket': bucket_name, 'Key': output_key}, 
        ExpiresIn=3600
    )

    return response

runpod.serverless.start({"handler": handler})
