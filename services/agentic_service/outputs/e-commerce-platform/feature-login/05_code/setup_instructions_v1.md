# Setup

1. Clone the repository.
2. Install dependencies: `npm install`.
3. Create a `.env` file and add the following environment variables:
   - MONGO_URI=your-mongodb-connection-string
   - JWT_SECRET=your-jwt-secret-key
   - JWT_EXPIRES_IN=7d
   - PORT=5000
4. Start the server: `node server.js`.