# Start the front end
cd frontend
npm run dev

# Start the backend
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8997