import os
import requests
import boto3
import cv2
import numpy as np
from gradio_client import Client
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

    # Salvează imaginile temporar pe disc pentru a putea fi trimise la API-ul de pe Hugging Face
    face_image_path = "/tmp/face_image.png"
    body_image_path = "/tmp/body_image.png"
    cv2.imwrite(face_image_path, face_image)
    cv2.imwrite(body_image_path, body_image)

    # Conectează-te la API-ul de pe Hugging Face
    client = Client("https://dentro-face-swap.hf.space/--replicas/ygqln/")

    # Debug: afiseaza datele înainte de a trimite cererea la API
    print(f"face_image_path: {face_image_path}")
    print(f"body_image_path: {body_image_path}")
    print(f"face_index: {face_index}")
    print(f"body_index: {body_index}")

    # Trimite cererea către API-ul de face swap folosind indicii din input
    try:
        result = client.predict(
            face_image_path,  # Imaginea sursă cu fața
            face_index,       # Indicele feței în imaginea sursă
            body_image_path,  # Imaginea destinație cu corpul
            body_index        # Indicele feței în imaginea destinație
        )

        # Verifică dacă rezultatul este un URL sau date de imagine
        if isinstance(result, str) and result.startswith("http"):
            result_image_data = requests.get(result).content
        elif isinstance(result, bytes):
            result_image_data = result
        else:
            raise ValueError("Rezultatul nu este un URL de imagine valid sau date de imagine.")
        
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
