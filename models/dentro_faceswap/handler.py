import os
import io
import requests
import boto3
import numpy as np
from PIL import Image, ImageOps
import onnxruntime as ort
from insightface.app import FaceAnalysis
import runpod

# Funcție pentru a asigura că modelul este descărcat și salvat local
def ensure_model(model_name, model_path):
    if not os.path.exists(model_path):
        url = 'https://huggingface.co/spaces/Dentro/face-swap/resolve/main/inswapper_128.onnx'
        response = requests.get(url)
        if response.status_code == 200:
            with open(model_path, 'wb') as f:
                f.write(response.content)
        else:
            raise RuntimeError(f"Failed downloading model from {url}")

def handler(job):
    job_input = job["input"]
    bucket_name = job_input["bucket_name"]
    face_image_key = job_input["face_image_key"]  # Cheia pentru imaginea cu fata
    body_image_key = job_input["body_image_key"]  # Cheia pentru imaginea corpului
    output_key = job_input["output_key"]
    aws_access_key_id = job_input["aws_access_key_id"]
    aws_secret_access_key = job_input["aws_secret_access_key"]
    aws_region = job_input["aws_region"]
    face_index = int(job_input["face_index"])
    body_index = int(job_input["body_index"])
    endpoint = job_input.get("endpoint", None)

    # Set AWS credentials and region
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region

    # Initialize S3 client with a custom endpoint if provided
    s3 = boto3.client('s3', endpoint_url=endpoint)

    # Load the face image from S3
    response = s3.get_object(Bucket=bucket_name, Key=face_image_key)
    face_image_data = response['Body'].read()
    face_image = Image.open(io.BytesIO(face_image_data)).convert("RGB")

    # Load the body image from S3
    response = s3.get_object(Bucket=bucket_name, Key=body_image_key)
    body_image_data = response['Body'].read()
    body_image = Image.open(io.BytesIO(body_image_data)).convert("RGB")

    # Initialize FaceAnalysis and the swapper model
    app = FaceAnalysis(name='buffalo_l')
    app.prepare(ctx_id=0, det_size=(640, 640))

    # Ensure model is downloaded and available
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

    # Detect faces in the face image
    face_faces = get_faces(face_image)
    selected_face = get_face(face_faces, face_index)

    # Detect faces in the body image
    body_faces = get_faces(body_image)
    selected_body_face = get_face(body_faces, body_index)

    # Perform the face swap
    result_image = swapper.get(body_image, selected_body_face, selected_face, paste_back=True)

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

# Start the serverless function using runpod
runpod.serverless.start({"handler": handler})
