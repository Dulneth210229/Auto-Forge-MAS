# Software Requirements Specification - Login Feature

## 1. Introduction
Project: E-commerce Platform
Feature: User Login
Stack: MERN (MongoDB, Express, React, Node.js)
Version: 1.0

## 2. Business Goal
Allow registered users to securely authenticate using email and password.
After successful login, the user receives a JWT token.

## 3. Functional Requirements
- FR-001: User can submit email and password on the login form
- FR-002: System validates that both fields are non-empty
- FR-003: System verifies email exists in the database
- FR-004: System compares submitted password with bcrypt hash
- FR-005: On success, system returns a signed JWT access token
- FR-006: On failure, system returns a clear error message
- FR-007: JWT token expires after 7 days

## 4. Non-Functional Requirements
- Response time under 500ms
- Passwords never stored in plain text
- All endpoints return JSON

## 5. API Expectations
- POST /api/auth/login
  Body: { email, password }
  Response: { token, user: { id, email, role } }

## 6. Data Requirements
- email (string, unique, indexed)
- password (string, bcrypt hashed)
- role (enum: customer or admin)