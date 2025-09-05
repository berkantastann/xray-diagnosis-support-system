from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image as PILImage
from io import BytesIO
import google.generativeai as genai
from app import db
from app.models.image import Image, ImageLabel, DoctorComment
from config import Config
import base64

bp = Blueprint('main', __name__)

# Load the PyTorch model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = models.densenet121(pretrained=False)
model.classifier = torch.nn.Sequential(
    torch.nn.Linear(model.classifier.in_features, 14)
)
state_dict = torch.load('DenseNet121_model.pth', map_location=device)
new_state_dict = {k[4:] if k.startswith('net.') else k: v for k, v in state_dict.items()}
model.load_state_dict(new_state_dict)
model.to(device)
model.eval()

# Configure Gemini API
if not Config.GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY bulunamadı. Lütfen .env dosyasını kontrol edin.")

genai.configure(api_key=Config.GOOGLE_API_KEY)
model_llm = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={
        "temperature": 0.7,
        "max_output_tokens": 2048,
    }
)

def process_image(image_data):
    # Image preprocessing
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Load and preprocess image
    img = PILImage.open(BytesIO(image_data))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Apply transformations
    img_tensor = transform(img).unsqueeze(0).to(device)
    
    # Make prediction
    with torch.no_grad():
        predictions = model(img_tensor)
        predictions = torch.sigmoid(predictions).cpu().numpy()[0]
    
    return predictions

def generate_llm_report(predictions_list):
    try:
        high_prob_diseases = [disease for disease, conf in predictions_list if conf > 0.5]
        medium_prob_diseases = [disease for disease, conf in predictions_list if 0.2 < conf <= 0.5]
        
        prompt = f"""Sen deneyimli bir radyoloji uzmanısın. Aşağıdaki X-ray görüntüsünde tespit edilen hastalıklar için kısa ve öz bir tıbbi rapor hazırla.

Yüksek olasılıklı hastalıklar: {', '.join(high_prob_diseases) if high_prob_diseases else 'Yüksek olasılıklı hastalık tespit edilmedi'}
Orta olasılıklı hastalıklar: {', '.join(medium_prob_diseases) if medium_prob_diseases else 'Orta olasılıklı hastalık tespit edilmedi'}

Lütfen aşağıdaki başlıklar altında kısa ve öz bir rapor hazırla:
1. Bulgular: Tespit edilen hastalıkların kısa açıklaması
2. Değerlendirme: Hastalıkların ciddiyeti ve etkileri
3. Öneriler: Kısa ve net öneriler
4. Takip Planı: Gerekli takip adımları

Önemli:
- Her bölümü 2-3 cümle ile özetle
- Gereksiz detaylardan kaçın
- Tıbbi terminolojiyi kullan
- Raporu Türkçe olarak hazırla
- Hasta bilgileri ve radyolog bilgilerini raporda belirtme"""
        
        try:
            response = model_llm.generate_content(prompt)
            
            if not response or not response.text:
                raise Exception("API yanıtı boş")
                
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            print(f"API Hatası: {error_msg}")
            
            if "429" in error_msg:
                return """API kullanım limiti aşıldı. Lütfen birkaç dakika bekleyip tekrar deneyin.

Bulgular:
- Yüksek olasılıklı hastalıklar: {}
- Orta olasılıklı hastalıklar: {}

Değerlendirme:
- Lütfen birkaç dakika bekleyip raporu tekrar oluşturmayı deneyin.

Öneriler:
- Sistem şu anda yoğun kullanımda, lütfen daha sonra tekrar deneyin.

Takip Planı:
- Rapor oluşturma işlemini birkaç dakika sonra tekrar deneyebilirsiniz.""".format(
                    ', '.join(high_prob_diseases) if high_prob_diseases else 'Yüksek olasılıklı hastalık tespit edilmedi',
                    ', '.join(medium_prob_diseases) if medium_prob_diseases else 'Orta olasılıklı hastalık tespit edilmedi'
                )
            else:
                return f"API hatası: {error_msg}"
                
    except Exception as e:
        return f"Rapor oluşturulurken bir hata oluştu: {str(e)}"

@bp.route('/')
@login_required
def index():
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': 'Dosya seçilmedi'
        })
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'Dosya seçilmedi'
        })
    
    try:
        image_data = file.read()
        predictions = process_image(image_data)
        
        # Save image to database
        new_image = Image(filename=secure_filename(file.filename),
                        image_data=image_data,
                        user_id=current_user.id)
        db.session.add(new_image)
        db.session.commit()
        
        # Save predictions
        disease_names = [
            'No Finding',
            'Enlarged Cardiomediastinum',
            'Cardiomegaly',
            'Lung Opacity',
            'Lung Lesion',
            'Edema',
            'Consolidation',
            'Pneumonia',
            'Atelectasis',
            'Pneumothorax',
            'Pleural Effusion',
            'Pleural Other',
            'Fracture',
            'Support Devices'
        ]
        
        predictions_list = []
        for disease, confidence in zip(disease_names, predictions):
            label = ImageLabel(disease_name=disease,
                            confidence=float(confidence),
                            image_id=new_image.id)
            db.session.add(label)
            predictions_list.append((disease, float(confidence)))
        
        # Generate LLM report
        llm_report = generate_llm_report(predictions_list)
        new_image.llm_report = llm_report
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'predictions': predictions_list,
            'llm_report': llm_report,
            'image_id': new_image.id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@bp.route('/save_predictions', methods=['POST'])
@login_required
def save_predictions():
    try:
        data = request.get_json()
        image_id = data.get('image_id')
        confirmed_labels = data.get('confirmed_labels', [])
        patient_name = data.get('patient_name')
        doctor_comment = data.get('doctor_comment')

        if not image_id:
            return jsonify({'success': False, 'message': 'Resim ID\'si gerekli'}), 400

        image = Image.query.get(image_id)
        if not image:
            return jsonify({'success': False, 'message': 'Resim bulunamadı'}), 404

        if image.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Bu işlem için yetkiniz yok'}), 403

        if patient_name:
            image.patient_name = patient_name

        if doctor_comment:
            comment = DoctorComment(
                comment=doctor_comment,
                image_id=image_id,
                user_id=current_user.id
            )
            db.session.add(comment)

        for label in image.labels:
            label.is_confirmed = label.disease_name in confirmed_labels

        db.session.commit()
        return jsonify({'success': True, 'message': 'Tahminler ve bilgiler başarıyla kaydedildi'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/history')
@login_required
def history():
    images = Image.query.filter_by(user_id=current_user.id).order_by(Image.created_at.desc()).all()
    
    # Convert image data to base64 for display
    for image in images:
        image.image_data_base64 = base64.b64encode(image.image_data).decode('utf-8')
    
    return render_template('history.html', images=images)

@bp.route('/save_comment', methods=['POST'])
@login_required
def save_comment():
    try:
        data = request.get_json()
        image_id = data.get('image_id')
        comment_text = data.get('comment')

        if not image_id or not comment_text:
            return jsonify({'success': False, 'message': 'Resim ID ve yorum gerekli'}), 400

        # Resim kaydını bul
        image = Image.query.get(image_id)
        if not image:
            return jsonify({'success': False, 'message': 'Resim bulunamadı'}), 404

        # Kullanıcı kontrolü
        if image.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Bu işlem için yetkiniz yok'}), 403

        # Yeni yorum oluştur
        comment = DoctorComment(
            comment=comment_text,
            image_id=image_id,
            user_id=current_user.id
        )
        db.session.add(comment)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Yorum başarıyla kaydedildi'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500 