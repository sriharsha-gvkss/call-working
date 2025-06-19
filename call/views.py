from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from twilio.twiml.voice_response import VoiceResponse, Record, Say, Gather
from twilio.rest import Client
from django.conf import settings
from urllib.parse import quote
from .models import Recording, CallResponse
import re
from django.views.decorators.http import require_http_methods
from datetime import datetime
import os
from dotenv import load_dotenv
from django.utils import timezone
import pandas as pd
import logging
import time
import json
from io import BytesIO
from django.contrib import messages

logger = logging.getLogger(__name__)

# Load environment variables first
load_dotenv()

# Initialize Twilio client with environment variables
client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Public URL for webhooks - Now using settings.PUBLIC_URL instead of hardcoded value

def format_phone_number(phone_number):
    """Format phone number to E.164 format"""
    # Remove any non-digit characters
    phone_number = ''.join(filter(str.isdigit, phone_number))
    
    # If number starts with 91, keep it as is
    if phone_number.startswith('91'):
        return f"+{phone_number}"
    
    # If number is 10 digits, add 91
    if len(phone_number) == 10:
        return f"+91{phone_number}"
    
    return phone_number

# Make a call to client
@csrf_exempt
@require_http_methods(["POST"])
def make_call(request):
    try:
        phone_number = request.POST.get('phone_number')
        if not phone_number:
            messages.error(request, "Phone number is required")
            return redirect('dashboard')

        # Format phone number for India
        if not phone_number.startswith('+'):
            if phone_number.startswith('0'):
                phone_number = '+91' + phone_number[1:]
            else:
                phone_number = '+91' + phone_number

        # Create Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Create webhook URL using settings
        webhook_url = f"{settings.PUBLIC_URL}/answer/"
        
        # Make the call
        call = client.calls.create(
            to=phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=webhook_url,
            record=True
        )
        
        # Create initial call response record
        CallResponse.objects.create(
            phone_number=phone_number,
            call_sid=call.sid,
            call_status=call.status,
            question="Call initiated"
        )
        
        logger.info(f"Call initiated to {phone_number} with SID: {call.sid}")
        messages.success(request, f"Call successfully initiated to {phone_number}")
        return redirect('dashboard')
        
    except Exception as e:
        logger.error(f"Error making call: {str(e)}")
        messages.error(request, f"Error making call: {str(e)}")
        return redirect('dashboard')

# Answer call with questions
@csrf_exempt
@require_http_methods(["POST"])
def answer(request):
    """Handle incoming call and start the interview"""
    try:
        # Get the call SID from the request
        call_sid = request.POST.get('CallSid')
        if not call_sid:
            logger.error("No CallSid provided in request")
            return HttpResponse('No CallSid provided', status=400)

        # Get the phone number from the request
        phone_number = request.POST.get('To', '')
        logger.info(f"Received call from {phone_number} with SID: {call_sid}")
        
        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Get call details
        call = client.calls(call_sid).fetch()
        logger.info(f"Call details retrieved: {call.status}")
        
        # Create initial call response record
        try:
            response = CallResponse.objects.create(
                phone_number=phone_number,
                call_sid=call_sid,
                question="Call initiated",
                call_status='in-progress'
            )
            logger.info(f"Created initial CallResponse record with ID: {response.id}")
        except Exception as db_error:
            logger.error(f"Database error creating CallResponse: {str(db_error)}")
            # Continue even if database fails
        
        # Create TwiML response - redirect to voice with q=0 to start
        resp = VoiceResponse()
        resp.redirect(f"{settings.PUBLIC_URL}/voice?q=0&name=there")
        
        logger.info(f"Redirected call {call_sid} to voice interview")
        return HttpResponse(str(resp), content_type="text/xml")
        
    except Exception as e:
        logger.error(f"Error in answer view: {str(e)}")
        resp = VoiceResponse()
        resp.say("We're sorry, but there was an error processing your call. Please try again later.", voice='Polly.Amy')
        resp.hangup()
        return HttpResponse(str(resp), content_type="text/xml")

def fetch_transcript(recording_sid):
    """Fetch transcript for a recording using Twilio's API"""
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Get the recording
        recording = client.recordings(recording_sid).fetch()
        
        # Get the transcript
        transcript = client.recordings(recording_sid).transcriptions.list()
        
        if transcript:
            return transcript[0].transcription_text
        return None
    except Exception as e:
        logger.error(f"Error fetching transcript: {str(e)}")
        return None

# Handle recorded answer
@csrf_exempt
@require_http_methods(["POST"])
def recording_status(request):
    try:
        # Get the recording SID from the request
        recording_sid = request.POST.get('RecordingSid')
        if not recording_sid:
            return HttpResponse('No RecordingSid provided', status=400)

        # Get the call SID from the request
        call_sid = request.POST.get('CallSid')
        if not call_sid:
            return HttpResponse('No CallSid provided', status=400)

        # Get the response ID from the URL parameters
        response_id = request.GET.get('response_id')
        if not response_id:
            return HttpResponse('No response_id provided', status=400)

        # Initialize Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Get call details
        call = client.calls(call_sid).fetch()
        
        # Get recording details
        recording = client.recordings(recording_sid).fetch()
        
        # Find the CallResponse record
        try:
            response = CallResponse.objects.get(id=response_id)
        except CallResponse.DoesNotExist:
            return HttpResponse('CallResponse not found', status=404)

        # Update the response with recording details
        response.recording_sid = recording_sid
        response.recording_url = recording.uri
        response.recording_duration = recording.duration
        response.call_status = call.status
        response.call_duration = call.duration
        response.save()

        # Try to get the transcript
        try:
            # Get transcript for this recording
            transcript = client.transcriptions.list(recording_sid=recording_sid)
            if transcript:
                response.transcript = transcript[0].transcription_text
                response.transcript_status = 'completed'
            else:
                response.transcript_status = 'pending'
        except Exception as e:
            logger.error(f"Error fetching transcript for recording {recording_sid}: {str(e)}")
            response.transcript_status = 'failed'
        response.save()

        # Create a new VoiceResponse for the next question
        resp = VoiceResponse()
        
        # Define questions
        questions = [
            "Hi, please tell us your full name.",
            "What is your work experience?",
            "What was your previous job role?",
            "Why do you want to join our company?"
        ]
        
        # Count how many question responses we already have for this call (excluding "Call initiated")
        existing_responses = CallResponse.objects.filter(
            call_sid=call_sid,
            question__in=questions
        ).count()
        
        if existing_responses < len(questions):
            # Ask the next question
            resp.say(questions[existing_responses], voice='Polly.Amy')
            resp.record(
                action=f'{settings.PUBLIC_URL}/voice/?response_id={response.id}',
                maxLength='30',
                playBeep=False
            )
        else:
            # All questions have been asked
            resp.say("Thank you for your time. We will review your responses and get back to you soon.", voice='Polly.Amy')
            
            # Update all responses for this call to completed
            CallResponse.objects.filter(call_sid=call_sid).update(call_status='completed')

        return HttpResponse(str(resp))
        
    except Exception as e:
        logger.error(f"Error in recording_status: {str(e)}")
        resp = VoiceResponse()
        resp.say("We're sorry, but there was an error processing your response. Please try again later.", voice='Polly.Amy')
        return HttpResponse(str(resp))

# HR Dashboard
def dashboard(request):
    """Display dashboard with all responses"""
    try:
        logger.info("Dashboard view accessed")
        
        # Test database connection first
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                logger.info("Database connection test successful")
        except Exception as db_conn_error:
            logger.error(f"Database connection failed: {db_conn_error}")
            messages.error(request, f"Database connection error: {db_conn_error}")
            return render(request, 'call/dashboard.html', {
                'responses': [],
                'total_responses': 0,
                'total_recordings': 0,
                'total_transcripts': 0,
                'responses_by_call': {},
                'transcript_stats': {'completed': 0, 'pending': 0, 'failed': 0},
                'error': f"Database connection failed: {db_conn_error}"
            })
        
        # Test if CallResponse table exists
        try:
            with connection.cursor() as cursor:
                if 'sqlite' in settings.DATABASES['default']['ENGINE'].lower():
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_callresponse'")
                else:
                    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename='call_callresponse'")
                
                if not cursor.fetchone():
                    logger.error("call_callresponse table does not exist")
                    messages.error(request, "Database table 'call_callresponse' does not exist. Please run migrations.")
                    return render(request, 'call/dashboard.html', {
                        'responses': [],
                        'total_responses': 0,
                        'total_recordings': 0,
                        'total_transcripts': 0,
                        'responses_by_call': {},
                        'transcript_stats': {'completed': 0, 'pending': 0, 'failed': 0},
                        'error': "Database table 'call_callresponse' does not exist. Please run migrations."
                    })
                else:
                    logger.info("call_callresponse table exists")
        except Exception as table_check_error:
            logger.error(f"Error checking table existence: {table_check_error}")
            messages.error(request, f"Error checking database table: {table_check_error}")
        
        # Get all responses ordered by creation date
        try:
            responses = CallResponse.objects.all().order_by('-created_at')
            logger.info(f"Successfully queried {responses.count()} responses")
        except Exception as query_error:
            logger.error(f"Error querying CallResponse: {query_error}")
            messages.error(request, f"Error loading responses: {query_error}")
            return render(request, 'call/dashboard.html', {
                'responses': [],
                'total_responses': 0,
                'total_recordings': 0,
                'total_transcripts': 0,
                'responses_by_call': {},
                'transcript_stats': {'completed': 0, 'pending': 0, 'failed': 0},
                'error': f"Error loading responses: {query_error}"
            })
        
        # Get transcript statistics
        try:
            transcript_stats = {
                'completed': responses.filter(transcript_status='completed').count(),
                'pending': responses.filter(transcript_status='pending').count(),
                'failed': responses.filter(transcript_status='failed').count()
            }
            logger.info(f"Transcript stats: {transcript_stats}")
        except Exception as stats_error:
            logger.error(f"Error calculating transcript stats: {stats_error}")
            transcript_stats = {'completed': 0, 'pending': 0, 'failed': 0}
        
        # Group responses by phone number and call
        try:
            responses_by_call = {}
            for response in responses:
                if response.call_sid not in responses_by_call:
                    responses_by_call[response.call_sid] = {
                        'phone_number': response.phone_number,
                        'call_status': response.call_status,
                        'call_duration': response.call_duration,
                        'created_at': response.created_at,
                        'responses': []
                    }
                responses_by_call[response.call_sid]['responses'].append({
                    'question': response.question,
                    'recording_url': response.recording_url,
                    'recording_duration': response.recording_duration,
                    'transcript': response.transcript,
                    'transcript_status': response.transcript_status,
                    'created_at': response.created_at
                })
            logger.info(f"Grouped responses into {len(responses_by_call)} calls")
        except Exception as grouping_error:
            logger.error(f"Error grouping responses: {grouping_error}")
            responses_by_call = {}
        
        context = {
            'responses': responses,
            'total_responses': responses.count(),
            'total_recordings': responses.exclude(recording_url__isnull=True).count(),
            'total_transcripts': transcript_stats['completed'],
            'responses_by_call': responses_by_call,
            'transcript_stats': transcript_stats
        }
        
        logger.info("Dashboard context prepared successfully")
        return render(request, 'call/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in dashboard view: {str(e)}")
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return render(request, 'call/dashboard.html', {
            'responses': [],
            'total_responses': 0,
            'total_recordings': 0,
            'total_transcripts': 0,
            'responses_by_call': {},
            'transcript_stats': {'completed': 0, 'pending': 0, 'failed': 0},
            'error': f"Dashboard error: {str(e)}"
        })

def index(request):
    """Render the main page"""
    return render(request, 'call/dashboard.html')

def test_config(request):
    """Test Twilio configuration and webhook URLs"""
    try:
        # Test Twilio credentials
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        account = client.api.accounts(settings.TWILIO_ACCOUNT_SID).fetch()
        
        # Get webhook URLs
        answer_url = f"{settings.PUBLIC_URL}/answer/"
        voice_url = f"{settings.PUBLIC_URL}/voice/"
        
        # Test database connection
        call_count = CallResponse.objects.count()
        
        config_info = {
            'twilio_account_sid': settings.TWILIO_ACCOUNT_SID,
            'twilio_auth_token': 'Configured' if settings.TWILIO_AUTH_TOKEN else 'Not Configured',
            'twilio_phone_number': settings.TWILIO_PHONE_NUMBER,
            'public_url': settings.PUBLIC_URL,
            'answer_webhook': answer_url,
            'voice_webhook': voice_url,
            'database_connection': 'Connected' if call_count is not None else 'Error',
            'total_calls': call_count,
            'debug_mode': settings.DEBUG,
        }
        
        return render(request, 'call/test_config.html', {'config': config_info})
        
    except Exception as e:
        logger.error(f"Error in test_config: {str(e)}")
        return render(request, 'call/test_config.html', {
            'error': str(e),
            'config': {
                'twilio_account_sid': settings.TWILIO_ACCOUNT_SID,
                'twilio_auth_token': 'Configured' if settings.TWILIO_AUTH_TOKEN else 'Not Configured',
                'twilio_phone_number': settings.TWILIO_PHONE_NUMBER,
                'public_url': settings.PUBLIC_URL,
                'debug_mode': settings.DEBUG,
            }
        })

def view_response(request, response_id):
    """Display the details of a specific response"""
    response = CallResponse.objects.get(id=response_id)
    return render(request, 'call/view_response.html', {'response': response})

def export_to_excel(request):
    try:
        # Get all responses
        responses = CallResponse.objects.all().order_by('-created_at')
        
        # Create a DataFrame
        data = []
        for response in responses:
            data.append({
                'Phone Number': response.phone_number,
                'Question': response.question or 'N/A',
                'Response': response.response or 'N/A',
                'Recording URL': response.recording_url or 'N/A',
                'Recording Duration (seconds)': response.recording_duration or 'N/A',
                'Transcript': response.transcript or 'N/A',
                'Transcript Status': response.transcript_status,
                'Call SID': response.call_sid or 'N/A',
                'Call Duration (seconds)': response.call_duration or 'N/A',
                'Call Status': response.call_status or 'N/A',
                'Created At': response.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Updated At': response.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        df = pd.DataFrame(data)
        
        # Create Excel writer
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Call Responses', index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Call Responses']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        # Set up the response
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=call_responses.xlsx'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        messages.error(request, f"Error exporting to Excel: {str(e)}")
        return redirect('dashboard')

@csrf_exempt
def voice(request):
    """Handle voice response and ask questions - Simplified approach"""
    try:
        # Get parameters from request
        q = int(request.GET.get("q", "0"))
        name = request.GET.get("name", "there")
        call_sid = request.POST.get('CallSid')
        phone_number = request.POST.get('From', '')
        
        logger.info(f"Voice route: q={q}, name={name}, call_sid={call_sid}")
        
        # Load questions from JSON file
        try:
            questions_path = os.path.join(settings.BASE_DIR, "questions.json")
            with open(questions_path, "r", encoding="utf-8") as f:
                questions = json.load(f)
        except Exception as e:
            logger.error(f"Error loading questions: {e}")
            # Fallback questions
            questions = [
                "Hi, please tell us your full name.",
                "What is your work experience?",
                "What was your previous job role?",
                "Why do you want to join our company?"
            ]
        
        # Create TwiML response
        response = VoiceResponse()
        
        # Handle initial greeting
        if q == 0:
            response.say(f"Hello {name}, welcome to the HR interview. Let's begin.")
            response.redirect(f"{settings.PUBLIC_URL}/voice?q=1&name={name}")
            return HttpResponse(str(response), content_type="text/xml")
        
        # Handle questions
        if q <= len(questions):
            # Get the current question (q-1 because q starts at 1)
            current_question = questions[q-1]
            
            # Create or update CallResponse record
            try:
                call_response, created = CallResponse.objects.get_or_create(
                    call_sid=call_sid,
                    question=current_question,
                    defaults={
                        'phone_number': phone_number,
                        'call_status': 'in-progress'
                    }
                )
                logger.info(f"CallResponse {'created' if created else 'updated'}: {call_response.id}")
            except Exception as db_error:
                logger.error(f"Database error: {db_error}")
                # Continue even if database fails
            
            # If this is the last question
            if q == len(questions):
                response.say(f"Thanks {name} for your answers. Goodbye!")
                response.hangup()
                
                # Update call status to completed
                if call_sid:
                    CallResponse.objects.filter(call_sid=call_sid).update(call_status='completed')
                    logger.info(f"Call {call_sid} completed")
            else:
                # Ask the current question
                response.say(current_question, voice='Polly.Amy')
                
                # Record the response
                response.record(
                    action=f"{settings.PUBLIC_URL}/voice?q={q+1}&name={name}",
                    maxLength='30',
                    playBeep=False,
                    trim='trim-silence'
                )
                
                logger.info(f"Asked question {q}: {current_question}")
        
        return HttpResponse(str(response), content_type="text/xml")
        
    except Exception as e:
        logger.error(f"Error in voice view: {str(e)}")
        response = VoiceResponse()
        response.say("We're sorry, but there was an error processing your call. Please try again later.", voice='Polly.Amy')
        response.hangup()
        return HttpResponse(str(response), content_type="text/xml")

@csrf_exempt
def transcription_webhook(request):
    """Handle transcription webhook from Twilio"""
    if request.method == "POST":
        try:
            # Get transcription data from request
            transcript_text = request.POST.get('TranscriptionText')
            recording_url = request.POST.get('RecordingUrl')
            call_sid = request.POST.get('CallSid')
            recording_sid = request.POST.get('RecordingSid')
            
            logger.info(f"Received transcription for CallSID: {call_sid}")
            logger.info(f"Transcript: {transcript_text}")
            logger.info(f"Recording URL: {recording_url}")
            
            # Find or create CallResponse
            response, created = CallResponse.objects.get_or_create(
                recording_sid=recording_sid,
                defaults={
                    'phone_number': call_sid,  # Using call_sid temporarily
                    'question': 'Auto-transcribed response',
                    'recording_url': recording_url,
                    'transcript': transcript_text,
                    'transcript_status': 'completed'
                }
            )
            
            if not created:
                # Update existing response
                response.transcript = transcript_text
                response.transcript_status = 'completed'
                response.save()
            
            return HttpResponse("Transcription received", status=200)
            
        except Exception as e:
            logger.error(f"Error in transcription webhook: {str(e)}")
            return HttpResponse(f"Error processing transcription: {str(e)}", status=500)
            
    return HttpResponse("Invalid request method", status=400)