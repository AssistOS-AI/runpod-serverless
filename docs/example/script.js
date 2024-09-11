let uploadedFileUrl = '';
let randomKey = '';

// Function to generate a random string
function generateRandomString(length) {
    const randomBytes = crypto.getRandomValues(new Uint8Array(32));
    const base64String = btoa(String.fromCharCode.apply(null, randomBytes));
    const base64UrlString = base64String.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return base64UrlString;
}

function uploadFile() {
    const accessKeyId = document.getElementById('accessKeyId').value;
    const secretAccessKey = document.getElementById('secretAccessKey').value;
    const bucketName = 'assistos-demo-bucket';
    const endpoint = 'https://assistos-demo-bucket.fra1.digitaloceanspaces.com';
    const fileInput = document.getElementById('fileInput');
    const loadingSpinner = document.getElementById('loadingSpinner');

    if (!fileInput.files.length) {
        alert('Please select a file to upload.');
        return;
    }

    const file = fileInput.files[0];
    const fileExtension = file.name.split('.').pop(); // Extract the file extension
    randomKey = generateRandomString(16) + "." + fileExtension; // Append the extension to the random key

    const s3 = new AWS.S3({
        endpoint: new AWS.Endpoint(endpoint),
        credentials: new AWS.Credentials({
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey
        }),
        s3ForcePathStyle: true,
    });

    const params = {
        Bucket: bucketName,
        Key: randomKey,
        Body: file,
        ACL: 'public-read'
    };

    loadingSpinner.style.display = '';

    s3.upload(params, function(err, data) {
        loadingSpinner.style.display = 'none';

        if (err) {
            console.error('Upload Error:', err);
            alert('File upload failed: ' + err.message);
        } else {
            console.log('Upload Success:', data);
            uploadedFileUrl = data.Location;
            alert('File uploaded successfully!');
        }
    });
}

function submitForm(event) {
    const accessKeyId = document.getElementById('accessKeyId').value;
    const secretAccessKey = document.getElementById('secretAccessKey').value;
    const bucketName = 'assistos-demo-bucket';
    const endpoint = 'https://assistos-demo-bucket.fra1.digitaloceanspaces.com';
    event.preventDefault();

    const apiKey = document.getElementById('apiKey').value;
    const form = document.getElementById('inputForm');
    const loadingSpinner = document.getElementById('loadingSpinner');

    if (!uploadedFileUrl) {
        alert('Please upload a file first.');
        return;
    }

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
            "aws_region": "fra1"
        }
    };

    fetch('https://api.runpod.ai/v2/xufpmrxai3j5ee/run', {
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
    const statusUrl = `https://api.runpod.ai/v2/xufpmrxai3j5ee/status/${requestId}`;
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
