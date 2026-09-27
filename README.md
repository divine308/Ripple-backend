# Ripple

### See the impact before you change the code.

Ripple is a developer workflow built around **IBM Bob and the Model Context Protocol (MCP)** for understanding what a code change can affect before it is implemented.

A developer shouldn't have to make a change, run the application, wait for something to break, then start tracing backwards through a codebase to figure out why.

Ripple gives Bob the context to do that work first.

It connects **IBM Bob** to a repository-aware code intelligence layer that builds a graph of the codebase, traces relationships between files and symbols, simulates proposed changes, and turns the results into a practical verification plan.

The idea is simple:

> **Don't just ask what the code does. Ask what changes when the code changes.**

---

## Bob is at the center

Ripple is not an AI chatbot with a code graph attached to it.

**IBM Bob is the interaction layer at the center of Ripple.**

Through MCP, Bob can access Ripple's repository intelligence and use it as part of a developer's workflow.

```text
                    IBM Bob
                       │
                       │ MCP
                       ▼
              ┌─────────────────┐
              │      Ripple     │
              │  Code Intelligence
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
         Code Graph        Impact Engine
              │                 │
              └────────┬────────┘
                       ▼
                  Repository
```

This means Bob doesn't have to reason about a repository from isolated files alone.

Ripple gives Bob structured information about how the repository is connected and what a proposed change could touch.

---

# The Problem

Codebases are connected systems.

A function can have callers you forgot about.
A component can be imported in places you didn't know existed.
A seemingly harmless rename can break references.
A shared module can affect multiple parts of an application.
A test may be the only thing revealing that a dependency was important.

The problem isn't always writing the change.

The problem is knowing **the boundary of the change**.

Ripple is built to make that boundary visible.

---

# How Ripple Works

Ripple follows a developer through six stages:

```text
Understand
    ↓
Predict
    ↓
Simulate
    ↓
Change
    ↓
Verify
    ↓
Report
```

Each stage feeds the next instead of treating code analysis as a one-off graph visualization.

---

## 1. Understand

Ripple first builds an understanding of the connected repository.

The backend scans the repository and constructs a code graph representing relationships discovered across the codebase.

These relationships can include:

* Imports
* Dependencies
* Function calls
* Symbol references
* Modules
* Tests
* Exposed relationships

The result is a machine-readable representation of how the repository is actually connected.

---

## 2. Predict

Once the repository has been mapped, Ripple can investigate the area surrounding a target file, symbol, function, or module.

Instead of stopping at:

> "This file imports X."

Ripple can follow the surrounding relationships and identify what sits downstream of the target.

That provides the basis for predicting a change's potential blast radius.

---

## 3. Simulate

This is where Ripple moves from inspection to **change intelligence**.

A developer can describe a proposed change without modifying the repository.

Ripple currently supports simulations such as:

* **Modify**
* **Delete**
* **Rename**
* **Add**

The simulation traverses the repository graph and classifies potential consequences into categories such as:

### Direct impact

Code immediately connected to the target.

### Indirect impact

Code reached through downstream relationships.

### Potentially broken

Areas where the proposed change could invalidate an existing relationship.

### Tests to rerun

Tests connected to the affected area that should be considered during verification.

The purpose isn't to claim that every predicted dependency will definitely break.

It is to give the developer a concrete map of **where to look before making the change**.

---

# Ripple Map

The Ripple Map provides a visual view of the repository's relationships.

Developers can explore how code elements connect instead of navigating the project entirely through folders and files.

The graph becomes the foundation for the rest of Ripple.

It is not the final product.

---

# Ripple Analysis

Ripple Analysis takes a target inside the repository and examines its surrounding relationships.

It can be used to investigate:

* Dependencies
* Call relationships
* References
* Connected modules
* Potential downstream impact
* Related tests

The analysis gives Bob and the developer structured evidence to work from.

---

# Ripple Simulation

Ripple Simulation answers a more specific question:

> **"If I make this change, what could be affected?"**

A proposed change is applied conceptually to the graph rather than directly to the source code.

Ripple then follows the relationships around the target and produces a change-impact view.

This makes simulation useful before implementation, especially for changes involving shared or highly connected code.

---

# Verification

Knowing what might be affected is only half of the problem.

Ripple also turns impact information into a verification workflow.

After a proposed change, the developer can identify:

* Relevant affected areas
* Dependencies worth checking
* Potentially broken relationships
* Tests that should be rerun

The objective is to make verification targeted instead of blindly testing an entire repository and hoping the important failure appears.

---

# Ripple Report

Ripple brings the results together into a readable change report.

A report can communicate:

* The proposed change
* The target
* Direct impact
* Indirect impact
* Potentially affected areas
* Dependencies
* Verification targets
* Tests to consider
* Risk-related findings

The report is designed to answer one practical question:

> **What should I pay attention to because of this change?**

---

# MCP: The Bridge Between Bob and Ripple

The **Model Context Protocol** is what connects Bob to Ripple's capabilities.

Ripple exposes repository and analysis functionality through its MCP server so that Bob can request structured information when it needs it.

The integration is designed around tools such as:

```text
ripple_repository_summary
ripple_get_graph
ripple_dependency_analysis
ripple_analyze_impact
ripple_risk_analysis
ripple_verification_analysis
ripple_run_all_agents
ripple_get_file
```

The important part is not the number of tools.

It is the separation of responsibilities:

```text
Bob
│
│ decides what information is needed
│
▼
MCP
│
│ provides the interface
│
▼
Ripple
│
│ performs repository analysis
│
▼
Code Graph + Analysis Engine
│
▼
Repository evidence
```

Bob remains the developer-facing intelligence layer.

Ripple supplies the repository-specific structure and analysis that Bob can work with.

---

# Why MCP Matters

Without an integration layer, an AI coding assistant and a repository analysis system are separate experiences.

With MCP, Ripple can expose its capabilities directly to Bob.

That creates a much tighter workflow:

**Developer → Bob → Ripple → Repository → Ripple → Bob → Developer**

The developer doesn't have to manually copy graph information, dependency lists, or analysis results into a conversation.

Bob can retrieve the relevant Ripple context through the MCP interface.

---

# Ripple Agents

Ripple also includes specialized analysis capabilities that can operate across different parts of the workflow.

These capabilities can contribute to:

* Repository understanding
* Impact analysis
* Risk analysis
* Verification
* Combined change analysis

The agents work with the repository intelligence rather than treating the repository as an unstructured text dump.

---

# Repository-Agnostic by Design

Ripple is not built around one specific application.

A connected repository becomes the subject of analysis.

The code graph is generated from what Ripple discovers inside that repository, allowing the same workflow to be applied across different codebases.

The test repository is only a test repository.

**Ripple is the product.**

---

# Architecture

Ripple is split into a React frontend and a FastAPI backend.

### Frontend

The frontend provides the developer workspace:

* Repository connection
* Codebase exploration
* Ripple Map
* Ripple Analysis
* Ripple Simulation
* Verification
* Reports
* Bob interface
* Agent interface

Built with:

* React
* Vite
* JavaScript / JSX
* Tailwind CSS
* Lucide React
* React Router

### Backend

The backend provides the repository intelligence layer:

* Repository scanning
* Code graph construction
* Dependency analysis
* Impact analysis
* Change simulation
* Risk analysis
* Verification analysis
* Repository summaries
* File retrieval
* MCP server

Built with:

* Python
* FastAPI
* NetworkX
* Pydantic
* Uvicorn
* MCP

---

# Project Structure

Ripple is maintained as two repositories.

```text
Ripple
│
├── Ripple Frontend
│   ├── React
│   ├── Vite
│   ├── Tailwind CSS
│   ├── Ripple Map
│   ├── Ripple Analysis
│   ├── Ripple Simulation
│   ├── Verification
│   ├── Reports
│   ├── Bob
│   └── Agents
│
└── Ripple Backend
    ├── FastAPI
    ├── Repository Scanner
    ├── Code Graph
    ├── Impact Engine
    ├── Simulation
    ├── Verification
    ├── Risk Analysis
    └── MCP Server
```

---

# Technology Stack

| Layer                  | Technology       |
| ---------------------- | ---------------- |
| Developer Intelligence | IBM Bob          |
| Tool Integration       | MCP              |
| Frontend               | React            |
| Build Tool             | Vite             |
| Language               | JavaScript / JSX |
| Styling                | Tailwind CSS     |
| Icons                  | Lucide React     |
| Backend                | Python           |
| API                    | FastAPI          |
| Code Graph             | NetworkX         |
| Validation             | Pydantic         |
| Server                 | Uvicorn          |

---

# Running Ripple Locally

## Backend

Create and activate a Python virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

Start the backend:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Ripple's backend will be available at:

```text
http://127.0.0.1:8000
```

---

## Frontend

Install the frontend dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

---

# Repository Links

## Frontend

[GitHub — Ripple Frontend](https://github.com/divine308/Ripple-frontend)

## Backend

[GitHub — Ripple Backend](https://github.com/divine308/Ripple-backend)

---

# The Core Idea

Ripple is built around a simple shift in how developers think about changes.

Most development tools help answer:

> **"What is this code?"**

Ripple is focused on:

> **"What happens if I change this code?"**

With **IBM Bob at the center**, **MCP connecting Bob to Ripple**, and a repository-aware graph underneath, Ripple turns that question into something a developer can investigate before touching the code.

**Understand the code.
Predict the impact.
Simulate the change.
Verify what matters.**

That's Ripple.
