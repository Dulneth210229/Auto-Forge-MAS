/* ==========================================================================
   AutoForge website - SITE DATA
   --------------------------------------------------------------------------
   This is the ONE file to edit when you get real links, photos, dates or
   marks. Everything on the Documents, Presentations, Milestones and About
   pages is generated from the objects below.

   - Document / slide links: paste the OneDrive or SharePoint share link into
     `url`. Leave it as "" while the link is not ready - the site will show
     "Link coming soon" for that item automatically.
   - Optional `embed`: if OneDrive gives you a separate "Embed" URL
     (File > Share > Embed), paste it here and the in-page viewer will use it.
   - Member photos: put the real image in assets/img/team/ and change `photo`.
   ========================================================================== */

window.SITE = {
  project: {
    name: "AutoForge",
    title: "AutoForge: A Checkpointed, Human-in-the-Loop Multi-Agent SDLC Pipeline",
    groupId: "R26-SE-033",
    university: "Sri Lanka Institute of Information Technology (SLIIT)",
    faculty: "Faculty of Computing",
    department: "Department of Software Engineering",
    degree: "BSc (Hons) in Information Technology, Specialising in Software Engineering",
    year: "2026",
    repo: "https://github.com/Dulneth210229/Auto-Forge-MAS"
  },

  /* ---------------------------------------------------------------- TEAM */
  members: [
    {
      id: "santhuka",
      name: "Santhuka D.N.M.D.",
      studentId: "IT22098078",
      email: "it22098078@my.sliit.lk",
      photo: "assets/img/team/santhuka.svg",
      component: "Requirement Generation, Domain Enrichment and Checkpointed Orchestration",
      agents: ["Requirement Agent", "Domain Agent", "Orchestrator"],
      summary:
        "Built the first two stages of the pipeline and the layer that connects all seven agents: a conversational " +
        "Requirement Agent with a deterministic quality gate, a retrieval-grounded Domain Agent that can only add what " +
        "it can cite, and a LangGraph state graph checkpointed to MongoDB so every stage can pause for a person and resume after a restart.",
      highlights: [
        "Retrieval raised useful domain requirements from 8 to 14",
        "7 of 7 controlled interruptions resumed at the correct stage",
        "\"Small plan, deterministic merge\" design for enrichment and revision"
      ],
      links: { github: "", linkedin: "" }
    },
    {
      id: "sansala",
      name: "Sansala T.G.B.D.",
      studentId: "IT22174826",
      email: "it22174826@my.sliit.lk",
      photo: "assets/img/team/sansala.svg",
      component: "Architecture Planning and UI/UX Design Generation",
      agents: ["Architecture Agent", "UI/UX Agent"],
      summary:
        "Built the design stages: an Architecture Agent that produces a fifteen-section plan traced to every SRS requirement, " +
        "with use case, sequence and class diagrams checked against UML rules, and a UI/UX Agent that designs pages " +
        "component by component and assembles live, self-contained previews.",
      highlights: [
        "Every FR, AC, VR and NFR traced in the architecture plan",
        "Rule-checked UML diagrams rendered with PlantUML",
        "Placeholder-free page previews; shared design system updated only on approval"
      ],
      links: { github: "", linkedin: "" }
    },
    {
      id: "dissanayake",
      name: "Dissanayake T.C.",
      studentId: "IT22157232",
      email: "it22157232@my.sliit.lk",
      photo: "assets/img/team/dissanayake.svg",
      component: "Code Generation with Sandboxed Verification",
      agents: ["Coder Agent"],
      summary:
        "Built the Coder Agent: it validates a code plan against the approved design, implements it on an isolated git " +
        "branch with tools scoped to the project, verifies every attempt in a Docker sandbox, and reports from the real " +
        "git diff. The branch is merged only when a person approves it.",
      highlights: [
        "Ten hard verification gates: build, boot, routes, schema/form, navigation and more",
        "Agentic and batch coding paths, chosen by model capability",
        "Merge on approval, discard on rejection, undo on revoke"
      ],
      links: { github: "", linkedin: "" }
    },
    {
      id: "oberathna",
      name: "Oberathna R.D.T.D.",
      studentId: "IT22102478",
      email: "it22102478@my.sliit.lk",
      photo: "assets/img/team/oberathna.svg",
      component: "Security Analysis and Quality Assurance",
      agents: ["Security Agent", "QA Agent"],
      summary:
        "Built the verification end of the pipeline: a Security Agent combining an AST pattern scanner, a secret scanner " +
        "and npm audit with an optional AI review, and a QA Agent that generates unit, integration and regression tests, " +
        "runs them with Jest in the sandbox and explains every failure.",
      highlights: [
        "Security precision 87.5% and recall 77.8% on a controlled set",
        "Findings mapped to Critical, Moderate and Warning tiers with CWE IDs",
        "Fix loop: findings sent back to the Coder Agent and re-scanned"
      ],
      links: { github: "", linkedin: "" }
    }
  ],

  supervisors: [
    { name: "Nuwan Kodagoda", role: "Supervisor", email: "nuwan.k@sliit.lk", photo: "assets/img/team/supervisor.svg" },
    { name: "Eishan Weerasinghe", role: "Co-supervisor", email: "eisha.w@sliit.lk", photo: "assets/img/team/cosupervisor.svg" }
  ],

  /* ---------------------------------------------------------- DOCUMENTS
     status: "available" | "pending"
     When you add a url, also set status to "available".                 */
  documents: [
    {
      id: "taf",
      group: "Project Charter",
      title: "Topic Assessment Form (TAF) / Project Charter",
      description: "The approved research topic, scope, team and supervisor details that started the project.",
      type: "PDF",
      url: "https://mysliit-my.sharepoint.com/:b:/g/personal/it22098078_my_sliit_lk/IQCu-LD52Q6NT6crRgNzD1nBAS9Up5wpYzZdv5UT2LN83pI?e=7sEVse",
      embed: "",
      status: "available",
      date: ""
    },
    {
      id: "proposal-group",
      group: "Proposal",
      title: "Project Proposal Document",
      description: "The research problem, objectives, literature survey, methodology and work plan for AutoForge.",
      type: "PPTX",
      url: "https://mysliit-my.sharepoint.com/:p:/g/personal/it22098078_my_sliit_lk/IQCtM4FxygqkS6IL4ZQNTvusARTUEqbOwEB3n68yQrHaNAA?e=4uRlOz",
      embed: "",
      status: "available",
      date: ""
    },
    {
      id: "checklist-1",
      group: "Check Lists",
      title: "Progress Presentation 1 Check List",
      description: "Completion check list submitted with the first progress presentation.",
      type: "TXT",
      url: "https://mysliit-my.sharepoint.com/:t:/g/personal/it22098078_my_sliit_lk/IQDJTcbtvky1TaTwurHOFq9EAQDEuweENM4bo2A8HcLIbqk?e=YBzVbI",
      embed: "",
      status: "available",
      date: ""
    },
    {
      id: "checklist-2",
      group: "Check Lists",
      title: "Progress Presentation 2 Check List",
      description: "Completion check list submitted with the second progress presentation.",
      type: "MP4",
      url: "https://mysliit-my.sharepoint.com/:v:/g/personal/it22098078_my_sliit_lk/IQDtttngNwVnTYNQpSA8qHyCAS6qode6gRjuXJep0Pt8FzQ?nav=eyJyZWZlcnJhbEluZm8iOnsicmVmZXJyYWxBcHAiOiJPbmVEcml2ZUZvckJ1c2luZXNzIiwicmVmZXJyYWxBcHBQbGF0Zm9ybSI6IldlYiIsInJlZmVycmFsTW9kZSI6InZpZXciLCJyZWZlcnJhbFZpZXciOiJNeUZpbGVzTGlua0NvcHkifX0&e=PON6ZZ",
      embed: "",
      status: "available",
      date: ""
    },
    {
      id: "paper",
      group: "Research Paper",
      title: "Research Paper",
      description: "AutoForge: A Checkpointed, Human-in-the-Loop Multi-Agent SDLC Pipeline.",
      type: "DOCX",
      url: "https://mysliit-my.sharepoint.com/:w:/g/personal/it22098078_my_sliit_lk/IQAtush4QjzLT6LJM3UgJATGAazsTg7NwkrGf7pguihZh4I?e=t2iDvn",
      embed: "",
      status: "available",
      date: ""
    },
    {
      id: "final-common",
      group: "Final Documents",
      title: "Final Report - Common Integrated Report (Main)",
      description: "The integrated report covering the complete seven-agent pipeline and the team's evaluation.",
      type: "PDF",
      url: "",
      embed: "",
      status: "pending",
      date: ""
    },
    {
      id: "final-santhuka",
      group: "Final Documents",
      title: "Final Report - Santhuka D.N.M.D. (IT22098078)",
      description: "Requirement generation, domain enrichment and checkpointed orchestration.",
      type: "PDF",
      url: "",
      embed: "",
      status: "pending",
      date: ""
    },
    {
      id: "final-sansala",
      group: "Final Documents",
      title: "Final Report - Sansala T.G.B.D. (IT22174826)",
      description: "Architecture planning and UI/UX design generation.",
      type: "PDF",
      url: "",
      embed: "",
      status: "pending",
      date: ""
    },
    {
      id: "final-dissanayake",
      group: "Final Documents",
      title: "Final Report - Dissanayake T.C. (IT22157232)",
      description: "Code generation with sandboxed verification.",
      type: "PDF",
      url: "",
      embed: "",
      status: "pending",
      date: ""
    },
    {
      id: "final-oberathna",
      group: "Final Documents",
      title: "Final Report - Oberathna R.D.T.D. (IT22102478)",
      description: "Security analysis and quality assurance.",
      type: "PDF",
      url: "",
      embed: "",
      status: "pending",
      date: ""
    }
  ],

  /* ------------------------------------------------------- PRESENTATIONS */
  presentations: [
    {
      id: "proposal-slides",
      title: "Proposal Presentation",
      description: "The problem, the research gap, the seven-agent idea and the plan for each member's component.",
      url: "https://mysliit-my.sharepoint.com/:p:/g/personal/it22098078_my_sliit_lk/IQCtM4FxygqkS6IL4ZQNTvusARTUEqbOwEB3n68yQrHaNAA?e=4uRlOz",
      embed: "",
      status: "available",
      date: ""
    },
    {
      id: "pp1-slides",
      title: "Progress Presentation 1",
      description: "Progress on each agent, the first working pipeline stages and the design of the approval gates.",
      url: "https://mysliit-my.sharepoint.com/:p:/g/personal/it22098078_my_sliit_lk/IQCGzWGqeZ7TT6QE4zEvQ4mYARCb5m9Gk90HG5ns3vxOALY?e=leVnYb",
      embed: "",
      status: "available",
      date: ""
    },
    {
      id: "pp2-slides",
      title: "Progress Presentation 2",
      description: "The integrated seven-agent pipeline, checkpointed orchestration and the first evaluation results.",
      url: "https://mysliit-my.sharepoint.com/:p:/g/personal/it22098078_my_sliit_lk/IQCUGnjYJXxnRqfKSXeFkRALAcjbJHBdNvXkt6x20DnIfmg?e=BfDIZp",
      embed: "",
      status: "available",
      date: ""
    },
    {
      id: "final-slides",
      title: "Final Presentation",
      description: "The complete system, the case study, the evaluation results and the demonstration.",
      url: "",
      embed: "",
      status: "pending",
      date: ""
    }
  ],

  /* ---------------------------------------------------------- MILESTONES
     Fill in `date` and `marks` when you have the official values.
     status: "completed" | "in-progress" | "upcoming"                     */
  milestones: [
    {
      id: "proposal",
      title: "Project Proposal",
      date: "",
      marks: "",
      status: "completed",
      summary: "Defines the research problem, the gap, the objectives and how the team will build and evaluate AutoForge.",
      assessed: [
        "Topic Assessment Form (TAF) and project charter",
        "Proposal document with literature survey and research gap",
        "Proposal presentation to the panel",
        "Individual component scope for each member"
      ],
      deliverables: ["taf", "proposal-group", "proposal-slides"]
    },
    {
      id: "pp1",
      title: "Progress Presentation 1",
      date: "",
      marks: "",
      status: "completed",
      summary: "The first progress review: each member shows the design and the first working version of their agents.",
      assessed: [
        "Progress against the proposal plan",
        "Design of each component and its interfaces",
        "Working demonstration of the implemented parts",
        "Completion check list"
      ],
      deliverables: ["pp1-slides", "checklist-1"]
    },
    {
      id: "pp2",
      title: "Progress Presentation 2",
      date: "",
      marks: "",
      status: "completed",
      summary: "The second progress review: the integrated pipeline running end to end with human approval gates.",
      assessed: [
        "Integration of all seven agents",
        "Checkpointed orchestration and approval flow",
        "Early evaluation results",
        "Completion check list"
      ],
      deliverables: ["pp2-slides", "checklist-2"]
    },
    {
      id: "paper",
      title: "Research Paper",
      date: "",
      marks: "",
      status: "in-progress",
      summary: "A research paper describing AutoForge and its evaluation, prepared for submission to a conference.",
      assessed: [
        "Contribution and positioning against related work",
        "Methodology and evaluation design",
        "Results and discussion"
      ],
      deliverables: ["paper"]
    },
    {
      id: "final",
      title: "Final Assessment",
      date: "",
      marks: "",
      status: "in-progress",
      summary: "The final report, the final presentation and a full demonstration of the completed system.",
      assessed: [
        "Common integrated report and four individual reports",
        "Final presentation and system demonstration",
        "Achievement of research objectives",
        "Commercialisation and sustainability considerations"
      ],
      deliverables: ["final-common", "final-santhuka", "final-sansala", "final-dissanayake", "final-oberathna", "final-slides"]
    },
    {
      id: "viva",
      title: "Viva",
      date: "",
      marks: "",
      status: "upcoming",
      summary: "An individual oral examination on each member's component, design decisions and results.",
      assessed: [
        "Understanding of the individual component",
        "Justification of design and technology choices",
        "Interpretation of results and limitations"
      ],
      deliverables: []
    }
  ]
};
