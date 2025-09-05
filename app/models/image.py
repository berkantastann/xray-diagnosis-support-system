from datetime import datetime
from app import db

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_name = db.Column(db.String(120), nullable=True)
    labels = db.relationship('ImageLabel', backref='image', lazy=True)
    doctor_comments = db.relationship('DoctorComment', backref='image', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    llm_report = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Image {self.filename}>'

class ImageLabel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disease_name = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<ImageLabel {self.disease_name}>'

class DoctorComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text, nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DoctorComment {self.id}>' 