import os
from typing import Optional
from fastapi import FastAPI, UploadFile, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
import anthropic
from dotenv import load_dotenv
import json
import tempfile
from rag_handler import rag_handler
from pydantic import BaseModel
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import re

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Tax Form Parser")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Configure paths
if os.name == 'nt':  # Windows
    # Tesseract path
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    # Poppler path
    os.environ["PATH"] += os.pathsep + r'C:\Program Files\poppler-24.08.0\Library\bin'

# Build vector store on startup
@app.on_event("startup")
async def startup_event():
    rag_handler.build_vector_store()

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Tax Assistant</title>
            <style>
                :root {
                    --primary-bg: #ffffff;
                    --secondary-bg: #f7f7f8;
                    --border-color: #e5e5e5;
                    --text-primary: #1a1a1a;
                    --text-secondary: #666666;
                    --accent-color: #10a37f;
                }

                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: var(--primary-bg);
                    color: var(--text-primary);
                }

                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                }

                .header {
                    text-align: center;
                    padding: 20px 0;
                    border-bottom: 1px solid var(--border-color);
                }

                .header h1 {
                    color: var(--accent-color);
                    margin: 0;
                    font-size: 24px;
                }

                .chat-container {
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px 0;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }

                .message {
                    padding: 20px;
                    border-radius: 8px;
                    max-width: 85%;
                    line-height: 1.5;
                }

                .user-message {
                    background-color: var(--accent-color);
                    color: white;
                    align-self: flex-end;
                    margin-left: auto;
                }

                .bot-message {
                    background-color: var(--secondary-bg);
                    color: var(--text-primary);
                    align-self: flex-start;
                }

                .bot-message h3 {
                    color: var(--accent-color);
                    margin-top: 0;
                    margin-bottom: 10px;
                }

                .bot-message ul {
                    margin: 10px 0;
                    padding-left: 20px;
                }

                .bot-message li {
                    margin-bottom: 5px;
                }

                .bot-message p {
                    margin: 10px 0;
                }

                .bot-message strong {
                    color: var(--accent-color);
                }

                .input-container {
                    padding: 20px 0;
                    border-top: 1px solid var(--border-color);
                    position: relative;
                }

                #chat-input {
                    width: 100%;
                    padding: 12px 20px;
                    border: 1px solid var(--border-color);
                    border-radius: 8px;
                    font-size: 16px;
                    background-color: var(--primary-bg);
                    color: var(--text-primary);
                    resize: none;
                    min-height: 24px;
                    max-height: 200px;
                    overflow-y: auto;
                }

                #chat-input:focus {
                    outline: none;
                    border-color: var(--accent-color);
                }

                .send-button {
                    position: absolute;
                    right: 10px;
                    bottom: 30px;
                    background: none;
                    border: none;
                    cursor: pointer;
                    color: var(--accent-color);
                    padding: 8px;
                }

                .send-button:hover {
                    opacity: 0.8;
                }

                .send-icon {
                    width: 24px;
                    height: 24px;
                }

                .typing-indicator {
                    display: flex;
                    align-items: center;
                    gap: 5px;
                    align-self: flex-start;
                    background-color: var(--secondary-bg);
                    padding: 20px;
                    border-radius: 8px;
                    color: var(--text-secondary);
                }

                .typing-dot {
                    width: 8px;
                    height: 8px;
                    background-color: var(--text-secondary);
                    border-radius: 50%;
                    animation: typing 1s infinite;
                }

                .typing-dot:nth-child(2) {
                    animation-delay: 0.2s;
                }

                .typing-dot:nth-child(3) {
                    animation-delay: 0.4s;
                }

                @keyframes typing {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                }

                @media (max-width: 768px) {
                    .container {
                        padding: 10px;
                    }
                    
                    .message {
                        max-width: 90%;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Tax Assistant</h1>
                </div>
                
                <div class="chat-container" id="chat-container">
                    <div class="message bot-message">
                        <h3>Welcome!</h3>
                        <p>I'm your tax assistant. I can help you understand your tax filing requirements and guide you through the process.</p>
                        <p>You can ask me questions about:</p>
                        <ul>
                            <li>Which forms you need to file</li>
                            <li>How to file your taxes</li>
                            <li>Important deadlines</li>
                            <li>Common tax situations</li>
                        </ul>
                        <p>What would you like to know?</p>
                    </div>
                </div>
                
                <div class="input-container">
                    <textarea 
                        id="chat-input" 
                        placeholder="Ask about your tax filing requirements..."
                        rows="1"
                        oninput="autoResize(this)"
                    ></textarea>
                    <button class="send-button" id="send-button" onclick="sendMessage()">
                        <svg class="send-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M22 2L11 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </div>
            </div>

            <script>
                let conversationId = "default";

                function autoResize(textarea) {
                    textarea.style.height = 'auto';
                    textarea.style.height = textarea.scrollHeight + 'px';
                }

                async function sendMessage() {
                    const input = document.getElementById('chat-input');
                    const sendButton = document.getElementById('send-button');
                    const message = input.value.trim();
                    if (!message) return;

                    // Disable input and button while processing
                    input.classList.add('input-disabled');
                    sendButton.disabled = true;

                    // Add user message to chat
                    const chatContainer = document.getElementById('chat-container');
                    chatContainer.innerHTML += `
                        <div class="message user-message">
                            ${message}
                        </div>
                    `;

                    // Show typing indicator
                    chatContainer.innerHTML += `
                        <div class="typing-indicator" id="typing-indicator">
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                            <div class="typing-dot"></div>
                        </div>
                    `;

                    // Clear input and reset height
                    input.value = '';
                    input.style.height = 'auto';

                    try {
                        const response = await fetch('/tax-guidance', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ 
                                message: message,
                                conversation_id: conversationId
                            })
                        });

                        const data = await response.json();
                        
                        // Update conversation ID if provided
                        if (data.conversation_id) {
                            conversationId = data.conversation_id;
                        }
                        
                        // Remove typing indicator
                        document.getElementById('typing-indicator').remove();
                        
                        // Add bot response to chat
                        chatContainer.innerHTML += `
                            <div class="message bot-message">
                                ${data.response}
                            </div>
                        `;

                        // Scroll to bottom
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    } catch (error) {
                        console.error('Error:', error);
                        document.getElementById('typing-indicator').remove();
                        chatContainer.innerHTML += `
                            <div class="message bot-message">
                                Sorry, there was an error processing your request. Please try again.
                            </div>
                        `;
                    } finally {
                        // Re-enable input and button
                        input.classList.remove('input-disabled');
                        sendButton.disabled = false;
                        input.focus();
                    }
                }

                // Allow sending message with Enter key
                document.getElementById('chat-input').addEventListener('keypress', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                    }
                });
            </script>
        </body>
    </html>
    """

def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image using Tesseract OCR."""
    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF using Tesseract OCR."""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        text = ""
        for image in images:
            text += pytesseract.image_to_string(image)
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

def extract_text_from_pdf_by_boxes(pdf_path: str, form_type: str) -> dict:
    """Extract text from a PDF by specific box regions based on form type."""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        result = {}
        
        # Define box regions for different form types
        if form_type.lower() == "w-2":
            # W-2 box coordinates (x, y, width, height)
            boxes = {
                "employee_ssn": (100, 100, 200, 30),  # Box a
                "employer_ein": (100, 150, 200, 30),  # Box b
                "wages_tips_other": (100, 200, 200, 30),  # Box 1
                "federal_income_tax": (100, 250, 200, 30),  # Box 2
                "social_security_wages": (100, 300, 200, 30),  # Box 3
                "social_security_tax": (100, 350, 200, 30),  # Box 4
                "medicare_wages": (100, 400, 200, 30),  # Box 5
                "medicare_tax": (100, 450, 200, 30),  # Box 6
                "social_security_tips": (100, 500, 200, 30),  # Box 7
                "allocated_tips": (100, 550, 200, 30),  # Box 8
                "dependent_care_benefits": (100, 600, 200, 30),  # Box 10
                "nonqualified_plans": (100, 650, 200, 30),  # Box 11
                "statutory_employee": (100, 700, 30, 30),  # Box 13 checkbox
                "retirement_plan": (150, 700, 30, 30),  # Box 13 checkbox
                "third_party_sick_pay": (200, 700, 30, 30),  # Box 13 checkbox
                "state": (100, 750, 200, 30),  # Box 15
                "state_id": (100, 800, 200, 30),  # Box 15
                "state_wages": (100, 850, 200, 30),  # Box 16
                "state_income_tax": (100, 900, 200, 30),  # Box 17
                "local_wages": (100, 950, 200, 30),  # Box 18
                "local_income_tax": (100, 1000, 200, 30),  # Box 19
                "locality_name": (100, 1050, 200, 30),  # Box 20
            }
        elif form_type.lower() == "1099-nec":
            # 1099-NEC box coordinates
            boxes = {
                "payer_name": (100, 100, 200, 30),
                "payer_address": (100, 150, 200, 60),
                "payer_tin": (100, 250, 200, 30),
                "recipient_name": (100, 300, 200, 30),
                "recipient_address": (100, 350, 200, 60),
                "recipient_tin": (100, 450, 200, 30),
                "nonemployee_compensation": (100, 500, 200, 30),
                "federal_income_tax": (100, 550, 200, 30),
                "state": (100, 600, 200, 30),
                "state_income": (100, 650, 200, 30),
                "state_tax_withheld": (100, 700, 200, 30),
                "local_income": (100, 750, 200, 30),
                "local_tax_withheld": (100, 800, 200, 30),
            }
        else:
            raise ValueError(f"Unsupported form type: {form_type}")
        
        # Process each page
        for image in images:
            for box_name, (x, y, width, height) in boxes.items():
                # Crop the image to the box region
                box_image = image.crop((x, y, x + width, y + height))
                
                # Extract text from the box
                text = pytesseract.image_to_string(box_image).strip()
                
                # For checkbox fields, detect if checked
                if box_name in ["statutory_employee", "retirement_plan", "third_party_sick_pay"]:
                    # Convert to boolean based on presence of marks
                    result[box_name] = bool(re.search(r'[Xx✓]', text))
                else:
                    result[box_name] = text
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF box processing failed: {str(e)}")

def process_with_claude(text: str) -> dict:
    """Process OCR text with Claude AI to extract structured data."""
    # Get relevant context from IRS guides
    context = rag_handler.get_relevant_context(text)
    
    prompt = f"""You are a tax document parser with access to IRS tax guides. Given raw OCR output from a scanned W-2 or 1099-NEC form, extract the following fields and return them in strict JSON format. Make sure all property names are enclosed in double quotes.

For checkbox fields (statutory_employee, retirement_plan, third_party_sick_pay), use true/false instead of strings. A checkbox is considered checked (true) if:
- There is an X mark in the box
- There is a checkmark (✓) in the box
- The box is filled in or shaded
- The word "Yes" or "X" appears next to the box
- The box is marked in any way that clearly indicates it should be selected

{context}

Here is a template showing the typical layout of a W-2 form. Use this to help locate and extract the correct information:

W-2 Template:
[Top Section]
Employee's social security number: [Box a]
Employer identification number (EIN): [Box b]
Wages, tips, other compensation: [Box 1]
Federal income tax withheld: [Box 2]
Social security wages: [Box 3]
Social security tax withheld: [Box 4]
Medicare wages and tips: [Box 5]
Medicare tax withheld: [Box 6]
Social security tips: [Box 7]
Allocated tips: [Box 8]
Dependent care benefits: [Box 10]
Nonqualified plans: [Box 11]

[Checkboxes Section]
☐ Statutory employee [Box 13]
☐ Retirement plan [Box 13]
☐ Third-party sick pay [Box 13]

[State Section]
State: [Box 15]
State ID number: [Box 15]
State wages, tips, etc.: [Box 16]
State income tax: [Box 17]
Local wages, tips, etc.: [Box 18]
Local income tax: [Box 19]
Locality name: [Box 20]

For W-2:
{{
  "form_type": "W-2",
  "employee_name": "",
  "employee_address": "",
  "employee_ssn": "",
  "employer_name": "",
  "employer_ein": "",
  "employer_address": "",
  "wages_tips_other_compensation": "",
  "federal_income_tax_withheld": "",
  "social_security_wages": "",
  "social_security_tax_withheld": "",
  "medicare_wages": "",
  "medicare_tax_withheld": "",
  "social_security_tips": "",
  "allocated_tips": "",
  "dependent_care_benefits": "",
  "nonqualified_plans": "",
  "statutory_employee": false,
  "retirement_plan": false,
  "third_party_sick_pay": false,
  "other": "",
  "state": "",
  "state_ID": "",
  "state_wages": "",
  "state_income_tax": "",
  "local_wages": "",
  "local_income_tax": "",
  "locality_name": ""
}}

For 1099-NEC:
{{
  "form_type": "1099-NEC",
  "payer_name": "",
  "payer_address": "",
  "payer_tin": "",
  "recipient_name": "",
  "recipient_address": "",
  "recipient_tin": "",
  "nonemployee_compensation": "",
  "federal_income_tax_withheld": "",
  "state": "",
  "state_income": "",
  "state_tax_withheld": "",
  "local_income": "",
  "local_tax_withheld": ""
}}

If fields are missing or unclear, make a best effort and add a comment noting the issue. Use the IRS tax guide information provided to ensure accuracy.

IMPORTANT: Return ONLY valid JSON. Do not include any additional text or explanations outside the JSON structure.

Here is the OCR text to process:
{text}"""

    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract JSON from Claude's response
        response_text = response.content[0].text
        
        # Clean the response text to ensure it's valid JSON
        # Remove any text before the first { and after the last }
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON found in Claude's response")
        
        json_str = response_text[start_idx:end_idx]
        
        # Try to parse the JSON
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Raw response from Claude: {response_text}")
            print(f"Attempted to parse: {json_str}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse JSON from Claude's response: {str(e)}"
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Claude processing failed: {str(e)}"
        )

@app.post("/parse-tax-form")
async def parse_tax_form(file: UploadFile, form_type: str = "W-2"):
    """Endpoint to process uploaded tax forms with box-based parsing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # Extract text based on file type
        if file.filename.lower().endswith('.pdf'):
            result = extract_text_from_pdf_by_boxes(temp_file_path, form_type)
        else:
            # For non-PDF files, use the existing image processing
            text = extract_text_from_image(temp_file_path)
            result = process_with_claude(text)
        
        return JSONResponse(content=result)
    
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

class TaxGuidanceRequest(BaseModel):
    message: str
    conversation_id: str = None

class Conversation:
    def __init__(self):
        self.messages = []

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self):
        return self.messages

# Store conversations in memory (in production, use a proper database)
conversations = {}

def get_conversation(conversation_id: str) -> Conversation:
    if conversation_id not in conversations:
        conversations[conversation_id] = Conversation()
    return conversations[conversation_id]

@app.post("/tax-guidance")
async def get_tax_guidance(request: TaxGuidanceRequest):
    """Endpoint for interactive tax filing guidance."""
    # Get or create conversation
    conversation = get_conversation(request.conversation_id or "default")
    
    # Add user message to conversation history
    conversation.add_message("user", request.message)
    
    # Get conversation history
    history = conversation.get_messages()
    
    prompt = f"""You are a helpful and expert tax advisor for the 2024 tax year (filing in 2025). 
    The user has asked the following question: "{request.message}"

    Previous conversation context:
    {json.dumps(history[:-1], indent=2) if len(history) > 1 else "No previous context"}

    Your job is to provide **comprehensive, actionable, and accurate** tax advice based on:
    - Current IRS guidelines (as of 2024)
    - Filing deadlines for 2025 (April 15 and October 15 for extensions)
    - Standard deductions, credits, and important tax considerations
    - Recent tax law changes and updates

    When structuring your response:
    1. Start with a clear, direct answer to the user's question
    2. Follow with detailed explanations and relevant examples
    3. Include specific numbers, percentages, and thresholds when applicable
    4. Use clear formatting:
       - <h3> for main sections
       - <ul> and <li> for lists and steps
       - <p> for paragraphs
       - <strong> for critical information (deadlines, limits, requirements)
    5. If the question requires multiple considerations, break down the answer into clear sections
    6. Include practical next steps or action items when relevant

    IMPORTANT:
    - Provide specific, actionable advice based on current tax law
    - Use real numbers and thresholds from 2024 tax year
    - Include relevant tax forms and schedules when applicable
    - Explain complex concepts in simple terms
    - If a situation is complex, break it down into manageable steps
    - Maintain context from previous messages when relevant
    - Focus on providing clear guidance rather than general information

    Examples of topics you should be able to address:
    - Tax planning strategies and optimization
    - Retirement account contributions and limits
    - Investment income and capital gains
    - Business deductions and expenses
    - Tax credits and deductions
    - Filing status and dependents
    - Estimated tax payments
    - Tax implications of major life events
    - State and local tax considerations

    Do not hallucinate new credits or deductions. Base all advice on known U.S. tax law as of 2024.
    """

    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Add assistant's response to conversation history
        response_text = response.content[0].text
        
        # Check if response ends with incomplete sentence
        if response_text.strip().endswith(('.', '!', '?')):
            # Response is complete
            conversation.add_message("assistant", response_text)
        else:
            # Response is incomplete, add ellipsis
            conversation.add_message("assistant", response_text + "...")
        
        return {
            "response": response_text,
            "conversation_id": request.conversation_id or "default"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tax guidance generation failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 