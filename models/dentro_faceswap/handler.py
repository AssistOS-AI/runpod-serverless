import os
import io
import boto3
import numpy as np
from PIL import Image
import onnxruntime as ort
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
import requests

# Function to download the model if it doesn't exist
def download_model(url, path):
    response = requests.get(url)
    with open(path, 'wb') as f:
        f.write(response.content)
    print(f"Model downloaded to {path}.")

# Function to ensure the model is downloaded
def ensure_model(model_name, model_path):
    if not os.path.exists(model_path):
        print(f"Model {model_name} not found. Downloading...")
        url = 'https://huggingface.co/spaces/Dentro/face-swap/resolve/main/inswapper_128.onnx'
        download_model(url, model_path)
    else:
        print(f"Model {model_name} already exists at {model_path}.")

def handler(job):
    job_input = job["input"]
    bucket_name = job_input["bucket_name"]
    face_image_key = job_input["face_image_key"]
    body_image_key = job_input["body_image_key"]
    face_index = int(job_input["face_index"])
    body_index = int(job_input["body_index"])
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

    # Load the face and body images from S3
    face_response = s3.get_object(Bucket=bucket_name, Key=face_image_key)
    body_response = s3.get_object(Bucket=bucket_name, Key=body_image_key)

    face_image_data = face_response['Body'].read()
    body_image_data = body_response['Body'].read()

    face_image = Image.open(io.BytesIO(face_image_data)).convert("RGB")
    body_image = Image.open(io.BytesIO(body_image_data)).convert("RGB")

    # Initialize FaceAnalysis and the swapper model
    app = FaceAnalysis(name='buffalo_l')
    app.prepare(ctx_id=0, det_size=(640, 640))

    # Define model path and ensure model is downloaded
    model_path = 'inswapper_128.onnx'
    ensure_model('inswapper_128.onnx', model_path)
    swapper = ort.InferenceSession(model_path)

    # Prepare the images
    def get_faces(image):
        faces = app.get(image)
        return sorted(faces, key=lambda x: x.bbox[0])

    def get_face(faces, face_id):
        if len(faces) < face_id or face_id < 1:
            raise ValueError(f"The image includes only {len(faces)} faces, however, you asked for face {face_id}")
        return faces[face_id - 1]

    # Detect faces in the face and body images
    face_faces = get_faces(face_image)
    body_faces = get_faces(body_image)

    if not face_faces or not body_faces:
        raise ValueError("No faces detected in one or both images.")

    source_face = get_face(face_faces, face_index)
    destination_face = get_face(body_faces, body_index)

    # Perform the face swap
    result_image = swapper.get(face_image, destination_face, source_face, paste_back=True)

    # Save the result image to a BytesIO buffer
    buffer = io.BytesIO()
    result_image.save(buffer, format="PNG")
    buffer.seek(0)

    # Upload the result image to S3
    s3.put_object(Bucket=bucket_name, Key=output_key, Body=buffer, ContentType='image/png')

    # Return a presigned URL for the output image
    response = s3.generate_presigned_url('get_object',
                                         Params={'Bucket': bucket_name,
                                                 'Key': output_key}, ExpiresIn=3600)
    return response
