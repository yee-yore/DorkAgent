import sys, os, re, subprocess, getpass
from datetime import datetime

# --- Runtime environment bootstrap: Python & packages ---
REQUIRED_PACKAGES = {
    "python-dotenv": "dotenv",
    "crewai": "crewai",
    "crewai-tools": "crewai_tools",
    "langchain-openai": "langchain_openai",
    "termcolor": "termcolor",
    "prompt-toolkit": "prompt_toolkit",
    "pyfiglet": "pyfiglet",
    "schedule": "schedule",
}

def _warn_python_version():
    required_major, required_minor, required_patch = 3, 11, 9
    v = sys.version_info
    if (v.major, v.minor) != (required_major, required_minor) or v.micro != required_patch:
        print(f"[!] Detected Python {v.major}.{v.minor}.{v.micro}. Recommended: 3.11.9.")
        print("[!] Continuing, but if you see issues, use Python 3.11.9.")

def _pip_install(spec: str):
    try:
        print(f"[+] Installing: {spec} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", spec])
    except Exception as e:
        print(f"[!] Failed to install {spec}: {e}")
        raise

def _ensure_packages():
    import importlib
    missing = []
    for pip_name, import_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(import_name)
        except Exception:
            missing.append(pip_name)

    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if missing and os.path.isfile(req_file):
        try:
            print(f"[+] Syncing dependencies from requirements.txt ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file, "--upgrade", "--upgrade-strategy", "only-if-needed"])
            missing = []  # reset and re-evaluate
            for pip_name, import_name in REQUIRED_PACKAGES.items():
                importlib.import_module(import_name)
            return
        except Exception as e:
            print(f"[!] Failed to install from requirements.txt: {e}. Falling back to per-package installs.")

    # Install any still-missing packages individually
    for pip_name in missing:
        _pip_install(pip_name)
    # Final import verification
    for _, import_name in REQUIRED_PACKAGES.items():
        importlib.import_module(import_name)

# Execute checks before importing third-party modules
_warn_python_version()
_ensure_packages()

# Import third-party modules after ensuring they are available
from dotenv import load_dotenv
from crewai import Crew, LLM, Task, Agent
from langchain_openai import ChatOpenAI
from termcolor import colored
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from crewai_tools import SerperDevTool, ScrapeWebsiteTool
import pyfiglet
from crewai.utilities.exceptions.context_window_exceeding_exception import LLMContextLengthExceededError

# Load environment early so model constructors see keys
load_dotenv()

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

def _read_env_file(path: str) -> dict:
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        data[k.strip()] = v.strip()
        except Exception:
            pass
    return data

def _write_env_file(path: str, values: dict):
    existing = _read_env_file(path)
    existing.update(values)
    lines = [f"{k}={existing[k]}" for k in sorted(existing.keys())]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def ensure_api_keys(llm_type: str):
    required_keys = ["SERPER_API_KEY"]
    if llm_type == "openai":
        required_keys.append("OPENAI_API_KEY")
    elif llm_type == "anthropic":
        required_keys.append("ANTHROPIC_API_KEY")
    elif llm_type == "gemini":
        required_keys.append("GEMINI_API_KEY")

    missing = [k for k in required_keys if not os.getenv(k)]
    if missing:
        print("[!] Missing required API keys: " + ", ".join(missing))
        provided = {}
        for key in missing:
            prompt_text = f"Enter value for {key}: "
            try:
                val = getpass.getpass(prompt_text)
            except Exception:
                val = input(prompt_text)
            provided[key] = val.strip()
        _write_env_file(ENV_PATH, provided)
        # Reload environment so subsequent code can read keys
        load_dotenv(dotenv_path=ENV_PATH, override=True)

# Load environment early so model constructors see keys
load_dotenv()

def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")

def display_banner():
    print(" ")
    print(" ")
    ascii_banner = pyfiglet.figlet_format("Dork Agent", font="big")
    print(colored(ascii_banner, "red"))
    print(colored("                                        by yee-yore", "red"))
    print("\n")
    print("DorkAgent is a LLM-powered agent for automated Google Dorking in bug hunting & pentesting.")
    print(colored("[Ver]", "red") + " Current DorkAgent version is v1.3")
    print("=" * 90)

def verify_api_key(llm_type):
    required_keys = ["SERPER_API_KEY"]

    if llm_type == "openai":
        required_keys.append("OPENAI_API_KEY")
    elif llm_type == "anthropic":
        required_keys.append("ANTHROPIC_API_KEY")
    elif llm_type == "gemini":
        required_keys.append("GEMINI_API_KEY")

    load_dotenv()

    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        print("?슚 Missing required API keys:")
        for key in missing_keys:
            print(f"   ??{key} is not set")
        print("\nPlease check your .env file and set the missing keys.")
        sys.exit(1)

def select_llm():
    ClaudeHaiku = LLM(
        api_key=os.getenv('ANTHROPIC_API_KEY'),
        model='anthropic/claude-3-5-haiku-20241022',
    )

    GPT4oMini = ChatOpenAI(
        model_name="gpt-4o-mini-2024-07-18", 
        temperature=0
    )

    GeminiFlash = LLM(
        api_key=os.getenv('GEMINI_API_KEY'),
        model='gemini/gemini-2.0-flash',
    )
    
    while True:
        print("\n")
        print("1. GPT-4o Mini")
        print("2. Claude 3.5 Haiku")
        print("3. Gemini 2.0 Flash")
        print("\n")
        
        choice = input("[?] Choose LLM for Agents (1 - 3): ").strip()
        
        if choice == "1":
            return GPT4oMini, "openai"
        elif choice == "2":
            return ClaudeHaiku, "anthropic"
        elif choice == "3":
            return GeminiFlash, "gemini"
        else:
            print("Invalid choice. Please enter 1 - 3.")

def get_file_path(prompt_text):
    completer = PathCompleter()
    return prompt(prompt_text, completer=completer).strip()

def get_target_domains():
    target_domains = []

    while True:
        print("\n")
        print("1] Single Domain")
        print("2] Multi Domain (from file)")
        print("\n") 
        
        choice = input("[?] Enter your target type (1 - 2): ").strip()

        if choice == "1":
            domain = input("[?] Enter the target domain: ").strip()
            target_domains.append(domain)
            break
            
        elif choice == "2": 
            file_path = get_file_path("[?] Enter the file path: ")
            if os.path.isfile(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    for line in file:
                        domain = line.strip()
                        target_domains.append(domain)
                break 
            else:
                print("??File not found. Please enter a valid file path.")
        
        else:
            print("?슚 Invalid choice. Please select 1 - 2.")

    return target_domains

def select_depth():
    while True:
        print("\n")
        print("1] target.com")
        print("2] *.target.com")
        print("3] *.*.target.com")
        print("\n")
        depth = input("[?] Choose depth for dorking (1 - 3): ").strip()
        
        if depth in ["1", "2", "3"]:
            return depth
        else:
            print("Invalid choice. Please enter 1 - 3.")

def integrate_notify(): 
    while True: 
        print("\n") 
        print("\n") 
        print("\n")
 
        notify = input("[?] Do you want to send a report using notify? (Y or N): ").strip() 
         
        if notify in ["Y", "y", "N", "n"]: 
            return notify 
        else: 
            print("??Invalid choice. Please enter Y or N")

def adjust_depth(target_domains, depth):
    try:
        depth = int(depth)  
        if depth < 1:  
            raise ValueError("Invalid depth value")
    except ValueError:
        print("??Invalid depth input. Defaulting to depth = 1.")
        depth = 1

    if depth == 1:
        adjusted_domains = target_domains
    else:
        prefix = ".".join(["*"] * (depth - 1))  
        adjusted_domains = [f"{prefix}.{domain}" for domain in target_domains]

    return adjusted_domains

def sanitize_filename(domain_name):

    # '*' -> 'wildcard'
    sanitized = domain_name.replace('*', 'wildcard')
    sanitized = re.sub(r'[\\/*?:"<>|]', '', sanitized)
    
    return sanitized

def agents(llm):

    searcher = Agent(
        role="searcher",
        goal="Performing advanced Google searches using Google Dorks",
        backstory="An expert in Google Dorking techniques for information gathering",
        verbose=True,
        allow_delegation=False,
        tools=[SerperDevTool()],
        llm=llm,
        respect_context_window=True,
    )

    bughunter = Agent(
        role="bughunter",
        goal="Identifying attack surfaces and vulnerabilities in target domains",
        backstory="A skilled penetration tester specializing in web security and vulnerability assessments",
        verbose=True,
        allow_delegation=False,
        tools=[ScrapeWebsiteTool()],
        llm=llm,
        respect_context_window=True,
    )

    writer = Agent(
        role="writer",
        goal="Generating well-structured and detailed reports based on findings",
        backstory="A technical writer specializing in cybersecurity documentation and structured reporting",
        verbose=True,
        allow_delegation=False,
        llm=llm,
        respect_context_window=True,
    )

    return [searcher, bughunter, writer]

# Removed min/max interactive configuration and system prompt per request

def task(target_domain, domain, agents):
       
    task1 = Task(
        description=f"""
        # Google Dorking Search Analysis

        ## Objective
        Execute the following Google Dork queries for the domain {domain} and collect ONLY REAL search results that actually exist.

        ## Google Dork Query List
        1. site:{target_domain} (intitle:"index of /" | intitle:"docker-compose.yml" | intitle:".env" | intitle:"config.yml" | intitle:".git" | intitle:"package.json" | intitle:"requirements.txt" | intitle:".gitignore" | intitle:"IIS Windows Server")
        2. site:{target_domain} (ext:pdf | ext:doc | ext:docx | ext:xls | ext:xlsx | ext:csv | ext:ppt | ext:pptx | ext:txt | ext:rtf | ext:odt) ("INTERNAL USE ONLY" | "INTERNAL ONLY" | "TRADE SECRET" | "NOT FOR DISTRIBUTION" | "NOT FOR PUBLIC RELEASE" | "EMPLOYEE ONLY")
        3. site:{target_domain} (ext:csv | ext:txt | ext:json | ext:xlsx | ext:xls | ext:sql | ext:log | ext:xml) (intext:"id" | intext:"uid" | intext:"uuid" | intext:"username" | intext:"password" | intext:"userid" | intext:"email" | intext:"ssn" | intext:"phone" | intext:"date of birth" | intext:"Social Security Number" | intext:"credit card" | intext:"CCV" | intext:"CVV" | intext:"card number")
        4. site:{target_domain} (inurl:action | inurl:page | inurl:pid | inurl:uid | inurl:id | inurl:search | inurl:cid | inurl:idx | inurl:no)
        5. site:{target_domain} (inurl:admin | inurl:administrator | inurl:wp-login | inurl:manage | inurl:control | inurl:panel | inurl:dashboard | inurl:wp-admin | inurl:phpmyadmin | inurl:console)
        6. site:{target_domain} ext:txt inurl:robots.txt
        7. site:{target_domain} (ext:yaml | ext:yml | ext:ini | ext:conf | ext:config | ext:log | ext:pdf | ext:xml | ext:json) (intext:"token" | intext:"access_token" | intext:"api_key" | intext:"private_key" | intext:"secret" | intext:"BEGIN RSA PRIVATE KEY" | intext:"BEGIN DSA PRIVATE KEY" | intext:"BEGIN OPENSSH PRIVATE KEY")
        8. site:{target_domain} (inurl:/download.jsp | inurl:/downloads.jsp | inurl:/upload.jsp) | inurl:/uploads.jsp | inurl:/download.php | inurl:/downloads.php | inurl:/upload.php) | inurl:/uploads.php)
        9. site:{target_domain} (inurl:index.php?page | inurl:file | inurl:inc | inurl:layout | inurl:template | inurl:content | inurl:module | inurl:include= | inurl:require= | inurl:load= | inurl:get= | inurl:show= | inurl:read=)
        10. site:{target_domain} (ext:pdf | ext:doc | ext:docx | ext:ppt | ext:pptx) (intext:"join.slack" | intext:"t.me" | intext:"trello.com/invite" | intext:"notion.so" | intext:"atlassian.net" | intext:"asana.com" | intext:"teams.microsoft.com" | intext:"zoom.us/j" | intext:"bit.ly")
        11. site:{target_domain} (inurl:url= | inurl:continue= | inurl:redirect | inurl:return | inurl:target | inurl:site= | inurl:view= | inurl:path | inurl:returl= | inurl:next= | inurl:fallback= | inurl:u= | inurl:goto= | inurl:link=)
        12. (site:*.s3.amazonaws.com | site:*.s3-external-1.amazonaws.com | site:*.s3.dualstack.us-east-1.amazonaws.com | site:*.s3.ap-south-1.amazonaws.com) "{domain}"
        13. site:{target_domain} inurl:eyJ (inurl:token | inurl:jwt | inurl:access | inurl:auth | inurl:authorization | inurl:secret)
        14. site:{target_domain} inurl:api (inurl:/v1/ | inurl:/v2/ | inurl:/v3/ | inurl:/v4/ | inurl:/v5/ | inurl:/rest)
        15. site:{target_domain} (inurl:/graphql | inurl:/swagger | inurl:swagger-ui | inurl:/rest | inurl:api-docs)
        16. site:{target_domain} inurl:"error" | intitle:"exception" | intitle:"failure" | intitle:"server at" | inurl:exception | "database error" | "SQL syntax" | "undefined index" | "unhandled exception" | "stack trace" | "SQL syntax error" | "mysql_fetch" | "Warning: mysql" | "PostgreSQL query failed" | "Notice: Undefined" | "Warning: include" | "Fatal error" | "Parse error"
        17. site:{target_domain} ext:log | ext:txt | ext:conf | ext:cnf | ext:ini | ext:env | ext:sh | ext:bak | ext:backup | ext:swp | ext:old | ext:~ | ext:git | ext:svn | ext:htpasswd | ext:htaccess | ext:json | ext:sql
        18. site:openbugbounty.org inurl:reports intext:"{domain}"
        19. (site:groups.google.com | site:googleapis.com | site:drive.google.com | site:dropbox.com | site:box.com | site:onedrive.live.com | site:firebaseio.com | site:*.amazonaws.com | site:*.azure.com | site:*.digitaloceanspaces.com | site:pastebin.com | site:paste2.org | site:pastehtml.com | site:slexy.org | site:github.com | site:gitlab.com | site:bitbucket.org) "{domain}"
        20. site:{target_domain} (inurl:dev | inurl:test | inurl:staging | inurl:development | inurl:debug | intext:"phpinfo()" | inurl:phpinfo.php | inurl:info.php | inurl:test.php | inurl:dev.php | inurl:debug.php | intext:"version" | intext:"powered by" | intext:"built with" | intext:"running")
        21. site:{target_domain} (inurl:server | inurl:backup | inurl:config | inurl:setting | inurl:log | inurl:monitor | inurl:metric | inurl:health | inurl:status)
        22. site:{target_domain} (intext:"PAGE NOT FOUND" | intext:"project not found" | intext:"Repository not found"  | intext:"domain does not exist" | intext:"This page could not be found" | intext:"404 Blog is not found" | intext:"No settings were found for this company" | intext:"domain name is invalid")
        23. site:*.{target_domain} -www (inurl:admin | inurl:login | inurl:portal | inurl:dashboard | inurl:jenkins | inurl:gitlab | inurl:bitbucket | inurl:jira | inurl:confluence)
        24. site:{target_domain} (inurl:exec | inurl:shell | inurl:command | inurl:cmd | inurl:system | inurl:eval)
        25. site:{target_domain} (inurl:lang= | inurl:locale= | inurl:country= | intext:"?lang=" | intext:"?language=")
        26. site:{target_domain} inurl:"/.well-known/" (inurl:security.txt | inurl:humans.txt | inurl:apple-app-site-association)
        27. site:{target_domain} (inurl:wp-content/uploads | inurl:wp-config | inurl:wp-admin | inurl:wp-includes) -inurl:wp-content (filetype:sql | filetype:txt | filetype:log)
        28. (cache:{target_domain} | site:web.archive.org "{domain}") (intext:"password" | intext:"admin" | intext:"login" | intext:"internal")
        29. site:crt.sh "{domain}" | site:certificate.transparency.log "{domain}"
        30. (site:linkedin.com | site:twitter.com | site:facebook.com) "{domain}" (intext:"employee" | intext:"work at" | intext:"@{domain}")

        ## Execution Process - YOU MUST FOLLOW THIS
        1. Execute EACH of the 30 queries in sequence - DO NOT SKIP ANY QUERIES
        2. Document results for each query even if it returns nothing
        3. Continue until ALL 30 queries have been executed
        4. Only then compile final results

        ## Search Guidelines
        - Execute each query exactly in the format specified above.
        - If a query returns no results, immediately proceed to the next google dork.
        - ONLY report URLs that you ACTUALLY find in the search results.
        - NEVER fabricate or hallucinate any URLs or search results.
        - If all queries return no results, return empty results list.
        - Search only within the provided domain; do not expand the search scope.
      
        ## Exclusion Criteria
        - Exclude results containing the following keywords (high false positive likelihood):
          * Common documents: "Advertisement", "Agreement", "Terms", "Policy", "License", "Disclaimer"
          * Support materials: "API Docs", "Forum", "Help", "Community", "Code of Conduct", "Knowledge Base", "Support Center", "Customer Support"
          * Development content: "Developers", "Statement", "Support", "Rules", "Docs", "Developer Portal", "Engineering Blog"
          * Example content: "example", "sample", "demo", "dummy", "placeholder", "mockup"
          * Documents: "Guideline", "Template", "Documentation", "User Manual", "Reference Guide"
          * Corporate communications: "About Us", "Press", "Media", "Careers"

        - Also exclude:
          * Files with naming patterns like:
            - "example_*", "sample_*", "demo_*", "*_sample.*", "*_demo.*"
          * Content that appears non-production:
            - Sequential IDs (user1, user2, user3)
            - Dummy email patterns (test@example.com, admin@localhost, user@test.com)
            - Placeholder usernames (admin, root, temp, organizer)
          * Content with artificial data patterns:
            - Generic sequential identifiers
            - Predictable naming conventions
          * Training materials or documentation examples
          * Onboarding and introductory content

        - Comprehensive URL filtering:
          * Exclude URLs containing subdirectories like:
            - "/help/"
            - "/support/"
            - "/docs/"
            - "/examples/"
            - "/tutorial/"
          * Avoid results from known documentation domains
          * Filter out URLs with explicit non-production indicators
        """,
        expected_output=f"""
        <findings>
        [
          {{
            "total_queries": <number_of_queries_executed>,
            "queries_with_results": <number_of_queries_with_results>,
            "total_urls_found": <number_of_urls_found>,
            "results": [
              // Only include this section if results were actually found
              {{
                "query_index": <index_of_query>,
                "query": "<exact_query_executed>",
                "urls_found": [
                  {{
                    "url": "<actual_url_found>",
                    "title": "<actual_page_title>",
                    "description": "<brief_description_of_actual_content>"
                  }}
                  // Additional URLs if found
                ]
              }}
              // Additional queries with results
            ],
            "queries_without_results": [<indices_of_queries_that_returned_no_results>]
          }}
        ]
        </findings>
        """,
        agent=agents[0]
    )
    
    task2 = Task(
        description=f"""
        # Vulnerability and Attack Vector Analysis

        ## Objective
        Analyze the Google Dorking results found by the searcher to identify potential security vulnerabilities or attack vectors.
        
        ## CRITICAL INSTRUCTIONS
        - ONLY analyze URLs that were ACTUALLY found by the searcher in Task 1.
        - DO NOT invent, fabricate, or hallucinate any vulnerabilities or findings.
        - If no URLs were found by the searcher, report that no vulnerabilities could be identified.
        - DO NOT use example data from this prompt as actual findings.
        - ALWAYS base your analysis SOLELY on real search results.
        
        ## Filtering Example Data
        - EXCLUDE any files with names containing words like "example", "sample", "demo", "dummy"
        - Do not report vulnerabilities based on example, training files
        - Be skeptical of data that looks too perfect or follows obvious patterns (e.g., sequential IDs, test@example.com)
        - For user data, verify it appears to be actual user information rather than placeholder content
        - If data contains elements like "example_value_based_audience_file" or similar indicators of non-production data, exclude it
        - Pay special attention to file metadata, headers, or comments that might indicate example status

        ## Analysis Categories
        1. Sensitive File Exposure:
           - Configuration files (.env, config.yml, web.config, .ini, .conf)
           - Source code-related files (.git, package.json, requirements.txt, .gitignore)
           - Directory listings (index of /)
           - Log files (*.log)
           - Backup files (*.bak, *.backup, *.old)
           - Database dump files (*.sql, *.dump)

        2. Sensitive Information Exposure:
           - API keys, access tokens, OAuth credentials
           - Hardcoded passwords, connection strings
           - Cloud credentials (AWS/Azure/GCP)
           - Encryption keys, private certificates
           - Session identifiers, cookie information
           - Personally identifiable information (PII) - emails, phone numbers, social security numbers, credit card info

        3. Potential Attack Vectors:
           - URL parameter manipulation points (inurl:action, inurl:page, inurl:pid, inurl:uid, inurl:id, inurl:search, etc.)
           - Parameters potentially vulnerable to SQL injection
           - Output points potentially vulnerable to XSS
           - URL/file handling parameters with SSRF potential
           - Potential file inclusion attack vectors (inurl:index.php?page, inurl:file, inurl:inc, etc.)
           - File upload/download endpoints (inurl:/upload.php, inurl:/uploads.jsp, inurl:/download.php, etc.)
           - File path parameters potentially vulnerable to path traversal attacks

        4. Authentication/Authorization Issues:
           - Exposed admin pages (inurl:admin, inurl:administrator, inurl:wp-login)
           - Insecure authentication mechanisms
           - Access control flaws (IDOR, etc.)
           - Open redirect vulnerabilities (inurl:url, inurl:continue, inurl:returnto, inurl:redirect, etc.)
           - Session management issues

        5. Infrastructure Information Exposure:
           - Cloud storage misconfigurations (S3 buckets, Azure Blob, etc.)
           - Internal IP addresses, hostnames
           - Development environment information
           - Service structure information
           - Internal collaboration tool links (Slack, Trello, Notion, Teams, etc.)
           - Restricted path information through robots.txt
           - Server version, operating system information

        ## Severity Assessment Criteria
        - Critical: Direct system access or sensitive data exposure (credentials, tokens, PII)
        - High: Access to important functions/data (source code, configuration files, internal documents)
        - Medium: Vulnerabilities with limited impact (partial information disclosure, potential injection points)
        - Low: Information exposure without a direct attack vector

        ## For Each Finding, Analyze:
        1. Vulnerability type
        2. Location (URL)
        3. Severity (Critical, High, Medium, Low)
        4. Vulnerability description
        5. Potential impact
        6. Attack vector (PoC or verification method)
        """,
        expected_output=f"""
        <findings>
        [
          {{
            "domain": "{target_domain}",
            "total_urls_analyzed": <number_of_urls_analyzed>,
            "total_vulnerabilities": <number_of_vulnerabilities_found>,
            "total_excluded": <number_of_urls_excluded>,
            "vulnerabilities": [
              // Only include if actual vulnerabilities were found based on real results
              {{
                "type": "<vulnerability_type>",
                "subtype": "<vulnerability_subtype>",
                "url": "<actual_url_from_search_results>",
                "severity": "<severity_level>",
                "description": "<description_of_actual_vulnerability>",
                "impact": "<potential_impact>",
                "evidence": "<actual_evidence_from_page>",
                "exploit_vector": "<how_the_vulnerability_could_be_exploited>",
                "remediation": "<recommended_fix>"
              }}
              // Additional vulnerabilities if found
            ],
            "excluded_urls": [
              // Only include if URLs were excluded
              {{
                "url": "<excluded_url>",
                "reason": "<reason_for_exclusion>"
              }}
              // Additional excluded URLs
            ]
          }}
        ]
        </findings>
        """,
        agent=agents[1],
    )

    task3 = Task(
        description=f"""
        # Enhanced Security Assessment Report Creation

        ## Objective
        Create a comprehensive security assessment report for {target_domain} that provides actionable intelligence for attack vector exploitation and information disclosure remediation.

        ## CRITICAL INSTRUCTIONS
        - ONLY include vulnerabilities and findings that were ACTUALLY identified by the bug hunter in Task 2.
        - NEVER fabricate or hallucinate any vulnerabilities, findings, or evidence.
        - If the bug hunter found no vulnerabilities, state clearly that no vulnerabilities were found.
        - Use ONLY real data from the previous tasks - do not use any example data from this prompt.
        - Focus on providing actionable intelligence for manual security testing.

        ## Enhanced Report Structure

        ### 1. Executive Summary
        - Target scope and methodology
        - Total findings count and risk distribution
        - Key attack vectors discovered
        - Information disclosure summary
        - Overall risk rating and business impact

        ### 2. Attack Vector Analysis
        - Categorize findings by attack vector type (XSS, SQLi, SSRF, LFI, Open Redirect, etc.)
        - Provide manual testing recommendations for each vector
        - Include tool suggestions (Burp Suite, SQLMap, XSStrike, etc.)
        - Rate exploitability (Easy, Medium, Hard)

        ### 3. Information Disclosure Assessment
        - Categorize by data sensitivity (Credentials, PII, Source Code, Configs, etc.)
        - Assess business and compliance impact (GDPR, HIPAA, PCI-DSS)
        - Provide immediate remediation steps
        - Rate exposure risk and accessibility

        ### 4. Technical Findings
        - Detailed vulnerability descriptions with evidence
        - Proof of concept guidance for manual testing
        - Reproduction steps where applicable
        - Impact analysis and exploitation scenarios

        ### 5. Risk Prioritization Matrix
        - Rank findings by exploitability vs impact
        - Recommend testing order for security researchers
        - Highlight quick wins and critical exposures

        ### 6. Next Steps & Recommendations
        - Manual testing recommendations for each finding
        - Suggested tools and techniques
        - Timeline for validation and remediation
        - Additional reconnaissance suggestions

        ## Formatting Requirements
        - Use clear section headers and professional formatting
        - Include severity icons: ?뵶 Critical, ?윝 High, ?윞 Medium, ?뵷 Low, ?뱄툘 Info
        - Assign unique IDs: AV-001 (Attack Vector), ID-001 (Information Disclosure)
        - Use tables for risk matrices and summaries
        - Include actionable commands and URLs where relevant

        ## Focus Areas
        - Provide specific manual testing guidance
        - Emphasize actionable intelligence over generic descriptions
        - Include business context and real-world impact
        - Suggest verification methods and tools
        """,
        expected_output=f"""
        # Security Assessment Report for {target_domain}
        
        *Generated by DorkAgent - Attack Vector & Information Disclosure Analysis*
        
        ---

        ## 1. Executive Summary

        **Target Scope**: {target_domain}
        
        **Risk Distribution:**
        -  Critical: <critical_count> findings
        -  High: <high_count> findings  
        -  Medium: <medium_count> findings
        -  Low: <low_count> findings
        -  Informational: <info_count> findings

        **Key Attack Vectors Discovered:**
        - <primary_attack_vector_1>
        - <primary_attack_vector_2>
        - <primary_attack_vector_3>

        **Information Disclosure Summary:**
        - <information_disclosure_type_1>: <count> instances
        - <information_disclosure_type_2>: <count> instances

        **Overall Risk Rating**: <overall_risk_level>

        ---

        ## 2. Attack Vector Analysis

        <If no attack vectors found: "No exploitable attack vectors were identified during this assessment.">

        ### Parameter Injection Opportunities
        
        #### AV-001: <Attack Vector Type> - <URL>
        - **Vector Type**: <XSS/SQLi/SSRF/LFI/etc>
        - **Parameter**: <parameter_name> (<GET/POST> parameter)
        - **Evidence**: <actual_error_message_or_response>
        - **Test Payload**: <specific_payload_used>
        - **Exploitability**: <Easy/Medium/Hard>
        - **Manual Testing**: 
          - Tool: <recommended_tool>
          - Command: `<specific_command_or_payload>`
        - **Business Impact**: <actual_business_impact>

        ### Administrative Interface Exposure

        #### AV-002: <Admin Panel Type> - <URL>
        - **Interface Type**: <admin_panel_description>
        - **Authentication**: <authentication_status>
        - **Page Title**: <actual_page_title>
        - **Login Fields**: <username_field>, <password_field>
        - **Testing Approach**: <specific_manual_testing_steps>

        ---

        ## 3. Information Disclosure Assessment

        <If no information disclosure found: "No sensitive information exposure was identified.">

        ### Sensitive Data Exposure

        #### ID-001: <Data Type> Exposure - <URL>
        - **Information Found**: <specific_information_description>
        - **Specific Data Exposed**:
          - <data_item_1>: <actual_value_1>
          - <data_item_2>: <actual_value_2>
          - <data_item_3>: <actual_value_3>
        - **Content Preview**: `<sample_content_from_file>`
        - **Sensitivity Level**: <critical/high/medium/low>
        - **File Location**: <file_path_or_directory>
        - **Accessibility**: <publicly_accessible/authentication_required>
        - **Compliance Risk**: <gdpr/hipaa/pci_specific_risk>
        - **Immediate Action**: <specific_remediation_step>

        ### Configuration & Source Code Leakage

        #### ID-002: <File Type> - <URL>
        - **File Type**: <configuration_file/source_code/backup/etc>
        - **Information Found**: <specific_information_in_file>
        - **Sensitive Content**:
          - API Keys: <api_key_count> found
          - Database Info: <database_details>
          - Internal IPs: <ip_addresses>
          - Credentials: <credential_details>
        - **Content Sample**: 
          ```
          <actual_code_or_config_snippet>
          ```
        - **Risk Level**: <critical/high/medium/low>
        - **File Size**: <file_size>
        - **Last Modified**: <modification_date>
        - **Remediation**: <specific_fix_action>

        ---

        ## 4. Risk Prioritization Matrix

        | Finding ID | Type | Severity | Exploitability | Business Impact | Priority |
        |------------|------|----------|----------------|-----------------|----------|
        | AV-001 | <type> |  Critical | Easy | High | 1 |
        | ID-001 | <type> |  High | N/A | Medium | 2 |

        ---

        ## 5. Manual Testing Recommendations

        ### Immediate Actions
        1. **<Finding_ID>**: <specific_manual_test>
        2. **<Finding_ID>**: <specific_manual_test>

        ### Testing Tools & Commands
        ```bash
        # For SQL Injection testing
        sqlmap -u "<url_with_parameter>" --dbs

        # For XSS testing  
        xsstrike -u "<url_with_parameter>"

        # For directory brute-forcing
        ffuf -u "<url>/FUZZ" -w /path/to/wordlist
        ```

        ### Burp Suite Extensions
        - <recommended_extension_1> for <vulnerability_type>
        - <recommended_extension_2> for <attack_vector>

        ---

        ## 6. Next Steps & Timeline

        ### Week 1: Critical & High Priority
        - [ ] Validate AV-001: <specific_test>
        - [ ] Secure ID-001: <remediation_action>

        ### Week 2: Medium Priority  
        - [ ] Test remaining parameter injection points
        - [ ] Review exposed configuration files

        ### Ongoing Monitoring
        - Implement monitoring for new exposed endpoints
        - Regular Google Dorking assessments
        - Directory listing prevention validation

        ---

        ## 7. Additional Reconnaissance Suggestions

        ### Subdomain Enumeration
        ```bash
        sublist3r -d {target_domain}
        amass enum -d {target_domain}
        ```

        ### Technology Stack Analysis
        - Wappalyzer analysis of discovered endpoints
        - Version detection on exposed services
        - Framework-specific vulnerability research

        ---

        *This report provides reconnaissance intelligence for authorized security testing only.*
        """,
        agent=agents[2],
    )
    return [task1, task2, task3]

# Override select_llm with env-validated constructor
def select_llm():
    while True:
        print("\n")
        print("1. GPT-4o Mini")
        print("2. Claude 3.5 Haiku")
        print("3. Gemini 2.0 Flash")
        print("\n")

        choice = input("[?] Choose LLM for Agents (1 - 3): ").strip()

        if choice == "1":
            llm_type = "openai"
            ensure_api_keys(llm_type)
            llm = ChatOpenAI(
                model_name="gpt-4o-mini-2024-07-18",
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY"),
            )
            return llm, llm_type
        elif choice == "2":
            llm_type = "anthropic"
            ensure_api_keys(llm_type)
            llm = LLM(
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                model='anthropic/claude-3-5-haiku-20241022',
            )
            return llm, llm_type
        elif choice == "3":
            llm_type = "gemini"
            ensure_api_keys(llm_type)
            llm = LLM(
                api_key=os.getenv('GEMINI_API_KEY'),
                model='gemini/gemini-2.0-flash',
            )
            return llm, llm_type
        else:
            print("Invalid choice. Please enter 1 - 3.")

if __name__ == "__main__":

    # Display banner
    clear_terminal()
    display_banner()

    # Select LLM
    llm, llm_type = select_llm()

    # API KEY verification
    load_dotenv()
    verify_api_key(llm_type)

    # Get domain(s)
    clear_terminal()
    display_banner()
    domains = get_target_domains()

    # Select depth
    clear_terminal()
    display_banner()
    depth = select_depth()
    target_domains = adjust_depth(domains, depth)

    # Integrate notify
    clear_terminal()
    display_banner() 
    notify = integrate_notify()

    # Default search results per query
    n_results = 10

    agent_list = agents(llm)

    # Diagnostic: show configured results per query for Serper tool
    try:
        configured_n = None
        from crewai_tools import SerperDevTool as _Serp
        for _a in agent_list:
            for _t in getattr(_a, 'tools', []) or []:
                if isinstance(_t, _Serp):
                    configured_n = getattr(_t, 'n_results', None) or getattr(_t, 'num_results', None) or getattr(_t, 'num', None)
                    break
            if configured_n is not None:
                break
        if configured_n is not None:
            print(f"[i] Serper search results per query configured to: {configured_n}")
    except Exception:
        pass

    # Make directory for logging
    date = datetime.now().strftime("%y%m%d")
    LOG_DIR = os.path.join("./log", date)
    os.makedirs(LOG_DIR, exist_ok=True)

    for i, domain in enumerate(domains):
        target_domain = target_domains[i]
        original_domain = target_domain 
        
        if '*' in target_domain:
            domain_parts = target_domain.split('.')
            base_domain = domain_parts[1]  
        else:
            domain = target_domain.split('.', maxsplit=target_domain.count('.'))[-1]
            base_domain = target_domain
        
        safe_domain = sanitize_filename(base_domain)
        
        tasks = task(original_domain, domain, agent_list)

        crew = Crew(
            agents=agent_list,  
            tasks=tasks, 
            verbose=1,
            max_rpm=15, # use 15, if you're using gemini free plan
            output_log_file=True,
        )

        print(f"Dorking on {original_domain}...")

        try:
            result = crew.kickoff()
        except LLMContextLengthExceededError as e:
            print("[!] Context window exceeded. Reducing search results and retrying...")
            # Reduce n_results and rebuild agents/crew once
            n_results = max(10, n_results // 2)
            agent_list = agents(llm)
            crew = Crew(agents=agent_list, tasks=tasks, verbose=1, max_rpm=15, output_log_file=True)
            try:
                result = crew.kickoff()
            except LLMContextLengthExceededError:
                print("[!] Still too large. Falling back to 15 results and retrying once more...")
                n_results = 15
                agent_list = agents(llm)
                crew = Crew(agents=agent_list, tasks=tasks, verbose=1, max_rpm=15, output_log_file=True)
                result = crew.kickoff()

        time_stamp = datetime.now().strftime("%H%M%S")
        report = os.path.join(f"log/{date}", f"{date}_{time_stamp}_{safe_domain}.md")
        
        with open(report, "w", encoding="utf-8") as f:
            f.write(str(result))

        if notify.lower() in ["y"]: 
            try: 
                cmd = f'notify -bulk -p telegram -i "{report}"' 
                os.system(cmd) 
                print(f"Report sent successfully via notify!") 
            except Exception as e: 
                print(f"Error sending report via notify: {str(e)}")

