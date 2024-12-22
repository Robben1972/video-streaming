import os
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from dotenv import load_dotenv
from supabase import create_client, Client
import httpx
from datetime import datetime, UTC

load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

templates.env.globals.update(now=lambda: datetime.now(UTC))

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

@app.get('/', response_class=HTMLResponse)
async def home(request: Request):
    videos = supabase.storage.from_(SUPABASE_BUCKET).list()
    return templates.TemplateResponse('home.html', {'request': request, 'videos': videos})

@app.get('/videos/{video_name}')
async def get_video(video_name: str):
    video_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(video_name)
    
    if not video_url:
        return {'error': 'video not found'}
    
    async def video_stream():
        async with httpx.AsyncClient() as client:
            async with client.stream('GET', video_url, headers={'Range': 'bytes=0-'}, timeout=None) as response:
                async for chunck in response.aiter_bytes():
                    yield chunck
    return StreamingResponse(video_stream(), media_type='video/mp4')

                
@app.get('/watch/{video_name}', response_class=HTMLResponse)
async def watch_video(request: Request, video_name: str):
    title = video_name.rsplit('.',1)[0].replace('_', ' ')
    return templates.TemplateResponse('watch.html', {'request': request, 'video_name': video_name, 'title': title})


@app.get('/upload', response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse('upload.html', {'request': request})

@app.post('/upload')
async def upload_video(request: Request, title: str = File(...), video_file: UploadFile = File(...)):
    contents = await video_file.read()
    
    file_extension = video_file.filename.split('.')[-1]
    file_name = f"{title.replace(' ', '_')}.{file_extension}"
    try: 
        res = supabase.storage.from_(SUPABASE_BUCKET).upload(file_name, contents)
        message = 'Uploaded file successfully'
    except Exception as e:
        message = f"Error uploading file: {e}"

        
    return templates.TemplateResponse('upload.html', {'request': request, 'message': message})










