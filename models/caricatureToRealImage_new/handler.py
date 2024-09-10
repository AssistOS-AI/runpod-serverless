import cv2
import numpy as np
from PIL import Image
import torch
import boto3
import io
import os
from diffusers import StableDiffusionXLControlNetPipeline, ControlNetModel, AutoencoderKL
import runpod

def handler(job):
    job_input = job["input"]  # Access the input from the request.
    bucket_name = job_input["bucket_name"]
    input_key = job_input["input_key"]
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

    # Load the image from S3
    response = s3.get_object(Bucket=bucket_name, Key=input_key)
    image_data = response['Body'].read()
    image = Image.open(io.BytesIO(image_data))
    image = np.array(image)

    # Convert image to grayscale and then apply Canny edge detection
    image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image
    edges = cv2.Canny(image_gray, 100, 200)
    image = np.stack([edges] * 3, axis=-1)
    image = Image.fromarray(image)

    # Initialize ControlNet and Stable Diffusion XL pipeline
    controlnet = ControlNetModel.from_pretrained("TheMistoAI/MistoLine", torch_dtype=torch.float16)
    vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)
    pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        controlnet=controlnet,
        vae=vae,
        torch_dtype=torch.float16
    )
    pipe.enable_model_cpu_offload()

    # Generate output image using the pipeline
    prompt = "aerial view, a futuristic research complex in a bright foggy jungle, hard lighting"
    negative_prompt = 'low quality, bad quality, sketches'
    controlnet_conditioning_scale = 0.5
    output_image = pipe(
        prompt,
        negative_prompt=negative_prompt,
        image=image,
        controlnet_conditioning_scale=controlnet_conditioning_scale
    ).images[0]

    # Save the output image back to S3
    buffer = io.BytesIO()
    output_image.save(buffer, format="PNG")
    buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=output_key, Body=buffer, ContentType='image/png')

    # Return presigned URL for the output image
    response = s3.generate_presigned_url('get_object',
                                         Params={'Bucket': bucket_name, 'Key': output_key},
                                         ExpiresIn=3600)
    return response

runpod.serverless.start({"handler": handler})  # Required.
