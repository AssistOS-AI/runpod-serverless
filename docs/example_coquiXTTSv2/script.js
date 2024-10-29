let randomKey = '';

function generateRandomString(length) {
    const randomBytes = crypto.getRandomValues(new Uint8Array(32));
    const base64String = btoa(String.fromCharCode.apply(null, randomBytes));
    const base64UrlString = base64String.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return base64UrlString;
}

function saveCredentials() {
    const fields = ['accessKeyId', 'secretAccessKey', 'apiKey'];
    fields.forEach(field => {
        const value = document.getElementById(field).value;
        localStorage.setItem(field, value);
    });
}

function restoreCredentials() {
    const fields = ['accessKeyId', 'secretAccessKey', 'apiKey'];
    fields.forEach(field => {
        const value = localStorage.getItem(field);
        if (value) {
            document.getElementById(field).value = value;
        }
    });
}

// Handle voice cloning checkbox
document.getElementById('enableVoiceClone').addEventListener('change', function() {
    const voiceCloneOptions = document.getElementById('voiceCloneOptions');
    voiceCloneOptions.classList.toggle('hidden', !this.checked);
    const referenceAudio = document.getElementById('referenceAudio');
    if (!this.checked) {
        referenceAudio.value = '';
    }
});

async function uploadReferenceAudio(file, s3Config) {
    const fileKey = `reference_${generateRandomString(16)}${getFileExtension(file.name)}`;

    const s3 = new AWS.S3({
        accessKeyId: s3Config.accessKeyId,
        secretAccessKey: s3Config.secretAccessKey,
        endpoint: s3Config.endpoint,
        s3ForcePathStyle: true,
        signatureVersion: 'v4'
    });

    await s3.upload({
        Bucket: s3Config.bucketName,
        Key: fileKey,
        Body: file,
        ContentType: file.type
    }).promise();

    return fileKey;
}

function getFileExtension(filename) {
    return filename.slice((filename.lastIndexOf(".") - 1 >>> 0) + 2);
}

function handleError(message) {
    const form = document.getElementById('inputForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const submitBtn = document.getElementById('submitBtn');
    const errorDiv = document.getElementById('error');

    form.classList.remove('hidden');
    loadingSpinner.classList.add('hidden');
    submitBtn.disabled = false;

    errorDiv.textContent = `Error: ${message}`;
    errorDiv.classList.remove('hidden');
}

async function submitForm(event) {
    event.preventDefault();

    // Get form elements
    const form = document.getElementById('inputForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');
    const submitBtn = document.getElementById('submitBtn');

    // Hide previous results and errors
    resultDiv.classList.add('hidden');
    errorDiv.classList.add('hidden');

    try {
        // Get form values
        const accessKeyId = document.getElementById('accessKeyId').value;
        const secretAccessKey = document.getElementById('secretAccessKey').value;
        const apiKey = document.getElementById('apiKey').value;
        const text = document.getElementById('text').value;
        const language = document.getElementById('language').value;
        const enableVoiceClone = document.getElementById('enableVoiceClone').checked;

        // Save credentials
        saveCredentials();

        // Show loading state
        form.classList.add('hidden');
        loadingSpinner.classList.remove('hidden');
        submitBtn.disabled = true;

        // S3 Configuration
        const s3Config = {
            accessKeyId,
            secretAccessKey,
            bucketName: 'assistos-demo-bucket',
            endpoint: 'https://assistos-demo-bucket.fra1.digitaloceanspaces.com'
        };

        // Prepare request body
        const requestBody = {
            input: {
                bucket_name: s3Config.bucketName,
                output_key: `output_${generateRandomString(16)}.wav`,
                aws_access_key_id: accessKeyId,
                aws_secret_access_key: secretAccessKey,
                endpoint: s3Config.endpoint,
                aws_region: "fra1",
                text: text,
                language: language
            }
        };

        // Handle voice cloning if enabled
        if (enableVoiceClone) {
            const referenceAudio = document.getElementById('referenceAudio').files[0];
            if (referenceAudio) {
                const referenceKey = await uploadReferenceAudio(referenceAudio, s3Config);
                requestBody.input.reference_key = referenceKey;
            }
        }

        // Make API request
        const response = await fetch('https://api.runpod.ai/v2/ynfas564lyueuq/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        checkStatus(data.id, apiKey);

    } catch (error) {
        console.error('Error:', error);
        handleError(error.message);
    }
}

function checkStatus(requestId, apiKey) {
    const statusUrl = `https://api.runpod.ai/v2/ynfas564lyueuq/status/${requestId}`;
    const intervalId = setInterval(async () => {
        try {
            const response = await fetch(statusUrl, {
                headers: {
                    'Authorization': `Bearer ${apiKey}`
                }
            });
            const data = await response.json();

            if (data.status === 'COMPLETED') {
                clearInterval(intervalId);
                displayResult(data.output);
            } else if (data.status === 'FAILED') {
                clearInterval(intervalId);
                handleError('Processing failed. Please try again.');
            }
        } catch (error) {
            clearInterval(intervalId);
            handleError(`Error checking status: ${error.message}`);
        }
    }, 5000);
}

function displayResult(output) {
    const form = document.getElementById('inputForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const resultDiv = document.getElementById('result');
    const submitBtn = document.getElementById('submitBtn');
    const audioElement = document.getElementById('audioElement');
    const downloadLink = document.getElementById('downloadLink');

    // Reset UI states
    loadingSpinner.classList.add('hidden');
    form.classList.remove('hidden');
    submitBtn.disabled = false;
    resultDiv.classList.remove('hidden');

    // Handle both string and object response formats
    const audioUrl = typeof output === 'string' ? output : output.audio_url;

    // Update audio player and download link
    audioElement.src = audioUrl;
    downloadLink.href = audioUrl;

    // Scroll to the result
    resultDiv.scrollIntoView({ behavior: 'smooth' });
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    restoreCredentials();
    document.getElementById('inputForm').addEventListener('submit', submitForm);
});