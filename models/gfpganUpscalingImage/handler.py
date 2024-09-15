import os
import cv2
import numpy as np
import io
import requests
import runpod
import boto3
import torch  # Import PyTorch pentru verificarea GPU-ului
from gfpgan.utils import GFPGANer
from realesrgan.utils import RealESRGANer
from basicsr.archs.srvgg_arch import SRVGGNetCompact

# Helper function to download the model files
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

    # Paths for the models
    gfpgan_model_url = 'https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth'
    gfpgan_model_path = 'GFPGANv1.4.pth'
    realesrgan_model_url = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth'
    realesrgan_model_path = 'realesr-general-x4v3.pth'

    # Download the models if they don't exist
    download_model(gfpgan_model_url, gfpgan_model_path)
    download_model(realesrgan_model_url, realesrgan_model_path)

    # Initialize RealESRGAN upscaler
    model = SRVGGNetCompact(num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=32, upscale=4, act_type='prelu')
    
    # Determine if GPU is available and supports FP16
    half = True if torch.cuda.is_available() and torch.cuda.get_device_capability(0)[0] >= 7 else False
    
    # Optimize RealESRGAN for GPU if available, otherwise set half to False for CPU
    upsampler = RealESRGANer(scale=4, model_path=model_path, model=model, tile=0, tile_pad=10, pre_pad=0, half=half)

    # Initialize GFPGANer with RealESRGAN as background upsampler
    face_enhancer = GFPGANer(
        model_path=gfpgan_model_path, 
        upscale=2,  # Set upscale to 2, matching demo settings
        arch='clean', 
        channel_multiplier=2, 
        bg_upsampler=upsampler  # Use RealESRGAN as background upsampler
    )

    # Enhance the image using GFPGAN v1.4 with RealESRGAN upscaling
    # Added 'weight' parameter to allow fine-tuning face restoration
    _, _, output = face_enhancer.enhance(
        image, 
        has_aligned=False,  # No aligned faces
        only_center_face=False,  # Restore all faces in the image
        paste_back=True,  # Paste restored faces back into the original image
        weight=0.5  # Default weight for blending restored face and original
    )

    # Save the output image to a buffer
    _, buffer = cv2.imencode('.png', output)
    buffer = io.BytesIO(buffer)

    # Save the output image back to S3
    s3.put_object(Bucket=bucket_name, Key=output_key, Body=buffer.getvalue(), ContentType='image/png')

    # Return presigned URL for the output image
    response = s3.generate_presigned_url('get_object',
                                         Params={'Bucket': bucket_name, 'Key': output_key},
                                         ExpiresIn=3600)
    return response

runpod.serverless.start({"handler": handler})
