# Enhanced SRS - Login Feature

## Domain Analysis

### Entities
- User: id, email, passwordHash, role, createdAt, updatedAt

### Business Rules
1. Email must be unique across all users
2. Password hashed with bcrypt (salt rounds >= 10)
3. JWT token contains: userId, email, role, iat, exp
4. Token expiry: 7 days
5. Login failure message is generic to prevent oracle attacks

### Domain Services
- AuthService: validateCredentials(email, password), generateToken(user)
- UserRepository: MongoDB data access

### Error Cases
- Empty fields: 400 "Email and password are required"
- Email not found: 401 "Invalid email or password"
- Wrong password: 401 "Invalid email or password"
- Server error: 500 "Internal server error"

### Constraints
- Never expose passwordHash in any API response
- Use env vars: MONGO_URI, JWT_SECRET, JWT_EXPIRES_IN
- Bcrypt compare in service layer only