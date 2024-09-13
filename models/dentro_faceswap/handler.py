import os
import boto3
import cv2
import numpy as np
from inswapper import InSwapper  # Asigură-te că ai importat corect
import runpod

def handler(job):
    try:
        # Accesează input-ul din cererea jobului
        job_input = job["input"]
    except KeyError as e:
        return f"Cheia '{e.args[0]}' nu a fost găsită în cererea jobului."

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

    # Setează credentialele și regiunea pentru AWS
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region

    # Inițializează clientul S3
    s3 = boto3.client('s3', endpoint_url=endpoint)

    # Descarcă imaginea cu fața de pe S3
    face_response = s3.get_object(Bucket=bucket_name, Key=face_image_key)
    face_image_data = face_response['Body'].read()
    face_image = cv2.imdecode(np.frombuffer(face_image_data, np.uint8), cv2.IMREAD_COLOR)

    # Descarcă imaginea destinatarului (cu corpul) de pe S3
    body_response = s3.get_object(Bucket=bucket_name, Key=body_image_key)
    body_image_data = body_response['Body'].read()
    body_image = cv2.imdecode(np.frombuffer(body_image_data, np.uint8), cv2.IMREAD_COLOR)

    # Salvează imaginile temporar pe disc
    face_image_path = "/tmp/face_image.png"
    body_image_path = "/tmp/body_image.png"
    cv2.imwrite(face_image_path, face_image)
    cv2.imwrite(body_image_path, body_image)

    # Aplică modelul de schimbare a feței
    try:
        result_image = run_face_swap(face_image_path, body_image_path, face_index, body_index)
        _, buffer = cv2.imencode('.png', result_image)
        result_image_data = buffer.tobytes()
        
        # Salvează imaginea rezultată în S3
        s3.put_object(Bucket=bucket_name, Key=output_key, Body=result_image_data, ContentType='image/png')

        # Returnează un URL presigned pentru a accesa imaginea finală
        response = s3.generate_presigned_url('get_object',
                                             Params={'Bucket': bucket_name,
                                                     'Key': output_key},
                                             ExpiresIn=3600)

        return response

    except Exception as e:
        return f"A apărut o eroare: {e}"

# Pornește handler-ul RunPod pentru a asculta cererile
runpod.serverless.start({"handler": handler})
