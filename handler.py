import cv2
import numpy as np
from PIL import Image
from diffusers import StableDiffusionControlNetPipeline, ControlNetModel, UniPCMultistepScheduler
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
    aws_session_token = job_input["aws_session_token"]
    region_name = job_input["region_name"]
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_SESSION_TOKEN'] = aws_session_token
    os.environ['AWS_DEFAULT_REGION'] = region_name
    s3 = boto3.client('s3')
    # Load the image from S3
    response = s3.get_object(Bucket=bucket_name, Key=input_key)
    image_data = response['Body'].read()
    image = Image.open(io.BytesIO(image_data))
    image = np.array(image)

    # Convert image to grayscale if necessary
    if image.ndim == 3 and image.shape[2] == 3:
        image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        image_gray = image

    # Apply Canny edge detection
    low_threshold = 100
    high_threshold = 200
    edges = cv2.Canny(image_gray, low_threshold, high_threshold)
    edges = np.stack([edges] * 3, axis=-1)

    # Convert edges to PIL image
    image_pil = Image.fromarray(edges)

    # Load ControlNet and Stable Diffusion pipeline
    controlnet = ControlNetModel.from_pretrained("lllyasviel/sd-controlnet-canny", torch_dtype=torch.float16)
    pipe = StableDiffusionControlNetPipeline.from_pretrained("runwayml/stable-diffusion-v1-5", controlnet=controlnet,
                                                             safety_checker=None, torch_dtype=torch.float16)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.enable_model_cpu_offload()

    # Generate output image
    output_image = pipe("bird", image_pil, num_inference_steps=20).images[0]

    # Save the output image back to S3
    buffer = io.BytesIO()
    output_image.save(buffer, format="PNG")
    buffer.seek(0)
    s3.put_object(Bucket=bucket_name, Key=output_key, Body=buffer, ContentType='image/png')

    # return output bucket and key
    s3_client = boto3.client('s3')
    response = s3_client.generate_presigned_url('get_object',
                                                Params={'Bucket': bucket_name,
                                                        'Key': output_key}, ExpiresIn=3600)
    return response


runpod.serverless.start({"handler": handler})  # Required.
