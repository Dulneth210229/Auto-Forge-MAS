# Software Design Specification - Login Feature

## Architecture
Style: Modular (Route -> Controller -> Service -> Repository -> Model)
Stack: MERN

## File Structure
backend/
  config/db.js
  models/User.js
  repositories/user.repository.js
  services/auth.service.js
  controllers/auth.controller.js
  routes/auth.routes.js
  middleware/validate.js
  utils/jwt.js
  app.js
  server.js

## Environment Variables
- MONGO_URI: MongoDB connection string
- JWT_SECRET: Secret key for signing JWT tokens
- JWT_EXPIRES_IN: Token expiry duration (e.g. 7d)
- PORT: Express server port (default 5000)

## API Design
POST /api/auth/login
  Request:  { email, password }
  Response 200: { token, user: { id, email, role } }
  Response 400: { error: "Email and password are required" }
  Response 401: { error: "Invalid email or password" }

## Data Model
User:
  _id: ObjectId
  email: String (unique, required, lowercase)
  passwordHash: String (required, select: false)
  role: String (enum: customer|admin, default: customer)
  createdAt, updatedAt: Date

## Security
- bcrypt.compare() in AuthService
- JWT signed with HS256
- passwordHash excluded by default (select: false)
- Input validated in middleware

## Run Commands
- npm install
- node server.js