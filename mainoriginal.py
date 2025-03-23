from fastapi import FastAPI, HTTPException, Depends, Form, Request 
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
import requests

# TMDB API Configuration
TMDB_API_KEY = "ee091c3f115057190dea4e57dcd6f55b"  # Replace with your actual API key
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# FastAPI Instance
app = FastAPI()

# Template Configuration
templates = Jinja2Templates(directory="templates")

# Password Hashing Configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MySQL Database Configuration
DATABASE_URL = "mysql+pymysql://root:root@localhost/movies_db"
engine = create_engine(DATABASE_URL, echo=True)

# ORM Session and Base
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define User Table
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))

# Create Tables in MySQL
Base.metadata.create_all(bind=engine)

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API: Fetch Popular Movies from TMDB
@app.get("/movies/popular")
def get_popular_movies():
    url = f"{TMDB_BASE_URL}/movie/popular?api_key={TMDB_API_KEY}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch movies")
    
    return response.json()

# Login Route
@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Login Authentication
@app.post("/login")
async def authenticate_user(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "Shlok" and password == "1234":
        return RedirectResponse(url="/recommendations", status_code=303)
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

# Movie Recommendation Page
@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations(request: Request):
    response = requests.get(f"{TMDB_BASE_URL}/movie/popular?api_key={TMDB_API_KEY}")
    movies = response.json().get('results', [])
    
    return templates.TemplateResponse("ui.html", {"request": request, "movies": movies})

# New Route for Personalized Movie Recommendations
@app.post("/recommend", response_class=HTMLResponse)
async def recommend_movies(request: Request, movie_name: str = Form(...)):
    search_url = f"{TMDB_BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    search_response = requests.get(search_url).json()
    
    if not search_response.get("results"):
        return templates.TemplateResponse("ui.html", {"request": request, "movies": [], "error": "Movie not found."})

    movie = search_response["results"][0]
    movie_id = movie["id"]
    movie_genres = movie.get("genre_ids", [])  # Fixed genre extraction

    recommend_url = f"{TMDB_BASE_URL}/movie/{movie_id}/recommendations?api_key={TMDB_API_KEY}"
    similar_url = f"{TMDB_BASE_URL}/movie/{movie_id}/similar?api_key={TMDB_API_KEY}"

    recommend_response = requests.get(recommend_url)
    if recommend_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch recommendations")
    recommend_response = recommend_response.json().get("results", [])
    
    similar_response = requests.get(similar_url).json().get("results", [])

    genre_movies = []
    if movie_genres:
        genre_url = f"{TMDB_BASE_URL}/discover/movie?api_key={TMDB_API_KEY}&with_genres={','.join(map(str, movie_genres))}&sort_by=popularity.asc"
        genre_movies = requests.get(genre_url).json().get("results", [])

    all_recommendations = {m["id"]: m for m in (recommend_response + similar_response + genre_movies)}.values()
    
    return templates.TemplateResponse("ui.html", {"request": request, "movies": list(all_recommendations)})

# Movie Details Page
@app.get("/movie/{movie_id}", response_class=HTMLResponse)
async def movie_details(request: Request, movie_id: int):
    movie_url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,reviews"
    movie_response = requests.get(movie_url).json()
    
    if "status_code" in movie_response:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    movie = {
        "title": movie_response["title"],
        "poster_path": movie_response["poster_path"],
        "release_date": movie_response["release_date"],
        "genres": [genre["name"] for genre in movie_response.get("genres", [])],
        "cast": [cast["name"] for cast in movie_response.get("credits", {}).get("cast", [])[:5]],
        "overview": movie_response["overview"],
        "reviews": [review["content"] for review in movie_response.get("reviews", {}).get("results", [])]
    }
    
    return templates.TemplateResponse("movie_details.html", {"request": request, "movie": movie})

# Root Route
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login")
