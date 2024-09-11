import os
import boto3
import torch
import cv2
import numpy as np
import subprocess
import runpod
import requests
import librosa
from moviepy.editor import VideoFileClip
import tempfile

# Ensure the Wav2Lip model is correctly imported
try:
    from Wav2Lip.models.wav2lip import Wav2Lip
except ImportError as e:
    print(f"Failed to import Wav2Lip: {e}")

# Define the model URL and path
wav2lip_model_url = 'https://iiitaphyd-my.sharepoint.com/:u:/g/personal/radrabha_m_research_iiit_ac_in/Eb3LEzbfuKlJiR600lQWRxgBIY27JZg80f7V9jtMfbNDaQ?e=TBFBVW'
wav2lip_model_path = 'wav2lip.pth'

# Function to download the model if not present
def download_model(url, save_path):
    if not os.path.exists(save_path):
        print(f"Downloading Wav2Lip model to {save_path}...")
        response = requests.get(url, stream=True)
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print("Download completed.")
    else:
        print(f"Model already exists at {save_path}.")

download_model(wav2lip_model_url, wav2lip_model_path)

# Function to load the model from a .pth file
def load_model_from_pth(path):
    model = Wav2Lip()
    checkpoint = torch.load(path, map_location=torch.device('cpu'))
    model.load_state_dict(checkpoint['state_dict'])
    return model.eval()

# Function to preprocess audio into mel spectrogram
def preprocess_mel(audio, sample_rate):
    mel = librosa.feature.melspectrogram(y=audio, sr=sample_rate, n_fft=400, hop_length=160, n_mels=80)
    mel = np.log(mel + 1e-5)
    mel = np.expand_dims(mel, axis=0)
    return mel

def model_inference(frames, mel_spectrogram, model, device='cpu'):
    synced_frames = []

    # Send model to device (GPU or CPU)
    model = model.to(device)

    # Process each frame (batch inference is possible but keeping it simple here)
    for frame in frames:
        # Resize and normalize the frame
        frame = cv2.resize(frame, (96, 96))  # Wav2Lip uses 96x96 frames
        frame = np.float32(frame) / 255.0    # Normalize frame
        frame = np.transpose(frame, (2, 0, 1))  # Convert to channel-first (C, H, W)
        frame = torch.FloatTensor(frame).unsqueeze(0).to(device)  # Add batch dimension and send to device

        # Convert mel-spectrogram to torch tensor and send to device
        mel = torch.FloatTensor(mel_spectrogram).unsqueeze(0).to(device)

        # Run the frame and mel-spectrogram through the Wav2Lip model
        with torch.no_grad():
            output = model(mel, frame)

        # Post-process the output frame and convert it back to image format
        output = output.squeeze().cpu().numpy().transpose(1, 2, 0)
        output = np.clip(output * 255, 0, 255).astype(np.uint8)
        synced_frames.append(output)

    return synced_frames
# Function to sync the mouth movements in the video frames using the model
def sync_mouth(frames, mel_spectrogram, model):
    synced_frames = []
    for frame in frames:
        synced_frame = model_inference(frame, mel_spectrogram, model)
        synced_frames.append(synced_frame)
    return synced_frames

# Main handler for processing the video and audio synchronization
def handler(job):
    job_input = job["input"]
    bucket_name = job_input["bucket_name"]
    video_input_key = job_input["video_input_key"]
    audio_input_key = job_input["audio_input_key"]
    output_key = job_input["output_key"]
    aws_access_key_id = job_input["aws_access_key_id"]
    aws_secret_access_key = job_input["aws_secret_access_key"]
    aws_region = job_input["aws_region"]
    endpoint = job_input.get("endpoint", None)

    # Setup AWS S3 client
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_DEFAULT_REGION'] = aws_region
    s3 = boto3.client('s3', endpoint_url=endpoint)

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input_video.mp4")
        audio_path = os.path.join(tmpdir, "input_audio.wav")
        output_video_path = os.path.join(tmpdir, "output_video.mp4")
        final_output_path = os.path.join(tmpdir, "final_output.mp4")

        # Download video and audio from S3
        video_response = s3.get_object(Bucket=bucket_name, Key=video_input_key)
        audio_response = s3.get_object(Bucket=bucket_name, Key=audio_input_key)

        with open(video_path, "wb") as f:
            f.write(video_response['Body'].read())
        with open(audio_path, "wb") as f:
            f.write(audio_response['Body'].read())

        # Load the model and process the files
        model = load_model_from_pth(wav2lip_model_path)
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = model.to(device).eval()

        video_clip = VideoFileClip(video_path)
        audio_clip, sample_rate = librosa.load(audio_path, sr=16000)

        frames = [frame for frame in video_clip.iter_frames()]
        mel_spectrogram = preprocess_mel(audio_clip, sample_rate)

        synced_frames = sync_mouth(frames, mel_spectrogram, model)

        # Write the output video
        height, width, _ = synced_frames[0].shape
        out = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*'mp4v'), video_clip.fps, (width, height))
        for frame in synced_frames:
            out.write(frame)
        out.release()

        # Combine video and audio and upload to S3
        subprocess.run(['ffmpeg', '-y', '-i', output_video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', final_output_path])
        with open(final_output_path, "rb") as f:
            s3.put_object(Bucket=bucket_name, Key=output_key, Body=f, ContentType='video/mp4')

        response = s3.generate_presigned_url('get_object',
                                             Params={'Bucket': bucket_name,
                                                     'Key': output_key}, ExpiresIn=3600)
    return response

# Start the Runpod serverless handler
runpod.serverless.start({"handler": handler})
