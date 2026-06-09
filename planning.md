# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

--- For the purposes of this project, I chose the Academic domain and helping incoming and current students at the university of central florida answer class related questions, reviews on professors / classes as well as acadmic advisor related questions. The information is difficult to find otherwise since the information is often times stored in random sites containing a lot of information or there are informal reviews from students themselves which are not present in the official documents / scattered across various platforms. 

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | RMF | Used to gather overall ratings / reviews on university overall | https://www.ratemyprofessors.com/school/1082 
| 2 | RMF | Used to gather overall ratings / reviews on specific professors at UCF | https://www.ratemyprofessors.com/search/professors/1082?q=*
| 3 | UCF Subreddit (Academic Filter) | Used to gather overall ratings / reviews on specific courses / thoughts on courses at UCF | https://www.reddit.com/r/ucf/?f=flair_name%3A%22Academic%20%E2%9C%8F%EF%B8%8F%22 
| 4 | UCF Simple Syllabus Repository | Used to gain information regarding specific information about various courses at UCF offered by specific professors | https://ucf.simplesyllabus.com/en-US/syllabus-library 
| 5 | Undergraduate Catalog | Contains information regarding official Academic Advising documents | https://www.ucf.edu/catalog/undergraduate/#/content/66bcc88ff93938001c54838a 
| 6 | Undergraduate Catalog | Contains information regarding official services for Academic Advancement and Success | https://www.ucf.edu/catalog/undergraduate/#/content/66bcc898f93938001c5483da
| 7 | Undergraduate Catalog | Contains information regarding Student Financial Assistance and information regarding student aid | https://www.ucf.edu/catalog/undergraduate/#/content/66bcc898f93938001c5483dc
| 8 | Undergraduate Catalog | Contains information regarding Undergraduate Admissions including orientations, applicant requirements etc | https://www.ucf.edu/catalog/undergraduate/#/content/66bcc898f93938001c5483db
| 9 | Undergraduate Catalog | Contains information regarding University Campus Resources | https://www.ucf.edu/catalog/undergraduate/#/content/66bcc88df93938001c54837a
| 10 | Undergraduate Catalog | Contains information regarding Academic Programs and Research Institudes at UCF | https://www.ucf.edu/catalog/undergraduate/#/content/66bcc88df93938001c54837b

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
