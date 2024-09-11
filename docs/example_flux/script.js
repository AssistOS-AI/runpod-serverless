let uploadedFileUrl = '';
let randomKey = '';

// Function to generate a random string
function generateRandomString(length) {
    const randomBytes = crypto.getRandomValues(new Uint8Array(32));
    const base64String = btoa(String.fromCharCode.apply(null, randomBytes));
    const base64UrlString = base64String.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return base64UrlString;
}

function submitForm(event) {
    const accessKeyId = document.getElementById('accessKeyId').value;
    const secretAccessKey = document.getElementById('secretAccessKey').value;
    const bucketName = 'assistos-demo-bucket';
    const endpoint = 'https://assistos-demo-bucket.fra1.digitaloceanspaces.com';
    const hf_auth_token = document.getElementById('authApiKey').value;
    const prompt = document.getElementById('prompt').value;
    event.preventDefault();

    const apiKey = document.getElementById('apiKey').value;
    const form = document.getElementById('inputForm');
    const loadingSpinner = document.getElementById('loadingSpinner');

    form.style.display = 'none';
    loadingSpinner.style.display = '';

    const requestBody = {
        "input": {
            "bucket_name": bucketName,
            "input_key": randomKey,
            "output_key": generateRandomString(16),
            "aws_access_key_id": accessKeyId,
            "aws_secret_access_key": secretAccessKey,
            "endpoint": endpoint,
            "aws_region": "fra1",
            "hf_auth_token": hf_auth_token,
            "hf_prompt": prompt
        }
    };

    fetch('https://api.runpod.ai/v2/ynfas564lyueuq/run', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(requestBody)
    })
        .then(response => response.json())
        .then(data => {
            console.log('Request ID:', data.id);
            checkStatus(data.id, apiKey);
        })
        .catch((error) => {
            loadingSpinner.style.display = 'none';
            form.style.display = '';
            console.error('Error:', error);
            alert('Request failed: ' + error);
        });
}

function checkStatus(requestId, apiKey) {
    const statusUrl = `https://api.runpod.ai/v2/ynfas564lyueuq/status/${requestId}`;
    const loadingSpinner = document.getElementById('loadingSpinner');
    const form = document.getElementById('inputForm');

    // Ensure the spinner is visible while checking status
    loadingSpinner.style.display = '';
    form.style.display = 'none';

    const intervalId = setInterval(() => {
        fetch(statusUrl, {
            headers: {
                'Authorization': `Bearer ${apiKey}`
            }
        })
            .then(response => response.json())
            .then(data => {
                console.log('Status:', data.status);
                if (data.status === 'COMPLETED') {
                    clearInterval(intervalId);
                    loadingSpinner.style.display = 'none'; // Hide spinner when completed
                    displayResult(data.output);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                clearInterval(intervalId);
                loadingSpinner.style.display = 'none'; // Hide spinner on error
                form.style.display = ''; // Show form again if there's an error
            });
    }, 5000);
}

function displayResult(outputUrl) {
    const resultDiv = document.getElementById('result');
    document.getElementById('inputForm').style.display = 'none';
    resultDiv.innerHTML = `<p>Processing completed. <a href="${outputUrl}" target="_blank">Click here</a> to view the output image.</p>`;
    document.getElementById('inputForm').style.display = ''; // Show the form again
}
