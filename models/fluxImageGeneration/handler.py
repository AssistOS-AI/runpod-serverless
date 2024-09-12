import boto3
import io
import os
import requests
from PIL import Image
import runpod

# Handler function to accept input and return the presigned URL of the output image
def handler(job):
    job_input = job["input"]  # Access the input from the request
    bucket_name = job_input["bucket_name"]
    output_key = job_input["output_key"]
    aws_access_key_id = job_input["aws_access_key_id"]
    aws_secret_access_key = job_input["aws_secret_access_key"]
    aws_region = job_input["aws_region"]
    hf_auth_token = job_input["hf_auth_token"]  # API token for hugging face model
    hf_prompt = job_input["hf_prompt"]  # Text prompt for hugging face model
    endpoint = job_input.get("endpoint", None)  # Optional custom endpoint URL

    # Set AWS credentials and region
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region

    # Initialize S3 client with a custom endpoint if provided
    s3 = boto3.client('s3', endpoint_url=endpoint)

    # HuggingFace API details
    API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {hf_auth_token}"}

     # Send the query to Hugging Face API directly
    response = requests.post(API_URL, headers=headers, json={"inputs": hf_prompt})

    if response.status_code == 200:
        # Read the response content
        image_bytes = response.content

        # Load the image using PIL from the response bytes
        image = Image.open(io.BytesIO(image_bytes))

        # Save the image into a BytesIO buffer
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        # Upload the image to S3
        s3.put_object(Bucket=bucket_name, Key=output_key, Body=buffer, ContentType='image/png')

        # Generate a URL for the uploaded image in S3
        response_url = s3.generate_presigned_url('get_object',
                                              Params={'Bucket': bucket_name, 'Key': output_key},
                                              ExpiresIn=3600)
        return response_url
    else:
        raise Exception(f"Hugging Face API request failed with status code {response.status_code}")

runpod.serverless.start({"handler": handler})  # Required to start the serverless function