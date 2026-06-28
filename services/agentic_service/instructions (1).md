# instructions.md  
# Human-in-the-Loop Multi-Agent SDLC Automation System  
## Enterprise E-commerce / LMS Feature-by-Feature Development Platform

---

## 1. Purpose of This Document

This `instructions.md` file is the main reference document for developing a **Human-in-the-Loop Multi-Agentic AI System** that automates the Software Development Life Cycle (SDLC) for enterprise-level applications such as:

- E-commerce platforms
- Learning Management Systems (LMS)
- CRM systems
- Admin dashboards
- SaaS applications

The system must not generate the full application at once.  
Instead, it must develop the final application **feature by feature** using an iterative SDLC workflow.

Example:

```text
Iteration 1: Login Feature
Iteration 2: Signup Feature
Iteration 3: Product Listing Feature
Iteration 4: Cart Feature
Iteration 5: Checkout Feature
Iteration 6: Order Management Feature
...
```

Each feature must pass through multiple AI agents, and a human must approve each stage before the output is passed to the next agent.

---

## 2. Project Vision

The goal is to build a scalable enterprise-level **Multi-Agent Software Engineering Platform** that allows users to generate real-world applications through a controlled SDLC pipeline.

The platform should allow a user or Business Analyst (BA) to enter a feature request such as:

```text
Develop the login feature for an E-commerce system using MERN stack.
```

Then the system should automatically perform:

```text
Requirement Analysis
→ Domain Enhancement
→ Architecture Design
→ UI/UX Design
→ Code Generation
→ Runtime Deployment
→ Live Preview
```

However, each step must be reviewed and approved by a human before continuing.

---

## 3. Main System Name

Recommended project name:

```text
AutoForge
```

Alternative names:

- SDLC Forge
- Agentic SDLC Builder
- AutoDev MAS
- FeatureForge AI
- Enterprise App Forge

For consistency, use **AutoForge** in the codebase and documentation unless the project name changes later.

---

## 4. Main System Type

This project is a:

```text
Human-in-the-Loop Multi-Agentic AI System for SDLC Automation
```

It is not just a chatbot.

It is not just a code generator.

It is a workflow-based AI software engineering platform where each agent produces professional artifacts that are stored, reviewed, revised, approved, and passed to the next SDLC stage.

---

## 5. Core Development Approach

The system must follow **feature-by-feature iterative development**.

Do not generate the full E-commerce or LMS application at once.

Each feature must be treated as a separate SDLC unit.

Each feature should produce its own artifacts:

```text
SRS
Enhanced SRS
SDS
Use Case Diagram
UI/UX Design
Generated Code
Runtime Logs
Preview URL
Approval Records
Revision Records
Traceability Records
```

When a new feature is developed, the system must load previous approved artifacts and merge the new feature into the existing application without breaking already completed features.

---

## 6. MVP Scope

For the first implementation phase, focus only on these agents:

1. Requirement Agent
2. Domain Agent
3. Architecture Agent
4. UI/UX Agent
5. Coder Agent
6. Deployment/Runtime Agent

Do not implement these agents in the first MVP:

1. Security Agent
2. Testing Agent

Security Agent and Testing Agent must be designed as future plug-in agents, but they should not be part of the first implementation scope.

---

## 7. Human-in-the-Loop Rule

The system must always follow this rule:

```text
No agent output can be passed to the next agent without human approval.
```

After every agent generates an output, the frontend must show the output to the user.

The user must be able to:

- Approve the output
- Reject the output
- Add revision comments
- Edit the artifact manually
- Request regeneration
- Compare previous and new versions
- Continue to the next agent only after approval

Approval gates are mandatory after:

```text
Requirement Agent
Domain Agent
Architecture Agent
UI/UX Agent
Coder Agent
Deployment/Runtime Agent
```

---

## 8. High-Level Workflow

The system workflow must be:

```text
START
  ↓
Create Project
  ↓
Create Feature
  ↓
Requirement Agent
  ↓
Human Approval Gate
  ↓
Domain Agent
  ↓
Human Approval Gate
  ↓
Architecture Agent
  ↓
Human Approval Gate
  ↓
UI/UX Agent
  ↓
Human Approval Gate
  ↓
Coder Agent
  ↓
Human Approval Gate
  ↓
Deployment/Runtime Agent
  ↓
Live Preview URL
  ↓
Human Feedback
  ↓
Next Feature Iteration
END
```

---

## 9. Example Use Case: E-commerce Login Feature

The user enters:

```text
Project Type: E-commerce
Feature: Login
Tech Stack: MERN
Roles: Customer, Admin
Requirement: Users should be able to login using email and password.
```

The flow should be:

### Step 1: Requirement Agent

Generate:

- `SRS_v1.md`
- `SRS_v1.json`

### Step 2: Human Approval

User approves or requests revision.

### Step 3: Domain Agent

Enhance the SRS using E-commerce domain knowledge.

Generate:

- `Enhanced_SRS_v1.md`
- `Enhanced_SRS_v1.json`
- `Domain_Improvements_v1.json`

### Step 4: Human Approval

User approves or requests revision.

### Step 5: Architecture Agent

Generate:

- `SDS_v1.md`
- `SDS_v1.json`
- `usecase_v1.puml`
- `usecase_v1.png`
- `api_contract_v1.json`
- `openapi_v1.yaml`

### Step 6: Human Approval

User approves or requests revision.

### Step 7: UI/UX Agent

Generate:

- High-fidelity login UI
- HTML + Tailwind CSS
- React component if required
- Rendered preview
- User flow if required
- UI metadata

### Step 8: Human Approval

User approves or requests revision.

### Step 9: Coder Agent

Generate MERN code for only the Login feature.

Generate:

- Backend code
- Frontend code
- File tree
- Environment variable list
- Code manifest
- Requirement-code mapping

### Step 10: Human Approval

User approves or requests revision.

### Step 11: Deployment/Runtime Agent

Deploy or run the application in a sandbox.

Return:

- Build status
- Runtime logs
- Preview URL
- Error logs if any

---

## 10. Agent Responsibilities

---

# 10.1 Requirement Agent

## Purpose

The Requirement Agent collects structured BA input and generates the initial Software Requirements Specification (SRS).

## Input

The Requirement Agent should accept structured input such as:

```json
{
  "project_name": "AutoForge E-commerce",
  "project_type": "E-commerce",
  "feature_name": "Login",
  "target_stack": "MERN",
  "user_roles": ["Customer", "Admin"],
  "business_goal": "Allow registered users to securely access their account.",
  "functional_requirements": [
    "User can login using email and password",
    "System validates credentials",
    "System returns authentication token after successful login"
  ],
  "non_functional_requirements": [
    "Login response should be fast",
    "UI should be responsive",
    "Errors should be clear"
  ],
  "constraints": [
    "Use MERN stack",
    "Use JWT authentication"
  ],
  "assumptions": [
    "User account already exists"
  ]
}
```

## Output

The Requirement Agent must generate:

```text
SRS_v1.md
SRS_v1.json
```

## SRS Markdown Must Include

- Feature title
- Feature description
- Business objective
- Scope
- Out of scope
- User roles
- Functional requirements
- Non-functional requirements
- User stories
- Acceptance criteria
- Input/output requirements
- UI expectations
- API expectations
- Data requirements
- Validation rules
- Constraints
- Assumptions
- Risks
- Dependencies

## SRS JSON Must Include Stable IDs

Use stable IDs such as:

```text
FR-001
FR-002
NFR-001
AC-001
UC-001
BR-001
```

Example:

```json
{
  "feature_id": "feature-login",
  "feature_name": "Login",
  "functional_requirements": [
    {
      "id": "FR-001",
      "description": "The user shall be able to login using email and password."
    }
  ],
  "acceptance_criteria": [
    {
      "id": "AC-001",
      "description": "Given valid credentials, when the user submits the login form, then the system must authenticate the user successfully."
    }
  ]
}
```

## Requirement Agent Rules

- Do not generate code.
- Do not generate architecture diagrams.
- Do not add unrelated features.
- Ask clarifying questions only when required fields are missing.
- Otherwise, make reasonable assumptions and document them.
- Always generate both Markdown and JSON.
- Always preserve feature scope.

---

# 10.2 Domain Agent

## Purpose

The Domain Agent enhances the approved SRS using domain knowledge through RAG.

## Input

The Domain Agent receives:

```text
Approved SRS Markdown
Approved SRS JSON
Project type
Feature name
Domain knowledge retrieved from vector database
```

## RAG Knowledge Sources

For E-commerce, the knowledge base may include:

- Authentication workflows
- Customer account rules
- Product catalog rules
- Cart and checkout rules
- Order lifecycle
- Payment concepts
- Shipping concepts
- Admin workflows
- Inventory concepts
- Enterprise usability rules
- Business validation rules

For LMS, the knowledge base may include:

- Course management
- Student enrollment
- Instructor workflows
- Lesson access
- Quizzes
- Certificates
- Progress tracking
- Admin management

## Output

The Domain Agent must generate:

```text
Enhanced_SRS_v1.md
Enhanced_SRS_v1.json
Domain_Improvements_v1.json
```

## Domain Agent Must Enhance

- Missing requirements
- Edge cases
- Business rules
- Data validations
- Acceptance criteria
- Domain assumptions
- User flows
- Role-based behavior
- Enterprise-level expectations

## Domain Agent Rules

- Do not destroy or fully rewrite the original SRS.
- Preserve the BA’s original intention.
- Clearly list all enhancements made.
- Clearly mark newly added domain assumptions.
- Do not generate code.
- Do not generate UI.
- Do not generate architecture diagrams.

---

# 10.3 Architecture Agent

## Purpose

The Architecture Agent converts the enhanced SRS into a Software Design Specification (SDS).

## Input

The Architecture Agent receives:

```text
Approved SRS
Approved Enhanced SRS
Project type
Feature name
Target stack
Previous feature artifacts if available
```

## Output

The Architecture Agent must generate:

```text
SDS_v1.md
SDS_v1.json
api_contract_v1.json
openapi_v1.yaml
usecase_v1.puml
usecase_v1.png
traceability_architecture_v1.json
```

## SDS Must Include

- Feature design overview
- Architecture style
- Frontend responsibility
- Backend responsibility
- Database design
- API endpoints
- Request/response models
- Data flow
- Error handling design
- Authentication/authorization design if relevant
- Folder structure suggestion
- Dependency list
- Integration with previous features
- Scalability notes
- Traceability to requirements

## Diagram Rule

For MVP, generate only:

```text
Use Case Diagram
```

Do not generate component list diagrams.

Do not generate unnecessary class, sequence, or object diagrams unless explicitly requested.

## Toolchain for Use Case Diagram

Use:

```text
PlantUML → Graphviz → PNG
```

Store both the `.puml` and `.png` files.

## Architecture Agent Rules

- Do not generate code.
- Do not generate UI.
- Do not include Security Agent or Testing Agent outputs in the MVP.
- The architecture must be clear and simple enough to defend in front of a supervisor or panel.
- Architecture must be practical for MERN implementation.
- API contracts must match the approved requirements.

---

# 10.4 UI/UX Agent

## Purpose

The UI/UX Agent generates the user interface and user experience design for the approved feature.

## Input

The UI/UX Agent receives:

```text
Approved SRS
Approved Enhanced SRS
Approved SDS
Feature name
User UI preferences
Branding instructions
Theme preferences
```

## User Input Before UI Generation

The user must be able to provide:

- Theme style
- Color preference
- Layout preference
- Mobile-first or desktop-first design
- Simple or modern design
- Enterprise SaaS style
- Required UI elements
- Branding text
- Accessibility preferences

Example:

```json
{
  "theme": "modern dark",
  "primary_color": "blue",
  "layout": "centered card",
  "responsive": true,
  "include_forgot_password": true,
  "include_remember_me": true
}
```

## Output

The UI/UX Agent must generate:

```text
ui_design_v1.md
ui_metadata_v1.json
user_flow_v1.mmd
user_flow_v1.png
wireframe_v1.html
wireframe_v1.png
react_component_v1.jsx
tailwind_styles_v1.md
```

## UI Generation Requirements

The UI/UX Agent must generate:

- High-fidelity UI
- HTML + Tailwind CSS
- Optional React component
- Responsive design
- Form states
- Error states
- Loading states
- Success states
- Accessibility-friendly labels
- Modern styling
- Realistic enterprise-level UI

## Rendering Tools

Recommended tools:

```text
HTML + Tailwind CSS
Playwright for rendering screenshots
Mermaid for user flows
```

## UI/UX Agent Rules

- Do not generate low-fidelity wireframes unless explicitly requested.
- Generate high-fidelity wireframes by default.
- Do not hardcode unrelated features.
- UI must match the approved feature only.
- User must be able to revise the UI.
- Render the UI inside the MAS frontend.
- Store the HTML and PNG screenshot as artifacts.

---

# 10.5 Coder Agent

## Purpose

The Coder Agent generates the actual MERN application code for the approved feature.

## Input

The Coder Agent receives:

```text
Approved SRS
Approved Enhanced SRS
Approved SDS
Approved API contract
Approved UI/UX output
Previous generated application code
Previous feature manifests
Human-provided environment variables
```

## Important Rule

The Coder Agent must generate only the exact approved feature.

Example:

If the approved feature is Login, the Coder Agent must not generate Cart, Product Listing, Checkout, or Admin Dashboard unless those are approved requirements.

## Human Input Before Code Generation

Before the Coder Agent runs, the frontend must ask the user for environment variables such as:

```text
MONGODB_URI
JWT_SECRET
PORT
CLIENT_URL
VITE_API_BASE_URL
```

The system must allow the user to enter these values safely.

## MERN Code Generation

For MERN stack, generate:

### Backend

- Express.js server
- MongoDB connection
- Mongoose models
- Controllers
- Routes
- Services if needed
- Middleware
- Environment variable loader
- Error handling
- API response format

### Frontend

- React components
- Tailwind CSS UI
- API integration
- Form handling
- Loading state
- Error state
- Success state
- Token handling if approved
- Feature routes

### Shared

- API constants
- Validation schemas if needed
- Types if TypeScript is used

## Output

The Coder Agent must generate:

```text
code_manifest_v1.json
file_tree_v1.json
generated_files/
requirement_code_map_v1.json
setup_instructions_v1.md
env_requirements_v1.md
merge_report_v1.md
```

## Code Manifest Must Include

```json
{
  "feature_id": "feature-login",
  "generated_files": [],
  "modified_files": [],
  "deleted_files": [],
  "input_artifacts": {
    "srs": "SRS_v1.json",
    "enhanced_srs": "Enhanced_SRS_v1.json",
    "sds": "SDS_v1.json",
    "api_contract": "api_contract_v1.json",
    "uiux": "ui_metadata_v1.json"
  },
  "run_commands": {
    "backend": "npm run dev",
    "frontend": "npm run dev"
  }
}
```

## Code Generation Rules

- Prefer patch-based changes when modifying an existing application.
- Do not rewrite the whole project unnecessarily.
- Preserve previously approved features.
- Merge new feature routes carefully.
- Update navigation only when required.
- Update shared API client if needed.
- Keep generated code clean and readable.
- Avoid hardcoded database links or secrets.
- Use `.env.example` but never expose real secrets.
- Every code file must trace back to approved requirements.

---

# 10.6 Deployment/Runtime Agent

## Purpose

The Deployment/Runtime Agent runs or deploys the generated application and returns a preview URL.

## Input

The Deployment/Runtime Agent receives:

```text
Generated code
Code manifest
Environment variables
Run commands
Deployment target
```

## Deployment Options

Possible deployment/runtime targets:

- Local Docker sandbox
- Replit
- CodeSandbox
- StackBlitz
- Temporary cloud preview
- Local process runner

For MVP, start with a local sandbox or Docker-based runtime if external sandbox APIs are too complex.

## Output

The Deployment/Runtime Agent must generate:

```text
deployment_status_v1.json
build_logs_v1.txt
runtime_logs_v1.txt
error_logs_v1.txt
preview_url_v1.json
deployment_instructions_v1.md
```

## Deployment Agent Responsibilities

- Install dependencies
- Build frontend
- Start backend
- Start frontend
- Inject environment variables
- Detect build errors
- Detect runtime errors
- Capture logs
- Return preview URL
- Allow rerun after revision

## Deployment Agent Rules

- Do not expose secrets in logs.
- Do not silently ignore errors.
- Return clear error messages.
- Store all logs as artifacts.
- Send preview URL to the frontend.

---

## 11. Future Agents

Security Agent and Testing Agent are not part of the first MVP, but the system must be designed so they can be added later.

---

# 11.1 Future Testing Agent

The Testing Agent may later generate and run:

- Unit tests
- Integration tests
- API tests
- Regression tests
- UI tests
- Playwright tests

Possible tools:

- Jest
- Vitest
- React Testing Library
- Supertest
- Playwright
- Pytest for MAS backend

---

# 11.2 Future Security Agent

The Security Agent may later perform:

- Static code analysis
- Dependency vulnerability checks
- Authentication review
- Authorization review
- Secret scanning
- Input validation checks
- OWASP-based checks
- Risk scoring
- Compliance traceability

Possible tools:

- Custom Python AST rules
- OSV.dev
- NVD
- Semgrep if allowed
- Custom security rules

---

## 12. Backend Technology Stack

Use:

```text
Python
FastAPI
LangChain
LangGraph
Pydantic
Uvicorn
PostgreSQL or MongoDB
FAISS or ChromaDB
Ollama
OpenAI API or other API-based LLMs
WebSockets or Server-Sent Events
PlantUML
Graphviz
Playwright
Docker
```

Recommended backend stack for MVP:

```text
Python + FastAPI + LangGraph + LangChain + Pydantic + Ollama + ChromaDB + File-based artifact storage
```

---

## 13. Frontend Technology Stack

Use:

```text
React
Vite
Tailwind CSS
Axios
TanStack Query
Zustand or Redux
Monaco Editor
Markdown Renderer
JSON Viewer
WebSocket or SSE Client
```

Recommended frontend stack for MVP:

```text
React + Vite + Tailwind CSS + Axios + Zustand + Markdown Preview + Monaco Editor
```

---

## 14. Generated Application Stack

For the generated E-commerce or LMS applications, use MERN stack by default:

```text
MongoDB
Express.js
React
Node.js
Tailwind CSS
```

Do not generate Python/FastAPI, Java/Spring Boot, or other stacks for the target application unless the user explicitly changes the target stack.

The MAS platform backend can be Python/FastAPI, but the generated application should be MERN by default.

---

## 15. Recommended Backend Folder Structure

```text
services/
  agentic_service/
    app/
      main.py
      api/
        routes/
          projects.py
          features.py
          agents.py
          approvals.py
          artifacts.py
          revisions.py
          deployments.py
          llm_settings.py
          env_vars.py
      agents/
        requirement_agent.py
        domain_agent.py
        architecture_agent.py
        uiux_agent.py
        coder_agent.py
        deployment_agent.py
      workflows/
        sdlc_graph.py
        approval_gates.py
        state.py
      services/
        artifact_service.py
        approval_service.py
        revision_service.py
        rag_service.py
        llm_provider_service.py
        streaming_service.py
        plantuml_service.py
        graphviz_service.py
        ui_render_service.py
        deployment_service.py
      providers/
        base_provider.py
        ollama_provider.py
        openai_provider.py
      vectorstore/
        domain_knowledge_store.py
        loaders.py
        embeddings.py
      schemas/
        project_schema.py
        feature_schema.py
        requirement_schema.py
        domain_schema.py
        architecture_schema.py
        uiux_schema.py
        coder_schema.py
        deployment_schema.py
        approval_schema.py
        artifact_schema.py
      models/
        project.py
        feature.py
        artifact.py
        approval.py
        revision.py
        llm_setting.py
      database/
        connection.py
        migrations/
      utils/
        file_manager.py
        logger.py
        json_utils.py
        markdown_utils.py
        id_generator.py
      tests/
        test_requirement_agent.py
        test_artifact_service.py
        test_approval_flow.py
    outputs/
    requirements.txt
    .env.example
```

---

## 16. Recommended Frontend Folder Structure

```text
frontend/
  src/
    api/
      projectsApi.js
      featuresApi.js
      agentsApi.js
      artifactsApi.js
      approvalsApi.js
      deploymentsApi.js
      llmSettingsApi.js
    components/
      layout/
        Sidebar.jsx
        Topbar.jsx
        AppLayout.jsx
      pipeline/
        AgentProgressStepper.jsx
        AgentCard.jsx
        ApprovalPanel.jsx
        RevisionCommentBox.jsx
      viewers/
        MarkdownViewer.jsx
        JSONViewer.jsx
        CodeViewer.jsx
        DiagramViewer.jsx
        ArtifactViewer.jsx
        LogViewer.jsx
      uiux/
        UIPreviewFrame.jsx
        WireframePreview.jsx
        ThemePreferenceForm.jsx
      settings/
        LLMProviderSelector.jsx
        EnvironmentVariableForm.jsx
      deployment/
        DeploymentStatusCard.jsx
        PreviewURLCard.jsx
    pages/
      Dashboard.jsx
      CreateProject.jsx
      ProjectDetails.jsx
      FeaturePipeline.jsx
      AgentOutputReview.jsx
      ArtifactDetails.jsx
      DeploymentPreview.jsx
      LLMSettings.jsx
    store/
      projectStore.js
      featureStore.js
      workflowStore.js
      streamStore.js
    hooks/
      useAgentStream.js
      useArtifacts.js
      useApproval.js
    utils/
      formatDate.js
      downloadFile.js
    App.jsx
    main.jsx
  package.json
  .env.example
```

---

## 17. LangGraph Workflow Design

Use LangGraph to orchestrate the agent workflow.

The graph should include agent nodes and approval pause states.

```text
START
  ↓
requirement_agent
  ↓
requirement_approval_gate
  ↓
domain_agent
  ↓
domain_approval_gate
  ↓
architecture_agent
  ↓
architecture_approval_gate
  ↓
uiux_agent
  ↓
uiux_approval_gate
  ↓
coder_agent
  ↓
coder_approval_gate
  ↓
deployment_agent
  ↓
deployment_approval_gate
  ↓
END
```

The workflow state should include:

```json
{
  "project_id": "",
  "feature_id": "",
  "current_agent": "",
  "current_stage": "",
  "approval_status": "",
  "revision_requested": false,
  "revision_comment": "",
  "artifacts": {},
  "llm_settings": {},
  "env_vars_reference": {},
  "streaming_enabled": true
}
```

## LangGraph Rules

- Each agent is a graph node.
- Each approval gate is a pause/checkpoint node.
- The graph must stop after each agent output.
- The graph resumes only after approval.
- If revision is requested, route back to the same agent.
- Save every output before moving to the next node.

---

## 18. Artifact Management

Artifacts must be stored carefully.

Recommended artifact path:

```text
outputs/
  {project_slug}/
    {feature_slug}/
      01_requirements/
      02_domain/
      03_architecture/
      04_uiux/
      05_code/
      06_deployment/
```

Example:

```text
outputs/
  ecommerce-platform/
    feature-login/
      01_requirements/
        SRS_v1.md
        SRS_v1.json
        approval_v1.json
      02_domain/
        Enhanced_SRS_v1.md
        Enhanced_SRS_v1.json
        Domain_Improvements_v1.json
        approval_v1.json
      03_architecture/
        SDS_v1.md
        SDS_v1.json
        api_contract_v1.json
        openapi_v1.yaml
        usecase_v1.puml
        usecase_v1.png
        traceability_architecture_v1.json
        approval_v1.json
      04_uiux/
        ui_design_v1.md
        ui_metadata_v1.json
        user_flow_v1.mmd
        user_flow_v1.png
        wireframe_v1.html
        wireframe_v1.png
        react_component_v1.jsx
        approval_v1.json
      05_code/
        code_manifest_v1.json
        file_tree_v1.json
        generated_files/
        requirement_code_map_v1.json
        setup_instructions_v1.md
        env_requirements_v1.md
        merge_report_v1.md
        approval_v1.json
      06_deployment/
        deployment_status_v1.json
        build_logs_v1.txt
        runtime_logs_v1.txt
        error_logs_v1.txt
        preview_url_v1.json
        deployment_instructions_v1.md
        approval_v1.json
```

## Artifact Rules

- Never overwrite approved artifacts.
- Use versions such as `v1`, `v2`, `v3`.
- Store human comments with each revision.
- Store approval status.
- Store model/provider metadata.
- Store timestamp.
- Store traceability mapping.
- Store generated files separately from metadata.

---

## 19. Data Models

Use these conceptual data models.

---

# 19.1 Project

```json
{
  "project_id": "proj_001",
  "project_name": "E-commerce Platform",
  "project_type": "E-commerce",
  "target_stack": "MERN",
  "created_by": "user_001",
  "created_at": "",
  "updated_at": ""
}
```

---

# 19.2 Feature

```json
{
  "feature_id": "feature-login",
  "project_id": "proj_001",
  "feature_name": "Login",
  "feature_description": "Allow users to login using email and password",
  "feature_status": "in_progress",
  "current_agent": "requirement_agent",
  "created_at": "",
  "updated_at": ""
}
```

---

# 19.3 Artifact

```json
{
  "artifact_id": "artifact_001",
  "project_id": "proj_001",
  "feature_id": "feature-login",
  "agent_name": "requirement_agent",
  "artifact_type": "SRS",
  "artifact_format": "markdown",
  "file_path": "outputs/ecommerce-platform/feature-login/01_requirements/SRS_v1.md",
  "version": 1,
  "approval_status": "pending",
  "created_at": ""
}
```

---

# 19.4 Approval

```json
{
  "approval_id": "approval_001",
  "artifact_id": "artifact_001",
  "agent_name": "requirement_agent",
  "status": "approved",
  "reviewer_comment": "Approved for next stage",
  "approved_by": "human_user",
  "approved_at": ""
}
```

---

# 19.5 Revision

```json
{
  "revision_id": "revision_001",
  "artifact_id": "artifact_001",
  "previous_version": 1,
  "new_version": 2,
  "revision_comment": "Add forgot password acceptance criteria",
  "revised_by": "human_user",
  "created_at": ""
}
```

---

# 19.6 LLM Settings

```json
{
  "provider": "ollama",
  "model": "llama3.1",
  "base_url": "http://localhost:11434",
  "temperature": 0.2,
  "max_tokens": 4096,
  "streaming_enabled": true
}
```

---

## 20. API Endpoint Design

---

# 20.1 Project APIs

```text
POST   /projects
GET    /projects
GET    /projects/{project_id}
PUT    /projects/{project_id}
DELETE /projects/{project_id}
```

---

# 20.2 Feature APIs

```text
POST /projects/{project_id}/features
GET  /projects/{project_id}/features
GET  /features/{feature_id}
PUT  /features/{feature_id}
```

---

# 20.3 Agent Run APIs

```text
POST /features/{feature_id}/agents/requirement/run
POST /features/{feature_id}/agents/domain/run
POST /features/{feature_id}/agents/architecture/run
POST /features/{feature_id}/agents/uiux/run
POST /features/{feature_id}/agents/coder/run
POST /features/{feature_id}/agents/deployment/run
```

---

# 20.4 Approval APIs

```text
POST /artifacts/{artifact_id}/approve
POST /artifacts/{artifact_id}/reject
POST /artifacts/{artifact_id}/request-revision
```

---

# 20.5 Artifact APIs

```text
GET /features/{feature_id}/artifacts
GET /artifacts/{artifact_id}
GET /artifacts/{artifact_id}/download
GET /artifacts/{artifact_id}/versions
```

---

# 20.6 Revision APIs

```text
POST /artifacts/{artifact_id}/revisions
GET  /artifacts/{artifact_id}/revisions
```

---

# 20.7 Streaming APIs

Use either SSE:

```text
GET /stream/features/{feature_id}/agents/{agent_name}
```

Or WebSocket:

```text
WS /ws/features/{feature_id}/agents/{agent_name}
```

---

# 20.8 LLM Settings APIs

```text
GET  /settings/llm
POST /settings/llm
PUT  /settings/llm
```

---

# 20.9 Environment Variable APIs

```text
POST /features/{feature_id}/env
GET  /features/{feature_id}/env/status
PUT  /features/{feature_id}/env
```

---

# 20.10 Deployment APIs

```text
POST /features/{feature_id}/deployment/run
GET  /features/{feature_id}/deployment/status
GET  /features/{feature_id}/deployment/logs
GET  /features/{feature_id}/deployment/preview
```

---

## 21. LLM Provider Abstraction

The system must support both local and cloud LLM providers.

Supported providers:

```text
Ollama
OpenAI API
Other future APIs
```

Create a common base provider.

Example:

```python
class BaseLLMProvider:
    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError

    def stream(self, prompt: str, **kwargs):
        raise NotImplementedError

    def invoke_agent(self, messages: list, **kwargs):
        raise NotImplementedError
```

Provider files:

```text
providers/
  base_provider.py
  ollama_provider.py
  openai_provider.py
```

The user must be able to select:

- Provider
- Model
- Base URL
- API key
- Temperature
- Max tokens
- Streaming on/off

---

## 22. Streaming Design

The system must support live response streaming.

Streaming should be available for:

- Requirement Agent generation
- Domain Agent generation
- Architecture Agent generation
- UI/UX Agent generation
- Coder Agent generation
- Deployment logs

Recommended options:

```text
Server-Sent Events
WebSockets
LangChain streaming callbacks
LangGraph streaming events
```

The frontend should display:

- Current running agent
- Streaming text
- Completion status
- Error messages
- Generated artifact links
- Approval buttons after completion

---

## 23. RAG Design for Domain Agent

The Domain Agent must use a RAG system.

Recommended components:

```text
Document Loader
Text Splitter
Embedding Model
Vector Database
Retriever
Domain Enhancement Prompt
```

Possible vector stores:

```text
ChromaDB
FAISS
```

Possible embedding providers:

```text
Ollama embeddings
OpenAI embeddings
Sentence Transformers
```

Domain knowledge folders:

```text
knowledge_base/
  ecommerce/
    authentication.md
    product_catalog.md
    cart_checkout.md
    order_management.md
    admin_workflows.md
  lms/
    course_management.md
    enrollment.md
    quizzes.md
    progress_tracking.md
```

The RAG system should retrieve only relevant knowledge for the current feature.

Example:

For Login feature, retrieve:

```text
authentication.md
account_validation.md
role_based_access.md
```

Do not inject unrelated knowledge such as cart or payment rules into Login.

---

## 24. Prompting Rules for All Agents

Every agent prompt must include:

```text
Role
Goal
Input artifacts
Output format
Constraints
Validation rules
Human approval requirement
Do-not-do list
```

Each agent must output both:

```text
Human-readable artifact
Machine-readable artifact
```

Where applicable.

Example:

```text
Markdown + JSON
```

The JSON output must be valid and parseable.

---

## 25. General Agent Output Rules

All agents must follow these rules:

- Stay inside the approved feature scope.
- Do not invent unrelated features.
- Do not skip required artifacts.
- Do not bypass human approval.
- Do not overwrite previous approved artifacts.
- Generate versioned outputs.
- Generate traceability metadata.
- Keep outputs practical and implementation-ready.
- Mention assumptions clearly.
- Use stable IDs.
- Produce professional enterprise-level documentation.

---

## 26. Feature Merge Strategy

The system must support feature-by-feature merging.

When a new feature is generated, the Coder Agent must:

1. Load previous approved code manifest.
2. Load previous generated file tree.
3. Identify files that need to be created.
4. Identify files that need to be modified.
5. Avoid unnecessary full rewrites.
6. Apply patch-based updates where possible.
7. Preserve existing working features.
8. Update routes, navigation, API clients, and shared models carefully.
9. Generate a merge report.
10. Save the new code manifest.

Example:

```text
Login feature already exists.
Signup feature is generated.
Coder Agent must add signup route, signup page, auth controller update, user model update if needed, and frontend navigation update.
Login must continue to work.
```

---

## 27. Environment Variable Management

Environment variables should be collected before Coder Agent or Deployment Agent runs.

Do not hardcode secrets.

Use `.env.example`.

Example:

```text
MONGODB_URI=
JWT_SECRET=
PORT=5000
CLIENT_URL=http://localhost:5173
VITE_API_BASE_URL=http://localhost:5000/api
```

The system should store only references or encrypted values for sensitive variables.

Never print real secrets in logs.

---

## 28. Frontend UI Requirements for MAS Platform

The MAS frontend should include:

```text
Dashboard
Project Creation Page
Project Details Page
Feature Creation Page
Feature Pipeline Page
Agent Output Review Page
Artifact Viewer
Diagram Viewer
UI Preview Page
Code Viewer
Deployment Preview Page
LLM Settings Page
Environment Variable Input Page
Revision History Page
```

The Feature Pipeline Page should show:

```text
Requirement → Domain → Architecture → UI/UX → Coder → Deployment
```

Each stage should show:

- Pending
- Running
- Completed
- Revision requested
- Approved
- Failed

---

## 29. Approval Panel Requirements

The Approval Panel should include:

- Approve button
- Request Revision button
- Reject button
- Comment box
- Version selector
- Artifact download button
- Continue to next agent button after approval

The next agent button must be disabled until approval is completed.

---

## 30. Artifact Viewer Requirements

The Artifact Viewer should support:

- Markdown preview
- JSON preview
- Code preview
- PNG diagram preview
- HTML preview
- Logs preview
- Version history
- Download option

Use Monaco Editor for code and JSON viewing if possible.

---

## 31. UI Preview Requirements

The UI/UX output must be rendered inside the MAS frontend.

Possible preview methods:

- iframe preview for generated HTML
- React component preview
- PNG screenshot preview
- Playwright-rendered screenshot

The user should be able to request changes directly from the preview page.

---

## 32. Deployment Preview Requirements

Deployment page should show:

- Build status
- Runtime status
- Backend URL
- Frontend URL
- Live preview URL
- Logs
- Error messages
- Rerun deployment button

---

## 33. MVP Implementation Roadmap

---

# Phase 1: Project Setup

Build:

- FastAPI backend
- React frontend
- Basic database connection
- Basic project and feature APIs
- Basic artifact folder structure

---

# Phase 2: Requirement Agent

Build:

- BA intake form
- Requirement Agent prompt
- SRS Markdown generation
- SRS JSON generation
- Validation
- Artifact saving
- Approval UI

---

# Phase 3: Domain Agent

Build:

- Domain knowledge folder
- Vector database setup
- RAG retrieval
- Enhanced SRS generation
- Domain improvements artifact
- Approval UI

---

# Phase 4: Architecture Agent

Build:

- SDS generation
- API contract generation
- OpenAPI generation
- PlantUML use case generation
- Graphviz/PlantUML PNG rendering
- Architecture approval UI

---

# Phase 5: UI/UX Agent

Build:

- UI preference form
- HTML + Tailwind generation
- High-fidelity wireframe generation
- Playwright screenshot rendering
- UI preview page
- UI revision workflow

---

# Phase 6: Coder Agent

Build:

- Artifact-driven MERN code generation
- File tree generation
- Code manifest
- Environment variable collection
- Requirement-code mapping
- Feature merge logic

---

# Phase 7: Deployment/Runtime Agent

Build:

- Local sandbox runner
- Dependency installation
- Build command runner
- Runtime command runner
- Log capture
- Preview URL return
- Deployment status UI

---

# Phase 8: Full Iterative Feature Workflow

Build:

- Login feature full pipeline
- Signup feature full pipeline
- Merge Signup with Login
- Validate artifact continuity
- Validate approval gates
- Validate revision workflow

---

## 34. MVP Success Criteria

The MVP is successful when the system can:

1. Create an E-commerce project.
2. Create Login as the first feature.
3. Generate SRS for Login.
4. Allow human approval.
5. Enhance SRS using Domain Agent.
6. Allow human approval.
7. Generate SDS and Use Case Diagram.
8. Allow human approval.
9. Generate Login UI.
10. Allow human approval.
11. Generate MERN code for Login.
12. Allow human approval.
13. Run or deploy the generated Login application.
14. Return a preview URL.
15. Create Signup as the second feature.
16. Merge Signup with the existing Login application.
17. Preserve all artifacts with versions.

---

## 35. Recommended Prompt Templates

---

# 35.1 Requirement Agent Prompt Template

```text
You are the Requirement Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to generate a Software Requirements Specification for the given feature.

Input:
{ba_input}

Rules:
- Generate only requirements for the given feature.
- Do not generate architecture.
- Do not generate UI.
- Do not generate code.
- Use stable IDs for requirements.
- Produce both Markdown and JSON.
- Include assumptions and constraints.
- Make the output suitable for enterprise-level software development.

Output:
1. SRS Markdown
2. SRS JSON
```

---

# 35.2 Domain Agent Prompt Template

```text
You are the Domain Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to enhance the approved SRS using retrieved domain knowledge.

Input:
Approved SRS:
{srs}

Retrieved Domain Knowledge:
{retrieved_context}

Rules:
- Preserve the original BA intention.
- Add missing domain-specific requirements.
- Add edge cases and business rules.
- Add improved acceptance criteria.
- Do not generate architecture.
- Do not generate UI.
- Do not generate code.
- Output enhanced Markdown and JSON.

Output:
1. Enhanced SRS Markdown
2. Enhanced SRS JSON
3. Domain improvements JSON
```

---

# 35.3 Architecture Agent Prompt Template

```text
You are the Architecture Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to generate the Software Design Specification for the approved feature.

Input:
Approved SRS:
{srs}

Enhanced SRS:
{enhanced_srs}

Rules:
- Generate SDS for the approved feature only.
- Generate API contract.
- Generate OpenAPI specification.
- Generate PlantUML use case diagram source.
- Do not generate code.
- Do not generate UI.
- Do not generate component list diagrams.
- Keep the design practical for MERN stack implementation.

Output:
1. SDS Markdown
2. SDS JSON
3. API contract JSON
4. OpenAPI YAML
5. PlantUML use case diagram
6. Architecture traceability JSON
```

---

# 35.4 UI/UX Agent Prompt Template

```text
You are the UI/UX Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to generate a high-fidelity UI design for the approved feature.

Input:
Approved SRS:
{srs}

Enhanced SRS:
{enhanced_srs}

SDS:
{sds}

User UI Preferences:
{ui_preferences}

Rules:
- Generate UI only for the approved feature.
- Use HTML and Tailwind CSS.
- Generate high-fidelity design.
- Include responsive design.
- Include loading, error, and success states.
- Do not generate backend code.
- Do not add unrelated features.

Output:
1. UI design explanation
2. HTML + Tailwind CSS
3. Optional React component
4. UI metadata JSON
5. User flow Mermaid if needed
```

---

# 35.5 Coder Agent Prompt Template

```text
You are the Coder Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to generate MERN stack source code for the approved feature.

Input Artifacts:
SRS:
{srs}

Enhanced SRS:
{enhanced_srs}

SDS:
{sds}

API Contract:
{api_contract}

UI/UX Output:
{uiux_output}

Previous Code Manifest:
{previous_code_manifest}

Environment Variables:
{env_requirements}

Rules:
- Generate only the approved feature.
- Do not generate unrelated features.
- Preserve previous working features.
- Use patch-based modifications where possible.
- Generate clean MERN stack code.
- Do not hardcode secrets.
- Generate a code manifest.
- Generate requirement-code mapping.
- Generate setup instructions.

Output:
1. File tree
2. Full generated files
3. Code manifest
4. Requirement-code mapping
5. Setup instructions
6. Merge report
```

---

# 35.6 Deployment Agent Prompt Template

```text
You are the Deployment/Runtime Agent in a Human-in-the-Loop Multi-Agent SDLC Automation System.

Your task is to run or deploy the generated application and return a preview URL.

Input:
Generated Code:
{generated_code}

Code Manifest:
{code_manifest}

Environment Variables:
{env_vars}

Rules:
- Install dependencies.
- Build the application.
- Start backend and frontend.
- Capture logs.
- Return runtime errors clearly.
- Return preview URL.
- Do not expose secrets.

Output:
1. Deployment status JSON
2. Build logs
3. Runtime logs
4. Error logs
5. Preview URL JSON
6. Testing instructions for the user
```

---

## 36. Validation Rules

Each agent output must be validated.

Validation examples:

### Requirement Agent

- JSON must parse correctly.
- Required fields must exist.
- Stable IDs must exist.
- Markdown file must not be empty.

### Domain Agent

- Enhanced SRS must include original requirements.
- Improvements list must not be empty.
- JSON must parse correctly.

### Architecture Agent

- SDS must reference approved requirement IDs.
- PlantUML must compile.
- PNG must be generated.
- API contract must include endpoints.

### UI/UX Agent

- HTML must be valid enough to render.
- Tailwind classes should be present.
- Preview screenshot must be generated.
- UI must match feature scope.

### Coder Agent

- File tree must be valid.
- Code manifest must be valid JSON.
- Generated files must match approved feature.
- Environment variables must not be hardcoded.

### Deployment Agent

- Logs must be captured.
- Preview URL must be returned if successful.
- Errors must be stored if failed.

---

## 37. Observability and Logging

The system should log:

- Agent started
- Agent completed
- Agent failed
- Tool called
- Artifact generated
- Approval submitted
- Revision requested
- Deployment started
- Deployment completed
- Runtime error

Logs should include:

```text
timestamp
project_id
feature_id
agent_name
event_type
status
message
```

Do not log real secrets.

---

## 38. Error Handling

The system must handle:

- Invalid BA input
- Invalid JSON from LLM
- Missing artifacts
- Unapproved previous stage
- PlantUML rendering failure
- UI rendering failure
- Code generation failure
- Deployment failure
- Missing environment variables
- LLM provider timeout
- Ollama server unavailable
- OpenAI API error

Errors must be shown clearly in the frontend and saved as artifacts/logs.

---

## 39. Security and Privacy Rules for MVP

Even though Security Agent is future scope, the MAS platform itself must follow basic security practices:

- Do not expose API keys.
- Do not print secrets in logs.
- Use `.env` files.
- Use `.env.example` for documentation.
- Validate user input.
- Sanitize file paths.
- Prevent path traversal.
- Restrict artifact access by project/user if authentication is added.
- Store sensitive environment variables securely.

---

## 40. Enterprise-Level Best Practices

The system should follow:

- Modular architecture
- Clean separation of concerns
- Agent-specific responsibilities
- Versioned artifacts
- Traceability
- Human approval
- Observable workflow
- Configurable LLM providers
- Streaming responses
- Error recovery
- Revision support
- Feature merge strategy
- Scalable folder structure
- Future plug-in support for Security and Testing agents

---

## 41. Development Commands

Example backend setup:

```bash
cd services/agentic_service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Example frontend setup:

```bash
cd frontend
npm install
npm run dev
```

Example Ollama setup:

```bash
ollama serve
ollama pull llama3.1
```

Example PlantUML rendering:

```bash
java -jar plantuml.jar usecase_v1.puml
```

Example Playwright setup:

```bash
npm install -D playwright
npx playwright install
```

---

## 42. Important Constraints

The project must follow these constraints:

- Use Python/FastAPI for the MAS backend.
- Use React for the MAS frontend.
- Use MERN as the default generated application stack.
- Use LangGraph for workflow orchestration.
- Use LangChain for LLM/RAG integration.
- Support Ollama and AI APIs.
- Support response streaming.
- Use human approval gates.
- Use versioned artifacts.
- Use feature-by-feature SDLC.
- Do not include Security and Testing agents in MVP.
- Do not generate component list diagrams.
- Do not generate unrelated features.
- Do not hardcode secrets.
- Do not overwrite approved artifacts.
- Do not move to the next agent without approval.

---

## 43. Final Expected System Behavior

The final system should allow a user to build an enterprise E-commerce or LMS application like this:

```text
User creates project
User adds Login feature
Requirement Agent generates SRS
User approves
Domain Agent enhances SRS
User approves
Architecture Agent generates SDS and Use Case Diagram
User approves
UI/UX Agent generates high-fidelity UI
User approves
Coder Agent generates MERN code
User approves
Deployment Agent runs app and gives preview URL
User tests feature
User adds Signup feature
System repeats SDLC
Signup is merged with Login
System continues feature by feature
Final complete application is produced
```

---

## 44. Future Expansion

After MVP is working, add:

```text
Testing Agent
Security Agent
Traceability Dashboard
BA Approval Dashboard
Role-based user management
Team collaboration
Cloud deployment
GitHub repository integration
CI/CD pipeline generation
Automated documentation generation
Enterprise templates
Reusable project blueprints
```

---

## 45. Final Instruction to Any AI Assistant Using This File

When using this `instructions.md` file, always act as a senior software architect and senior AI agent engineer.

Do not give only theory.

Always provide:

- Practical implementation steps
- Correct folder structures
- Agent responsibilities
- Data models
- API endpoints
- Workflow logic
- Artifact structure
- Prompt templates
- Human approval logic
- Feature merge logic
- Tool recommendations
- MVP roadmap

Always remember:

```text
This system is a Human-in-the-Loop Multi-Agent SDLC Automation Platform.
It develops enterprise applications feature by feature.
It uses approval gates.
It stores artifacts.
It supports revisions.
It supports Ollama and AI APIs.
It uses Python/FastAPI for the MAS backend.
It uses React for the MAS frontend.
It generates MERN applications by default.
```

---
