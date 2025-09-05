document.addEventListener('DOMContentLoaded', function() {
    // File upload handling
    const fileInput = document.getElementById('file');
    const previewImage = document.getElementById('previewImage');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const uploadForm = document.getElementById('uploadForm');
    const predictButton = document.getElementById('predictButton');
    const errorDiv = document.getElementById('error');
    const savePredictionsArea = document.getElementById('savePredictionsArea');
    const savePredictionsBtn = document.getElementById('savePredictionsBtn');
    const currentImageId = document.getElementById('currentImageId');

    // Initialize file upload handling
    if (fileInput && previewImage && uploadPlaceholder) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewImage.src = e.target.result;
                        previewImage.style.display = 'block';
                        uploadPlaceholder.style.display = 'none';
                    };
                    reader.readAsDataURL(file);
                    errorDiv.innerHTML = '';
                } else {
                    errorDiv.innerHTML = '<div class="alert alert-danger">Lütfen geçerli bir görüntü dosyası seçin.</div>';
                    fileInput.value = '';
                }
            }
        });
    }

    // Initialize form submission handling
    if (uploadForm) {
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!fileInput.files[0]) {
                errorDiv.innerHTML = '<div class="alert alert-danger">Lütfen bir görüntü seçin.</div>';
                return;
            }

            const formData = new FormData(uploadForm);
            predictButton.disabled = true;
            predictButton.innerHTML = '<span class="loading"></span> İşleniyor...';
            savePredictionsArea.style.display = 'none';

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    updatePredictions(data.predictions, data.image_id);
                    updateReport(data.llm_report);
                    currentImageId.value = data.image_id;
                    savePredictionsArea.style.display = 'block';
                    errorDiv.innerHTML = '';
                } else {
                    errorDiv.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                }
            } catch (error) {
                errorDiv.innerHTML = '<div class="alert alert-danger">Bir hata oluştu. Lütfen tekrar deneyin.</div>';
            } finally {
                predictButton.disabled = false;
                predictButton.innerHTML = '<i class="bi bi-lightning-charge"></i> Tahmin Et';
            }
        });
    }

    // Update predictions display
    function updatePredictions(predictions, imageId) {
        const predictionsDiv = document.getElementById('predictions');
        if (!predictionsDiv) return;

        predictions.sort((a, b) => b[1] - a[1]);

        predictionsDiv.innerHTML = predictions.map(([disease, confidence]) => {
            const percentage = (confidence * 100).toFixed(1);
            let confidenceClass = 'low';
            if (confidence > 0.5) confidenceClass = 'high';
            else if (confidence > 0.2) confidenceClass = 'medium';

            return `
                <div class="prediction-item">
                    <div class="form-check">
                        <input class="form-check-input prediction-checkbox" 
                               type="checkbox" 
                               value="${disease}"
                               id="check_${disease.replace(/\s+/g, '_')}">
                        <label class="form-check-label" for="check_${disease.replace(/\s+/g, '_')}">
                            <span>${disease}</span>
                            <span class="confidence confidence-${confidenceClass}">${percentage}%</span>
                        </label>
                    </div>
                    <div class="progress">
                        <div class="progress-bar bg-${confidenceClass}" 
                             role="progressbar" 
                             style="width: ${percentage}%" 
                             aria-valuenow="${percentage}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        predictions.forEach(([disease, confidence]) => {
            if (confidence > 0.5) {
                const checkbox = document.getElementById(`check_${disease.replace(/\s+/g, '_')}`);
                if (checkbox) checkbox.checked = true;
            }
        });

        if (savePredictionsBtn) {
            savePredictionsBtn.disabled = false;
            savePredictionsBtn.innerHTML = '<i class="bi bi-check-circle"></i> Seçili Tahminleri Kaydet';
        }
    }

    // Initialize save predictions handling
    if (savePredictionsBtn) {
        savePredictionsBtn.addEventListener('click', async function() {
            const checkedPredictions = Array.from(document.querySelectorAll('.prediction-checkbox:checked'))
                .map(checkbox => checkbox.value);
            
            if (checkedPredictions.length === 0) {
                errorDiv.innerHTML = '<div class="alert alert-warning">Lütfen en az bir tahmin seçin.</div>';
                return;
            }

            const patientName = document.getElementById('patientName').value;
            const doctorComment = document.getElementById('doctorComment').value;

            try {
                const response = await fetch('/save_predictions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        image_id: currentImageId.value,
                        confirmed_labels: checkedPredictions,
                        patient_name: patientName,
                        doctor_comment: doctorComment
                    })
                });

                const data = await response.json();
                if (data.success) {
                    errorDiv.innerHTML = '<div class="alert alert-success">Tahminler ve bilgiler başarıyla kaydedildi.</div>';
                    savePredictionsBtn.innerHTML = '<i class="bi bi-check-circle-fill"></i> Kaydedildi';
                } else {
                    errorDiv.innerHTML = `<div class="alert alert-danger">${data.message}</div>`;
                }
            } catch (error) {
                errorDiv.innerHTML = '<div class="alert alert-danger">Bir hata oluştu. Lütfen tekrar deneyin.</div>';
            }
        });

        document.addEventListener('change', function(e) {
            if (e.target && e.target.classList.contains('prediction-checkbox')) {
                savePredictionsBtn.innerHTML = '<i class="bi bi-check-circle"></i> Seçili Tahminleri Kaydet';
            }
        });
    }

    // Update report display
    function updateReport(report) {
        const reportDiv = document.getElementById('report');
        if (!reportDiv) return;

        const sections = report.split('\n\n').filter(section => section.trim());
        reportDiv.innerHTML = sections.map(section => {
            const [title, ...content] = section.split('\n');
            return `
                <div class="report-section">
                    <h6 class="section-title">${title}</h6>
                    <p class="section-content">${content.join('<br>')}</p>
                </div>
            `;
        }).join('');
    }

    // Initialize history page functionality
    if (document.querySelector('.history-item')) {
        const historyItems = document.querySelectorAll('.history-item');
        
        historyItems.forEach(item => {
            const checkboxes = item.querySelectorAll('.prediction-checkbox');
            const saveButton = item.querySelector('.save-prediction');
            const savedButton = item.querySelector('.saved-button');
            
            if (checkboxes.length && saveButton && savedButton) {
                checkboxes.forEach(checkbox => {
                    checkbox.addEventListener('change', function() {
                        saveButton.style.display = 'block';
                        savedButton.style.display = 'none';
                    });
                });

                saveButton.addEventListener('click', async function() {
                    const imageId = this.dataset.imageId;
                    const checkedPredictions = Array.from(
                        item.querySelectorAll(`input[name="confirmed_${imageId}"]:checked`)
                    ).map(checkbox => checkbox.value);

                    if (checkedPredictions.length === 0) {
                        alert('Lütfen en az bir tahmin seçin.');
                        return;
                    }

                    try {
                        const response = await fetch('/save_predictions', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                image_id: imageId,
                                confirmed_labels: checkedPredictions
                            })
                        });

                        const data = await response.json();
                        if (data.success) {
                            saveButton.style.display = 'none';
                            savedButton.style.display = 'block';

                            const successAlert = document.createElement('div');
                            successAlert.className = 'alert alert-success alert-dismissible fade show mt-2';
                            successAlert.innerHTML = `
                                Tahminler başarıyla kaydedildi.
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            `;
                            this.parentElement.appendChild(successAlert);
                            setTimeout(() => successAlert.remove(), 3000);
                        } else {
                            alert(data.message || 'Bir hata oluştu. Lütfen tekrar deneyin.');
                        }
                    } catch (error) {
                        alert('Bir hata oluştu. Lütfen tekrar deneyin.');
                    }
                });
            }
        });
    }
}); 