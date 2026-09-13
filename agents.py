from crewai import Agent
from crewai_tools import SerperDevTool, SerpApiGoogleSearchTool, SerplyWebSearchTool, ScrapeWebsiteTool, FileWriterTool

def agents(llm, search_engine: str = "serper") -> list:
    """Create and configure CrewAI agents."""

    if search_engine == "serpapi":
        search_tool = SerpApiGoogleSearchTool()
    elif search_engine == "serply":
        search_tool = SerplyWebSearchTool()
    else:
        search_tool = SerperDevTool()

    searcher = Agent(
        role="searcher",
        goal="Performing advanced Google searches using Google Dorks",
        backstory="An expert in Google Dorking techniques for information gathering",
        verbose=True,
        tools=[search_tool],
        llm=llm,
    )

    bughunter = Agent(
        role="bughunter",
        goal="Identifying attack surfaces and vulnerabilities in target domains",
        backstory="A skilled penetration tester specializing in web security and vulnerability assessments",
        verbose=True,
        tools=[ScrapeWebsiteTool()],
        llm=llm,
    )

    writer = Agent(
        role="writer",
        goal="Generating well-structured and detailed reports based on findings",
        backstory="A technical writer specializing in cybersecurity documentation and structured reporting",
        verbose=True,
        tools=[FileWriterTool()],
        llm=llm,
        inject_date=True,
    )

    return [searcher, bughunter, writer]