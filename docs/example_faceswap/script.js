let sourceFileKey = '';
let destinationFileKey = '';
let sourceFileUrl = '';
let destinationFileUrl = '';

// Function to generate a random string
function generateRandomString(length) {
    const randomBytes = crypto.getRandomValues(new Uint8Array(32));
    const base64String = btoa(String.fromCharCode.apply(null, randomBytes));
    const base64UrlString = base64String.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return base64UrlString;
}

function saveCredentials() {
    const accessKeyId = document.getElementById('accessKeyId').value;
    const secretAccessKey = document.getElementById('secretAccessKey').value;
    const apiKey = document.getElementById('apiKey').value;

    localStorage.setItem('accessKeyId', accessKeyId);
    localStorage.setItem('secretAccessKey', secretAccessKey);
    localStorage.setItem('apiKey', apiKey);
}

function restoreCredentials() {
    const accessKeyId = localStorage.getItem('accessKeyId');
    const secretAccessKey = localStorage.getItem('secretAccessKey');
    const apiKey = localStorage.getItem('apiKey');

    if (accessKeyId) {
        document.getElementById('accessKeyId').value = accessKeyId;
    }
    if (secretAccessKey) {
        document.getElementById('secretAccessKey').value = secretAccessKey;
    }
    if (apiKey) {
        document.getElementById('apiKey').value = apiKey;
    }
}

function uploadFile() {
    const accessKeyId = document.getElementById('accessKeyId').value;
    const secretAccessKey = document.getElementById('secretAccessKey').value;
    const bucketName = 'assistos-demo-bucket';
    const endpoint = 'https://assistos-demo-bucket.fra1.digitaloceanspaces.com';
    
    // Select file inputs
    const sourceFileInput = document.getElementById('SourceFile');
    const destinationFileInput = document.getElementById('DestinationFile');
    
    if (!sourceFileInput.files.length || !destinationFileInput.files.length) {
        alert('Please select both source and destination files to upload.');
        return;
    }
    
    const sourceFile = sourceFileInput.files[0];
    const destinationFile = destinationFileInput.files[0];

    const sourceFileExtension = sourceFile.name.split('.').pop();
    const destinationFileExtension = destinationFile.name.split('.').pop();
    sourceFileKey = generateRandomString(16) + "." + sourceFileExtension;
    destinationFileKey = generateRandomString(16) + "." + destinationFileExtension;

    const s3 = new AWS.S3({
        endpoint: new AWS.Endpoint(endpoint),
        credentials: new AWS.Credentials({
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey
        }),
        s3ForcePathStyle: true,
    });

    const sourceFileParams = {
        Bucket: bucketName,
        Key: sourceFileKey,
        Body: sourceFile,
        ACL: 'public-read'
    };
    
    const destinationFileParams = {
        Bucket: bucketName,
        Key: destinationFileKey,
        Body: destinationFile,
        ACL: 'public-read'
    };

    const loadingSpinner = document.getElementById('loadingSpinner');
    loadingSpinner.style.display = '';

    const uploadSourceFile = s3.upload(sourceFileParams).promise();
    const uploadDestinationFile = s3.upload(destinationFileParams).promise();

    Promise.all([uploadSourceFile, uploadDestinationFile])
        .then(results => {
            loadingSpinner.style.display = 'none';
            console.log('Upload Success:', results);
            sourceFileUrl = results[0].Location;
            destinationFileUrl = results[1].Location;
            alert('Files uploaded successfully!');
        })
        .catch(err => {
            loadingSpinner.style.display = 'none';
            console.error('Upload Error:', err);
            alert('File upload failed: ' + err.message);
        });
}

function submitForm(event) {
    event.preventDefault();

    const accessKeyId = document.getElementById('accessKeyId').value;
    const secretAccessKey = document.getElementById('secretAccessKey').value;
    const bucketName = 'assistos-demo-bucket';
    const endpoint = 'https://assistos-demo-bucket.fra1.digitaloceanspaces.com';
    const apiKey = document.getElementById('apiKey').value;
    const form = document.getElementById('inputForm');
    const loadingSpinner = document.getElementById('loadingSpinner');

    const sourceFileIndex = document.getElementById('SourceFileIndex').value;
    const destinationFileIndex = document.getElementById('DestinationFileIndex').value;

    if (!sourceFileKey || !destinationFileKey) {
        alert('Please upload both source and destination files first.');
        return;
    }
    
    form.style.display = 'none';
    loadingSpinner.style.display = '';

    const requestBody = {
        "input": {
            "bucket_name": bucketName,
            "source_file_key": sourceFileKey,
            "destination_file_key": destinationFileKey,
            "source_file_index": sourceFileIndex,
            "destination_file_index": destinationFileIndex,
            "output_key": generateRandomString(16),
            "aws_access_key_id": accessKeyId,
            "aws_secret_access_key": secretAccessKey,
            "endpoint": endpoint,
            "aws_region": "fra1"
        }
    };

    fetch('https://api.runpod.ai/v2/nvxq25nz8lnrm7/run', {
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
    const statusUrl = `https://api.runpod.ai/v2/nvxq25nz8lnrm7/status/${requestId}`;
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
            } else if (data.status === 'FAILED') {
                clearInterval(intervalId);
                loadingSpinner.style.display = 'none'; // Hide spinner on error
                form.style.display = ''; // Show form again if there's an error
                alert('The request failed. Please try again.');
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
    resultDiv.innerHTML = `<p>Processing completed. <a href="${outputUrl}" target="_blank">Click here</a> to view the output image.</p>`;
    document.getElementById('inputForm').style.display = ''; // Show the form again
}

document.addEventListener('DOMContentLoaded', restoreCredentials);
