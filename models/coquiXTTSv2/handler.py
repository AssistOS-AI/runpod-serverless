import os
import io
import boto3
import torch
import runpod
import soundfile as sf
from TTS.api import TTS
from pydub import AudioSegment

# Supported languages by XTTS-v2
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "pl": "Polish",
    "tr": "Turkish",
    "ru": "Russian",
    "nl": "Dutch",
    "cs": "Czech",
    "ar": "Arabic",
    "zh-cn": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "hu": "Hungarian",
    "hi": "Hindi"
}


def download_and_convert_audio(s3_client, bucket_name, reference_key):
    """
    Download reference audio and convert it to proper format if needed
    """
    try:
        # Download reference audio from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=reference_key)
        audio_data = response['Body'].read()

        # Save temporarily
        temp_path = "/tmp/reference_original"
        with open(temp_path, 'wb') as f:
            f.write(audio_data)

        # Convert to WAV if needed and ensure proper format
        audio = AudioSegment.from_file(temp_path)

        # Convert to mono if stereo
        if audio.channels > 1:
            audio = audio.set_channels(1)

        # Set sample rate to 22050Hz
        if audio.frame_rate != 22050:
            audio = audio.set_frame_rate(22050)

        # Export as WAV
        output_path = "/tmp/reference.wav"
        audio.export(output_path, format="wav")

        # Clean up original temp file
        os.remove(temp_path)

        return output_path

    except Exception as e:
        print(f"Error processing reference audio: {str(e)}")
        raise


def handler(job):
    try:
        job_input = job["input"]
        bucket_name = job_input["bucket_name"]
        output_key = job_input["output_key"]
        aws_access_key_id = job_input["aws_access_key_id"]
        aws_secret_access_key = job_input["aws_secret_access_key"]
        aws_region = job_input["aws_region"]
        endpoint = job_input.get("endpoint", None)
        text = job_input.get("text", "Hello, this is a test of text to speech.")
        language = job_input.get("language", "en")

        # Voice cloning parameters
        reference_key = job_input.get("reference_key", None)
        use_voice_cloning = reference_key is not None

        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Language {language} not supported. Supported languages: {', '.join(SUPPORTED_LANGUAGES.keys())}")

        # Set AWS credentials and region
        os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
        os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
        os.environ['AWS_DEFAULT_REGION'] = aws_region

        # Initialize S3 client
        s3 = boto3.client('s3', endpoint_url=endpoint)

        # Initialize TTS model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

        # Output path for generated audio
        output_path = "/tmp/output.wav"

        if use_voice_cloning:
            # Process reference audio
            reference_path = download_and_convert_audio(s3, bucket_name, reference_key)

            # Generate speech with voice cloning
            tts.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=reference_path,
                language=language,
                speed=1.0
            )

            # Clean up reference file
            os.remove(reference_path)
        else:
            # Generate speech without voice cloning
            tts.tts_to_file(
                text=text,
                file_path=output_path,
                language=language,
                speed=1.0
            )

        # Upload to S3
        with open(output_path, 'rb') as audio_file:
            s3.upload_fileobj(
                audio_file,
                bucket_name,
                output_key,
                ExtraArgs={
                    'ContentType': 'audio/wav'
                }
            )

        # Generate presigned URL
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': output_key
            },
            ExpiresIn=3600
        )

        # Clean up generated audio file
        os.remove(output_path)

        # Return response with additional metadata
        return {
            "audio_url": presigned_url,
            "language": language,
            "language_name": SUPPORTED_LANGUAGES[language],
            "used_voice_cloning": use_voice_cloning
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}


runpod.serverless.start({"handler": handler})