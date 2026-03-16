// main.js - Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
    
    // Elements
    const fileInput = document.getElementById('fileInput');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const removePhotoBtn = document.getElementById('removePhotoBtn');
    const submitBtn = document.getElementById('submitBtn');
    const uploadForm = document.getElementById('uploadForm');

    // Camera Elements
    const cameraWebcam = document.getElementById('cameraWebcam');
    const cameraCanvas = document.getElementById('cameraCanvas');
    const cameraLoading = document.getElementById('cameraLoading');
    const cameraError = document.getElementById('cameraError');
    const switchCameraBtn = document.getElementById('switchCameraBtn');
    const cameraContainer = document.getElementById('cameraContainer');

    // Camera State
    let currentStream = null;
    let usingFrontCamera = true;
    let cameraModeActive = false;

    // State Areas
    const idleState = document.getElementById('idleState');
    const loadingState = document.getElementById('loadingState');
    const resultState = document.getElementById('resultState');

    // Result Elements
    const resPreviewImage = document.getElementById('resPreviewImage');
    const resName = document.getElementById('resName');
    const resConfidence = document.getElementById('resConfidence');
    const resAction = document.getElementById('resAction');
    const resTime = document.getElementById('resTime');
    const resMessage = document.getElementById('resMessage');
    const syncStatus = document.getElementById('syncStatus');

    // --- Camera Initialization ---
    async function startCamera(facingMode = 'user') {
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
        }

        try {
            cameraLoading.classList.remove('hidden');
            cameraError.classList.add('hidden');
            
            const constraints = {
                video: {
                    facingMode: facingMode,
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: false
            };

            // Check if mediaDevices exists (missing if not localhost or HTTPS)
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error("Camera API not supported or requires a secure HTTPS connection.");
            }

            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            currentStream = stream;
            cameraWebcam.srcObject = stream;
            
            // Mirror logic for front camera
            if (facingMode === 'user') {
                cameraWebcam.classList.add('mirrored');
            } else {
                cameraWebcam.classList.remove('mirrored');
            }

            cameraLoading.classList.add('hidden');
            submitBtn.disabled = false;
            cameraModeActive = true;
        } catch (err) {
            console.error("Camera access error:", err);
            cameraLoading.classList.add('hidden');
            cameraError.classList.remove('hidden');
            
            // Show specific error inside the camera error UI
            const errorMsg = cameraError.querySelector('p');
            if (errorMsg && err.message) {
                errorMsg.textContent = err.message;
            }

            submitBtn.disabled = true;
            cameraModeActive = false;
        }
    }

    // Try to start camera on load if element exists
    if (cameraWebcam && !uploadForm.hasAttribute('style')) { 
        // Note: the style attribute check prevents starting if model isn't trained
        startCamera();
    }

    if (switchCameraBtn) {
        switchCameraBtn.addEventListener('click', () => {
            usingFrontCamera = !usingFrontCamera;
            startCamera(usingFrontCamera ? 'user' : 'environment');
        });
    }

    // --- Form & Capture Handling ---
    if (uploadForm) {
        // Fallback hidden file input handling
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                cameraContainer.classList.add('hidden'); // hide camera if file selected
                handleFileSelect(fileInput.files[0]);
            }
        });

        removePhotoBtn.addEventListener('click', () => {
            resetUploadState();
        });

        // AJAX Submission
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData();

            // 1. If user selected a file manually (fallback)
            if (fileInput.files.length > 0) {
                formData.append('photo', fileInput.files[0]);
            } 
            // 2. Otherwise capture from camera
            else if (cameraModeActive && currentStream) {
                const ctx = cameraCanvas.getContext('2d');
                cameraCanvas.width = cameraWebcam.videoWidth;
                cameraCanvas.height = cameraWebcam.videoHeight;
                
                // If mirrored, flip the canvas context before drawing
                if (usingFrontCamera) {
                    ctx.translate(cameraCanvas.width, 0);
                    ctx.scale(-1, 1);
                }
                
                ctx.drawImage(cameraWebcam, 0, 0, cameraCanvas.width, cameraCanvas.height);
                
                // Convert to Blob and append
                const blob = await new Promise(resolve => cameraCanvas.toBlob(resolve, 'image/jpeg', 0.9));
                formData.append('photo', blob, 'capture.jpg');
            } else {
                return; // Nothing to submit
            }

            // Show Loading
            idleState.classList.add('hidden');
            resultState.classList.add('hidden');
            loadingState.classList.remove('hidden');
            submitBtn.disabled = true;

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                loadingState.classList.add('hidden');
                
                if (data.success) {
                    showSuccessResult(data);
                } else {
                    showErrorResult(data.error, data.preview_url);
                }
            } catch (err) {
                loadingState.classList.add('hidden');
                showErrorResult("Network or server error occurred.");
            } finally {
                submitBtn.disabled = false;
            }
        });
    }

    function handleFileSelect(file) {
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreview.src = e.target.result;
                if(cameraContainer) cameraContainer.classList.add('hidden');
                previewContainer.classList.remove('hidden');
                submitBtn.disabled = false;
                
                // Reset right panel
                resultState.classList.add('hidden');
                loadingState.classList.add('hidden');
                idleState.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    }

    function resetUploadState() {
        fileInput.value = "";
        if(cameraModeActive && cameraContainer) {
            cameraContainer.classList.remove('hidden');
            submitBtn.disabled = false;
        } else {
            submitBtn.disabled = true;
        }
        
        previewContainer.classList.add('hidden');
        imagePreview.src = "";
        
        idleState.classList.remove('hidden');
        resultState.classList.add('hidden');
    }

    function showSuccessResult(data) {
        resultState.classList.remove('hidden');
        
        resPreviewImage.src = data.preview_url;
        resName.textContent = data.employee_name;
        resConfidence.textContent = `${data.confidence.toFixed(1)}% Match`;
        
        // Stats
        resAction.textContent = data.action === 'check_in' ? 'Check-In' : 'Check-Out';
        resAction.className = `status-chip ${data.action === 'check_in' ? 'in' : 'out'}`;
        
        resTime.textContent = data.action === 'check_in' ? data.check_in : data.check_out;
        
        resMessage.textContent = data.message;
        resMessage.className = "alert alert-success mt-4";
        
        // Sync Status
        if (data.sheets_synced) {
            syncStatus.innerHTML = `<i data-lucide="cloud-lightning" class="text-success"></i> <span class="text-success">Saved to Google Sheets</span>`;
        } else {
            syncStatus.innerHTML = `<i data-lucide="database"></i> <span class="text-muted">Saved to internal database (CSV)</span>`;
        }
        
        lucide.createIcons();
    }

    function showErrorResult(errorMsg, previewUrl) {
        resultState.classList.remove('hidden');
        
        resName.textContent = "Unknown";
        resConfidence.textContent = "No Match";
        resAction.textContent = "Failed";
        resTime.textContent = "--:--:--";
        
        resMessage.textContent = errorMsg;
        resMessage.className = "alert alert-error mt-4";
        
        if (previewUrl) {
            resPreviewImage.src = previewUrl;
        }
        
        syncStatus.innerHTML = `<i data-lucide="x-circle"></i> <span class="text-danger">Not Synced</span>`;
        lucide.createIcons();
    }
});
