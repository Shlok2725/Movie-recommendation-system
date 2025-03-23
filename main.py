from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import requests

# TMDB API Configuration
TMDB_API_KEY = "ee091c3f115057190dea4e57dcd6f55b"  # Replace with your actual API key
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# FastAPI Instance
app = FastAPI()

# Template Configuration
templates = Jinja2Templates(directory="templates")

# MySQL Database Configuration
DATABASE_URL = "mysql+pymysql://root:root@localhost/movies_db"
engine = create_engine(DATABASE_URL, echo=True)

# ORM Session and Base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# Create Tables in MySQL
Base.metadata.create_all(bind=engine)

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Fetch Popular Movies from TMDB
@app.get("/movies/popular", response_class=HTMLResponse)
async def get_popular_movies(request: Request):
    url = f"{TMDB_BASE_URL}/movie/popular?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch movies")
    
    movies = response.json().get("results", [])
    return templates.TemplateResponse("ui.html", {"request": request, "movies": {"Popular Movies": movies}})

# Search Movies by Name
@app.get("/search", response_class=HTMLResponse)
async def search_movies(request: Request, query: str):
    search_url = f"{TMDB_BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={query}"
    response = requests.get(search_url)

    if response.status_code != 200 or "results" not in response.json():
        return templates.TemplateResponse("ui.html", {"request": request, "movies": {}, "error": "Movie not found."})
    
    movies = response.json().get("results", [])
    return templates.TemplateResponse("ui.html", {"request": request, "movies": {"Search Results": movies}})

# Movie Details Page (Fetch Movie Info)
@app.get("/movie/{movie_id}", response_class=HTMLResponse)
async def movie_details(request: Request, movie_id: int):
    movie_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,reviews"
    response = requests.get(movie_url)

    if response.status_code != 200:
        return templates.TemplateResponse("movie_details.html", {"request": request, "error": "Movie Not Found."})
    
    movie_data = response.json()
    movie_details = {
        "title": movie_data.get("title", "Unknown"),
        "overview": movie_data.get("overview", "No description available."),
        "release_date": movie_data.get("release_date", "N/A"),
        "genres": [genre["name"] for genre in movie_data.get("genres", [])],
        "poster_path": movie_data.get("poster_path", ""),
        "cast": [cast["name"] for cast in movie_data.get("credits", {}).get("cast", [])[:5]],
        "reviews": [review["content"] for review in movie_data.get("reviews", {}).get("results", [])[:3]],
    }

    return templates.TemplateResponse("movie_details.html", {"request": request, "movie": movie_details})

# Root Route (Redirect to Popular Movies)
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/movies/popular")
