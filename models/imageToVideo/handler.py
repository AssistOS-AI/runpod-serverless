import cv2
import numpy as np
from PIL import Image
from diffusers import DiffusionPipeline
import torch
import boto3
import io
import os
import runpod

def handler(job):
    job_input = job["input"]
    bucket_name = job_input["bucket_name"]
    input_key = job_input["input_key"]
    output_key = job_input["output_key"]
    aws_access_key_id = job_input["aws_access_key_id"]
    aws_secret_access_key = job_input["aws_secret_access_key"]
    aws_region = job_input["aws_region"]
    endpoint = job_input.get("endpoint", None)

    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region

    s3 = boto3.client('s3', endpoint_url=endpoint)

    response = s3.get_object(Bucket=bucket_name, Key=input_key)
    image_data = response['Body'].read()
    image = Image.open(io.BytesIO(image_data))
    image = np.array(image)

    if image.ndim == 2 or image.shape[2] == 1:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    # Load Diffusion Pipeline for Img2Vid
    pipe = DiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid", torch_dtype=torch.float16
    ).to("cuda")
    pipe.enable_xformers_memory_efficient_attention()

    # Generate video frames
    video_frames = pipe(
        image=image,
        num_inference_steps=30,
        num_frames=16,
        guidance_scale=7.5,
    ).frames

    height, width, _ = video_frames[0].shape
    video_path = "/tmp/generated_video.mp4"
    out = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), 10, (width, height))

    for frame in video_frames:
        frame_rgb = np.array(frame)
        out.write(cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))

    out.release()

    with open(video_path, "rb") as video_file:
        s3.put_object(Bucket=bucket_name, Key=output_key, Body=video_file, ContentType='video/mp4')

    response = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': output_key}, ExpiresIn=3600)
    return response

runpod.serverless.start({"handler": handler})
