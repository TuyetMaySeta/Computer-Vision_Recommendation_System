"""
Module xử lý hình ảnh để trích xuất text và features
Sử dụng CLIP model cho image embeddings và OCR cho text extraction
"""

import os
from typing import Optional, Tuple, Dict
from PIL import Image
import numpy as np
from utils.logger import get_logger

logger = get_logger(__name__)

class ImageProcessor:
    def __init__(self):
        """Khởi tạo image processor"""
        self.ocr_engine = None
        self.clip_model = None
        self.clip_processor = None
        
    def _load_ocr_engine(self):
        """Load OCR engine (pytesseract)"""
        if self.ocr_engine is None:
            try:
                import pytesseract
                self.ocr_engine = pytesseract
                logger.info("OCR engine loaded successfully")
            except ImportError:
                logger.warning("pytesseract not installed. OCR will not be available.")
                logger.warning("Install with: pip install pytesseract")
                logger.warning("Also install Tesseract: https://github.com/tesseract-ocr/tesseract")
        return self.ocr_engine
    
    def _load_clip_model(self):
        """Load CLIP model for image embeddings"""
        if self.clip_model is None:
            try:
                from transformers import CLIPProcessor, CLIPModel
                
                logger.info("Loading CLIP model...")
                self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                logger.info("CLIP model loaded successfully")
            except ImportError:
                logger.error("transformers not installed. Install with: pip install transformers")
                return None
        return self.clip_model
    
    def extract_text_from_image(self, image_path: str) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Trích xuất text từ ảnh bằng OCR
        
        Args:
            image_path: Đường dẫn đến file ảnh
            
        Returns:
            Tuple (extracted_text, metadata)
        """
        try:
            # Check file exists
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return None, None
            
            # Load OCR engine
            ocr = self._load_ocr_engine()
            if ocr is None:
                logger.warning("OCR not available. Skipping text extraction.")
                return "", {}
            
            # Open image
            image = Image.open(image_path)
            
            # Extract metadata
            metadata = {
                'format': image.format,
                'size': image.size,
                'mode': image.mode,
                'width': image.width,
                'height': image.height
            }
            
            # Extract text using OCR
            logger.info("Extracting text from image using OCR...")
            text = ocr.image_to_string(image, lang='eng')
            
            # Clean extracted text
            text = text.strip()
            
            if text:
                logger.info(f"Extracted {len(text)} characters from image")
            else:
                logger.warning("No text found in image")
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return None, None
    
    def create_image_embedding(self, image_path: str) -> Optional[np.ndarray]:
        """
        Tạo embedding cho ảnh sử dụng CLIP model
        
        Args:
            image_path: Đường dẫn đến file ảnh
            
        Returns:
            Image embedding vector
        """
        try:
            # Load CLIP model
            if self._load_clip_model() is None:
                logger.error("CLIP model not available")
                return None
            
            # Open image
            image = Image.open(image_path)
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Process image
            logger.info("Creating image embedding with CLIP...")
            inputs = self.clip_processor(images=image, return_tensors="pt")
            
            # Get image features
            image_features = self.clip_model.get_image_features(**inputs)
            
            # Convert to numpy and normalize
            embedding = image_features.detach().numpy()[0]
            embedding = embedding / np.linalg.norm(embedding)
            
            logger.info(f"Image embedding created: shape {embedding.shape}")
            
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error creating image embedding: {e}")
            return None
    
    def process_image(self, image_path: str, extract_text: bool = True, 
                     create_embedding: bool = True) -> Dict:
        """
        Xử lý toàn bộ: OCR text + tạo embedding
        
        Args:
            image_path: Đường dẫn file ảnh
            extract_text: Có extract text không
            create_embedding: Có tạo embedding không
            
        Returns:
            Dictionary chứa kết quả xử lý
        """
        logger.info(f"Processing image: {image_path}")
        
        result = {
            'image_path': image_path,
            'text': None,
            'metadata': None,
            'embedding': None,
            'success': False
        }
        
        # Extract text
        if extract_text:
            text, metadata = self.extract_text_from_image(image_path)
            result['text'] = text
            result['metadata'] = metadata
        
        # Create embedding
        if create_embedding:
            embedding = self.create_image_embedding(image_path)
            result['embedding'] = embedding
        
        # Check success
        result['success'] = (
            (not extract_text or result['text'] is not None) and
            (not create_embedding or result['embedding'] is not None)
        )
        
        return result
    
    def analyze_image_content(self, image_path: str) -> str:
        """
        Phân tích nội dung ảnh và tạo description
        
        Args:
            image_path: Đường dẫn file ảnh
            
        Returns:
            Description string
        """
        result = self.process_image(image_path, extract_text=True, create_embedding=False)
        
        if not result['success']:
            return ""
        
        # Build description
        description_parts = []
        
        # Add metadata info
        metadata = result.get('metadata', {})
        if metadata:
            description_parts.append(f"Image: {metadata.get('width')}x{metadata.get('height')} pixels")
        
        # Add extracted text
        text = result.get('text', '').strip()
        if text and len(text) > 10:
            # Clean and format text
            text = ' '.join(text.split())
            description_parts.append(f"Text content: {text[:500]}")
        
        return '. '.join(description_parts)


class MultimodalProcessor:
    """
    Processor kết hợp text, image và document
    """
    def __init__(self):
        self.image_processor = ImageProcessor()
        
    def process_multimodal_input(self, text_query: Optional[str] = None,
                                 image_path: Optional[str] = None,
                                 pdf_path: Optional[str] = None) -> str:
        """
        Xử lý input multimodal: text + image + PDF
        
        Args:
            text_query: Text query
            image_path: Path to image
            pdf_path: Path to PDF
            
        Returns:
            Combined processed text
        """
        from processors.input_processor import InputProcessor
        
        input_processor = InputProcessor()
        combined_parts = []
        
        # 1. Process text query
        if text_query:
            logger.info("Processing text query...")
            processed_text = input_processor.process_query_text(text_query)
            combined_parts.extend([processed_text] * 3)  # Weight x3
        
        # 2. Process image
        if image_path:
            logger.info("Processing image...")
            image_result = self.image_processor.process_image(
                image_path, 
                extract_text=True, 
                create_embedding=False
            )
            
            if image_result['success']:
                # Add OCR text
                ocr_text = image_result.get('text', '').strip()
                if ocr_text and len(ocr_text) > 10:
                    logger.info(f"Extracted {len(ocr_text)} characters from image")
                    combined_parts.extend([ocr_text] * 2)  # Weight x2
                
                # Add image description
                description = self.image_processor.analyze_image_content(image_path)
                if description:
                    combined_parts.append(description)
        
        # 3. Process PDF
        if pdf_path:
            logger.info("Processing PDF...")
            raw_text, metadata = input_processor.extract_pdf_text(pdf_path)
            if raw_text:
                processed_pdf = input_processor.preprocess_file_text(raw_text, metadata)
                combined_parts.append(processed_pdf)
        
        # Combine all parts
        if not combined_parts:
            logger.error("No valid input provided")
            return None
        
        final_text = ' '.join(combined_parts)
        
        # Limit length
        if len(final_text) > 20000:
            final_text = final_text[:20000]
        
        logger.info(f"Multimodal processing complete: {len(final_text)} characters")
        
        return final_text