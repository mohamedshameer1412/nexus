import logging
import json
import re
from io import BytesIO
from pypdf import PdfReader
from django.conf import settings
from utils.gemini_service import get_gemini_service

logger = logging.getLogger(__name__)

def clean_json_text(text):
    """
    Clean the AI response to extract valid JSON
    """
    if not text:
        return ""
        
    # Find the start and end of the JSON array
    try:
        start_idx = text.find('[')
        end_idx = text.rfind(']') + 1
        
        if start_idx == -1 or end_idx == 0:
            # Maybe it returned a single object instead of array
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                text = f"[{text[start_idx:end_idx]}]"
                return text
            return text

        json_str = text[start_idx:end_idx]
        return json_str
    except Exception:
        return text

def parse_pdf_questions(pdf_file, use_ai=True):
    """
    Extract text from PDF and parse into question objects
    
    Args:
        pdf_file: PDF file object
        use_ai: boolean, whether to use Gemini AI for parsing
        
    Returns:
        dict: {
            'total_questions': int,
            'questions': list of dicts,
            'extracted_text': str,
            'requires_manual_review': bool
        }
    """
    try:
        # Read PDF content
        reader = PdfReader(pdf_file)
        full_text = ""
        
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                full_text += extracted + "\n\n"
            
        if not full_text.strip():
            return {
                'requires_manual_review': True,
                'error': 'No text could be extracted from this PDF. It might be scanned or image-based.',
                'questions': [],
                'total_questions': 0
            }
            
        if not use_ai:
            # Just return text if no AI requested
            return {
                'total_questions': 0,
                'questions': [],
                'extracted_text': full_text,
                'requires_manual_review': True
            }

        # Use unified Gemini service to parse the questions
        gemini = get_gemini_service()
        
        prompt = """
        Analyze the following text extracted from a quiz PDF and extract ALL questions (Multiple Choice, Short Answer, and Essay).
        
        CRITICAL INSTRUCTION: Return the output as a JSON ARRAY of objects. Do not return a single object. Extract ALL questions found in the text.
        
        For each question, the JSON object must have:
        - "question_text": The full question.
        - "question_type": "mcq", "short_answer", or "essay".
        - "options": An array of strings ["Option A", "Option B"...] (Only for MCQ).
        - "correct_answer": The correct option letter (A, B, C, D) for MCQ, or the text answer for others.
        - "explanation": A brief explanation of why the answer is correct (generate one if not in text).
        
        Text to analyze:
        """
        
        # Split text into chunks if too long (Gemini 1.5 Flash has a large context, but let's be safe)
        text_chunk = full_text[:30000]
        
        # Use fallback-enabled API call
        response_text = gemini.call_api_with_fallback(prompt + text_chunk, use_cache=False)
        
        # PRIMARY FALLBACK: If AI fails (returns None), use Regex Parser
        # Try to parse AI response
        if response_text:
            json_text = clean_json_text(response_text)
            try:
                questions = json.loads(json_text)
                
                # NORMALIZE: Ensure the keys match what frontend expects
                questions = normalize_questions(questions)
                
                return {
                    'total_questions': len(questions),
                    'questions': questions,
                    'extracted_text': full_text,
                    'requires_manual_review': False,
                    'source': 'ai_generated'
                }
            except json.JSONDecodeError as e:
                logger.error(f"JSON Decode Error: {e}")
                logger.error(f"Raw AI Response: {response_text}")
                # Fallthrough to Regex below

        # FALLBACK: Regex Parser
        logger.warning("Gemini AI failed / quota exceeded or Invalid JSON. Falling back to Regex.")
        regex_questions = parse_quiz_with_regex(full_text)
        
        # Log to debug file to see what Regex produced
        try:
            with open("debug_last_regex_parse.json", "w", encoding="utf-8") as f:
                json.dump(regex_questions, f, indent=2)
        except: pass

        if regex_questions:
            # Regex should already be normalized by our own code, but good to be safe
            regex_questions = normalize_questions(regex_questions)
            
            return {
                'total_questions': len(regex_questions),
                'questions': regex_questions,
                'extracted_text': full_text,
                'requires_manual_review': False,
                'source': 'regex_fallback'
            }

        return {
            'requires_manual_review': True,
            'error': 'Could not extract any questions. AI failed and Regex found no matches.',
            'extracted_text': full_text,
            'questions': [],
            'total_questions': 0
        }

    except Exception as e:
        logger.error(f"Error parsing PDF: {str(e)}")
        raise e

def normalize_questions(questions_list):
    """
    Standardize the questions list to match the frontend schema.
    Handles AI inconsistencies like 'question' vs 'question_text', 'options' array, etc.
    """
    normalized = []
    if not isinstance(questions_list, list):
        if isinstance(questions_list, dict):
            # If AI returned a single object with "questions" key
            if 'questions' in questions_list and isinstance(questions_list['questions'], list):
                questions_list = questions_list['questions']
            else:
                questions_list = [questions_list]
        else:
            return []

    for q in questions_list:
        new_q = {
            'difficulty_level': 3,
            'explanation': '',
            'required_keywords': []
        }
        
        # 1. Map Question Text
        new_q['question_text'] = q.get('question_text') or q.get('question') or q.get('Question') or "Untitled Question"
        
        # 2. Map Question Type
        raw_type = str(q.get('question_type') or q.get('type') or 'short_answer').lower()
        if 'choice' in raw_type or 'mcq' in raw_type:
            new_q['question_type'] = 'mcq'
        elif 'essay' in raw_type:
            new_q['question_type'] = 'essay'
        else:
            new_q['question_type'] = 'short_answer'
            
        # 3. Handle Options (Array or discrete keys)
        options = q.get('options') or q.get('Options')
        if new_q['question_type'] == 'mcq':
            if isinstance(options, list) and len(options) >= 2:
                # Map array [A, B, C, D] to option_a, option_b...
                labels = ['a', 'b', 'c', 'd']
                for i, opt_text in enumerate(options[:4]):
                     new_q[f'option_{labels[i]}'] = str(opt_text).strip()
            else:
                 # Try discrete keys
                 new_q['option_a'] = q.get('option_a') or q.get('A') or ''
                 new_q['option_b'] = q.get('option_b') or q.get('B') or ''
                 new_q['option_c'] = q.get('option_c') or q.get('C') or ''
                 new_q['option_d'] = q.get('option_d') or q.get('D') or ''
        
        # 4. Map Answer
        ans = q.get('correct_answer') or q.get('answer') or q.get('Answer') or q.get('model_answer')
        
        # Always provide model_answer field just in case
        new_q['model_answer'] = str(ans) if ans else ""
        
        if new_q['question_type'] == 'mcq':
            # Ensure proper single letter A/B/C/D
            clean_ans = str(ans).strip().upper() if ans else 'A'
            # Naive mapping: if the answer matches the text of an option, use the letter
            if len(clean_ans) > 1:
                # Naive check: does the text match one of the options?
                if clean_ans == new_q.get('option_a', '').upper(): clean_ans = 'A'
                elif clean_ans == new_q.get('option_b', '').upper(): clean_ans = 'B'
                elif clean_ans == new_q.get('option_c', '').upper(): clean_ans = 'C'
                elif clean_ans == new_q.get('option_d', '').upper(): clean_ans = 'D'
                else: 
                     # If we can't map it, default to A, but put the text in explanation as a fallback
                     if not new_q['explanation']:
                         new_q['explanation'] = f"Correct Answer: {ans}"
                     clean_ans = 'A' # Fallback
            new_q['correct_answer'] = clean_ans
        else:
            new_q['model_answer'] = str(ans) if ans else "No model answer provided."
            # Clear correct_answer for non-MCQ
            new_q['correct_answer'] = ''
            
        # 5. Explanations - Check multiple possible keys
        new_q['explanation'] = (q.get('explanation') or 
                                q.get('rationale') or 
                                q.get('reason') or 
                                q.get('Explanation') or 
                                "")
        
        normalized.append(new_q)
        
    return normalized

def parse_quiz_with_regex(text):
    """
    Fallback parser using patterns to extract questions without AI.
    Works best with structured files like:
    1. Question text...
    A. Option
    B. Option
    Answer: A
    Explanation: ...
    """
    questions = []
    lines = text.split('\n')
    current_q = None
    
    # Simple state machine
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect Question Start (e.g., "1.", "Q1:", "Question 1:")
        # We also look for lines ending in '?' if they are isolated
        is_new_question = False
        if re.match(r'^(Question\s+\d+|Q\d+|\d+[\.\)])', line, re.IGNORECASE):
            is_new_question = True
        elif line.endswith('?') and (current_q is None or current_q.get('correct_answer') or current_q.get('answer_found')):
             # Heuristic: If we finished the last question (found answer), this might be a new one
             is_new_question = True

        if is_new_question:
            if current_q:
                questions.append(finalize_question(current_q))
            
            # Clean header from text
            q_text = re.sub(r'^(Question\s+\d+|Q\d+|\d+[\.\)])[:\.]?\s*', '', line, flags=re.IGNORECASE).strip()
            
            current_q = {
                'question_text': q_text,
                'options': {},
                'question_type': 'short_answer', # Default, will change if options found
                'difficulty_level': 3
            }
            continue
            
        if current_q:
            # Detect Options (A., a), (A), [A])
            opt_match = re.match(r'^[\(\[]?([A-D])[\)\]\.]\s+(.+)', line, re.IGNORECASE)
            if opt_match:
                current_q['question_type'] = 'mcq'
                label = opt_match.group(1).upper()
                content = opt_match.group(2).strip()
                
                # Map A,B,C,D to option fields
                if label == 'A': current_q['option_a'] = content
                elif label == 'B': current_q['option_b'] = content
                elif label == 'C': current_q['option_c'] = content
                elif label == 'D': current_q['option_d'] = content
                continue
                
            # Detect Answer
            ans_match = re.match(r'^(Answer|Ans|Correct)[:\s-]*([A-D\w\s]+)', line, re.IGNORECASE)
            if ans_match:
                ans_text = ans_match.group(2).strip()
                if len(ans_text) == 1 and ans_text.upper() in ['A', 'B', 'C', 'D']:
                    current_q['correct_answer'] = ans_text.upper()
                else:
                    current_q['model_answer'] = ans_text
                current_q['answer_found'] = True
                continue

            # Detect Explanation
            exp_match = re.match(r'^(Explanation|Rationale)[:\s-]*(.+)', line, re.IGNORECASE)
            if exp_match:
                current_q['explanation'] = exp_match.group(2).strip()
                continue
                
            # Detect Question Type hints
            if "Multiple Choice" in line:
                current_q['question_type'] = 'mcq'
            elif "Essay" in line:
                current_q['question_type'] = 'essay'
            elif "Short Answer" in line:
                current_q['question_type'] = 'short_answer'
                
            # If no keyword matched, append to question text (multi-line question)
            # BUT only if we haven't started seeing options/answers yet
            if 'options' not in current_q or not current_q['options']:
                 if 'option_a' not in current_q and 'answer_found' not in current_q:
                    # Append to question text if it's not just a type label
                    clean_line = line.strip()
                    if clean_line:
                        current_q['question_text'] += " " + clean_line

    if current_q:
        questions.append(finalize_question(current_q))

    return questions

def finalize_question(q):
    """Clean up question object before returning"""
    # Clean up question text prefixes
    text = q.get('question_text', '').strip()
    # Remove common prefixes like "Multiple Choice " or "Short Answer " if they appear at start
    text = re.sub(r'^(Multiple Choice|Short Answer|Essay)[:\s-]*', '', text, flags=re.IGNORECASE).strip()
    q['question_text'] = text

    # Ensure mandatory fields
    if q['question_type'] == 'mcq':
        if not q.get('correct_answer'):
            q['correct_answer'] = 'A' # Default
    
    # Remove temporary flags
    if 'answer_found' in q: del q['answer_found']
    if 'options' in q: del q['options']
    
    return q
