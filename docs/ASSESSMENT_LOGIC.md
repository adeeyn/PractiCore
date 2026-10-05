# PractiCore Assessment Logic: Resume-Based and Internship-Driven Competency Assessment

**Document type:** System design and methodology section
**Project:** PractiCore — Internship Screening and Recommendation System
**Purpose:** To specify, in implementable terms, how a student's competencies are determined, measured, and compared against internship requirements — so that the resulting recommendation rests on demonstrated evidence rather than self-declared claims.

---

## I. Main Assessment Concept

PractiCore does **not** issue every student the same fixed questionnaire. The assessment is *adaptive* and *competency-based*: the questions a student receives are determined by three inputs, and these inputs differ from student to student.

1. **The Student Resume** — what the student claims to be able to do.
2. **The Target Internship Requirements** — what the employer needs.
3. **Core Competencies** — a small fixed baseline assessed for everyone.

The complete processing flow is:

```
Student Resume
        |
        v
NLP / spaCy Resume Extraction
        |
        v
Extracted Skills and Qualifications
        |
        v
Competency Mapping
        |
        +<-- Internship Posting
        |          |
        |          v
        |   Internship Requirement Extraction
        |          |
        |          v
        |   Required Competency Mapping
        |
        v
Cross-Matching of Competencies
        |
        v
Question Selection
        |
        v
Competency Assessment
        |
        v
Scoring
        |
        v
Student Competency Profile
        |
        v
Internship Cross-Matching
        |
        v
Internship Recommendation and Ranking
```

Each stage is described in detail below. The stages that carry the most methodological weight are **Step 5 (Cross-Matching)** and **Step 9 (Competency Profile)**, because they are where the central claim of this system is enforced.

### 1.1 The central claim

> A skill named on a resume is a **claim**. A score obtained on an assessment is **evidence**. PractiCore treats these as different things and never lets the claim substitute for the evidence.

Every rule in this document follows from that statement. It is the reason a student who lists *React* is nonetheless assessed on *Web Development*, and the reason an internship requirement the student never mentioned still causes an assessment to be generated.

---

## II. Step 1 — Student Submits Resume

The student first submits a resume or CV. The document may contain:

- Technical skills
- Programming languages
- Software, frameworks and tools
- Certifications
- Educational background
- Projects
- Work or internship experience
- Other technical experience

**Example resume content:**

> **Technical Skills:** JavaScript, React, SQL, Git, Linux
>
> **Projects:** Developed a web-based inventory system; used a MySQL database; used Git for version control

### 2.1 The claim/evidence distinction

The information in a resume is **not** automatically treated as proof of competency. The system maintains an explicit two-term vocabulary:

| Term | Definition | PractiCore status |
|---|---|---|
| **Resume-declared skill** | A skill the student claims to know, or has listed experience with | Recorded as a *trigger* only |
| **Demonstrated competency** | What the student demonstrates through the assessment | The basis for scoring and ranking |

The consequence is deliberate: **the assessment is partly used to verify the competencies the student claims.** A resume can cause a competency to be assessed; it cannot cause a competency to be considered demonstrated.

PractiCore therefore never performs `resume_skills → assessment_result`. It performs:

```
resume + internship requirements + core competencies
        -> assessment competencies
        -> ASSESSMENT (measurement)
        -> competency scores
```

The resume influences *what gets asked*. It does not influence *how well the student scores*.

---



## III. Step 2 — NLP / spaCy Extraction

PractiCore uses NLP (spaCy) to process the resume and convert unstructured text into structured data. The system identifies relevant entities, keywords and noun phrases, including terms such as:

- JavaScript, Python, Java
- React, HTML, CSS
- SQL, MySQL, PostgreSQL
- Git
- Linux, Windows Server
- Cisco, TCP/IP, DNS
- Problem-solving, teamwork

### 3.1 Normalisation

Extracted terms are normalised before mapping, so that surface variants collapse onto a single canonical term:

| As written in the resume | Normalised to |
|---|---|
| `JS` | JavaScript |
| `MySQL database` | MySQL |
| `React.js` | React |
| `Github` | Git |
| `Node-JS` | Node.js |

### 3.2 Purpose

The purpose of this stage is to convert unstructured resume information into structured competency data. It is a *preparation* stage — it produces candidate skills, not conclusions.

**Worked example.**

Resume sentence:
> "Developed a web application using React, JavaScript, and MySQL."

| Stage | Output |
|---|---|
| Raw text | free-form sentence |
| Normalised skills | React, JavaScript, MySQL |
| Mapped competencies (Step 3) | Web Development, Programming, Database |

### 3.3 Design note

Extraction errors are **non-fatal by design**. A missed or mis-detected skill changes which competencies are assessed, but it cannot inflate a score, because the resume never contributes to scoring. This bounds the damage any extraction error can do.


## IV. Step 3 — Competency Mapping

Extracted skills are mapped into broader, assessable competencies. This is the vocabulary bridge that lets a free-text skill and an employer's requirement be compared at all.

| Resume Skill | Competency |
|---|---|
| JavaScript | Programming / Web Development |
| React | Web Development |
| SQL | Database |
| Git | Version Control / Software Development |
| Linux | Operating Systems / Technical Support |
| Cisco | Networking |

### 4.1 Many-to-one mapping

Multiple skills may evidence the same competency:

```
JavaScript + Python + Java          ->  Programming
SQL + MySQL + PostgreSQL            ->  Database
HTML + CSS + JavaScript + React     ->  Web Development
Linux + Windows Server + Unix       ->  Operating Systems
```

### 4.2 One-to-many mapping

A single skill may also evidence more than one competency. This is not a data error; it reflects genuine breadth. JavaScript is simultaneously web work and programming, so it is recorded under both:

```
JavaScript  ->  { Web Development: primary, Programming: primary }
```

### 4.3 Why this matters for question selection

Because mapping happens **before** question selection, the assessment system selects questions at the *competency* level rather than searching for exact keywords. A student who writes "JS", "Javascript" and "Node.js" receives one coherent Web Development and Programming assessment, not three overlapping keyword matches — and does not receive a disproportionate share of the assessment for having written more synonyms.

---

## V. Step 4 — Internship Requirement Analysis

PractiCore also analyses the internship posting. An employer may post a structure such as:

**Required Skills:** React, JavaScript, SQL, Git
**Preferred:** Problem-solving, Teamwork

The system maps these requirements into the **same competency vocabulary** used for the resume. Reusing one map for both sources is essential: it is what allows a competency the student never mentioned to still be compared against what the employer asked for.

| Internship requirement | Required competency |
|---|---|
| React | Web Development |
| JavaScript | Programming / Web Development |
| SQL | Database |
| Git | Version Control / Software Development |
| Problem-solving | Problem Solving |
| Teamwork | Communication & Teamwork |

### 5.1 Requirement importance

Each requirement is tagged:

| Importance | Meaning | Default pass threshold |
|---|---|---|
| `essential` | The employer treats this as non-negotiable | 60% |
| `preferred` | Desirable but substitutable | 50% |

This is what later allows a missing essential requirement to cost more than a missing preferred one, without hard-coding weights per posting.

### 5.2 Prose as well as lists

Postings frequently state a need in the description without listing it as a skill — *"must be able to troubleshoot and communicate with end users."* The description text is therefore searched for mapped terms as well as the structured skills list, so that prose requirements are not lost.

---


---


## VI. Step 5 — Cross-Matching Logic

> **This is the most important section of the document.**

PractiCore does not assess the student on the basis of the resume alone. It also considers what the internship requires. The three resulting groups are computed independently and then combined.

### 6.1 The three competency groups

**Group A — Resume-Based Competencies**
Competencies identified from the student's resume via extraction and mapping. These are *candidates for verification*, not results.

**Group B — Internship-Based Competencies**
Competencies required by the selected internship. These are the employer's needs, independent of whether the student mentioned them.

**Group C — Core Competencies**
A small set of baseline competencies assessed for every student regardless of resume or target role. This keeps the assessment from degenerating into a purely vacancy-driven test and guarantees comparable baseline coverage across the cohort.

### 6.2 Combination

```
assessment_competencies = CORE  ∪  RESUME_TRIGGERED  ∪  INTERNSHIP_REQUIRED
                           (duplicates removed)
```

**Worked example.**

| Input | Content |
|---|---|
| Resume | React, JavaScript, SQL, Git, Linux |
| Internship | React, JavaScript, SQL, Git, Problem-solving |
| Core | Programming, Problem Solving, Database, Networking, Communication |

Resulting assessment pool:

| Competency | Source(s) |
|---|---|
| Web Development | resume + internship |
| Programming | core + resume + internship |
| Database | core + resume + internship |
| Version Control / Software Development | resume + internship |
| Problem Solving | core + internship |
| Networking Fundamentals | core |
| Communication & Teamwork | core |
| Operating Systems | resume |

Note that **Problem Solving** was included even though the resume never mentions it, and **Operating Systems** was included even though the internship never asks for it — each is justified by a different source. This is the behaviour the design intends.

### 6.3 Deduplication and provenance

Where a competency is raised by more than one source it is stored **once**, and the set of sources is retained. Retaining provenance is what makes the selection explainable to a student, a panel and an employer: the system can always answer *"why was I asked about Operating Systems?"*

### 6.4 Bounding the assessment

Competencies that are entirely unrelated to both the resume and the target internship must not dominate the assessment. Two controls enforce this:

- **A relevance filter.** A competency enters the pool only if a source raised it. Nothing is added speculatively. A student targeting a Web Developer role is not assessed on advanced networking or cybersecurity merely because they are an IT student.
- **A cap on targeted competencies.** An internship demanding many skills could otherwise generate an unwieldy assessment. The number of *non-core* competencies is capped; the core is never capped. When trimming, competencies the posting actually asked for are retained first.

### 6.5 Adaptivity

Because the pool is rebuilt for a given target posting, the **same student** is assessed differently for different applications. For one student with React, JavaScript, SQL, Linux and Git:

- targeting a **Web Developer Intern** produces a pool weighted toward Web Development and Programming;
- targeting an **IT Support Intern** produces a materially different pool, weighted toward Operating Systems, Troubleshooting and Technical Support.

### 6.6 A trigger must have somewhere to fire

Selecting a competency is only half the job. A resume skill becomes an assessment
section only if the bank actually holds questions for that competency; otherwise
`build_master_assessment` files it under `shortfall`, serves nothing, and the
student is left holding a claim with no way to verify it.

This is not hypothetical. The 130-item researcher bank maps onto ten canonical
codes, while the taxonomy declares eighteen, so six competencies held **zero**
items:

| Competency | Reached by (examples) | Before |
|---|---|---|
| DATA | pandas, Power BI, Tableau, data analysis | 0 items |
| GIT | git, GitHub, GitLab, branching | 0 items |
| SYS | business analysis, BPMN, requirements gathering | 0 items |
| OOP | oop, SOLID principles, design patterns | 0 items |
| DSA | algorithms, Big-O, recursion, linked list | 0 items |
| CLOUD | aws, docker, devops, CI/CD, terraform | 0 items |

A resume naming *pandas* or *git* therefore selected a competency that could never
be measured, and the profile fell through to the evidence-only branch and
displayed the claim on its own.

`services/competency_coverage_bank.py` closes that gap with 10 items per
competency (60 total), loaded by `flask --app app seed-coverage-bank`. It adds
questions only — **no new competencies**. GIT in particular already exists in
`COMPETENCIES`, deliberately split out of DEV, so a second "Git" competency would
have forked the framework. Item codes use the `MB2-` prefix so seeding cannot
collide with the document's `MB-*` rows or the published `Q*`/`PF-*` questions.

Same scenario, after seeding — the reported case now measures both skills:

```
resume: pandas, power bi, git, python, java, sql
total: 45 questions   shortfall: none
DATA 7 | GIT 7 | DB 7 | PROG 7 | DEV 6 | COMM 4 | NET 4 | PROB 3
```

### 6.7 Competency status reflects assessment state, never a claim

`CompetencyRepository.assessment_state()` derives each competency's label from
what actually happened, using the published pool sizes to tell "still has to sit
this" apart from "there is nothing to sit":

| Condition | Status |
|---|---|
| A score exists | **Assessed** — percentage + strength band |
| No score, questions published | **Assessment Required** |
| No score, nothing published | **Not assessed** |

The band comes from `competency_scoring.strength_level_for`, configured through
`COMPETENCY_STRENGTH_BANDS` (0-59 Weak / 60-79 Moderate / 80-100 Strong) rather
than hard-coded in a template. A competency with no score gets **no band at
all**, because "not measured" must never render as a measured result.

`evidence_strength()` still returns `Claimed` for an uncorroborated claim, but it
is the **resume-evidence corroboration** ladder used by cross-matching, not the
competency's result — the profile UI renders `score_percent` / `status` instead.

Before an assessment, a resume naming pandas and Power BI reads:

```
Data & Analytics
Resume claims: pandas, power bi
Assessment Required
10 questions available
```

and after sitting the section, from the student's own answers:

```
Data & Analytics
Resume claims: pandas, power bi
29%   Weak
```

The claim and the score stay separate rows in separate tables
(`resume_competency_evidence` vs `student_competency_scores`), so a claim can
never be written into the score and a score can never manufacture a claim.

This is the behaviour that distinguishes PractiCore from a fixed questionnaire.


## VII. Step 6 — Question Selection

PractiCore maintains a question bank. Conceptually, each competency owns a pool of items — for example a JavaScript pool, a React pool, an SQL pool, a Git pool and a Problem-Solving pool. The system draws only from the pools relevant to the student's assembled competency set.

**Worked example.** If the final competency pool is:

```
Web Development, Programming, Database,
Software Development, Problem Solving, Communication
```

the system may allocate:

| Competency | Items |
|---|---|
| Web Development | 3 |
| Programming | 3 |
| Database | 3 |
| Software Development | 2 |
| Problem Solving | 2 |
| Communication | 1 |
| **Total** | **14** |

The exact allocation is a **researcher-configurable parameter**, not a fixed constant.

### 7.1 Factors governing allocation

The number of questions must **not** be a simple function of the number of resume keywords. The system instead considers:

| Factor | Effect on allocation |
|---|---|
| Competency relevance | Unrelated competencies receive nothing |
| Internship importance | Essential requirements may receive more items |
| Assessment coverage | The core still receives baseline coverage |
| Available question pool | A competency with few items cannot be over-sampled |
| Maximum assessment length | Total length is capped for usability and timing |

The last two constraints are important in practice: a competency is never allocated more items than its pool can supply, and the total is never allowed to grow without bound as postings become more specific.

## VIII. Question Selection Priority

A clear priority ordering governs how limited assessment length is spent.

| Priority | Group | Rationale |
|---|---|---|
| **1** | Required by the internship **and** supported by the resume | Most likely to matter, and the claim is worth verifying |
| **2** | Required by the internship but **not** demonstrated in the resume | The employer asked for it; the claim is absent or weak |
| **3** | Demonstrated in the resume and **relevant** to the target internship | Verifies a claim the student will actually rely on |
| **4** | Core competencies | Baseline coverage, allocated a limited but non-zero share |

### 8.1 Purpose of the priority

The purpose is to **prevent the system from spending most of the assessment on unrelated resume skills.** A resume may list twenty technologies; an internship needs four. Measuring the twenty would produce a profile largely irrelevant to the vacancy.

**Worked example.**

Student resume: React, SQL, Linux
Internship requirements: React, SQL, Git

| Competency | Priority | Reason |
|---|---|---|
| Web Development (React) | 1 | Internship requires it, resume supports it |
| Database (SQL) | 1 | Internship requires it, resume supports it |
| Software Development (Git) | 2 | Internship requires it, resume does not claim it |
| Operating Systems (Linux) | 3 | Resume-relevant but not required by this posting |
| Core competencies | 4 | Limited baseline allocation |

The result is that Git — a skill the student never claimed — is assessed precisely *because* the employer asked for it, while Linux, which the student did claim, is not allowed to monopolise the assessment.

---


---

---


## IX. Step 7 — Randomization and Anti-Cheating

PractiCore prevents a student from repeatedly receiving an identical questionnaire.

### 9.1 Parallel forms (the primary mechanism)

Every competency has **three equivalent question forms**: Set A, Set B, Set C. The sets must:

- measure the **same** competency;
- have **comparable difficulty**;
- use the **same scoring scale**;
- use **different wording and scenarios**;
- avoid simply repeating the same item;
- never reveal the set identity to the student.

**Worked example.**

> Competency: Web Development
> - **Set A** — scenario-based questions measuring web development
> - **Set B** — different wording and scenario, same competency and difficulty
> - **Set C** — different wording and scenario, same competency and difficulty

When an assessment is generated, **one set is randomly selected per competency**:

| Student | Web Development | Database | Problem Solving |
|---|---|---|---|
| Student 1 | Set B | Set A | Set C |
| Student 2 | Set C | Set B | Set A |
| Student 3 | Set A | Set C | Set B |

### 9.2 Item-level randomisation

Within the selected form, the system additionally:

1. maintains multiple questions per competency;
2. randomly selects items from the appropriate pool;
3. randomises question order;
4. randomises answer-choice order;
5. tracks previously used questions and forms;
6. avoids immediate repetition;
7. provides different questions on retakes wherever possible.

**Worked example** (SQL pool):

```
Attempt 1:  SQL-002, SQL-007, SQL-011
Attempt 2:  SQL-001, SQL-005, SQL-013
```

### 9.3 Retake protection

On a retake the system consults the student's exposure history and prefers a form the student has **not** previously seen. If every form has already been used, it selects the form seen **longest ago**, so rotation continues rather than defaulting to a repeat. Where a competency has fewer than three forms available, the best available form is used **and the shortfall is recorded and reported** — the system does not silently pretend three forms exist.

### 9.4 Design goal

The goal is explicitly **not** to create different competencies for every attempt. It is to create **different questions that measure the same competency**, so that a retake is a genuine re-measurement rather than either a memory test or a different test entirely.

---


## X. Step 8 — Assessment Scoring

### 10.1 Item marking

```
Correct answer   = 1 point
Incorrect answer = 0 points
```

### 10.2 Competency score

```
Competency Score = ( Correct Answers / Total Questions for that Competency ) × 100
```

**Worked example.**

```
SQL:    3 correct out of 4   ->  75%
React:  2 correct out of 3   ->  66.67%
```

A guard applies: a competency with zero items receives no score and is reported as *Not assessed*, rather than being recorded as 0%. A 0% and a blank are different facts.

### 10.3 Per-competency storage

Scores are stored **per competency**, not only as a single overall figure. The overall assessment score is a derived summary and is never the primary record.

**Resulting student competency profile:**

| Competency | Score |
|---|---:|
| Web Development | 80% |
| Programming | 75% |
| Database | 90% |
| Software Development | 70% |
| Problem Solving | 85% |

### 10.4 Attempt history

Each attempt retains the *latest* score per competency as the current value, and the *best* score ever achieved, together with an attempt count. A weaker retake therefore does not erase demonstrated ability, and a stronger retake is not discarded.

---

## XI. Proficiency Level

Competency scores are interpreted through configurable proficiency bands.

### 11.1 Proposed band definitions

| Score range | Proposed level |
|---|---|
| 90–100 | Advanced |
| 75–89 | Proficient |
| 60–74 | Developing |
| Below 60 | Needs Development |

### 11.2 Status of these thresholds

> **These thresholds are proposed system rules only.** They are researcher-defined defaults and **must be validated by the researchers and advisers before being adopted as final thresholds.**

They are **not** claimed to derive from SFIA, CompTIA, Google, Cisco, or any external certification body. They are a starting configuration for pilot testing, not a validated instrument. Any figure in this document that is presented as a threshold should be read as provisional until the validation study is complete.

The current implementation additionally distinguishes two lower bands — *Foundational* and *Below Foundational* — because a very low score and a zero score are not the same result, and collapsing them would misdescribe the data.

### 11.3 Configuration

Bands are held in a single configuration table so that the research team can revise them without altering scoring or matching logic.

---



## XII. Step 9 — Student Competency Profile

The assessment results are converted into a structured **Student Competency Profile**. This is the system's central output.

**Example — Student A:**

| Competency | Assessment score | Resume evidence | Evidence strength |
|---|---:|---|---|
| Web Development | 80% | React, JavaScript | Strong |
| Programming | 75% | JavaScript, Python | Strong |
| Database | 90% | SQL, MySQL | Strong |
| Software Development | 70% | Git | Moderate |
| Problem Solving | 85% | Project experience | Strong |
| Operating Systems | 55% | Linux | Weak |

### 12.1 Three distinct evidence types

The profile keeps three things separate:

| Evidence type | Origin | Contributes to score? |
|---|---|---|
| **Resume evidence** | NLP extraction from the submitted document | No — corroboration only |
| **Assessment evidence** | Performance on validated questions | **Yes — this is the score** |
| **Combined profile** | The two, held together with a strength label | Yes, but assessment-led |

### 12.2 Evidence strength

Each competency is assigned an interpretable strength label:

| Label | Condition |
|---|---|
| **Strong** | Score ≥ 70% **and** corroborated by resume evidence |
| **Moderate** | Score ≥ 70% with no corroboration, or ≥ 50% with corroboration |
| **Weak** | Score ≥ 50% with no corroboration, or a low score with corroboration |
| **Claimed** | Resume evidence exists but **no assessment was taken** |
| **None** | Neither |

### 12.3 Why this matters

This separation prevents the system from treating a resume claim as automatic proof of proficiency. The clearest illustration:

| Competency | Resume evidence | Assessment score | Demonstrated competency |
|---|---|---|---|
| React / Web Development | Yes | 80% | **80%** — verified, strong |
| Linux / Operating Systems | Yes | 55% | **55%** — claimed but weakly demonstrated |
| Kubernetes | Yes | *not assessed* | **Claimed only** — no evidence |

A resume listing a skill never raises the student's score, and never creates a competency record where none was measured. The *Claimed* label exists precisely so that a claim is visible to the employer while remaining clearly distinct from evidence.

---


## XIII. Step 10 — Competency-Based Internship Matching

The student competency profile is compared against the competency requirements of each internship posting.

### 13.1 The comparison

**Student profile**

| Competency | Score |
|---|---:|
| Web Development | 80% |
| Programming | 75% |
| Database | 90% |
| Software Development | 70% |
| Problem Solving | 85% |

**Internship A requirements:** Web Development, Programming, Database, Software Development, Problem Solving

The system compares the student's *demonstrated* score in each required competency against the requirement's pass threshold.

### 13.2 Conceptual compatibility calculation

```
Coverage =  Σ ( Student Competency Score × Importance Weight )
           ─────────────────────────────────────────────────
                     Σ ( Importance Weight )
```

**Step 1 — coverage.** Each required competency contributes the student's demonstrated
score, weighted by the employer's importance marking.

**Step 2 — corroboration.** Evidence strength is converted to a value on a fixed
scale, then averaged across the required competencies:

| Strength | Value |
|---|---:|
| Strong | 100 |
| Moderate | 75 |
| Weak | 45 |
| Claimed | 25 |
| None | 0 |

A required competency the student has **never been assessed in** contributes zero
coverage and zero evidence, and is reported as *Not assessed* — the posting asked
for it and no result exists. This is the mechanism that stops a resume claim from
standing in for a missing measurement.

### 13.3 Configurable employer weights

The formula above generalises to arbitrary employer weights, and this is the intended
extension:

```
Coverage =  Σ ( Student Competency Score × Requirement Weight )
           ─────────────────────────────────────────────────
                    Σ ( Requirement Weight )

Example requirement weights:
  Web Development     30%
  Programming         20%
  Database            20%
  Problem Solving     20%
  Software Development 10%
```

> **These percentage weights are proposed, not yet implemented.** The current system
> applies a two-level importance weight (`essential` = ×2, `preferred` = ×1) rather
> than per-competency percentages. Per-competency weighting requires an additional
> weight field on the posting requirements, and is listed as outstanding work in
> Section XX.2. The weights must be validated by the researchers for each posting
> before adoption.

### 13.4 Importance weighting (implemented)

| Importance | Multiplier | Rationale |
|---|---:|---|
| `essential` | ×2 | A missing essential requirement is materially worse |
| `preferred` | ×1 | Desirable but substitutable |

### 13.5 Combining assessment and evidence

The final compatibility score is **assessment-led**:

```
Compatibility =  0.70 × (required-competency coverage)
              +  0.30 × (resume evidence strength)
```

The assessment term is the only component capable of producing a high score. Resume
evidence is capped as corroboration and can never create coverage where none was
measured.

> The 70/30 split is a **proposed weighting** and, like the proficiency bands,
> requires researcher and adviser validation before being treated as final.

### 13.5 Scoping and transparency

Evidence strength is averaged **only across competencies the posting actually requires**. A strong claim in an area the employer did not ask about must not inflate the compatibility score, so it is excluded from the calculation entirely rather than averaged in.

Each match retains a per-competency breakdown recording the score, the requirement threshold, the evidence strength and whether the requirement was met. The recommendation screen displays this, so a student can see exactly which requirement is limiting their score.

---

## XIV. Why This Is Not Simple Keyword Matching

PractiCore differs fundamentally from keyword-based filtering.

### 14.1 Traditional keyword matching

```
Resume contains "React"
   -> Internship requires "React"
   -> Match = Yes
```

This approach has a known weakness: it produces a **boolean** answer. It cannot distinguish between a student who has written "React" once and a student who has built three production applications and scored 90% on an assessment of the underlying competency. Both produce `Match = Yes`. It also cannot distinguish between a genuine and a copied claim.

### 14.2 PractiCore's approach

```
Resume contains "React"
   +  Assessment demonstrates Web Development at 80%
   +  Internship requires Web Development
   ->  Compatibility score reflecting demonstrated, weighted evidence
```

The system combines:

```
Resume evidence  +  Assessment evidence  +  Internship requirements
```

to produce a **graded, explainable** compatibility score rather than a boolean match.

### 14.3 Practical consequences

| Scenario | Keyword matcher | PractiCore |
|---|---|---|
| Claims React, no assessment | Match | *Claimed* — low evidence weight |
| Claims React, scores 20% | Match | Low compatibility — claim contradicted |
| Claims React, scores 95% | Match | High compatibility — claim verified |
| No React, scores 95% | No match | High compatibility — evidence over claim |
| Internship needs React, resume silent | No match | Assessed and matched on the requirement |

The fourth and fifth rows are the decisive ones. PractiCore can recommend a student who never mentioned a skill but demonstrated it, and can decline to recommend a student who claimed a skill and then failed to demonstrate it. A keyword matcher can do neither.

---

Each match retains a per-competency breakdown recording the score, the requirement threshold, the evidence strength and whether the requirement was met. The recommendation screen displays this, so a student can see exactly which requirement is limiting their score.


## XV. Pathway Role

### 15.1 Supported pathways

| Code | Pathway |
|---|---|
| **WMA** | Web Application Development |
| **NA** | Network Administration |
| **CS** | Computer Science |
| **TSM** | Technical Support Management |
| **IS** | Information Systems |

### 15.2 Pathway is contextual, not a filter

> **The pathway must NOT be used as a hard filter.**

The rationale is straightforward: a BSIT student under **WMA** may have strong networking skills, and a student under **NA** may have strong programming skills. Programme enrolment is a poor predictor of individual capability, and filtering on it would exclude demonstrably suitable candidates before any evidence was examined.

Therefore:

| Role | Function |
|---|---|
| **Pathway** | Contextual information — used for reporting, grouping and cohort analysis |
| **Competency** | The actual matching evidence used for scoring and ranking |

**Demonstrated competency has greater influence than the pathway label.** A WMA student who scores 90% on Networking Fundamentals is a stronger candidate for a network role than an NA student who has not been assessed in that area — and the system will rank them accordingly.

This is enforced structurally: the assessment-selection function accepts no pathway, programme, degree, major or year-level argument, so a pathway value cannot enter the selection logic even by accident.

---

---


## XVI. Complete End-to-End Example

This section traces a single student through every stage, explaining each transition.

### 16.1 Student resume

> "Developed a web-based inventory system using React and JavaScript. Used MySQL for data storage and Git for version control."

### 16.2 NLP extraction (Step 2)

| Stage | Result |
|---|---|
| Entity recognition | React, JavaScript, MySQL, Git |
| Normalisation | React, JavaScript, MySQL, Git |
| Structured output | 4 extracted skills |

**Transition:** free text → 4 discrete skill tokens.

### 16.3 Competency mapping (Step 3)

| Extracted skill | Competency |
|---|---|
| React | Web Development |
| JavaScript | Programming, Web Development |
| MySQL | Database |
| Git | Software Development (Version Control) |

**Result:** 4 skills → **4 competencies** (Web Development, Programming, Database, Software Development). Note the compression in the other direction: two skills map into one competency, which is why questions are drawn per competency rather than per keyword.

### 16.4 Target internship (Step 4)

| Requirement | Importance | Required competency |
|---|---|---|
| React | essential | Web Development |
| JavaScript | essential | Programming, Web Development |
| SQL | essential | Database |
| Git | preferred | Software Development |
| Problem-solving | preferred | Problem Solving |
| Teamwork | preferred | Communication & Teamwork |

### 16.5 Cross-matched competency pool (Step 5)

| Competency | Raised by | Priority |
|---|---|---|
| Web Development | resume + internship | 1 |
| Programming | core + resume + internship | 1 |
| Database | core + resume + internship | 1 |
| Software Development | resume + internship | 1 |
| Problem Solving | core + internship | 2 |
| Communication & Teamwork | core + internship | 2 |
| Networking Fundamentals | core | 4 |

**Transition:** 4 resume skills + 6 requirements + 5 core competencies → **7 deduplicated competencies**, each retaining its source provenance.

### 16.6 Question allocation (Step 6)

| Competency | Items |
|---|---:|
| Web Development | 3 |
| Programming | 3 |
| Database | 3 |
| Software Development | 2 |
| Problem Solving | 2 |
| Communication | 1 |
| **Total** | **14** |

Each competency receives one randomly selected parallel form (A, B or C), and the chosen form is recorded in the exposure history.

### 16.7 Scoring (Step 8)

| Competency | Result | Score |
|---|---|---:|
| Web Development | 5 of 6 | 83% |
| Programming | 6 of 8 | 75% |
| Database | 4 of 6 | 67% |
| Software Development | 2 of 2 | 100% |
| Problem Solving | 4 of 5 | 80% |
| Communication | 1 of 1 | 100% |

### 16.8 Student competency profile (Step 9)

| Competency | Assessment | Resume evidence | Strength |
|---|---:|---|---|
| Web Development | 83% | React, JavaScript | Strong |
| Programming | 75% | JavaScript | Strong |
| Database | 67% | MySQL | Moderate |
| Software Development | 100% | Git | Strong |
| Problem Solving | 80% | Project experience | Strong |
| Communication | 100% | — | Moderate |

### 16.9 Internship compatibility (Step 10)

**Step 1 — required-competency coverage.** Each required competency contributes its
demonstrated score, weighted by importance:

| Competency | Score | Importance | Weight |
|---|---:|---|---:|
| Web Development | 83 | essential | ×2 |
| Programming | 75 | essential | ×2 |
| Database | 67 | essential | ×2 |
| Problem Solving | 80 | preferred | ×1 |
| Software Development | 100 | preferred | ×1 |

```
Coverage = (83×2 + 75×2 + 67×2 + 80×1 + 100×1) / (2+2+2+1+1)
         = (166 + 150 + 134 + 80 + 100) / 8
         = 630 / 8 = 78.75  ->  79
```

Note that the strong 100% in Software Development carries **less** weight than the
67% in Database, because the employer marked Database essential and Software
Development preferred. Weighting by importance is what makes a mediocre score in a
critical competency rank below a strong score in a secondary one.

**Step 2 — evidence corroboration**, averaged over the required competencies only:

```
Evidence = (100 + 100 + 75 + 100 + 100) / 5 = 95
```

**Step 3 — combination**

```
Compatibility = 0.70 × 79 + 0.30 × 95 = 55.3 + 28.5 = 83.8  ->  84%
```

**Scoping rule:** a competency the posting does not require is excluded from both
terms. A strong claim in an area the employer did not ask about must not inflate
the score.

The student is recommended, and the breakdown shows precisely which competency is
weakest and most costly (Database, 67% and essential) — the actionable feedback the
student needs.

## XVII. Database / System Logic

### 17.1 Entity structure

| Entity | Purpose | Key relationships |
|---|---|---|
| `students` | Student account and programme context | 1 → many resumes, attempts |
| `resumes` | Uploaded document and metadata | 1 student → many |
| `extracted_skills` | NLP output per resume | 1 resume → many |
| `competencies` | The assessed competency taxonomy | referenced by all |
| `competency_skill_map` | Skill ↔ competency, with strength | many-to-many |
| `resume_competency_evidence` | What the resume **claims** | student ↔ competency |
| `internship_postings` | Employer vacancy | 1 → many requirements |
| `internship_competency_requirements` | What the posting **requires** | posting ↔ competency |
| `question_sets` | Parallel forms A/B/C | 1 competency → 3 forms |
| `assessment_questions` | The question bank | belongs to one form |
| `assessment_attempts` | One sitting | student, optional posting |
| `attempt_competencies` | Per-competency result + form used | attempt ↔ competency |
| `question_exposure_history` | Which form a student has seen | anti-repeat ledger |
| `student_competency_scores` | Durable demonstrated profile | student ↔ competency |
| `compatibility_scores` | Cached per-student/posting result | student ↔ posting |

### 17.2 Relationship flow

```
Student
  -> Resume
      -> Extracted Skills
          -> Competencies  (via competency_skill_map)

Internship
  -> Required Skills
      -> Required Competencies  (via internship_competency_requirements)

Student Competencies + Internship Competencies + Core Competencies
  -> Assessment Selection

Assessment Answers
  -> Per-Competency Scores  (attempt_competencies)
      -> Student Competency Scores

Competency Scores + Internship Requirements
  -> Compatibility Score  (compatibility_scores)
      -> Recommendation / Ranking
```

### 17.3 A deliberate separation

`resume_competency_evidence` and `student_competency_scores` are **two separate tables, not one**.

| Table | Contains | Can it raise a score? |
|---|---|---|
| `resume_competency_evidence` | Skills named on a resume | **No** |

## XVIII. Final Flow Diagram

```
                            STUDENT
                               |
                               v
                     RESUME SUBMISSION
                               |
                               v
                    NLP / SPACY EXTRACTION
                               |
                               v
                      SKILL NORMALIZATION
                               |
                               v
                       COMPETENCY MAPPING
                               |
              +----------------+----------------+
              |                                 |
              |          INTERNSHIP POSTING     |
              |                |                |
              |                v                |
              |   INTERNSHIP REQUIREMENT        |
              |        EXTRACTION               |
              |                |                |
              |                v                |
              |   REQUIRED COMPETENCY MAPPING   |
              |                |                |
              +----------------+----------------+
                               |
                               v
                       CROSS-MATCHING
                               |
                               v
        RESUME  +  INTERNSHIP  +  CORE COMPETENCIES
              (deduplicated, provenance kept)
                               |
                               v
                   QUESTION BANK SELECTION
                               |
                               v
            RANDOMIZED ASSESSMENT (Set A / B / C)
                               |
                               v
                     ASSESSMENT SCORING
                               |
                               v
                   COMPETENCY PROFILE
                       (score + evidence,
                        held separately)
                               |

## XIX. Important Design Principles

1. **Resume skills are claims, not automatic proof of competency.** They determine *what is assessed*, never *how well the student scores*.
2. **Assessment questions must be based on established competency sources.** Items are developed against documented competency frameworks and their provenance is retained with each item.
3. **Questions must be researcher-developed and validated.** Parallel forms require expert review and pilot testing before use.
4. **Internship requirements influence which competencies are assessed.** A requirement the student never mentioned still generates an assessment.
5. **Core competencies provide baseline coverage.** Every student receives comparable foundational measurement.
6. **The assessment should be adaptive, not completely fixed.** The same student is assessed differently for different target roles.
7. **Multiple questions must exist per competency** to support meaningful randomisation.
8. **Retakes should use different questions whenever possible**, preferring an unseen form and recording the shortfall when forms are unavailable.
9. **Competency scores must be stored individually**, never only as one overall figure.
10. **Pathway provides context, not a hard filter.** Demonstrated competency outweighs the programme label.
11. **Recommendation must consider both demonstrated competency and internship requirements**, with the assessment weighted above self-reported evidence.
12. **All scoring thresholds and weights must be configurable and validated by the researchers** before adoption.

---

## XX. Implementation Status

This section records the current state of the system honestly, so that the document and the software do not diverge.

### 20.1 Implemented and verified

| Component | Status |
|---|---|
| Competency taxonomy — 14 competencies, 5 core | Implemented |
| Skill-to-competency map — 91 skills | Implemented |
| Skill-to-competency and requirement-to-competency mapping | Implemented |
| Cross-matching with deduplication and provenance | Implemented, tested |
| Adaptive selection per target posting | Implemented, tested |
| Relevance filter and targeted-competency cap | Implemented, tested |
| Parallel form selection (A/B/C) with retake rotation | Implemented, tested |
| Exposure history ledger | Implemented |
| Per-competency scoring and evidence strength | Implemented, tested |
| Weighted cross-matching with importance weighting | Implemented, tested |
| Database schema — 10 new tables | Applied and verified |
| Live assessment routes (start, submit, results) | Rewired to the adaptive engine |
| Student-facing explanation of the selection | Implemented on the start screen |
| Requirement that pathway is never a hard filter | Enforced structurally and tested |

All 143 automated tests pass. The live path was exercised end to end against the
database: an assessment is built, a perfect submission is graded, the attempt and
per-competency results are persisted, and the resulting profile reads back
correctly. Adaptivity was confirmed with a web-leaning resume — targeting Full
Stack Web yields 14 questions across 7 competencies, while targeting IT Support
yields 20 across 10, and Troubleshooting appears only in the support variant.

### 20.2 Known gaps

| Gap | Detail | Impact |
|---|---|---|
| **Per-competency employer weights not implemented** | Matching uses two-level importance (`essential`/`preferred`), not the percentage weights shown in Section 13.3 | Employers cannot yet express a fine-grained priority between two required competencies |
| **Five competencies have only Form A** | `NET`, `SEC`, `DATA`, `SYS`, `EVID` have a single question form | Retake protection is weaker for those competencies; they are still assessed, but a retake may repeat the form |
| **Thresholds unvalidated** | Bands, weights and the 70/30 split are provisional | Must be validated before being reported as findings |

### 20.3 Outstanding work

1. Author parallel Form B and Form C items for Networking, Cybersecurity, Data & Analytics, Systems Analysis and Evidence.
2. Add a per-competency weight column to `internship_competency_requirements` to support employer-specified weights (Section 13.3).
3. Retire the legacy `AssessmentService.build()` once no caller remains; it is currently retained only for the overall summary score on the dashboard.
4. Run the validation study to confirm or revise the proposed thresholds and weights.

---

## Conclusion

The purpose of the PractiCore assessment is **not simply to test what a student knows.**

It is to generate a **structured competency profile** — in which demonstrated evidence and self-reported claims are held as distinct, separately weighted things — that the system can then use to cross-match students with internship opportunities on a defensible basis.

Every design decision described in this document follows from that objective.

                               v
                  INTERNSHIP COMPATIBILITY
                               |
                               v
                 RECOMMENDATION / RANKING
```

---

| `student_competency_scores` | Performance on the assessment | Yes |

This is a structural guarantee, not a coding convention. A bug in the resume parser cannot leak a claim into the score, because the claim is never stored in the same place as the score. A reviewer inspecting the schema can verify the claim/evidence separation without reading the scoring code.

---


---
