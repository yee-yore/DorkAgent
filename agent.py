from crewai import Agent
from crewai_tools import SerperDevTool, ScrapeWebsiteTool

def initialize_agents(llm):
    if isinstance(llm, tuple) and len(llm) == 2:
        gpt4o_mini, claude_haiku = llm
    else:
        gpt4o_mini = claude_haiku = llm

    searcher = Agent(
        role="searcher",
        goal="Performing advanced Google searches using Google Dorks",
        backstory="An expert in Google Dorking techniques for information gathering",
        verbose=False,
        allow_delegation=False,
        tools=[SerperDevTool()],
        llm=gpt4o_mini,
        max_rpm=50, # for avoiding Anthropic's rate limit
        max_retry_limit=5,
    )

    bughunter = Agent(
        role="bughunter",
        goal="Identifying attack surfaces and vulnerabilities in target domains",
        backstory="A skilled penetration tester specializing in web security and vulnerability assessments",
        verbose=False,
        allow_delegation=False,
        llm=claude_haiku,
        max_rpm=50,
        max_retry_limit=5, 
    )

    writer = Agent(
        role="writer",
        goal="Generating well-structured and detailed reports based on findings",
        backstory="A technical writer specializing in cybersecurity documentation and structured reporting",
        verbose=True,
        allow_delegation=False,
        llm=gpt4o_mini,
        max_rpm=50,
        max_retry_limit=5,  
    )

    return {"searcher": searcher, "bughunter": bughunter, "writer": writer}