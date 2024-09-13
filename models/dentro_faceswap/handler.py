import os
import io
import boto3
import numpy as np
from PIL import Image
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
import runpod

def handler(job):
    job_input = job["input"]
    bucket_name = job_input["bucket_name"]
    source_key = job_input["source_key"]
    destination_key = job_input["destination_key"]
    output_key = job_input["output_key"]
    aws_access_key_id = job_input["aws_access_key_id"]
    aws_secret_access_key = job_input["aws_secret_access_key"]
    aws_region = job_input["aws_region"]
    source_face_index = int(job_input["source_face_index"])
    destination_face_index = int(job_input["destination_face_index"])
    endpoint = job_input.get("endpoint", None)

    # Set AWS credentials and region
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region

    # Initialize S3 client with a custom endpoint if provided
    s3 = boto3.client('s3', endpoint_url=endpoint)

    # Load the source image from S3
    response = s3.get_object(Bucket=bucket_name, Key=source_key)
    source_image_data = response['Body'].read()
    source_image = Image.open(io.BytesIO(source_image_data)).convert("RGB")

    # Load the destination image from S3
    response = s3.get_object(Bucket=bucket_name, Key=destination_key)
    destination_image_data = response['Body'].read()
    destination_image = Image.open(io.BytesIO(destination_image_data)).convert("RGB")

    # Convert PIL image to numpy array
    def pil_to_np(image):
        return np.array(image)

    # Initialize FaceAnalysis and the swapper model
    app = FaceAnalysis(name='buffalo_l')
    app.prepare(ctx_id=0, det_size=(640, 640))
    model_path = '/app/inswapper_128.onnx'  # Adjust path as needed
    swapper = get_model(model_path, download=False)  # Use local model if available

    # Prepare the images
    def get_faces(image_np):
        faces = app.get(image_np)
        return sorted(faces, key=lambda x: x.bbox[0])

    def get_face(faces, face_id):
        if len(faces) < face_id or face_id < 1:
            raise ValueError(f"The image includes only {len(faces)} faces, however, you asked for face {face_id}")
        return faces[face_id - 1]

    # Convert images to numpy arrays
    source_image_np = pil_to_np(source_image)
    destination_image_np = pil_to_np(destination_image)

    # Detect faces in the source image
    source_faces = get_faces(source_image_np)
    source_face = get_face(source_faces, source_face_index)

    # Detect faces in the destination image
    destination_faces = get_faces(destination_image_np)
    destination_face = get_face(destination_faces, destination_face_index)

    # Perform the face swap
    result_image_np = swapper.get(destination_image_np, destination_face, source_face, paste_back=True)

    # Convert numpy array back to PIL image
    result_image = Image.fromarray(result_image_np)

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

runpod.serverless.start({"handler": handler})
