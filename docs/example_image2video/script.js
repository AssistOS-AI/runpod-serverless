let uploadedFileUrl = '';
let randomKey = '';
// Function to generate a random string
function generateRandomString(length) {
    const randomBytes = crypto.getRandomValues(new Uint8Array(32));
    const base64String = btoa(String.fromCharCode.apply(null, randomBytes));
    const base64UrlString = base64String.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return base64UrlString.substring(0, length); // Limit the random string length
}

function uploadFile() {
	@@ -81,15 +81,15 @@ function submitForm(event) {
        "input": {
            "bucket_name": bucketName,
            "input_key": randomKey,
            "output_key": generateRandomString(16) + '.mp4',  // Set output to MP4 video
            "aws_access_key_id": accessKeyId,
            "aws_secret_access_key": secretAccessKey,
            "aws_region": "fra1",
            "endpoint": endpoint
        }
    };

    fetch('https://api.runpod.ai/v2/n8mjvng9jjxist/run', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
	@@ -111,7 +111,7 @@ function submitForm(event) {
}

function checkStatus(requestId, apiKey) {
    const statusUrl = `https://api.runpod.ai/v2/n8mjvng9jjxist/status/${requestId}`;
    const loadingSpinner = document.getElementById('loadingSpinner');
    const form = document.getElementById('inputForm');

	@@ -132,7 +132,7 @@ function checkStatus(requestId, apiKey) {
                if (data.status === 'COMPLETED') {
                    clearInterval(intervalId);
                    loadingSpinner.style.display = 'none'; // Hide spinner when completed
                    displayResult(data.output); // Updated to handle video URL from the Python handler
                }
            })
            .catch(error => {
	@@ -146,6 +146,6 @@ function checkStatus(requestId, apiKey) {

function displayResult(outputUrl) {
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = `<p>Processing completed. <a href="${outputUrl}" target="_blank">Click here</a> to view the output video.</p>`;
    document.getElementById('inputForm').style.display = ''; // Show the form again
}
