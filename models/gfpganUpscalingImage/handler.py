import os
import cv2
import numpy as np
import io
import requests
import runpod
import boto3
from gfpgan.utils import GFPGANer
# Helper function to download the GFPGAN model file
def download_model(url, model_path):
    if not os.path.exists(model_path):
        print(f"Downloading {model_path}...")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(model_path, 'wb') as f:
                f.write(response.content)
            print(f"Model {model_path} downloaded successfully!")
        else:
            raise Exception(f"Failed to download {model_path} from {url}")
def handler(job):
    job_input = job["input"]
    bucket_name = job_input["bucket_name"]
    input_key = job_input["input_key"]
    output_key = job_input["output_key"]
    aws_access_key_id = job_input["aws_access_key_id"]
    aws_secret_access_key = job_input["aws_secret_access_key"]
    aws_region = job_input["aws_region"]
    endpoint = job_input.get("endpoint", None)
    # Set AWS credentials and region
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region
    # Initialize S3 client with a custom endpoint if provided
    s3 = boto3.client('s3', endpoint_url=endpoint)
    # Load the image from S3
    response = s3.get_object(Bucket=bucket_name, Key=input_key)
    image_data = response['Body'].read()
    image = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)

    # Paths for the model
    gfpgan_model_url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth'
    gfpgan_model_path = 'GFPGANv1.4.pth'

    # Download the GFPGAN model if it doesn't exist
    download_model(gfpgan_model_url, gfpgan_model_path)
    # Initialize GFPGANer with the model
    face_enhancer = GFPGANer(
        model_path=gfpgan_model_path, upscale=2, arch='clean', channel_multiplier=2)
    # Enhance the image using GFPGAN
    _, _, output = face_enhancer.enhance(image, has_aligned=False, only_center_face=False, paste_back=True)
    # Save the output image to a buffer
    _, buffer = cv2.imencode('input.png', output)
    buffer = io.BytesIO(buffer)
    # Save the output image back to S3
    s3.put_object(Bucket=bucket_name, Key=output_key, Body=buffer.getvalue(), ContentType='image/png')
    # Return presigned URL for the output image
    response = s3.generate_presigned_url('get_object',
                                         Params={'Bucket': bucket_name,
                                                 'Key': output_key}, ExpiresIn=3600)
    return response
runpod.serverless.start({"handler": handler})
