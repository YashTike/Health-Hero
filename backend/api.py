"""FastAPI server for medical bill processing and debate system."""

import logging
from io import BytesIO
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.ocr.pipeline import OCRPipeline
from backend.agents.pipeline import process_medical_bill
from backend.agents.debate import DebateManager, generate_debate_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Medical Bill Fighter API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OCR pipeline (singleton)
ocr_pipeline = OCRPipeline()


class MessageResponse(BaseModel):
    """Response model for a single message."""
    id: str
    role: str  # "medical" or "bill"
    name: str
    text: str
    timestamp: str


class ProcessBillResponse(BaseModel):
    """Response model for bill processing."""
    messages: List[MessageResponse]
    summary_stats: Dict[str, Any]
    debate_summary: Dict[str, str]


def map_debate_role_to_frontend(role: str) -> str:
    """Map debate system roles to frontend roles.
    
    Args:
        role: Debate role ("fighter" or "hospital")
    
    Returns:
        Frontend role ("bill" or "medical")
    """
    mapping = {
        "fighter": "bill",
        "hospital": "medical"
    }
    return mapping.get(role, role)


def get_agent_name(role: str) -> str:
    """Get agent display name based on role.
    
    Args:
        role: Agent role ("medical" or "bill")
    
    Returns:
        Display name
    """
    names = {
        "medical": "NorthRiver Medical",
        "bill": "Bill Fighter"
    }
    return names.get(role, role)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/process-bill", response_model=ProcessBillResponse)
async def process_bill(
    file: UploadFile = File(...),
    prompt: str = Form("")
):
    """Process a medical bill through the complete pipeline.
    
    This endpoint:
    1. Extracts text from the uploaded file (PDF or image)
    2. Runs the LLM pipeline (extraction → analysis → negotiation)
    3. Runs the debate system (fighter vs. hospital)
    4. Returns the debate transcript in frontend format
    
    Args:
        file: Uploaded file (PDF or image)
        prompt: Optional prompt/instructions from the user
    
    Returns:
        ProcessBillResponse with messages, summary stats, and debate summary
    
    Raises:
        HTTPException: If processing fails
    """
    try:
        logger.info(f"Processing bill upload: {file.filename}")
        
        # Read file contents
        contents = await file.read()
        file_obj = BytesIO(contents)
        
        # Step 1: OCR - Extract text from file
        logger.info("Step 1: Running OCR pipeline...")
        try:
            ocr_result = ocr_pipeline.extract(file_obj, return_pages=False)
            ocr_text = ocr_result if isinstance(ocr_result, str) else ocr_result.get("text", "")
            
            if not ocr_text or len(ocr_text.strip()) < 50:
                raise ValueError(
                    "OCR extraction yielded insufficient text. "
                    "Please ensure the file is a clear PDF or image of a medical bill."
                )
            
            logger.info(f"OCR extracted {len(ocr_text)} characters")
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract text from file: {str(e)}"
            )
        
        # Step 2: LLM Pipeline - Extract, analyze, and generate negotiation materials
        logger.info("Step 2: Running LLM pipeline (extraction → analysis → negotiation)...")
        try:
            pipeline_result = process_medical_bill(ocr_text=ocr_text)
            bill_json = pipeline_result["analysis"]  # Enriched line items for debate
            
            if not bill_json:
                raise ValueError(
                    "No line items were extracted from the bill. "
                    "Please ensure the document is a valid medical bill."
                )
            
            logger.info(f"Pipeline processed {len(bill_json)} line items")
        except Exception as e:
            logger.error(f"LLM pipeline failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process bill: {str(e)}"
            )
        
        # Step 3: Debate System - Run debate between fighter and hospital
        logger.info("Step 3: Running debate system...")
        try:
            debate_manager = DebateManager(max_rounds=10)
            debate_transcript = debate_manager.run_debate(
                bill_json=bill_json,
                num_rounds=10
            )
            
            logger.info(f"Debate completed with {len(debate_transcript)} messages")
        except Exception as e:
            logger.error(f"Debate system failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to run debate: {str(e)}"
            )
        
        # Step 4: Generate debate summary
        logger.info("Step 4: Generating debate summary...")
        try:
            summary = generate_debate_summary(
                bill_json=bill_json,
                debate_transcript=debate_transcript
            )
        except Exception as e:
            logger.warning(f"Failed to generate debate summary: {e}")
            summary = {
                "patient_arguments": "Summary generation failed.",
                "hospital_arguments": "Summary generation failed.",
                "recommendation": "Please review the debate transcript manually."
            }
        
        # Step 5: Convert debate transcript to frontend format
        import uuid
        from datetime import datetime
        
        messages = []
        base_time = datetime.now().timestamp() * 1000  # milliseconds
        
        for i, debate_msg in enumerate(debate_transcript):
            # Map debate roles to frontend roles
            frontend_role = map_debate_role_to_frontend(debate_msg["role"])
            agent_name = get_agent_name(frontend_role)
            
            # Generate timestamp (1 minute intervals)
            timestamp_ms = base_time + (i * 60 * 1000)
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000).strftime("%I:%M %p")
            
            message = MessageResponse(
                id=str(uuid.uuid4()),
                role=frontend_role,
                name=agent_name,
                text=debate_msg["content"],
                timestamp=timestamp
            )
            messages.append(message)
        
        # Prepare response
        response = ProcessBillResponse(
            messages=messages,
            summary_stats=pipeline_result.get("summary_stats", {}),
            debate_summary=summary
        )
        
        logger.info("Bill processing completed successfully")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing bill: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

