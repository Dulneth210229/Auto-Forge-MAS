"""
Coder Agent Integration Test
=============================
Purpose:
    Test the Coder Agent end-to-end WITHOUT requiring the Domain Agent
    or Architecture Agent to be running.

    This script:
    1. Creates a project  (E-commerce Platform / MERN)
    2. Creates a feature  (Login)
    3. Seeds approved SRS artifact     (simulates Requirement Agent output)
    4. Seeds approved Enhanced SRS     (simulates Domain Agent output)
    5. Seeds approved SDS artifact     (simulates Architecture Agent output)
    6. Calls POST /coder/run           (real Coder Agent execution)
    7. Prints every artifact generated

Run from the agentic_service directory:
    python test_coder_agent.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app
from app.services.in_memory_store import store
from app.services.artifact_service import artifact_service
from app.core.enums import AgentName, ArtifactType, ArtifactFormat, ApprovalStatus

client = TestClient(app)

# -----------------------------------------------------------------------
# SAMPLE ARTIFACT CONTENT
# -----------------------------------------------------------------------

SRS_MARKDOWN = """
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
""".strip()

ENHANCED_SRS_MARKDOWN = """
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
""".strip()

SDS_MARKDOWN = """
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
""".strip()

SDS_JSON = {
    "feature": "Login",
    "stack": "MERN",
    "env_vars": [
        {"name": "MONGO_URI", "description": "MongoDB connection string", "required": True},
        {"name": "JWT_SECRET", "description": "JWT signing secret", "required": True},
        {"name": "JWT_EXPIRES_IN", "description": "Token expiry (e.g. 7d)", "required": True},
        {"name": "PORT", "description": "Server port", "required": False}
    ]
}

# -----------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------

def section(title):
    print()
    print("=" * 65)
    print(f"  {title}")
    print("=" * 65)

def ok(msg):
    print(f"  [OK]  {msg}")

def fail(msg):
    print(f"  [FAIL]  {msg}")
    sys.exit(1)

def info(msg):
    print(f"  [INFO]  {msg}")

# -----------------------------------------------------------------------
# STEP 1: Create Project
# -----------------------------------------------------------------------
section("STEP 1 - Create Project")

r = client.post("/api/v1/projects", json={
    "project_name": "E-commerce Platform",
    "project_type": "E-commerce",
    "target_stack": "MERN",
    "created_by": "test_user"
})
if r.status_code != 200:
    fail(f"Create project failed: {r.status_code} - {r.text}")

project = r.json()
project_id = project["project_id"]
ok(f"Project: {project['project_name']} (id={project_id})")

# -----------------------------------------------------------------------
# STEP 2: Create Feature
# -----------------------------------------------------------------------
section("STEP 2 - Create Feature")

r = client.post(f"/api/v1/projects/{project_id}/features", json={
    "feature_name": "Login",
    "feature_description": "Allow users to authenticate using email and password. Returns JWT token."
})
if r.status_code != 200:
    fail(f"Create feature failed: {r.status_code} - {r.text}")

feature = r.json()
feature_id = feature["feature_id"]
ok(f"Feature: {feature['feature_name']} (id={feature_id})")

# -----------------------------------------------------------------------
# STEP 3: Seed Approved SRS (bypasses Requirement Agent)
# -----------------------------------------------------------------------
section("STEP 3 - Inject Approved SRS  [bypassing Requirement Agent]")

project_dict = store.projects[project_id]
feature_dict = store.features[feature_id]

srs_artifact = artifact_service.save_text_artifact(
    project=project_dict, feature=feature_dict,
    agent_name=AgentName.REQUIREMENT,
    artifact_type=ArtifactType.SRS,
    artifact_format=ArtifactFormat.MARKDOWN,
    filename="SRS_v{version}.md",
    content=SRS_MARKDOWN,
)
store.artifacts[srs_artifact.artifact_id]["approval_status"] = ApprovalStatus.APPROVED
ok(f"SRS saved + approved: {srs_artifact.artifact_id}")
info(f"File: {srs_artifact.file_path}")

# -----------------------------------------------------------------------
# STEP 4: Seed Approved Enhanced SRS (bypasses Domain Agent)
# -----------------------------------------------------------------------
section("STEP 4 - Inject Approved Enhanced SRS  [bypassing Domain Agent]")

esrs_artifact = artifact_service.save_text_artifact(
    project=project_dict, feature=feature_dict,
    agent_name=AgentName.DOMAIN,
    artifact_type=ArtifactType.ENHANCED_SRS,
    artifact_format=ArtifactFormat.MARKDOWN,
    filename="enhanced_SRS_v{version}.md",
    content=ENHANCED_SRS_MARKDOWN,
)
store.artifacts[esrs_artifact.artifact_id]["approval_status"] = ApprovalStatus.APPROVED
ok(f"Enhanced SRS saved + approved: {esrs_artifact.artifact_id}")
info(f"File: {esrs_artifact.file_path}")

# -----------------------------------------------------------------------
# STEP 5: Seed Approved SDS (bypasses Architecture Agent)
# -----------------------------------------------------------------------
section("STEP 5 - Inject Approved SDS  [bypassing Architecture Agent]")

sds_md_artifact = artifact_service.save_text_artifact(
    project=project_dict, feature=feature_dict,
    agent_name=AgentName.ARCHITECTURE,
    artifact_type=ArtifactType.SDS,
    artifact_format=ArtifactFormat.MARKDOWN,
    filename="SDS_v{version}.md",
    content=SDS_MARKDOWN,
)
store.artifacts[sds_md_artifact.artifact_id]["approval_status"] = ApprovalStatus.APPROVED

sds_json_artifact = artifact_service.save_json_artifact(
    project=project_dict, feature=feature_dict,
    agent_name=AgentName.ARCHITECTURE,
    artifact_type=ArtifactType.SDS,
    filename="SDS_v{version}.json",
    data=SDS_JSON,
    version_override=sds_md_artifact.version,
)
store.artifacts[sds_json_artifact.artifact_id]["approval_status"] = ApprovalStatus.APPROVED
ok(f"SDS Markdown saved + approved: {sds_md_artifact.artifact_id}")
ok(f"SDS JSON saved + approved:     {sds_json_artifact.artifact_id}")
info(f"SDS Markdown: {sds_md_artifact.file_path}")
info(f"SDS JSON:     {sds_json_artifact.file_path}")

# -----------------------------------------------------------------------
# STEP 6: Verify gates
# -----------------------------------------------------------------------
section("STEP 6 - Verifying Approval Gates")

gates = [
    ("SRS",          AgentName.REQUIREMENT,  ArtifactType.SRS,          ArtifactFormat.MARKDOWN),
    ("Enhanced SRS", AgentName.DOMAIN,       ArtifactType.ENHANCED_SRS, ArtifactFormat.MARKDOWN),
    ("SDS",          AgentName.ARCHITECTURE, ArtifactType.SDS,          ArtifactFormat.MARKDOWN),
]

for label, agent, atype, afmt in gates:
    found = artifact_service.get_latest_approved_artifact(
        feature_id=feature_id,
        agent_name=agent,
        artifact_type=atype,
        artifact_format=afmt,
    )
    if found:
        ok(f"Gate '{label}' PASSED  (artifact_id={found.artifact_id})")
    else:
        fail(f"Gate '{label}' FAILED - approved artifact not found")

# -----------------------------------------------------------------------
# STEP 7: Call /coder/run
# -----------------------------------------------------------------------
section("STEP 7 - Running Coder Agent  (POST /coder/run)")

info("Sending request... this may take 30-180 seconds depending on LLM speed")
print()

coder_request = {
    "env_vars": {
        "MONGO_URI":      "mongodb://localhost:27017/ecommerce",
        "JWT_SECRET":     "dev-secret-key-change-in-production",
        "JWT_EXPIRES_IN": "7d",
        "PORT":           "5000"
    },
    "skip_uiux": True,
    "human_comment": None,
    "coding_standards": None
}

r = client.post(
    f"/api/v1/features/{feature_id}/agents/coder/run",
    json=coder_request,
    timeout=300,
)

print(f"  HTTP Status: {r.status_code}")
print()

if r.status_code != 200:
    print("  [FAIL] Coder Agent returned an error:")
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text[:3000])
    sys.exit(1)

coder_response = r.json()

# -----------------------------------------------------------------------
# STEP 8: Print Results
# -----------------------------------------------------------------------
section("STEP 8 - Coder Agent Response")

ok(f"Status:  {coder_response.get('status')}")
ok(f"Message: {coder_response.get('message')}")
print()
info(f"Artifacts generated: {len(coder_response.get('artifact_ids', []))}")
print()

for i, art_id in enumerate(coder_response.get("artifact_ids", []), 1):
    artifact = store.artifacts.get(art_id)
    if artifact:
        print(f"    [{i}] {art_id}")
        print(f"         type:   {artifact['artifact_type']}")
        print(f"         format: {artifact['artifact_format']}")
        print(f"         file:   {artifact['file_path']}")
        print()
    else:
        print(f"    [{i}] {art_id}  (not found in store)")

# -----------------------------------------------------------------------
# STEP 9: List all files on disk
# -----------------------------------------------------------------------
section("STEP 9 - Files on Disk")

outputs_dir = Path("outputs")
if outputs_dir.exists():
    files = sorted([f for f in outputs_dir.rglob("*") if f.is_file()])
    info(f"Total files in outputs/: {len(files)}")
    print()
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"    {str(f):<70}  ({size_kb:.1f} KB)")
else:
    info("outputs/ directory not found")

# -----------------------------------------------------------------------
# STEP 10: Preview merge report
# -----------------------------------------------------------------------
section("STEP 10 - Merge Report Preview")

merge_report_path = None
for art_id in coder_response.get("artifact_ids", []):
    artifact = store.artifacts.get(art_id)
    if artifact and "merge_report" in str(artifact.get("file_path", "")):
        merge_report_path = artifact["file_path"]
        break

if merge_report_path and Path(merge_report_path).exists():
    content = Path(merge_report_path).read_text(encoding="utf-8")
    lines = content.splitlines()
    for line in lines[:60]:
        print(f"  {line}")
    if len(lines) > 60:
        print(f"  ... ({len(lines) - 60} more lines)")
    print()
    info(f"Full file: {merge_report_path}")
else:
    info("Merge report not found on disk")

# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------
section("TEST COMPLETE")
ok("Coder Agent ran successfully end-to-end.")
ok(f"Feature:     {feature['feature_name']}   (feature_id: {feature_id})")
ok(f"Artifacts:   outputs/e-commerce-platform/feature-login/05_code/")
print()
