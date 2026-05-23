from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import io
from pypdf import PdfReader
from pypdf.errors import PdfReadError
import uuid
import datetime
import docx
import fitz
import base64
from PIL import Image

app = FastAPI(title="Student Metadata API")

class GeminiResult(BaseModel):
    classification: str
    sentiment: str
    confidence_score: float
    entities: dict

@app.post("/enrich")
async def enrich(data: GeminiResult):
    """
    Enriches the Gemini output with business-specific metadata.
    """
    dept_map = {'invoice': 'Finance', 'contract': 'Legal', 'report': 'Management'}
    
    # Adjust confidence score based on entity completeness (are there any entities extracted?)
    has_entities = any(bool(v) for v in data.entities.values())
    adjusted_confidence = data.confidence_score if has_entities else max(0.0, data.confidence_score - 0.1)

    return {
        'document_id': str(uuid.uuid4()),
        'department': dept_map.get(data.classification.lower(), 'General'),
        'sensitivity': 'confidential' if 'amount' in str(data.entities).lower() else 'internal',
        'routing_tag': 'needs-review' if adjusted_confidence < 0.7 else 'auto-approved',
        'processed_at': datetime.datetime.utcnow().isoformat(),
        'confidence_score': round(adjusted_confidence, 2)
    }

@app.post("/extract-pdf")
async def extract_pdf(file: UploadFile = File(...)):
    """
    Extracts text and embedded images from an uploaded PDF file.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")
        
    try:
        content = await file.read()
        pdf_stream = io.BytesIO(content)
        reader = PdfReader(pdf_stream)
        
        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
                
        # Extract embedded images using PyMuPDF
        images = []
        seen_xrefs = set()
        doc = fitz.open(stream=content, filetype="pdf")
        for page_index in range(len(doc)):
            image_list = doc.get_page_images(page_index)
            for img_info in image_list:
                xref = img_info[0]
                if xref in seen_xrefs:
                    continue
                seen_xrefs.add(xref)
                
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.colorspace and pix.colorspace.name == fitz.csCMYK.name:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    png_bytes = pix.tobytes("png")
                    base64_str = base64.b64encode(png_bytes).decode("utf-8")
                    images.append({
                        "mime_type": "image/png",
                        "base64": base64_str
                    })
                except Exception:
                    pass
                
        return {
            "text": "\n".join(extracted_text),
            "images": images
        }
    except PdfReadError:
        raise HTTPException(status_code=400, detail="Failed to read PDF. The file may be corrupted.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred during extraction: {str(e)}")


@app.post("/extract-docx")
async def extract_docx(file: UploadFile = File(...)):
    """
    Extracts text and inline images from an uploaded DOCX file.
    """
    is_docx = (
        file.filename.lower().endswith(".docx") if file.filename else False
    ) or file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    if not is_docx:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid file type. Please upload a .docx file."}
        )
        
    try:
        content = await file.read()
        docx_stream = io.BytesIO(content)
        doc = docx.Document(docx_stream)
        
        paragraphs = [p.text for p in doc.paragraphs]
        text_content = "\n".join(paragraphs)
        
        images = []
        seen_blobs = set()
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                try:
                    img_part = rel.target_part
                    img_blob = img_part.blob
                    if img_blob in seen_blobs:
                        continue
                    seen_blobs.add(img_blob)
                    
                    img = Image.open(io.BytesIO(img_blob))
                    if img.mode == "CMYK":
                        img = img.convert("RGB")
                    
                    out_stream = io.BytesIO()
                    img.save(out_stream, format="PNG")
                    png_bytes = out_stream.getvalue()
                    
                    base64_str = base64.b64encode(png_bytes).decode("utf-8")
                    images.append({
                        "mime_type": "image/png",
                        "base64": base64_str
                    })
                except Exception:
                    pass
        
        return {
            "text": text_content,
            "images": images
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": f"An error occurred during extraction: {str(e)}"}
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the server is running.
    """
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    # Use "main:app" string and reload=True for auto-reloading on code changes
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
