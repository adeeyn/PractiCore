"""Supplementary question items for competencies the 130-item master bank omits.

Why this module exists
----------------------
The researcher document (master_bank_document.ITEMS) covers thirteen constructs
that map onto ten canonical codes: PROG, WEB, DB, SUPP, NET, OS, SEC, EVID,
COMM, PROB. The competency taxonomy declares eighteen. Six therefore held ZERO
assessment items:

    DATA  (pandas, Power BI, Tableau)      SYS    (business analysis, BPMN)
    GIT   (git, GitHub, branching)         OOP    (classes, SOLID, patterns)
    DSA   (algorithms, Big-O, recursion)   CLOUD  (AWS, Docker, CI/CD, IaC)

That gap is not cosmetic. A resume skill is only ever a TRIGGER: it causes a
competency to be VERIFIED. For these six codes the trigger had nothing to fire
into, so build_master_assessment filed them under `shortfall`, served zero
questions, and the student was shown the claim alone. Mapping them to questions
is what turns "Claimed" into a measured score.

Design constraints honoured
---------------------------
* NO new competencies. These six already exist in competency_taxonomy.COMPETENCIES
  (GIT was deliberately split out of DEV there), so this module adds questions
  only. Creating a second "Git" competency would fork the framework.
* Same row shape as the master bank, written by the same seeder, so
  master_selection picks them up through question_pool_by_competency() with no
  change to the selection engine.
* Ten items per competency, matching the master bank's depth. With a 40-50
  question attempt drawing 2-13 per competency, ten items is what makes
  "prefer unseen items on a retake" (pick_items/_staleness_rank) meaningful.
* Item codes are MB2-<CODE>-<nn>, a different family from the document's MB-*,
  so seeding never collides with an existing row and never rewrites one.
* Scenario-based wherever the construct is an applied or workplace skill, and
  the keyed option is always the one the explanation restates. verify_keys()
  adjudicates keys by explanation support, so a key that contradicts its own
  rationale is withheld rather than served.
"""
import random

# Short course_track code per competency (SkillTaxonomy.DOMAIN_TRACK_CODES).
TRACK_BY_COMPETENCY = {
    "DATA": "DATA", "SYS": "SYS", "GIT": "DEV",
    "OOP": "DEV", "DSA": "DEV", "CLOUD": "NET",
}

# Provenance recorded on every row. These items were written for this system
# against the frameworks cited in standard_ref; they are NOT extracted from the
# researcher document and must never claim to be.
SOURCE_TYPE = "Framework-Derived"
VALIDATION = "PractiCore-authored; pending expert review"

# The competencies this module is responsible for. The seeder reports what was
# already present, so it can never quietly duplicate a bank that already exists.
COVERED_COMPETENCIES = ("DATA", "SYS", "GIT", "OOP", "DSA", "CLOUD")

# (code, competency, sub_competency, type, difficulty,
#  question, (A, B, C, D), key, explanation, standard_ref)
ITEMS = [
    # ---------------- Data & Analytics ----------------
    ("MB2-DATA-01", "DATA", "Data quality", "Scenario-Based Multiple Choice", "medium",
     "You merge two sales spreadsheets for a monthly report. The same order ID appears "
     "twice with different totals. What should you do before publishing the report?",
     ("Publish both rows so no revenue is hidden",
      "Investigate the duplicate rows and reconcile them against the source system",
      "Average the two totals for every duplicated order",
      "Delete the order ID column so the rows no longer match"),
     "B", "Investigate the duplicate rows and reconcile them against the source system",
     "Google Data Analytics; data quality"),
    ("MB2-DATA-02", "DATA", "Data cleaning", "Multiple Choice", "easy",
     "In pandas, which operation returns the number of missing values per column?",
     ("df.shape", "df.isnull().sum()", "df.describe()", "df.dtypes"),
     "B", "df.isnull().sum()",
     "pandas documentation; missing data"),
    ("MB2-DATA-03", "DATA", "Visualisation", "Multiple Choice", "medium",
     "A chart shows sales by month. The y-axis starts at 90 instead of 0. What is the "
     "most likely consequence?",
     ("Small differences look far larger than they are",
      "The chart becomes easier to read",
      "The data becomes more accurate",
      "The months become unordered"),
     "A", "Small differences look far larger than they are",
     "Data visualisation practice; axis integrity"),
    ("MB2-DATA-04", "DATA", "Interpretation", "Scenario-Based Multiple Choice", "hard",
     "Your dashboard shows a strong correlation between ice cream sales and drownings. "
     "What is the defensible conclusion?",
     ("Eating ice cream causes drowning",
      "A third variable, such as hot weather, likely explains both",
      "The correlation proves the relationship is causal",
      "The sample size is too small to say anything"),
     "B", "A third variable, such as hot weather, likely explains both",
     "Google Data Analytics; correlation vs causation"),
    ("MB2-DATA-05", "DATA", "Data preparation", "Multiple Choice", "medium",
     "What is the main purpose of splitting a dataset into training and test sets?",
     ("To make the file smaller",
      "To estimate how the model performs on data it was not trained on",
      "To remove duplicate rows automatically",
      "To increase the number of features"),
     "B", "To estimate how the model performs on data it was not trained on",
     "SFIA DAI; model validation"),
    ("MB2-DATA-06", "DATA", "Reporting", "Scenario-Based Multiple Choice", "medium",
     "You build a Power BI report for managers. One chart is slow to load and is rarely "
     "used. What is the most appropriate response?",
     ("Keep it, because removing content is always wrong",
      "Investigate why it is slow and whether it informs a decision managers make",
      "Delete it without telling anyone",
      "Reduce it to a single number with no explanation"),
     "B", "Investigate why it is slow and whether it informs a decision managers make",
     "Business intelligence practice; decision support"),
    ("MB2-DATA-07", "DATA", "Data quality", "Multiple Choice", "hard",
     "A dataset records 'N/A', 'null' and '-' all meaning missing. Why is this a problem "
     "before analysis?",
     ("It makes the file too large to open",
      "Different missing-value markers are handled inconsistently by most tools",
      "Missing values cannot be stored in a spreadsheet",
      "It prevents the data from being exported"),
     "B", "Different missing-value markers are handled inconsistently by most tools",
     "Data preparation practice; missing values"),
    ("MB2-DATA-08", "DATA", "Analysis", "Multiple Choice", "medium",
     "Which pandas operation groups rows and applies an aggregate, such as the mean, "
     "per category?",
     ("df.sort_values()", "df.groupby()", "df.dropna()", "df.rename()"),
     "B", "df.groupby()",
     "pandas documentation; aggregation"),
    ("MB2-DATA-09", "DATA", "Interpretation", "Scenario-Based Multiple Choice", "hard",
     "A model reports 99% accuracy but predicts the majority class every time. What does "
     "this indicate?",
     ("The model is excellent",
      "The model has learned nothing useful, because accuracy hides class imbalance",
      "The test set is too small",
      "The model needs a larger learning rate"),
     "B", "The model has learned nothing useful, because accuracy hides class imbalance",
     "SFIA DAI; evaluation metrics"),
    ("MB2-DATA-10", "DATA", "Ethics", "Scenario-Based Multiple Choice", "medium",
     "You are asked to analyse customer records that include a field the team does not "
     "need. What is the best professional action?",
     ("Analyse everything, then delete the field afterwards",
      "Confirm the field is necessary, and if not, exclude or anonymise it",
      "Keep it in case it becomes useful later",
      "Share it with the whole team so nobody is left out"),
     "B", "Confirm the field is necessary, and if not, exclude or anonymise it",
     "Data ethics; data minimisation"),
    # ---------------- Version Control / Git ----------------
    ("MB2-GIT-01", "GIT", "Commits", "Multiple Choice", "easy",
     "What does a Git commit primarily record?",
     ("A full copy of the project at that moment",
      "A snapshot of tracked changes with a message describing them",
      "A list of files to delete",
      "A connection to the remote server"),
     "B", "A snapshot of tracked changes with a message describing them",
     "Git official documentation; commits"),
    ("MB2-GIT-02", "GIT", "Branching", "Scenario-Based Multiple Choice", "medium",
     "You are starting a feature that will take two weeks and others are working on main. "
     "What is the most appropriate first step?",
     ("Edit files directly on main so the history stays simple",
      "Create a feature branch so the work is isolated",
      "Delete the repository and start again",
      "Copy the whole project folder by hand"),
     "B", "Create a feature branch so the work is isolated",
     "Git branching workflow"),
    ("MB2-GIT-03", "GIT", "Merge conflicts", "Scenario-Based Multiple Choice", "hard",
     "Two people edit the same line and you get a merge conflict. What is the correct way "
     "to resolve it?",
     ("Delete the repository and re-download it",
      "Choose whichever version is longer",
      "Open the conflicting file, decide the intended result deliberately, then commit "
      "the resolution",
      "Run the merge again until it succeeds by luck"),
     "C", "Open the conflicting file, decide the intended result deliberately, then commit "
     "the resolution",
     "Git official documentation; merge conflicts"),
    ("MB2-GIT-04", "GIT", "Collaboration", "Scenario-Based Multiple Choice", "medium",
     "Before pushing a feature branch for review, what is the most useful check?",
     ("Run the project's tests and review your own diff",
      "Delete the commit history so reviewers see only the final file",
      "Push directly to main so it is deployed",
      "Change the remote URL to your own account"),
     "A", "Run the project's tests and review your own diff",
     "Code review practice"),
    ("MB2-GIT-05", "GIT", "Repository hygiene", "Multiple Choice", "medium",
     "What is the purpose of a .gitignore file?",
     ("To hide files from Git so they are not tracked",
      "To encrypt the repository password",
      "To increase repository size",
      "To prevent anyone cloning the repository"),
     "A", "To hide files from Git so they are not tracked",
     "Git official documentation; ignore rules"),
    ("MB2-GIT-06", "GIT", "Version control", "Multiple Choice", "easy",
     "What does the command `git status` report?",
     ("Which remote the repository is connected to",
      "The current state of the working tree and staging area",
      "The password stored for the remote",
      "A list of all deleted files permanently"),
     "B", "The current state of the working tree and staging area",
     "Git official documentation; status"),
    ("MB2-GIT-07", "GIT", "Collaboration", "Scenario-Based Multiple Choice", "hard",
     "You are asked to revert a feature that was released yesterday, while other commits "
     "landed after it. What is the safest approach?",
     ("Delete the repository and start over",
      "Create a new commit that undoes the specific change, leaving later work intact",
      "Manually edit every file in the project",
      "Ask each user to re-clone and guess"),
     "B", "Create a new commit that undoes the specific change, leaving later work intact",
     "Git revert semantics"),
    ("MB2-GIT-08", "GIT", "Branching", "Multiple Choice", "medium",
     "What is the usual relationship between a feature branch and `main` after the "
     "feature is approved?",
     ("The feature branch is merged into main and usually retired",
      "Main is deleted and renamed after the feature branch",
      "The feature branch replaces main permanently",
      "Both branches are deleted immediately"),
     "A", "The feature branch is merged into main and usually retired",
     "Git branching workflow"),
    ("MB2-GIT-09", "GIT", "Repository hygiene", "Scenario-Based Multiple Choice", "medium",
     "A teammate commits a 40 MB log file into the repository. What is the best immediate "
     "action?",
     ("Add it to .gitignore going forward, and stop tracking it with `git rm --cached`",
      "Leave it, because history cannot be changed",
      "Compress it into a zip and commit that instead",
      "Rename the file so it is less noticeable"),
     "A", "Add it to .gitignore going forward, and stop tracking it with `git rm --cached`",
     "Git repository hygiene"),
    ("MB2-GIT-10", "GIT", "Collaboration", "Scenario-Based Multiple Choice", "hard",
     "A teammate's branch has fallen many commits behind main and now shows conflicts "
     "everywhere. What is the recommended way to bring it up to date?",
     ("Delete their branch without telling them",
      "Merge or rebase main into their branch and resolve the conflicts deliberately",
      "Force-push their branch over main",
      "Copy their files into a new folder on your machine"),
     "B", "Merge or rebase main into their branch and resolve the conflicts deliberately",
     "Git integration workflow"),
    # ---------------- Systems Analysis ----------------
    ("MB2-SYS-01", "SYS", "Requirements", "Multiple Choice", "easy",
     "Which statement is a testable requirement?",
     ("The system should be fast and modern",
      "The report must load within 2 seconds for 500 rows",
      "The user interface should be intuitive",
      "The system should use the latest technology"),
     "B", "The report must load within 2 seconds for 500 rows",
     "Requirements engineering practice; verifiability"),
    ("MB2-SYS-02", "SYS", "Stakeholders", "Scenario-Based Multiple Choice", "medium",
     "Two stakeholders want conflicting features for the same release. As the analyst, "
     "what should you do first?",
     ("Implement the request from the more senior person and inform nobody",
      "Make both changes so nobody is disappointed",
      "Surface the conflict and agree a priority with both stakeholders",
      "Ignore both requests until the deadline passes"),
     "C", "Surface the conflict and agree a priority with both stakeholders",
     "SFIA BA; stakeholder management"),
    ("MB2-SYS-03", "SYS", "Process modelling", "Multiple Choice", "medium",
     "In BPMN, what does a decision gateway represent?",
     ("A start or end of a process",
      "A branch where the path depends on a condition",
      "A human task performed by a person",
      "A message sent to another system"),
     "B", "A branch where the path depends on a condition",
     "BPMN specification; gateways"),
    ("MB2-SYS-04", "SYS", "Use cases", "Multiple Choice", "easy",
     "What is the purpose of a use case diagram?",
     ("To show the actors and what they can do with the system",
      "To display the database schema",
      "To record the deployment schedule",
      "To list every line of source code"),
     "A", "To show the actors and what they can do with the system",
     "UML use case diagrams"),
    ("MB2-SYS-05", "SYS", "Requirements", "Scenario-Based Multiple Choice", "hard",
     "A stakeholder asks for a feature in one sentence with no detail. What is the most "
     "professional response?",
     ("Build exactly that and treat it as finished",
      "Elicit the details: who uses it, what it must achieve, and how success is judged",
      "Tell them requirements work slows the project down",
      "Copy a similar feature from another project without asking"),
     "B", "Elicit the details: who uses it, what it must achieve, and how success is judged",
     "SFIA BA; requirements elicitation"),
    ("MB2-SYS-06", "SYS", "Documentation", "Scenario-Based Multiple Choice", "medium",
     "A specification has been agreed. Why record the agreed scope and assumptions?",
     ("To lengthen the document so it looks thorough",
      "So both sides share the same baseline and disputes can be checked against it",
      "So the analyst can avoid future meetings",
      "Because requirements are only valid in writing"),
     "B", "So both sides share the same baseline and disputes can be checked against it",
     "Systems analysis practice; baselines"),
    ("MB2-SYS-07", "SYS", "Analysis", "Multiple Choice", "medium",
     "Which technique helps identify what a system must do and what it must not do?",
     ("Code generation", "Functional and non-functional requirements analysis",
      "Database indexing", "Performance tuning"),
     "B", "Functional and non-functional requirements analysis",
     "SFIA BA; requirements classification"),
    ("MB2-SYS-08", "SYS", "Process modelling", "Scenario-Based Multiple Choice", "medium",
     "A manual approval step is causing errors and delays. As the analyst, what should "
     "you recommend first?",
     ("Ask staff to work faster",
      "Model the process as-is to find where the errors enter, then propose a change",
      "Remove the approval step without analysis",
      "Document the step as unavoidable"),
     "B", "Model the process as-is to find where the errors enter, then propose a change",
     "BPMN; process analysis"),
    ("MB2-SYS-09", "SYS", "Stakeholders", "Scenario-Based Multiple Choice", "hard",
     "A key stakeholder leaves the project the week before go-live. What is the most "
     "important analyst action?",
     ("Assume requirements are now fixed and change nothing",
      "Re-confirm requirements and obtain sign-off from an authorised replacement",
      "Delay the release indefinitely",
      "Send the unfinished system to the intern team"),
     "B", "Re-confirm requirements and obtain sign-off from an authorised replacement",
     "SFIA BA; governance"),
    ("MB2-SYS-10", "SYS", "Documentation", "Multiple Choice", "easy",
     "What does a non-functional requirement describe?",
     ("A quality attribute such as performance, security or availability",
      "The name of a screen",
      "The project's start date",
      "The programmer's name"),
     "A", "A quality attribute such as performance, security or availability",
     "Requirements engineering; non-functional requirements"),
    # ---------------- Object-Oriented Programming ----------------
    ("MB2-OOP-01", "OOP", "Encapsulation", "Multiple Choice", "easy",
     "What is encapsulation?",
     ("Writing every class in a single file",
      "Hiding internal state behind a defined public interface",
      "Copying data between objects",
      "Naming every variable the same way"),
     "B", "Hiding internal state behind a defined public interface",
     "SFIA PROG; object-oriented principles"),
    ("MB2-OOP-02", "OOP", "Abstraction", "Multiple Choice", "medium",
     "Why is an abstract class used rather than a concrete one everywhere?",
     ("Abstract classes run faster",
      "It defines a shared contract without forcing one implementation",
      "It prevents the use of inheritance",
      "It stores data more efficiently"),
     "B", "It defines a shared contract without forcing one implementation",
     "SFIA PROG; abstraction"),
    ("MB2-OOP-03", "OOP", "Inheritance", "Scenario-Based Multiple Choice", "medium",
     "A `Dog` class inherits from `Animal`. What does that let `Dog` do?",
     ("Replace every method in Animal",
      "Reuse and specialise the behaviour defined by Animal",
      "Delete the Animal class automatically",
      "Prevent Dog from having its own methods"),
     "B", "Reuse and specialise the behaviour defined by Animal",
     "SFIA PROG; inheritance"),
    ("MB2-OOP-04", "OOP", "Polymorphism", "Multiple Choice", "medium",
     "What is the practical benefit of polymorphism?",
     ("Code can target a common interface without knowing the concrete type",
      "Every object becomes a string",
      "The program runs without errors",
      "Classes can be written faster"),
     "A", "Code can target a common interface without knowing the concrete type",
     "SFIA PROG; polymorphism"),
    ("MB2-OOP-05", "OOP", "SOLID principles", "Multiple Choice", "hard",
     "A single `OrderManager` class handles input validation, database writes and email "
     "sending. Which SOLID principle is being violated?",
     ("Single Responsibility", "Liskov Substitution", "Interface Segregation",
      "Dependency Inversion"),
     "A", "Single Responsibility",
     "SOLID principles; SRP"),
    ("MB2-OOP-06", "OOP", "SOLID principles", "Multiple Choice", "hard",
     "Every subclass of `Payment` must keep the same method signatures, whether or not it "
     "supports them. Which principle requires this?",
     ("Dependency Inversion", "Liskov Substitution", "Open/Closed", "Single Responsibility"),
     "B", "Liskov Substitution",
     "SOLID principles; LSP"),
    ("MB2-OOP-07", "OOP", "Design patterns", "Multiple Choice", "medium",
     "Which pattern is commonly used so a class can be created without hard-coding the "
     "concrete class it builds?",
     ("Observer", "Factory", "Decorator", "Singleton"),
     "B", "Factory",
     "GoF design patterns; Factory"),
    ("MB2-OOP-08", "OOP", "Composition", "Scenario-Based Multiple Choice", "medium",
     "A `Car` needs a different engine type depending on configuration. Which approach "
     "expresses this most directly?",
     ("Deep inheritance chain from Car to every engine type",
      "Pass the engine into Car as a composed object",
      "Duplicate the Car class once per engine type",
      "Store the engine type in a global variable"),
     "B", "Pass the engine into Car as a composed object",
     "SFIA PROG; composition over inheritance"),
    ("MB2-OOP-09", "OOP", "Encapsulation", "Scenario-Based Multiple Choice", "hard",
     "A class exposes a public list that callers can modify directly, breaking internal "
     "rules. What is the fix?",
     ("Make the list public so callers can edit it",
      "Keep the list private and expose a method that returns a safe copy",
      "Add a comment telling callers not to modify it",
      "Convert the list to a string"),
     "B", "Keep the list private and expose a method that returns a safe copy",
     "SFIA PROG; encapsulation"),
    ("MB2-OOP-10", "OOP", "SOLID principles", "Scenario-Based Multiple Choice", "medium",
     "A module depends on a concrete payment provider and is hard to test without it. "
     "Which principle addresses this?",
     ("Dependency Inversion: depend on an abstraction, not the concrete class",
      "Liskov Substitution",
      "Open/Closed: add more subclasses",
      "Single Responsibility: split the module further"),
     "A", "Dependency Inversion: depend on an abstraction, not the concrete class",
     "SOLID principles; DIP"),
    # ---------------- Data Structures & Algorithms ----------------
    ("MB2-DSA-01", "DSA", "Complexity", "Multiple Choice", "easy",
     "What does Big-O notation describe?",
     ("How much memory a program uses at one instant",
      "How an algorithm's cost grows as input size grows",
      "How many lines of code a program has",
      "How fast a computer's processor is"),
     "B", "How an algorithm's cost grows as input size grows",
     "Algorithm analysis; Big-O"),
    ("MB2-DSA-02", "DSA", "Linear search", "Multiple Choice", "easy",
     "What is the worst-case time complexity of searching an unsorted array of n items "
     "linearly?",
     ("O(1)", "O(log n)", "O(n)", "O(n log n)"),
     "C", "O(n)",
     "Algorithm analysis; linear search"),
    ("MB2-DSA-03", "DSA", "Data structures", "Multiple Choice", "medium",
     "Which data structure gives O(1) average lookup by key?",
     ("A sorted linked list", "A hash table (dictionary)",
      "An unsorted array scanned every time", "A stack"),
     "B", "A hash table (dictionary)",
     "SFIA PROG; hash tables"),
    ("MB2-DSA-04", "DSA", "Sorting", "Multiple Choice", "medium",
     "Why is quicksort commonly preferred over bubble sort on large datasets?",
     ("Quicksort has an average O(n log n) cost compared with bubble sort's O(n^2)",
      "Quicksort never uses comparisons",
      "Bubble sort cannot sort numbers",
      "Quicksort always sorts in place with no extra memory"),
     "A", "Quicksort has an average O(n log n) cost compared with bubble sort's O(n^2)",
     "Algorithm analysis; sorting"),
    ("MB2-DSA-05", "DSA", "Stacks and queues", "Multiple Choice", "easy",
     "Which structure would you use to evaluate an expression with nested parentheses?",
     ("A queue", "A stack", "A hash table", "A graph"),
     "B", "A stack",
     "SFIA PROG; stacks"),
    ("MB2-DSA-06", "DSA", "Trees", "Scenario-Based Multiple Choice", "medium",
     "You need to find an item in a balanced binary search tree. What is the search cost?",
     ("O(n)", "O(log n)", "O(n log n)", "O(1)"),
     "B", "O(log n)",
     "Binary search trees; balanced trees"),
    ("MB2-DSA-07", "DSA", "Recursion", "Scenario-Based Multiple Choice", "medium",
     "A recursive function calls itself with the same arguments and the program never "
     "terminates. What is the most likely cause?",
     ("The function is missing a base case or a step toward it",
      "The function is missing a return type",
      "The parameters are named incorrectly",
      "The language does not support recursion"),
     "A", "The function is missing a base case or a step toward it",
     "Programming fundamentals; recursion"),
    ("MB2-DSA-08", "DSA", "Linked lists", "Multiple Choice", "medium",
     "What is a key disadvantage of a singly linked list compared with an array for "
     "random access?",
     ("It cannot store duplicates",
      "Reaching an item by index requires traversing from the start",
      "It cannot be sorted",
      "It uses more memory for every single node"),
     "B", "Reaching an item by index requires traversing from the start",
     "SFIA PROG; linked lists"),
    ("MB2-DSA-09", "DSA", "Algorithm selection", "Scenario-Based Multiple Choice", "hard",
     "You must find the 10 most frequent words in a 10-million-word document. Which "
     "approach is most appropriate?",
     ("Sort the entire list alphabetically and read the first ten",
      "Count occurrences in a hash map and keep a small running top-10 structure",
      "Use a linear search over every word against every other word",
      "Store the document in reverse and read it backwards"),
     "B", "Count occurrences in a hash map and keep a small running top-10 structure",
     "Algorithm selection; frequency counting"),
    ("MB2-DSA-10", "DSA", "Complexity", "Scenario-Based Multiple Choice", "hard",
     "Two implementations of the same feature are benchmarked. One is O(n^2) and one is "
     "O(n log n). At n = 1,000,000 what is the practical difference?",
     ("There is no meaningful difference at that size",
      "The O(n log n) version does vastly fewer operations and scales far better",
      "The O(n^2) version is always more readable and therefore faster",
      "Both take exactly one operation per input"),
     "B", "The O(n log n) version does vastly fewer operations and scales far better",
     "Algorithm analysis; scaling"),
    # ---------------- Cloud & DevOps Fundamentals ----------------
    ("MB2-CLOUD-01", "CLOUD", "Cloud concepts", "Multiple Choice", "easy",
     "What is the main advantage of the pay-as-you-go cloud pricing model?",
     ("It is always cheaper than buying hardware",
      "Cost follows actual usage rather than a fixed purchase",
      "It removes the need for backups",
      "It guarantees applications will never fail"),
     "B", "Cost follows actual usage rather than a fixed purchase",
     "AWS Cloud Practitioner; pricing models"),
    ("MB2-CLOUD-02", "CLOUD", "Containers", "Multiple Choice", "medium",
     "What problem do containers primarily solve compared with a full virtual machine?",
     ("They run without an operating system",
      "They package an application with its dependencies for consistent, portable running",
      "They replace all testing",
      "They guarantee unlimited performance"),
     "B", "They package an application with its dependencies for consistent, portable running",
     "Docker documentation; containers"),
    ("MB2-CLOUD-03", "CLOUD", "CI/CD", "Multiple Choice", "easy",
     "What does continuous integration primarily ensure?",
     ("The application is always in production",
      "Code changes are automatically built and tested when they are contributed",
      "No one can merge code without approval",
      "The database is always backed up"),
     "B", "Code changes are automatically built and tested when they are contributed",
     "DevOps practice; continuous integration"),
    ("MB2-CLOUD-04", "CLOUD", "Virtualisation", "Multiple Choice", "medium",
     "In cloud terminology, what does a virtual machine provide that a container does not?",
     ("Faster startup times",
      "Its own virtualised operating system, with its own kernel",
      "Lower cost per workload",
      "Automatic scaling"),
     "B", "Its own virtualised operating system, with its own kernel",
     "CompTIA Linux+; virtualisation"),
    ("MB2-CLOUD-05", "CLOUD", "Infrastructure as code", "Scenario-Based Multiple Choice",
     "medium",
     "An environment must be rebuilt identically after a failure. Why define it with "
     "Terraform rather than manual steps?",
     ("Manual setup is faster",
      "The definition is versioned and reproducible, so rebuilds are consistent",
      "Terraform removes the need for monitoring",
      "Manual setup cannot create networks"),
     "B", "The definition is versioned and reproducible, so rebuilds are consistent",
     "HashiCorp Terraform; IaC"),
    ("MB2-CLOUD-06", "CLOUD", "Availability", "Scenario-Based Multiple Choice", "hard",
     "A production service must survive the loss of one physical server with minimal "
     "interruption. Which measure helps most?",
     ("Adding more memory to the single server",
      "Removing the health checks",
      "Running redundant instances behind a load balancer across failure zones",
      "Backing up the database once a week"),
     "C", "Running redundant instances behind a load balancer across failure zones",
     "AWS Cloud Practitioner; high availability"),
    ("MB2-CLOUD-07", "CLOUD", "Security", "Multiple Choice", "medium",
     "Why should application credentials be stored in a secret manager rather than in "
     "source code?",
     ("It makes the code shorter",
      "Secrets in code are exposed to everyone with repository access and end up in history",
      "Environment variables run faster",
      "Source control cannot store strings"),
     "B", "Secrets in code are exposed to everyone with repository access and end up in history",
     "Cloud security; secrets management"),
    ("MB2-CLOUD-08", "CLOUD", "Scaling", "Multiple Choice", "medium",
     "Traffic to an application doubles during a promotion. What is horizontal scaling?",
     ("Buying a larger single machine",
      "Adding more instances of the same application to share the load",
      "Increasing the disk size",
      "Running the application twice a day"),
     "B", "Adding more instances of the same application to share the load",
     "CompTIA Cloud+; scaling"),
    ("MB2-CLOUD-09", "CLOUD", "Deployment", "Scenario-Based Multiple Choice", "hard",
     "A release breaks production. Which practice would let you restore service fastest "
     "and most safely?",
     ("Edit the live server until it works",
      "Roll back to the last known-good version, then fix forward",
      "Delete the deployment history",
      "Disable all monitoring so the error is not logged"),
     "B", "Roll back to the last known-good version, then fix forward",
     "DevOps practice; rollback"),
    ("MB2-CLOUD-10", "CLOUD", "Operations", "Scenario-Based Multiple Choice", "medium",
     "A cloud bill rises sharply. What is the most appropriate first action?",
     ("Move every workload to a bigger provider immediately",
      "Review usage and cost data to find what changed before reacting",
      "Turn off all logging to reduce usage",
      "Assume the increase is normal and ignore it"),
     "B", "Review usage and cost data to find what changed before reacting",
     "FinOps practice; cost management"),
]

_STOPWORDS = {"the", "and", "for", "that", "with", "from", "you", "your"}


def _tokens(text):
    words = "".join(c.lower() if c.isalnum() else " " for c in str(text or "")).split()
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}


def _overlap(option, explanation):
    """Share of the option's own words that the explanation repeats.

    An explanation that IS the option text counts as full support. That matters
    for items whose answer is notation rather than prose ("O(n)", "df.groupby()"),
    where token overlap is meaningless but an exact restatement is not.
    """
    if str(option or "").strip().lower() == str(explanation or "").strip().lower():
        return 1.0
    o, e = _tokens(option), _tokens(explanation)
    return len(o & e) / len(o) if o else 0.0


def verify_keys(items=None):
    """Adjudicates each item's key against its own explanation.

    The keyed option always restates the explanation in this module, so this is a
    guard rather than a correction pass: an item whose key is NOT supported by its
    explanation is stored with is_active = 0 and never served. Withholding an item
    is always better than grading a student against a key we cannot justify.
    """
    items = ITEMS if items is None else items
    report = {}
    for item in items:
        options, key, explanation = item[6], item[7], item[8]
        keyed = options["ABCD".index(key)]
        best = max(range(len(options)), key=lambda n: _overlap(options[n], explanation))
        supported = _overlap(keyed, explanation) >= 0.5 and best == "ABCD".index(key)
        report[item[0]] = {
            "status": "Verified" if supported else "Unresolved",
            "recorded": key,
            "applied": key if supported else None,
            "rule": "explanation-token-match",
        }
    return report


def _rotate(code, options, key):
    """Moves the keyed option to a deterministic fresh position.

    Seeded by the item code, so re-seeding writes identical rows and a student
    cannot score by always picking the same letter.
    """
    options = list(options)
    target = random.Random(code).randrange(len(options))
    correct = options.pop("ABCD".index(key))
    options.insert(target, correct)
    return options, "ABCD"[target]


def as_rows():
    """One dict per item, shaped exactly like master_question_bank rows."""
    verification = verify_keys()
    rows = []
    for item in ITEMS:
        (code, competency, sub, qtype, difficulty,
         text, options, key, explanation, ref) = item
        info = verification[code]
        ordered, applied = _rotate(code, options, key)
        rows.append({
            "question_code": code,
            "course_track": TRACK_BY_COMPETENCY[competency],
            "category": sub,
            "competency": competency,
            "doc_competency": None,
            "target_role": sub,
            "question_type": qtype,
            "difficulty": difficulty,
            "standard_ref": ref,
            "question_text": text,
            "option_a": ordered[0], "option_b": ordered[1],
            "option_c": ordered[2], "option_d": ordered[3],
            "correct_option": applied or key,
            "explanation": explanation,
            "is_active": 1 if info["status"] == "Verified" else 0,
            "source_type": SOURCE_TYPE,
            "key_status": info["status"],
        })
    return rows


def counts_per_competency(active_only=False):
    counts = {}
    for row in as_rows():
        if active_only and not row["is_active"]:
            continue
        counts[row["competency"]] = counts.get(row["competency"], 0) + 1
    return counts


def answer_key_distribution():
    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for row in as_rows():
        counts[row["correct_option"]] += 1
    return counts