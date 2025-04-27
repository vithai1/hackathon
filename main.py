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
from tax_export import tax_export
from datetime import datetime

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
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    height: 100vh;
                    display: flex;
                    flex-direction: column;
                }

                .main-content {
                    display: flex;
                    gap: 20px;
                    flex: 1;
                    overflow: hidden;
                }

                .forms-section {
                    width: 40%;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }

                .chat-section {
                    width: 60%;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
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

                .upload-section {
                    padding: 20px;
                    background-color: var(--secondary-bg);
                    border-radius: 8px;
                    margin-bottom: 20px;
                }

                .upload-form {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }

                .file-input-container {
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }

                .file-input {
                    flex: 1;
                }

                .file-input::-webkit-file-upload-button {
                    visibility: hidden;
                }

                .file-input::before {
                    content: 'Select files';
                    display: inline-block;
                    background: var(--accent-color);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-right: 10px;
                }

                .file-input:hover::before {
                    opacity: 0.9;
                }

                .file-list {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    margin-bottom: 10px;
                }

                .file-item {
                    display: flex;
                    gap: 10px;
                    align-items: center;
                    padding: 8px;
                    background-color: var(--primary-bg);
                    border-radius: 4px;
                }

                .file-name {
                    flex: 1;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                .form-type-select {
                    padding: 8px;
                    border: 1px solid var(--border-color);
                    border-radius: 4px;
                    min-width: 120px;
                }

                .remove-file {
                    background: none;
                    border: none;
                    color: var(--text-secondary);
                    cursor: pointer;
                    padding: 4px 8px;
                    border-radius: 4px;
                }

                .remove-file:hover {
                    background-color: rgba(0, 0, 0, 0.1);
                }

                .upload-button {
                    background-color: var(--accent-color);
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                    align-self: flex-end;
                }

                .upload-button:hover {
                    opacity: 0.9;
                }

                .parsed-forms {
                    flex: 1;
                    overflow-y: auto;
                    padding-right: 10px;
                }

                .form-card {
                    background-color: var(--secondary-bg);
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                }

                .form-card h3 {
                    color: var(--accent-color);
                    margin-top: 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .form-card .delete-form {
                    background: none;
                    border: none;
                    color: var(--text-secondary);
                    cursor: pointer;
                    padding: 4px 8px;
                    border-radius: 4px;
                }

                .form-card .delete-form:hover {
                    background-color: rgba(0, 0, 0, 0.1);
                }

                .form-data {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                    gap: 10px;
                }

                .data-item {
                    background-color: var(--primary-bg);
                    padding: 8px;
                    border-radius: 4px;
                }

                .data-label {
                    font-size: 12px;
                    color: var(--text-secondary);
                }

                .data-value {
                    font-weight: 500;
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
                    .main-content {
                        flex-direction: column;
                    }

                    .forms-section, .chat-section {
                        width: 100%;
                    }

                    .parsed-forms {
                        max-height: 300px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Tax Assistant</h1>
                </div>
                
                <div class="main-content">
                    <div class="forms-section">
                        <div class="upload-section">
                            <form class="upload-form" id="upload-form">
                                <div class="file-input-container">
                                    <input type="file" class="file-input" id="file-input" accept=".pdf,.jpg,.jpeg,.png" multiple>
                                </div>
                                <div class="file-list" id="file-list">
                                    <!-- File items will be added here -->
                                </div>
                                <button type="submit" class="upload-button">Upload All</button>
                            </form>
                        </div>

                        <div class="parsed-forms" id="parsed-forms">
                            <!-- Parsed forms will be displayed here -->
                        </div>
                    </div>
                    
                    <div class="chat-section">
                        <div class="chat-container" id="chat-container">
                            <div class="message bot-message">
                                <h3>Welcome!</h3>
                                <p>I'm your tax assistant. I can help you understand your tax filing requirements and guide you through the process.</p>
                                <p>You can:</p>
                                <ul>
                                    <li>Upload your tax forms (W-2, 1099-NEC)</li>
                                    <li>Ask questions about your specific tax situation</li>
                                    <li>Get personalized advice based on your forms</li>
                                    <li>Learn about tax deductions and credits</li>
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
                </div>
            </div>

            <script>
                let conversationId = "default";
                let parsedForms = {};
                let filesToUpload = [];

                function autoResize(textarea) {
                    textarea.style.height = 'auto';
                    textarea.style.height = textarea.scrollHeight + 'px';
                }

                function createFormTypeSelect() {
                    const select = document.createElement('select');
                    select.className = 'form-type-select';
                    select.innerHTML = `
                        <option value="W-2">W-2</option>
                        <option value="1099-NEC">1099-NEC</option>
                        <option value="1099-INT">1099-INT</option>
                        <option value="1099-DIV">1099-DIV</option>
                        <option value="1099-B">1099-B</option>
                        <option value="1099-R">1099-R</option>
                        <option value="1099-MISC">1099-MISC</option>
                    `;
                    return select;
                }

                function addFileToList(file) {
                    const fileList = document.getElementById('file-list');
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    
                    const fileName = document.createElement('div');
                    fileName.className = 'file-name';
                    fileName.textContent = file.name;
                    
                    const formTypeSelect = createFormTypeSelect();
                    
                    const removeButton = document.createElement('button');
                    removeButton.className = 'remove-file';
                    removeButton.textContent = '×';
                    removeButton.onclick = () => {
                        fileItem.remove();
                        filesToUpload = filesToUpload.filter(f => f !== file);
                    };
                    
                    fileItem.appendChild(fileName);
                    fileItem.appendChild(formTypeSelect);
                    fileItem.appendChild(removeButton);
                    
                    fileList.appendChild(fileItem);
                    filesToUpload.push(file);
                }

                document.getElementById('file-input').addEventListener('change', function(e) {
                    const fileList = document.getElementById('file-list');
                    fileList.innerHTML = ''; // Clear existing files
                    filesToUpload = []; // Reset files array
                    
                    Array.from(e.target.files).forEach(file => {
                        addFileToList(file);
                    });
                });

                async function uploadForm(event) {
                    event.preventDefault();
                    
                    if (filesToUpload.length === 0) {
                        alert('Please select at least one file');
                        return;
                    }

                    for (const file of filesToUpload) {
                        const fileItem = Array.from(document.querySelectorAll('.file-item')).find(
                            item => item.querySelector('.file-name').textContent === file.name
                        );
                        const formType = fileItem.querySelector('.form-type-select').value;
                        
                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('form_type', formType);
                        formData.append('conversation_id', conversationId);

                        try {
                            const response = await fetch('/parse-tax-form', {
                                method: 'POST',
                                body: formData
                            });

                            const data = await response.json();
                            
                            // Store form data
                            const formId = Date.now() + Math.random().toString(36).substr(2, 9);
                            parsedForms[formId] = { type: formType, data: data };
                            
                            // Display parsed form data
                            displayParsedForm(formId, formType, data);
                            
                        } catch (error) {
                            console.error('Error:', error);
                            alert(`Error uploading file ${file.name}. Please try again.`);
                        }
                    }
                    
                    // Clear file input and list
                    document.getElementById('file-input').value = '';
                    document.getElementById('file-list').innerHTML = '';
                    filesToUpload = [];
                }

                function displayParsedForm(formId, formType, data) {
                    const parsedForms = document.getElementById('parsed-forms');
                    const formCard = document.createElement('div');
                    formCard.className = 'form-card';
                    formCard.id = `form-${formId}`;
                    
                    let html = `
                        <h3>
                            ${formType}
                            <button class="delete-form" onclick="deleteForm('${formId}')">×</button>
                        </h3>
                        <div class="form-data">
                    `;
                    
                    for (const [key, value] of Object.entries(data)) {
                        html += `
                            <div class="data-item">
                                <div class="data-label">${key.replace(/_/g, ' ').toUpperCase()}</div>
                                <div class="data-value">${value}</div>
                            </div>
                        `;
                    }
                    
                    html += '</div>';
                    formCard.innerHTML = html;
                    parsedForms.appendChild(formCard);
                }

                function deleteForm(formId) {
                    // Remove from DOM
                    const formElement = document.getElementById(`form-${formId}`);
                    if (formElement) {
                        formElement.remove();
                    }
                    
                    // Remove from storage
                    delete parsedForms[formId];
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
                        // Get all parsed forms data
                        const parsedFormsData = {};
                        for (const [formId, formData] of Object.entries(parsedForms)) {
                            parsedFormsData[formId] = formData;
                        }

                        const response = await fetch('/tax-guidance', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ 
                                message: message,
                                conversation_id: conversationId,
                                parsed_forms: parsedFormsData
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

                // Handle form upload
                document.getElementById('upload-form').addEventListener('submit', uploadForm);
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
        elif form_type.lower() == "1099-misc":
            # 1099-MISC box coordinates
            boxes = {
                "payer_name": (100, 100, 200, 30),
                "payer_address": (100, 150, 200, 60),
                "payer_tin": (100, 250, 200, 30),
                "recipient_name": (100, 300, 200, 30),
                "recipient_address": (100, 350, 200, 60),
                "recipient_tin": (100, 450, 200, 30),
                "rents": (100, 500, 200, 30),
                "royalties": (100, 550, 200, 30),
                "other_income": (100, 600, 200, 30),
                "federal_income_tax": (100, 650, 200, 30),
                "fishing_boat_proceeds": (100, 700, 200, 30),
                "medical_health_care_payments": (100, 750, 200, 30),
                "nonemployee_compensation": (100, 800, 200, 30),
                "substitute_payments": (100, 850, 200, 30),
                "crop_insurance_proceeds": (100, 900, 200, 30),
                "state": (100, 950, 200, 30),
                "state_income": (100, 1000, 200, 30),
                "state_tax_withheld": (100, 1050, 200, 30),
            }
        elif form_type.lower() == "1099-int":
            # 1099-INT box coordinates
            boxes = {
                "payer_name": (100, 100, 200, 30),
                "payer_address": (100, 150, 200, 60),
                "payer_tin": (100, 250, 200, 30),
                "recipient_name": (100, 300, 200, 30),
                "recipient_address": (100, 350, 200, 60),
                "recipient_tin": (100, 450, 200, 30),
                "interest_income": (100, 500, 200, 30),
                "early_withdrawal_penalty": (100, 550, 200, 30),
                "federal_income_tax": (100, 600, 200, 30),
                "state": (100, 650, 200, 30),
                "state_income": (100, 700, 200, 30),
                "state_tax_withheld": (100, 750, 200, 30),
            }
        elif form_type.lower() == "1099-div":
            # 1099-DIV box coordinates
            boxes = {
                "payer_name": (100, 100, 200, 30),
                "payer_address": (100, 150, 200, 60),
                "payer_tin": (100, 250, 200, 30),
                "recipient_name": (100, 300, 200, 30),
                "recipient_address": (100, 350, 200, 60),
                "recipient_tin": (100, 450, 200, 30),
                "ordinary_dividends": (100, 500, 200, 30),
                "qualified_dividends": (100, 550, 200, 30),
                "capital_gain_distributions": (100, 600, 200, 30),
                "federal_income_tax": (100, 650, 200, 30),
                "state": (100, 700, 200, 30),
                "state_income": (100, 750, 200, 30),
                "state_tax_withheld": (100, 800, 200, 30),
            }
        elif form_type.lower() == "1099-b":
            # 1099-B box coordinates
            boxes = {
                "payer_name": (100, 100, 200, 30),
                "payer_address": (100, 150, 200, 60),
                "payer_tin": (100, 250, 200, 30),
                "recipient_name": (100, 300, 200, 30),
                "recipient_address": (100, 350, 200, 60),
                "recipient_tin": (100, 450, 200, 30),
                "description": (100, 500, 200, 30),
                "date_acquired": (100, 550, 200, 30),
                "date_sold": (100, 600, 200, 30),
                "proceeds": (100, 650, 200, 30),
                "cost_basis": (100, 700, 200, 30),
                "wash_sale_loss_disallowed": (100, 750, 200, 30),
                "federal_income_tax": (100, 800, 200, 30),
            }
        elif form_type.lower() == "1099-r":
            # 1099-R box coordinates
            boxes = {
                "payer_name": (100, 100, 200, 30),
                "payer_address": (100, 150, 200, 60),
                "payer_tin": (100, 250, 200, 30),
                "recipient_name": (100, 300, 200, 30),
                "recipient_address": (100, 350, 200, 60),
                "recipient_tin": (100, 450, 200, 30),
                "gross_distribution": (100, 500, 200, 30),
                "taxable_amount": (100, 550, 200, 30),
                "federal_income_tax": (100, 600, 200, 30),
                "employee_contributions": (100, 650, 200, 30),
                "state": (100, 700, 200, 30),
                "state_distribution": (100, 750, 200, 30),
                "state_tax_withheld": (100, 800, 200, 30),
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
    
    prompt = f"""You are a tax document parser with access to IRS tax guides. Given raw OCR output from a scanned tax form, extract the following fields and return them in strict JSON format. Make sure all property names are enclosed in double quotes.

For checkbox fields, use true/false instead of strings. A checkbox is considered checked (true) if:
- There is an X mark in the box
- There is a checkmark (✓) in the box
- The box is filled in or shaded
- The word "Yes" or "X" appears next to the box
- The box is marked in any way that clearly indicates it should be selected

{context}

Here are the JSON templates for each form type:

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

For 1099-INT:
{{
  "form_type": "1099-INT",
  "payer_name": "",
  "payer_address": "",
  "payer_tin": "",
  "recipient_name": "",
  "recipient_address": "",
  "recipient_tin": "",
  "interest_income": "",
  "early_withdrawal_penalty": "",
  "federal_income_tax": "",
  "state": "",
  "state_income": "",
  "state_tax_withheld": ""
}}

For 1099-DIV:
{{
  "form_type": "1099-DIV",
  "payer_name": "",
  "payer_address": "",
  "payer_tin": "",
  "recipient_name": "",
  "recipient_address": "",
  "recipient_tin": "",
  "ordinary_dividends": "",
  "qualified_dividends": "",
  "capital_gain_distributions": "",
  "federal_income_tax": "",
  "state": "",
  "state_income": "",
  "state_tax_withheld": ""
}}

For 1099-B:
{{
  "form_type": "1099-B",
  "payer_name": "",
  "payer_address": "",
  "payer_tin": "",
  "recipient_name": "",
  "recipient_address": "",
  "recipient_tin": "",
  "description": "",
  "date_acquired": "",
  "date_sold": "",
  "proceeds": "",
  "cost_basis": "",
  "wash_sale_loss_disallowed": "",
  "federal_income_tax": ""
}}

For 1099-R:
{{
  "form_type": "1099-R",
  "payer_name": "",
  "payer_address": "",
  "payer_tin": "",
  "recipient_name": "",
  "recipient_address": "",
  "recipient_tin": "",
  "gross_distribution": "",
  "taxable_amount": "",
  "federal_income_tax": "",
  "employee_contributions": "",
  "state": "",
  "state_distribution": "",
  "state_tax_withheld": ""
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

class Conversation:
    def __init__(self):
        self.messages = []
        self.parsed_forms = {}  # Store parsed form data by form type

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def add_parsed_form(self, form_type: str, form_data: dict):
        if form_type not in self.parsed_forms:
            self.parsed_forms[form_type] = []
        self.parsed_forms[form_type].append(form_data)

    def get_messages(self):
        return self.messages

    def get_parsed_forms(self):
        return self.parsed_forms

# Store conversations in memory (in production, use a proper database)
conversations = {}

def get_conversation(conversation_id: str) -> Conversation:
    if conversation_id not in conversations:
        conversations[conversation_id] = Conversation()
    return conversations[conversation_id]

@app.post("/parse-tax-form")
async def parse_tax_form(file: UploadFile, form_type: str = "W-2", conversation_id: str = None):
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
        
        # If conversation_id is provided, store the parsed form data
        if conversation_id:
            conversation = get_conversation(conversation_id)
            conversation.add_parsed_form(form_type, result)
        
        return JSONResponse(content=result)
    
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

class TaxGuidanceRequest(BaseModel):
    message: str
    conversation_id: str = None
    parsed_forms: dict = None

@app.post("/tax-guidance")
async def get_tax_guidance(request: TaxGuidanceRequest):
    """Endpoint for interactive tax filing guidance with parsed form context."""
    # Get or create conversation
    conversation = get_conversation(request.conversation_id or "default")
    
    # Add user message to conversation history
    conversation.add_message("user", request.message)
    
    # Get conversation history and parsed forms
    history = conversation.get_messages()
    
    # Format parsed forms for context
    form_context = ""
    if request.parsed_forms:
        form_context = "\nParsed Tax Forms:\n"
        for form_id, form_data in request.parsed_forms.items():
            form_type = form_data.get('type', 'Unknown')
            form_context += f"\n{form_type} Form:\n"
            for key, value in form_data.get('data', {}).items():
                form_context += f"{key}: {value}\n"
    
    prompt = f"""You are a personalized tax advisor for the 2024 tax year (filing in 2025). You have access to the user's specific tax documents and should provide tailored advice based on their actual tax situation.

The user has asked the following question: "{request.message}"

Previous conversation context:
{json.dumps(history[:-1], indent=2) if len(history) > 1 else "No previous context"}

{form_context}

Your role is to provide **comprehensive, personalized, and actionable** tax advice based on:
1. The user's specific tax situation as shown in their uploaded forms
2. Current IRS guidelines (as of 2024)
3. Filing deadlines for 2025 (April 15 and October 15 for extensions)
4. Standard deductions, credits, and important tax considerations
5. Recent tax law changes and updates

When structuring your response:
1. Start with a clear, direct answer to the user's question
2. Reference specific data from their uploaded tax forms when relevant
3. Calculate and show totals based on their actual forms
4. Follow with detailed explanations and relevant examples
5. Include specific numbers, percentages, and thresholds when applicable
6. Use clear formatting:
   - <h3> for main sections
   - <ul> and <li> for lists and steps
   - <p> for paragraphs
   - <strong> for critical information (deadlines, limits, requirements)
7. If the question requires multiple considerations, break down the answer into clear sections
8. Include practical next steps or action items when relevant

IMPORTANT:
- ALWAYS check the parsed forms data first before responding
- If forms are present in the parsed_forms data, reference the specific numbers and data from those forms
- For income-related questions, calculate and show the total based on all uploaded forms
- If no forms are present in the parsed_forms data, then state that you need the forms to provide specific numbers
- Never say you don't have access to the forms if they are present in the parsed_forms data
- Maintain context from previous messages when relevant
- Focus on providing clear, personalized guidance rather than general information
- Use the parsed form data to provide tailored advice specific to their situation

Remember: You are their personal tax advisor. Your advice should be specific to their situation, not generic tax information."""

    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Add assistant's response to conversation history
        conversation.add_message("assistant", response.content[0].text)
        
        return {
            "response": response.content[0].text,
            "conversation_id": request.conversation_id or "default"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tax guidance generation failed: {str(e)}"
        )

@app.post("/export-tax-data")
async def export_tax_data(
    data: dict,
    form_type: str,
    export_format: str = "json",
    output_path: Optional[str] = None
):
    """Export parsed tax data to various formats."""
    try:
        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"export_{form_type}_{timestamp}.{export_format.lower()}"
        
        # Export based on format
        if export_format.lower() == "proseries":
            result_path = tax_export.export_to_proseries(data, form_type, output_path)
        elif export_format.lower() == "lacerte":
            result_path = tax_export.export_to_lacerte(data, form_type, output_path)
        elif export_format.lower() == "json":
            result_path = tax_export.export_to_json(data, output_path)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {export_format}"
            )
        
        return {
            "message": "Export successful",
            "path": result_path,
            "format": export_format
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 