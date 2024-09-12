import cv2
import numpy as np
from PIL import Image
from diffusers import StableDiffusionXLAdapterPipeline, T2IAdapter, EulerAncestralDiscreteScheduler, AutoencoderKL
from controlnet_aux.pidi import PidiNetDetector
import torch
import boto3
import io
import os
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
    prompt = job_input.get("prompt", "4k photo, highly detailed")
    negative_prompt = job_input.get("negative_prompt", "extra digit, fewer digits, cropped, worst quality, low quality, glitch, deformed, mutated, ugly, disfigured")

    # Set AWS credentials and region
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region

    # Initialize S3 client with a custom endpoint if provided
    s3 = boto3.client('s3', endpoint_url=endpoint)

    # Load image from S3
    response = s3.get_object(Bucket=bucket_name, Key=input_key)
    image_data = response['Body'].read()
    image = Image.open(io.BytesIO(image_data))
    image = np.array(image)

    # Convert image to grayscale if necessary
    if image.ndim == 3 and image.shape[2] == 3:
        image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        image_gray = image

    # Use PidiNet for sketch detection
    pidinet = PidiNetDetector.from_pretrained("lllyasviel/Annotators").to("cuda")
    image_pil = Image.fromarray(image_gray)
    image_sketch = pidinet(image_pil, detect_resolution=1024, image_resolution=1024, apply_filter=True)

    # Load T2I-Adapter for sketches
    adapter = T2IAdapter.from_pretrained(
        "TencentARC/t2i-adapter-sketch-sdxl-1.0", torch_dtype=torch.float16, variant="fp16"
    ).to("cuda")

    # Load Stable Diffusion XL model and scheduler
    model_id = 'stabilityai/stable-diffusion-xl-base-1.0'
    euler_a = EulerAncestralDiscreteScheduler.from_pretrained(model_id, subfolder="scheduler")
    vae = AutoencoderKL.from_pretrained("madebyollin/sdxl-vae-fp16-fix", torch_dtype=torch.float16)

    pipe = StableDiffusionXLAdapterPipeline.from_pretrained(
        model_id, vae=vae, adapter=adapter, scheduler=euler_a, torch_dtype=torch.float16, variant="fp16"
    ).to("cuda")
    pipe.enable_xformers_memory_efficient_attention()

    # Generate images
    gen_images = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=image_sketch,
        num_inference_steps=30,
        adapter_conditioning_scale=0.9,
        guidance_scale=7.5,
    ).images[0]

    # Save generated image back to S3
    buffer = io.BytesIO()
    gen_images.save(buffer, format="PNG")
    buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=output_key, Body=buffer, ContentType='image/png')

    # Return the presigned URL for the generated image
    response = s3.generate_presigned_url('get_object',
                                         Params={'Bucket': bucket_name,
                                                 'Key': output_key}, ExpiresIn=3600)
    return response

runpod.serverless.start({"handler": handler})